from .serializers import UserProfileSerializer
from .ai_service import generate_and_save_meal
from rest_framework import generics
from rest_framework.permissions import AllowAny
from .serializers import RegisterSerializer
from core.models import CustomUser, DailyPlan
from django.shortcuts import get_object_or_404
from .models import GroceryCart, GroceryCartItem
from .serializers import GroceryCartSerializer, GroceryCartItemSerializer
from .ai_service import substitute_ingredient_in_meal
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from .models import DailyPlan, MealSlot
from .bmi_calculator import calculate_bmi, bmi_category
from .bmi_calculator import calculate_bmr, calculate_tdee, calculate_target_calories
from datetime import date
from .models import UserProfile
from django.utils import timezone
from .services import calculate_weekly_progress
from rest_framework.views import APIView
from rest_framework import serializers
from drf_spectacular.utils import extend_schema, inline_serializer, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
import socket
from django.conf import settings
from django.db.models import Avg
from .models import DietitianReview
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from rest_framework.parsers import MultiPartParser, FormParser
import cloudinary.uploader
from rest_framework.decorators import api_view, permission_classes, parser_classes
from allauth.socialaccount.providers.google.views import GoogleOAuth2Adapter
from allauth.socialaccount.providers.oauth2.client import OAuth2Client
from dj_rest_auth.registration.views import SocialLoginView
from django.utils import timezone
from .permissions import IsDietitian
from drf_spectacular.utils import extend_schema
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .models import ConsultationRequest, ChatMessage
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework import status
from rest_framework import viewsets
from .models import Appointment
from .serializers import AppointmentSerializer
from .services import get_dietitian_profile_stats
from .services import get_active_clients_list
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes
from .services import get_dietitian_notifications
from rest_framework import status
from rest_framework import viewsets, permissions
from .models import DietitianReview
from .serializers import DietitianReviewSerializer
from .services import create_dietitian_review
from .services import get_dietitian_public_profile


class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()

        # Update the profile created by signals with the onboarding data
        profile = user.profile
        data = request.data

        profile.date_of_birth = data.get('date_of_birth', profile.date_of_birth)
        profile.gender = data.get('gender', profile.gender)
        profile.height = data.get('height', profile.height)
        profile.weight = data.get('weight', profile.weight)
        profile.role = data.get('role', 'PATIENT')
        profile.save()

        refresh = RefreshToken.for_user(user)

        return Response({
            "message": "Account created successfully!",
            "role": profile.role,
            "refresh": str(refresh),
            "access": str(refresh.access_token),
            "is_new_user": True
        }, status=status.HTTP_201_CREATED)
