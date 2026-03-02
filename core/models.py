from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from pgvector.django import VectorField
from django.contrib.auth.models import User

# --- MODULE 1: USERS ---
class CustomUser(AbstractUser):
    is_dietician = models.BooleanField(default=False)
    profile_picture = models.URLField(blank=True, null=True)


class RegularUserProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, primary_key=True, related_name='regular_profile')
    birth_date = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=[('M', 'Male'), ('F', 'Female'), ('O', 'Other')])
    activity_level = models.CharField(max_length=20, choices=[('sedentary', 'Sedentary'), ('active', 'Active')])
    current_weight_kg = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    height_cm = models.DecimalField(max_digits=5, decimal_places=2, null=True)
    dietary_goal = models.CharField(max_length=50, default="Maintenance")


class DieticianProfile(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, primary_key=True,
                                related_name='dietician_profile')
    license_number = models.CharField(max_length=50)
    is_verified = models.BooleanField(default=False)
    bio = models.TextField(blank=True)


# --- MODULE 2: FOOD ENGINE (AI READY) ---
class Ingredient(models.Model):
    name = models.CharField(max_length=200, db_index=True)
    calories = models.IntegerField(help_text="Per 100g")
    protein = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    carbs = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    fats = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    price_lkr = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    is_local = models.BooleanField(default=False)
    embedding = VectorField(dimensions=768, null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({'Local' if self.is_local else 'Imported'})"


class Substitution(models.Model):
    western_item = models.ForeignKey(Ingredient, related_name='western_versions', on_delete=models.CASCADE)
    local_item = models.ForeignKey(Ingredient, related_name='local_versions', on_delete=models.CASCADE)
    match_score = models.IntegerField(default=80, help_text="0-100 similarity score")
    cost_saving_ratio = models.DecimalField(max_digits=5, decimal_places=2, null=True)


class Recipe(models.Model):
    title = models.CharField(max_length=200)
    calories = models.IntegerField()
    instructions = models.TextField()
    prep_time_mins = models.IntegerField(blank=True, null=True)
    image_url = models.URLField(blank=True)
    is_ai_generated = models.BooleanField(default=False)

    def __str__(self):
        return self.title


class RecipeIngredient(models.Model):
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity = models.FloatField()
    unit = models.CharField(max_length=50, default='g')


# --- MODULE 3: MEAL PLANS ---
class WeeklyPlan(models.Model):
    user = models.ForeignKey(RegularUserProfile, on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    total_cost_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)


class DailyPlan(models.Model):
    week_plan = models.ForeignKey(WeeklyPlan, related_name='days', on_delete=models.CASCADE)
    day_name = models.CharField(max_length=20)


class MealSlot(models.Model):
    day_plan = models.ForeignKey(DailyPlan, related_name='meals', on_delete=models.CASCADE)
    meal_type = models.CharField(max_length=20, choices=[('B', 'Breakfast'), ('L', 'Lunch'), ('D', 'Dinner')])
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)
    is_substituted = models.BooleanField(default=False)


# --- MODULE 4: EXTRAS ---
class ConsultationRequest(models.Model):
    user = models.ForeignKey(RegularUserProfile, on_delete=models.CASCADE)
    dietician = models.ForeignKey(DieticianProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)

class ShoppingList(models.Model):
    plan = models.OneToOneField(WeeklyPlan, on_delete=models.CASCADE, related_name='shopping_list')
    generated_at = models.DateTimeField(auto_now_add=True)

class ShoppingListItem(models.Model):
    shopping_list = models.ForeignKey(ShoppingList, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantity_needed = models.DecimalField(max_digits=6, decimal_places=2)
    is_purchased = models.BooleanField(default=False)

class ChatMessage(models.Model):
    request = models.ForeignKey(ConsultationRequest, on_delete=models.CASCADE, related_name='messages')
    sender = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

class PriceUpdate(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)  # Who reported the price
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    reported_at = models.DateTimeField(auto_now_add=True)


class UserProfile(models.Model):

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    # Demographics
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female')]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=100)
    def __str__(self):
        return f"{self.user.username}'s Profile"