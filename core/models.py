from cloudinary.models import CloudinaryField
from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator
from pgvector.django import VectorField
from django.db.models.signals import post_save
from django.dispatch import receiver

# --- MODULE 1: USERS ---
class CustomUser(AbstractUser):
    is_dietician = models.BooleanField(default=False)


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
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE)
    start_date = models.DateField()
    end_date = models.DateField()
    total_cost_lkr = models.DecimalField(max_digits=10, decimal_places=2, default=0)


class DailyPlan(models.Model):
    week_plan = models.ForeignKey(WeeklyPlan, related_name='days', on_delete=models.CASCADE)
    day_name = models.CharField(max_length=20)
    water_consumed_ml = models.IntegerField(default=0)
    target_water_ml = models.IntegerField(default=2500)


class MealSlot(models.Model):
    MEAL_CHOICES = [
        ('B', 'Breakfast'),
        ('S1', 'Morning Snack'),
        ('L', 'Lunch'),
        ('S2', 'Mid Day Snack'),
        ('D', 'Dinner'),
    ]

    # 2. Link to the day plan
    day_plan = models.ForeignKey(DailyPlan, related_name='meals', on_delete=models.CASCADE)

    # 3. The actual data field
    meal_type = models.CharField(max_length=5, choices=MEAL_CHOICES)

    # 4. Link to the recipe
    recipe = models.ForeignKey(Recipe, on_delete=models.CASCADE)

    # 5. Status trackers
    is_substituted = models.BooleanField(default=False)
    is_consumed = models.BooleanField(default=False)

    class Meta:
        # Prevents a user from having two 'Lunches' on the same day
        unique_together = ('day_plan', 'meal_type')

    def __str__(self):
        return f"{self.day_plan.day_name} - {self.get_meal_type_display()}"

#  MODULE 4: EXTRAS
class ConsultationRequest(models.Model):
    user = models.ForeignKey('UserProfile', on_delete=models.CASCADE)
    dietician = models.ForeignKey(DieticianProfile, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, default='pending')
    created_at = models.DateTimeField(auto_now_add=True)


class Appointment(models.Model):
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('CANCELLED', 'Cancelled'),
        ('COMPLETED', 'Completed'),
    ]
    MEETING_CHOICES = [
        ('VIDEO', 'Video Call'),
        ('IN_PERSON', 'In Person')
    ]
    patient = models.ForeignKey(CustomUser, related_name='my_appointments', on_delete=models.CASCADE)
    dietitian = models.ForeignKey(CustomUser, related_name='dietitian_appointments', on_delete=models.CASCADE)
    date = models.DateField()
    time = models.TimeField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    appointment_type = models.CharField(max_length=100, default='General Consultation')
    meeting_type = models.CharField(max_length=20, choices=MEETING_CHOICES, default='VIDEO')
    meeting_link = models.URLField(blank=True, null=True, help_text="Zoom/Google Meet link")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.patient.username} with {self.dietitian.username} on {self.date}"

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
    is_read = models.BooleanField(default=False)

class PriceUpdate(models.Model):
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    user = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)  # Who reported the price
    new_price = models.DecimalField(max_digits=10, decimal_places=2)
    reported_at = models.DateTimeField(auto_now_add=True)


class UserProfile(models.Model):

    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE, related_name='profile')
    profile_picture = CloudinaryField('image', null=True, blank=True, folder='grist_profiles')

    USER_ROLES = [('PATIENT', 'Patient'), ('DIETITIAN', 'Dietitian')]
    role = models.CharField(max_length=15, choices=USER_ROLES, default='PATIENT')
    current_streak = models.IntegerField(default=0, help_text="Consecutive days logging in/eating meals")
    # Demographics
    GENDER_CHOICES = [('Male', 'Male'), ('Female', 'Female')]
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    date_of_birth = models.DateField(null=True, blank=True)
    country = models.CharField(max_length=100)
    # physical measurements and fitness goals
    weight = models.FloatField(null=True, blank=True)
    height = models.FloatField(null=True, blank=True)
    target_weight = models.FloatField(null=True, blank=True)
    primary_goal = models.CharField(max_length=50, blank=True)
    activity_level = models.CharField(max_length=50, blank=True)
    # Diet & Health
    dietary_preference = models.CharField(max_length=50, default="None")
    meals_per_day = models.IntegerField(default=3)
    target_calories = models.IntegerField(default=2000, help_text="Daily calorie goal")

    # JSONFields to store the Kotlin List<String>
    allergies = models.JSONField(default=list, blank=True)
    foods_to_avoid = models.JSONField(default=list, blank=True)
    medical_conditions = models.JSONField(default=list, blank=True)
    medications = models.JSONField(default=list, blank=True)

    def __str__(self):
        return f"{self.user.username}'s Profile"

#  MODULE 5: USER GROCERY CART
class GroceryCart(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='grocery_cart')
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Grocery Cart"

class GroceryCartItem(models.Model):
    cart = models.ForeignKey(GroceryCart, on_delete=models.CASCADE, related_name='items')
    ingredient = models.ForeignKey(Ingredient, on_delete=models.SET_NULL, null=True, blank=True)
    custom_name = models.CharField(max_length=150, null=True, blank=True)
    quantity = models.FloatField()
    unit = models.CharField(max_length=50)
    is_purchased = models.BooleanField(default=False)

    def __str__(self):
        if self.ingredient:
            return f"{self.ingredient.name} ({self.quantity} {self.unit})"
        return f"Custom Item ({self.quantity} {self.unit})"

    def get_item_name(self):
        return self.ingredient.name if self.ingredient else self.custom_name

# "receiver" listens for when a CustomUser is saved
@receiver(post_save, sender=CustomUser)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        # If a new user was just created, build their profile row immediately
        UserProfile.objects.get_or_create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_user_profile(sender, instance, **kwargs):
    # This ensures that if the User is saved, the Profile is also updated
    if hasattr(instance, 'profile'):
        instance.profile.save()


class DietitianReview(models.Model):
    # The dietitian being reviewed
    dietitian = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='received_reviews')
    # The patient leaving the review
    patient = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='given_reviews')

    # Restrict the rating to 1, 2, 3, 4, or 5
    rating = models.IntegerField(validators=[MinValueValidator(1), MaxValueValidator(5)])
    comment = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # A patient should only be able to leave one active review per dietitian
        unique_together = ('patient', 'dietitian')

    def __str__(self):
        return f"{self.patient.username} -> {self.dietitian.username} ({self.rating} Stars)"

class SystemNotification(models.Model):
    ALERT_TYPES = [
        ('APPOINTMENT', 'Appointment Alert'),
        ('QUESTIONNAIRE', 'Questionnaire Alert'),
        ('GENERAL', 'General System Alert')
    ]

    dietitian = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='system_notifications')
    patient = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True, related_name='triggered_notifications')
    alert_type = models.CharField(max_length=20, choices=ALERT_TYPES, default='GENERAL')
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.alert_type} for {self.dietitian.username}"