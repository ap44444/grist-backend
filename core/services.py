from datetime import timedelta
from django.utils import timezone
from .models import WeeklyPlan, RecipeIngredient
from django.db.models import Avg
from core.models import DietitianReview, CustomUser
from django.db.models import Q
from core.models import CustomUser
from django.utils import timezone
from .models import SystemNotification
from rest_framework.exceptions import ValidationError
from core.models import DietitianReview, CustomUser
from rest_framework.exceptions import ValidationError
from core.models import CustomUser, DietitianReview
from django.db.models import Avg
from .models import RecipeIngredient
from .models import DieticianProfile, Appointment, ChatMessage


def calculate_weekly_progress(profile, timeframe='this_week'):
    """Does all the math for the user's progress screen and returns a dictionary."""
    today = timezone.now().date()

    if timeframe == 'this_week':
        start_date = today - timedelta(days=today.weekday())
    else:
        start_date = today - timedelta(days=7)

    daily_calories = [0, 0, 0, 0, 0, 0, 0]
    consistency_grid = [False, False, False, False, False, False, False]
    total_calories = 0
    days_tracked = 0

    total_protein = 0.0
    total_carbs = 0.0
    total_fats = 0.0

    try:
        weekly_plan = WeeklyPlan.objects.get(user=profile.user, start_date__lte=today, end_date__gte=today)
        for i in range(7):
            target_date = start_date + timedelta(days=i)
            day_name = target_date.strftime('%A')

            daily_plan = weekly_plan.days.filter(day_name=day_name).first()
            if daily_plan:
                cals_today = sum(meal.recipe.calories for meal in daily_plan.meals.filter(is_consumed=True))
                daily_calories[i] = cals_today
                total_calories += cals_today

                if cals_today > 0:
                    days_tracked += 1
                if cals_today > 0 and abs(cals_today - profile.target_calories) <= 150:
                    consistency_grid[i] = True

                consumed_meals = daily_plan.meals.filter(is_consumed=True)
                for meal in consumed_meals:
                    for ri in RecipeIngredient.objects.filter(recipe=meal.recipe):
                        factor = ri.quantity / 100.0 if ri.unit.lower() in ['g', 'ml'] else 1.0
                        total_protein += float(ri.ingredient.protein) * factor
                        total_carbs += float(ri.ingredient.carbs) * factor
                        total_fats += float(ri.ingredient.fats) * factor

    except WeeklyPlan.DoesNotExist:
        pass

    avg_intake = round(total_calories / days_tracked) if days_tracked > 0 else 0
    consistency_percentage = round((sum(consistency_grid) / 7.0) * 100)

    total_macros = total_protein + total_carbs + total_fats
    if total_macros > 0:
        p_pct = int((total_protein / total_macros) * 100)
        c_pct = int((total_carbs / total_macros) * 100)
        f_pct = int((total_fats / total_macros) * 100)
    else:
        p_pct = c_pct = f_pct = 0

    return {
        "timeframe": timeframe,
        "avg_intake_kcal": avg_intake,
        "calorie_trends_array": daily_calories,
        "macronutrient_breakdown": {
            "protein_percent": p_pct,
            "fats_percent": f_pct,
            "carbs_percent": c_pct
        },
        "consistency": {"percentage": consistency_percentage, "daily_grid": consistency_grid}
    }
def get_daily_nutritional_summary(daily_plan):
    """Calculates total Protein, Carbs, and Fats for a specific day."""
    total_protein = 0
    total_carbs = 0
    total_fats = 0

    for slot in daily_plan.meals.all():
        # Look through all ingredients in each recipe of the day
        recipe_ingredients = RecipeIngredient.objects.filter(recipe=slot.recipe)
        for ri in recipe_ingredients:
            # Formula: (Ingredient Macro per 100g / 100) * Quantity in grams
            factor = ri.quantity / 100.0
            total_protein += float(ri.ingredient.protein) * factor
            total_carbs += float(ri.ingredient.carbs) * factor
            total_fats += float(ri.ingredient.fats) * factor

    return {
        "proteins": round(total_protein),
        "carbs": round(total_carbs),
        "fats": round(total_fats)
    }