@extend_schema(
    summary="Request AI Meal Recipe",
    parameters=[
        OpenApiParameter("type", OpenApiTypes.STR,
                         description="Meal type: breakfast, lunch, or dinner. Defaults to lunch.")
    ],
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_recipe(request):
    user_profile = request.user.profile
    meal_type = request.query_params.get('type', 'lunch')

    try:
        # We give the AI a window to answer.
        # If it takes too long, the 504 error tells the Kotlin app to show a "Retry" button.
        recipe_data = generate_and_save_meal(user_profile, meal_type=meal_type)
        return Response(recipe_data, status=200)

    except socket.timeout:
        return Response({"error": "AI is taking a bit long. Please try again in a moment!"}, status=504)
    except Exception as e:
        return Response({"error": "AI Chef is currently busy. Try again!"}, status=500)

# 1. READ (GET)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_grocery_cart(request):
    """Fetches the user's current cart and all items inside it"""
    cart, created = GroceryCart.objects.get_or_create(user=request.user)
    serializer = GroceryCartSerializer(cart)
    return Response(serializer.data)


# 2. CREATE (POST)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_cart_item(request):
    """Adds a new item (either an Ingredient ID or a custom text name)"""
    cart, created = GroceryCart.objects.get_or_create(user=request.user)

    serializer = GroceryCartItemSerializer(data=request.data)
    if serializer.is_valid():
        # Save it and specifically link it to THIS user's cart
        serializer.save(cart=cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 3. UPDATE (PATCH)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_cart_item(request, item_id):
    """Updates quantity or ticks the 'is_purchased' checkbox"""
    cart = get_object_or_404(GroceryCart, user=request.user)
    item = get_object_or_404(GroceryCartItem, id=item_id, cart=cart)

    # partial=True means the frontend can send JUST the checkbox state, or JUST the quantity
    serializer = GroceryCartItemSerializer(item, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 4. DELETE (DELETE)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_cart_item(request, item_id):
    """Removes an item completely from the cart"""
    cart = get_object_or_404(GroceryCart, user=request.user)
    item = get_object_or_404(GroceryCartItem, id=item_id, cart=cart)
    item.delete()
    return Response({"message": "Item deleted successfully"}, status=status.HTTP_204_NO_CONTENT)

@extend_schema(
    summary="Substitute an Ingredient",
    request=inline_serializer(name='SubRequest', fields={'ingredient_to_replace': serializers.CharField()}),
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_substitution(request, meal_slot_id):
    # The frontend will send the name of the ingredient they want to remove
    old_ingredient = request.data.get('ingredient_to_replace')

    if not old_ingredient:
        return Response({"error": "Please provide 'ingredient_to_replace' in the JSON body."}, status=400)

    result = substitute_ingredient_in_meal(request.user, meal_slot_id, old_ingredient)

    if result.get("status") == "success":
        return Response(result, status=200)
    else:
        return Response(result, status=400)

# Loging out a user
@extend_schema(
    summary="User Logout",
    request=inline_serializer(name='LogoutRequest', fields={'refresh_token': serializers.CharField()}),
    responses={205: inline_serializer(name='LogoutResponse', fields={'message': serializers.CharField()})}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_user(request):
    try:
        # The frontend sends {"refresh_token": "eyJh..."}
        refresh_token = request.data.get("refresh_token")

        if not refresh_token:
            return Response(
                {"error": "Refresh token is required to log out."},
                status=400
            )

        # Blacklist the token so it can never be used again
        token = RefreshToken(refresh_token)
        token.blacklist()

        return Response(
            {"status": "success", "message": "Successfully logged out."},
            status=205  # 205 means "Reset Content" (perfect for logouts)
        )

    except Exception as e:
        # If the token is fake or already blacklisted, we just return a 400
        return Response({"error": "Invalid token or token already logged out."}, status=400)


#  THE HOME DASHBOARD
@extend_schema(
    summary="Get Main Dashboard Today",
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dashboard_data(request):
    user_profile = request.user.profile
    today = timezone.now().date()
    today_name = today.strftime('%A')

    # The Weekly Balance array for the Bar Chart (Mon-Sun)
    #dummy data for the front end to build the UI
    weekly_balance = [50, 80, 100, 40, 0, 0, 0]

    try:
        # Look up the active plan using the date ranges AND the day name
        daily_plan = DailyPlan.objects.get(
            week_plan__user=user_profile,
            week_plan__start_date__lte=today,
            week_plan__end_date__gte=today,
            day_name=today_name
        )
        all_meals_today = daily_plan.meals.all()

        # Add up calories from meals they actually pressed "I ate this" on
        consumed_calories = sum(slot.recipe.calories for slot in all_meals_today if slot.is_consumed)

        # Find the next meal they haven't eaten yet
        next_meal_slot = all_meals_today.filter(is_consumed=False).first()
        next_meal_data = None
        if next_meal_slot:
            next_meal_data = {
                "id": next_meal_slot.id,
                "title": next_meal_slot.recipe.title,
                "image_url": getattr(next_meal_slot.recipe, 'image_url',
                                     "https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg"),
                "is_consumed": next_meal_slot.is_consumed
            }

        return Response({
            "target_calories": user_profile.target_calories,
            "consumed_calories": consumed_calories,
            "macros": {"carbs_eaten": 120, "carbs_target": 250, "protein_eaten": 85, "protein_target": 160,
                       "fat_eaten": 42, "fat_target": 70},
            "next_meal": next_meal_data,
            "water_consumed_l": daily_plan.water_consumed_ml / 1000.0,
            "water_target_l": daily_plan.target_water_ml / 1000.0,
            "streak_days": user_profile.current_streak,
            "weekly_balance_array": weekly_balance
        })

    except DailyPlan.DoesNotExist:
        # If they haven't generated a plan yet, send them a clean zeroed-out dashboard!
        return Response({
            "target_calories": user_profile.target_calories,
            "consumed_calories": 0,
            "macros": {"carbs_eaten": 0, "carbs_target": 250, "protein_eaten": 0, "protein_target": 160, "fat_eaten": 0,
                       "fat_target": 70},
            "next_meal": None,
            "water_consumed_l": 0.0,
            "water_target_l": 2.5,
            "streak_days": user_profile.current_streak,
            "weekly_balance_array": weekly_balance
        })

@extend_schema(
    summary="Get Profile Stats (BMI)",
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_profile_data(request):
    profile = request.user.profile

    bmi = 0.0
    category = "Unknown"

    if profile.height and profile.weight:
        # 1. Convert centimeters to meters for the bmi function
        height_in_meters = profile.height / 100.0

        # 2. Use the bmi function to calculate the exact BMI
        raw_bmi = calculate_bmi(profile.weight, height_in_meters)

        # 3. Round it to 1 decimal place so it looks clean on the mobile screen
        bmi = round(raw_bmi, 1)

        # 4. Use the bmi category function to label it (Underweight, Normal, etc.)
        category = bmi_category(raw_bmi)

    return Response({
        "user_id": request.user.id,
        "full_name": request.user.get_full_name() or request.user.username,
        "profile_picture_url": None,
        "streak_days": profile.current_streak,
        "bmi": bmi,
        "bmi_category": category
    })

@extend_schema(
    summary="Lock in Calorie Targets",
    request=inline_serializer(name='CalorieRequest', fields={
        'activity_level': serializers.CharField(),
        'goal_intensity': serializers.CharField()
    }),
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def calculate_and_save_calories(request):
    profile: UserProfile = request.user.profile

    # 1. Grab the user's choices from the mobile app's JSON request
    # If they don't send anything, we default to whatever is already saved in their profile
    activity = request.data.get('activity_level', profile.activity_level or 'sedentary')
    goal = request.data.get('goal_intensity', profile.primary_goal or 'maintain')

    # 2. Validate that we have the physical data needed for the math
    if not all([profile.weight, profile.height, profile.gender, profile.date_of_birth]):
        return Response({"error": "Missing weight, height, gender, or DOB. Please update profile first."}, status=400)

    # 3. Calculate their exact age from their Date of Birth
    today = date.today()
    dob = profile.date_of_birth
    age = today.year - dob.year - ((today.month, today.day) < (dob.month, dob.day))

    # 4. Run the medical math!
    bmr = calculate_bmr(profile.weight, profile.height, age, profile.gender)
    tdee = calculate_tdee(bmr, activity)
    daily_limit = calculate_target_calories(tdee, goal, profile.gender)

    # 5. Save the results to the database
    profile.activity_level = activity
    profile.primary_goal = goal
    profile.target_calories = daily_limit
    profile.save()

    return Response({
        "status": "success",
        "message": "Calorie targets locked in!",
        "metrics": {
            "age": age,
            "bmr": round(bmr),
            "tdee": round(tdee),          # How much they burn existing
            "target_calories": daily_limit # Their new daily goal
        }
    })


# Water tracker
@extend_schema(
    summary="Track Water Intake",
    description="Send the amount of water drank in milliliters. Defaults to 250ml.",
    request=inline_serializer(
        name='WaterRequest',
        fields={
            'amount_ml': serializers.IntegerField(default=250)
        }
    ),
    responses={
        200: inline_serializer(
            name='WaterResponse',
            fields={
                'status': serializers.CharField(),
                'message': serializers.CharField(),
                'total_water_ml': serializers.IntegerField(),
            }
        )
    }
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def track_water(request):
    profile = request.user.profile
    today = timezone.now().date()
    today_name = today.strftime('%A')  # Figures out if it's "Monday", "Tuesday", etc.

    # The app can send how much they drank, but defaults to a 250ml glass if empty
    amount_ml = request.data.get('amount_ml', 250)

    try:
        # Look for the daily plan that matches today's day of the week inside their active weekly plan
        daily_plan = DailyPlan.objects.get(
            week_plan__user=profile,
            week_plan__start_date__lte=today,
            week_plan__end_date__gte=today,
            day_name=today_name
        )

        daily_plan.water_consumed_ml += int(amount_ml)
        daily_plan.save()

        return Response({
            "status": "success",
            "message": f"Added {amount_ml}ml of water!",
            "total_water_ml": daily_plan.water_consumed_ml
        })

    except DailyPlan.DoesNotExist:
        return Response({"error": "No active meal plan found for today. Generate a weekly plan first!"}, status=400)


# meal tracker
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def track_meal(request, meal_slot_id):
    try:
        # The long query ensures a user can't accidentally check off someone else's meal!
        meal_slot = MealSlot.objects.get(
            id=meal_slot_id,
            day_plan__week_plan__user=request.user.profile
        )

        meal_slot.is_consumed = True
        meal_slot.save()

        return Response({
            "status": "success",
            "message": f"Successfully logged {meal_slot.get_meal_type_display()} as eaten!"
        })

    except MealSlot.DoesNotExist:
        return Response({"error": "Meal slot not found."}, status=404)

@extend_schema(
    summary="Get Weekly Progress Stats",
    parameters=[OpenApiParameter("timeframe", OpenApiTypes.STR, description="e.g., 'this_week'")],
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_progress_stats(request):
    profile = request.user.profile
    timeframe = request.query_params.get('timeframe', 'this_week')

    # 1. Ask the 'Brain' to do the math
    progress_data = calculate_weekly_progress(profile, timeframe)

    # 2. Return the HTTP Response
    return Response(progress_data)


@api_view(['PATCH', 'POST'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    profile = request.user.profile
    data = request.data

    # (Using .get() safely keeps the old data if the app forgets to send it)
    profile.date_of_birth = data.get('date_of_birth', profile.date_of_birth)
    profile.gender = data.get('gender', profile.gender)


    if hasattr(profile, 'country'):
        profile.country = data.get('country', profile.country)

        # The physical stats
    profile.height = data.get('height', profile.height)
    profile.weight = data.get('weight', profile.weight)
    profile.target_weight = data.get('target_weight', profile.target_weight)
    profile.target_calories = data.get('target_calories', profile.target_calories)

    # -Preferences and Tags
    if 'dietary_preference' in data:
        profile.dietary_preference = data['dietary_preference']
    if 'allergies' in data:
        profile.allergies = data['allergies']
    if 'medical_conditions' in data:
        profile.medical_conditions = data['medical_conditions']

    profile.save()

    return Response({
        "status": "success",
        "message": "Profile and onboarding data saved successfully!",
        "current_data": {
            "weight": profile.weight,
            "height": profile.height,
            "date_of_birth": profile.date_of_birth,
            "gender": profile.gender
        }
    })
class UserProfileCRUDView(APIView):
    """
    Handles Create (handled by registration), Read, Update, and Delete
    for the logged-in user's profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        # READ
        profile = request.user.profile
        serializer = UserProfileSerializer(profile)
        return Response(serializer.data)

    def put(self, request):
        # UPDATE
        profile = request.user.profile
        serializer = UserProfileSerializer(profile, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                "message": "Profile updated successfully!",
                "data": serializer.data
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request):
        # DELETE
        # Deleting the user automatically deletes their profile due to models.CASCADE
        user = request.user
        user.delete()
        return Response(
            {"message": "User account and profile permanently deleted."},
            status=status.HTTP_204_NO_CONTENT
        )

@api_view(['GET'])
@permission_classes([AllowAny]) # Anyone can check if the server is up!
def health_check(request):
    return Response({
        "status": "online",
        "server_time": timezone.now(),
        "environment": "production" if not getattr(settings, 'DEBUG', False) else "development"
    })


# 1. SUBMIT A REVIEW
@extend_schema(
    summary="Submit a Dietitian Review",
    description="Rate a dietitian 1-5 stars after a video call.",
    request=inline_serializer(
        name='SubmitReviewRequest',
        fields={
            'rating': serializers.IntegerField(help_text="Number between 1 and 5"),
            'comment': serializers.CharField(required=False, help_text="Optional text review")
        }
    ),
    responses={201: OpenApiTypes.OBJECT}  # Safe schema!
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_review(request, dietitian_id):
    dietitian = get_object_or_404(CustomUser, id=dietitian_id)

    rating = request.data.get('rating')
    comment = request.data.get('comment', '')

    if not rating or not (1 <= int(rating) <= 5):
        return Response({"error": "Please provide a valid rating between 1 and 5."}, status=400)

    # Create the review
    review = DietitianReview.objects.create(
        dietitian=dietitian,
        patient=request.user,
        rating=int(rating),
        comment=comment
    )

    return Response({
        "status": "success",
        "message": "Thank you for your review!",
        "review_id": review.id
    }, status=201)


# 2. GET REVIEWS & AVERAGE RATING
@extend_schema(
    summary="Get Dietitian Reviews",
    description="Returns all reviews for a dietitian and their average rating.",
    responses={200: OpenApiTypes.OBJECT}
)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
@parser_classes([MultiPartParser, FormParser])  # This tells Django to expect a FILE, not JSON
def upload_profile_picture(request):
    # 1. Check if the Android app actually attached a file named 'image'
    if 'image' not in request.FILES:
        return Response({"error": "No image file provided. Make sure the form-data key is 'image'."}, status=400)

    file = request.FILES['image']

    try:
        # 2. Upload the file to a specific folder in your Cloudinary account
        upload_data = cloudinary.uploader.upload(file, folder="grist_profiles")

        # 3. Extract the permanent HTTPS URL Cloudinary generated
        image_url = upload_data['secure_url']

        # 4. Save it to your database!
        profile = request.user.profile
        profile.profile_picture = image_url
        profile.save()

        return Response({
            "status": "success",
            "message": "Profile picture updated successfully!",
            "profile_picture_url": image_url
        })

    except Exception as e:
        return Response({"error": f"Cloudinary upload failed: {str(e)}"}, status=500)


class GoogleLogin(SocialLoginView):
    adapter_class = GoogleOAuth2Adapter
    client_class = OAuth2Client
    callback_url = ''

@extend_schema(
    summary="Get Dietitian Dashboard Data",
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDietitian]) # SECURITY: Only Dietitians allowed!
def get_dietitian_dashboard(request):
    # 1. Get current time context
    now = timezone.now()
    today = now.date()
    current_time = now.time()

    dietitian_user = request.user
    dietitian_profile = request.user.dietician_profile

    # 2. "Pending Plans": Count pending ConsultationRequests
    pending_plans_count = ConsultationRequest.objects.filter(
        dietitian=dietitian_profile,
        status='pending'
    ).count()

    # 3. "Messages" Badge: Count messages sent by patients
    # (Excludes messages sent BY the dietitian so they only see inbound messages)
    unread_messages_count = ChatMessage.objects.filter(
        request__dietitian=dietitian_profile
    ).exclude(sender=dietitian_user).count()

    # 4. "Today's Clients" & "Next Patient"
    # We use a try/except block here. This ensures YOUR code works right now,
    # and automatically links up the moment Team Member 2 pushes their Appointment model!
    try:
        from .models import Appointment

        # Count how many appointments are scheduled for today
        todays_clients_count = Appointment.objects.filter(
            dietitian=dietitian_user,
            date=today,
            status='CONFIRMED'
        ).count()

        # Find the single closest appointment today that hasn't happened yet
        next_appointment = Appointment.objects.filter(
            dietitian=dietitian_user,
            date=today,
            time__gte=current_time,
            status='CONFIRMED'
        ).order_by('time').first()

        if next_appointment:
            next_patient_data = {
                "patient_name": next_appointment.patient.get_full_name() or next_appointment.patient.username,
                "time": next_appointment.time.strftime("%I:%M %p"),
                "appointment_type": getattr(next_appointment, 'appointment_type', 'Consultation'),
                "meeting_link": getattr(next_appointment, 'meeting_link', None)
            }
        else:
            next_patient_data = None

    except ImportError:
        # Fallback just in case Team Member 2 hasn't merged their code yet
        todays_clients_count = 0
        next_patient_data = None

    # 5. Package it all into a clean JSON response for the Android app
    return Response({
        "todays_clients_count": todays_clients_count,
        "pending_plans_count": pending_plans_count,
        "unread_messages_count": unread_messages_count,
        "next_patient": next_patient_data
    })


@extend_schema(
    summary="Get Dietitian Appointments List",
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDietitian])
def get_dietitian_appointments(request):
    today = timezone.now().date()
    dietitian_user = request.user

    try:
        from .models import Appointment

        # 1. Fetch Today's Appointments
        todays_apps = Appointment.objects.filter(
            dietitian=dietitian_user,
            date=today,
            status='CONFIRMED'
        ).order_by('time')

        # 2. Fetch Future Appointments
        future_apps = Appointment.objects.filter(
            dietitian=dietitian_user,
            date__gt=today,
            status='CONFIRMED'
        ).order_by('date', 'time')

        # Helper function to format the data
        def format_app(app):
            return {
                "id": app.id,
                "patient_name": app.patient.get_full_name() or app.patient.username,
                "patient_image": getattr(app.patient.profile, 'profile_picture', None),
                "time": app.time.strftime("%I:%M %p"),
                "date_display": app.date.strftime("%b %d")  # e.g., "Oct 15"
            }

        return Response({
            "today": [format_app(app) for app in todays_apps],
            "future": [format_app(app) for app in future_apps]
        })

    except ImportError:
        # Failsafe until Team Member 2 merges their code
        return Response({
            "today": [],
            "future": []
        })

class AppointmentViewSet(viewsets.ModelViewSet):
    serializer_class = AppointmentSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # SECURITY: If it's a dietitian, show their schedule. If a patient, show their bookings.
        user = self.request.user
        if hasattr(user, 'profile') and user.profile.role == 'DIETITIAN':
            return Appointment.objects.filter(dietitian=user).order_by('date', 'time')
        return Appointment.objects.filter(patient=user).order_by('date', 'time')

    def perform_create(self, serializer):
        # Auto-assign the logged-in user as the patient
        serializer.save(patient=self.request.user)

@extend_schema(
    summary="Get Dietitian Profile & Active Clients",
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDietitian])
def get_dietitian_profile_view(request):
    profile_data = get_dietitian_profile_stats(request.user)
    return Response(profile_data)


@extend_schema(
    summary="Get Dietitian Active Clients",
    description="Returns a list of clients. Use the ?search= query parameter to filter by name.",
    parameters=[
        OpenApiParameter("search", OpenApiTypes.STR, description="Search by client name", required=False)
    ],
    responses={200: OpenApiTypes.ANY}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDietitian])
def get_active_clients_view(request):
    # Grab the text from the search bar (if they typed anything)
    search_query = request.query_params.get('search', None)

    # Run our math/database service
    clients_data = get_active_clients_list(request.user, search_query)

    return Response(clients_data)

@extend_schema(
    summary="Get Dietitian System Notifications",
    description="Returns the one-way system alerts (appointments, questionnaires) for the dietitian.",
    responses={200: OpenApiTypes.ANY}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated, IsDietitian])
def get_system_notifications_view(request):
    notifications_data = get_dietitian_notifications(request.user)
    return Response(notifications_data)






# --- THE VIEWS ---
@extend_schema(
    summary="Submit Dietitian Review",
    description="Submit a dual-rating review with tags.",
    request=inline_serializer(name='SubmitReview', fields={
        'dietitian_id': serializers.IntegerField(),
        'dietitian_rating': serializers.IntegerField(),
        'call_quality_rating': serializers.IntegerField(),
        'tags': serializers.ListField(child=serializers.CharField(), required=False),
        'comment': serializers.CharField(required=False)
    }),
    responses={201: OpenApiTypes.OBJECT}
)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def submit_review_view(request):
    data = request.data
    try:
        review = create_dietitian_review(
            patient_user=request.user,
            dietitian_id=data.get('dietitian_id'),
            dietitian_rating=data.get('dietitian_rating', 5),
            call_quality_rating=data.get('call_quality_rating', 5),
            tags=data.get('tags', []),
            comment=data.get('comment', '')
        )
        return Response({"message": "Review submitted successfully!"}, status=status.HTTP_201_CREATED)
    except Exception as e:
        return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

@extend_schema(
    summary="Get Dietitian Reviews",
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_dietitian_reviews(request, dietitian_id):
    dietitian = get_object_or_404(CustomUser, id=dietitian_id)
    reviews = DietitianReview.objects.filter(dietitian=dietitian).order_by('-created_at')

    # Calculate average using the new dietitian_rating field
    avg_rating = reviews.aggregate(Avg('dietitian_rating'))['dietitian_rating__avg'] or 0.0

    return Response({
        "dietitian_name": dietitian.get_full_name() or dietitian.username,
        "total_reviews": reviews.count(),
        "average_rating": round(avg_rating, 1),
        "reviews": DietitianReviewSerializer(reviews, many=True).data
    })

@extend_schema(
    summary="Get Dietitian Profile (Patient View)",
    description="Fetches the dietitian's contact info, average rating, and recent reviews.",
    responses={200: OpenApiTypes.OBJECT}
)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def patient_view_dietitian_profile(request, dietitian_id):
    # 1. Ask the service for the data
    profile_data = get_dietitian_public_profile(dietitian_id)

    if not profile_data:
        return Response({"error": "Dietitian not found."}, status=404)

    # 2. Serialize the preview list of reviews
    serialized_reviews = DietitianReviewSerializer(profile_data['recent_reviews'], many=True).data
    profile_data['recent_reviews'] = serialized_reviews

    # 3. Send it to the Android app
    return Response(profile_data)