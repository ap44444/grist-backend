from datetime import timedelta
from django.utils import timezone
from .models import WeeklyPlan


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
        weekly_plan = WeeklyPlan.objects.get(
            user=profile, start_date__lte=today, end_date__gte=today
        )

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