from datetime import timedelta
from django.utils import timezone
from .models import WeeklyPlan, RecipeIngredient
from django.db.models import Avg
from core.models import DietitianReview, CustomUser
from django.db.models import Q
from core.models import CustomUser
from django.utils import timezone
from .models import SystemNotification

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

    except WeeklyPlan.DoesNotExist:
        pass

    avg_intake = round(total_calories / days_tracked) if days_tracked > 0 else 0
    consistency_percentage = round((sum(consistency_grid) / 7.0) * 100)

    return {
        "timeframe": timeframe,
        "avg_intake_kcal": avg_intake,
        "calorie_trends_array": daily_calories,
        "macronutrient_breakdown": {"protein_percent": 30, "fats_percent": 25, "carbs_percent": 45},
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
    avg_rating = reviews.aggregate(Avg('rating'))['rating__avg'] or 0.0
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