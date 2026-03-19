from datetime import timedelta
from django.utils import timezone
from .models import WeeklyPlan, RecipeIngredient


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