def get_dietitian_profile_stats(user):
    """
    Service function to calculate all stats and aggregate data
    for the Dietitian Profile screen.
    """
    # 1. Grab their profiles
    dietitian_profile = getattr(user, 'dietician_profile', None)
    general_profile = getattr(user, 'profile', None)

    # 2. Calculate average rating and total reviews
    reviews = DietitianReview.objects.filter(dietitian=user)
    avg_rating = reviews.aggregate(Avg('dietitian_rating'))['dietitian_rating__avg'] or 0.0
    review_count = reviews.count()

    # 3. Find "Active Clients" (Patients who have confirmed appointments)
    try:
        from .models import Appointment
        active_patient_ids = Appointment.objects.filter(
            dietitian=user,
            status='CONFIRMED'
        ).values_list('patient_id', flat=True).distinct()

        active_clients = CustomUser.objects.filter(id__in=active_patient_ids)
    except ImportError:
        active_clients = []

    clients_data = [
        {"id": client.id, "name": client.get_full_name() or client.username}
        for client in active_clients
    ]

    # 4. Return the clean dictionary
    return {
        "full_name": f"Dr. {user.get_full_name() or user.username}",
        "profile_picture_url": getattr(general_profile, 'profile_picture', None),
        "rating": round(avg_rating, 1),
        "review_count": review_count,
        "basic_information": {
            "serial_number": getattr(dietitian_profile, 'license_number', 'N/A'),
            "email": user.email,
            "date_of_registry": user.date_joined.strftime("%b %d, %Y")
        },
        "active_clients": clients_data
    }


def get_active_clients_list(dietitian_user, search_query=None):
    """
    Fetches all active clients for a dietitian and applies an optional search filter.
    """
    try:
        from core.models import Appointment
        #  Get unique patient IDs who have a confirmed appointment
        active_patient_ids = Appointment.objects.filter(
            dietitian=dietitian_user,
            status='CONFIRMED'
        ).values_list('patient_id', flat=True).distinct()

        #  Grab those specific users from the database
        clients = CustomUser.objects.filter(id__in=active_patient_ids)

        # 3. Apply the search filter if the Android app sent one
        if search_query:
            clients = clients.filter(
                Q(first_name__icontains=search_query) |
                Q(last_name__icontains=search_query) |
                Q(username__icontains=search_query)
            )

        # Package the data for the UI
        clients_data = []
        for client in clients:
            general_profile = getattr(client, 'profile', None)
            clients_data.append({
                "id": client.id,
                "name": client.get_full_name() or client.username,
                "profile_picture_url": getattr(general_profile, 'profile_picture', None)
            })

        return clients_data

    except ImportError:
        # Failsafe if the Appointment model isn't merged yet
        return []


def get_dietitian_notifications(dietitian_user):
    """
    Fetches and formats system notifications for the one-way messaging UI.
    """
    notifications = SystemNotification.objects.filter(dietitian=dietitian_user).order_by('-created_at')

    today = timezone.now().date()
    formatted_data = []

    for notif in notifications:
        notif_date = notif.created_at.date()
        date_label = "TODAY" if notif_date == today else notif_date.strftime("%b %d, %Y")

        formatted_data.append({
            "id": notif.id,
            "alert_type": notif.alert_type,
            "message": notif.message,
            "time": notif.created_at.strftime("%I:%M %p"),  # e.g., "09:12 AM"
            "date_label": date_label,
            "is_read": notif.is_read,
            "patient_name": notif.patient.get_full_name() if notif.patient else None,
            "patient_id": notif.patient.id if notif.patient else None
        })

    return formatted_data


def create_dietitian_review(patient_user, dietitian_id, rating, comment=""):
    """
    Service to handle saving a patient's review of a dietitian.
    """
    # 1. Validate the rating
    try:
        rating = int(rating)
        if rating < 1 or rating > 5:
            raise ValidationError("Rating must be between 1 and 5 stars.")
    except (ValueError, TypeError):
        raise ValidationError("Invalid rating format.")

    # 2. Find the Dietitian
    dietitian = CustomUser.objects.filter(id=dietitian_id).first()
    if not dietitian:
        raise ValidationError("Dietitian not found.")

    # 3. Create or Update the review
    # (Using update_or_create means if they review again, it updates their old one instead of spamming)
    review, created = DietitianReview.objects.update_or_create(
        patient=patient_user,
        dietitian=dietitian,
        defaults={
            'rating': rating,
            'comment': comment
        }
    )

    return review

def create_dietitian_review(patient_user, dietitian_id, dietitian_rating, call_quality_rating, tags=None, comment=""):
    """
    Handles the business logic for creating or updating a dietitian review.
    """
    dietitian = CustomUser.objects.filter(id=dietitian_id).first()
    if not dietitian:
        raise ValidationError("Dietitian not found.")

    review, created = DietitianReview.objects.update_or_create(
        patient=patient_user,
        dietitian=dietitian,
        defaults={
            'dietitian_rating': int(dietitian_rating),
            'call_quality_rating': int(call_quality_rating),
            'tags': tags or [],
            'comment': comment
        }
    )
    return review


def get_dietitian_public_profile(dietitian_id):
    """
    Fetches the combined profile and review data for the Patient's view.
    """
    dietitian = CustomUser.objects.filter(id=dietitian_id).first()
    if not dietitian:
        return None

    # Grab all reviews for this dietitian, newest first
    reviews = DietitianReview.objects.filter(dietitian=dietitian).order_by('-created_at')

    # Calculate the average rating
    avg_rating = reviews.aggregate(Avg('dietitian_rating'))['dietitian_rating__avg'] or 0.0

    return {
        "id": dietitian.id,
        "full_name": dietitian.get_full_name() or dietitian.username,
        "profile_picture": getattr(dietitian.profile, 'profile_picture', None) if hasattr(dietitian,
                                                                                          'profile') else None,
        "email": dietitian.email,
        # Formats the date exactly like the Figma: "Jan 12, 2024"
        "date_of_registry": dietitian.date_joined.strftime("%b %d, %Y"),
        "average_rating": round(avg_rating, 1),
        "total_reviews": reviews.count(),
        # We grab the 5 most recent reviews for that preview list at the bottom
        "recent_reviews": reviews[:5]
    }


def update_user_streak(profile):
    """
    Checks the last active date and updates the streak accordingly.
    Call this whenever a user completes a 'streak-worthy' action (like logging a meal).
    """
    today = timezone.now().date()

    # If they already got their streak point for today, do nothing!
    if profile.last_active_date == today:
        return

    # If their last active date was exactly yesterday, the streak continues!
    elif profile.last_active_date == today - timedelta(days=1):
        profile.current_streak += 1

    # If they missed a day (or it's their very first time), reset to 1
    else:
        profile.current_streak = 1

    # Save today as their new last active date
    profile.last_active_date = today
    profile.save()

def get_dietitian_dashboard_stats(dietitian_user):
    """Calculates all statistics for the Dietitian Home Dashboard."""

    now = timezone.now()
    today = now.date()
    current_time = now.time()

    #  Profile Check
    dietitian_profile, _ = DieticianProfile.objects.get_or_create(user=dietitian_user)

    # Database Counts
    todays_clients_count = Appointment.objects.filter(
        dietitian=dietitian_user, date=today, status__in=['PENDING', 'CONFIRMED']
    ).count()

    pending_plans_count = Appointment.objects.filter(
        dietitian=dietitian_user, date=today, time__gte=current_time, status__in=['PENDING', 'CONFIRMED']
    ).count()

    unread_messages_count = ChatMessage.objects.filter(
        request__dietitian=dietitian_profile
    ).exclude(sender=dietitian_user).count()

    #  Next Patient Check
    next_appointment = Appointment.objects.filter(
        dietitian=dietitian_user, date=today, time__gte=current_time, status__in=['PENDING', 'CONFIRMED']
    ).order_by('time').first()

    next_patient_data = None
    if next_appointment:
        next_patient_data = {
            "patient_name": next_appointment.patient.username,
            "time": next_appointment.time.strftime("%I:%M %p"),
            "appointment_type": getattr(next_appointment, 'appointment_type', 'Consultation'),
            "meeting_link": getattr(next_appointment, 'meeting_link', None)
        }

    # Return the packaged dictionary
    return {
        "dietitian_name": dietitian_user.username,
        "todays_clients_count": todays_clients_count,
        "pending_plans_count": pending_plans_count,
        "unread_messages_count": unread_messages_count,
        "next_patient": next_patient_data
    }