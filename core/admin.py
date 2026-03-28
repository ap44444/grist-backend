from django.contrib import admin
from .models import Recipe, Ingredient, GroceryCart, GroceryCartItem
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from import_export.admin import ImportExportModelAdmin
from core.models import CustomUser, UserProfile, DieticianProfile
from .models import (
    Ingredient, Recipe, WeeklyPlan, DailyPlan, CustomUser,
    ShoppingList, ShoppingListItem, ChatMessage, PriceUpdate,
    RecipeIngredient,UserProfile
)
from .models import Appointment, ConsultationRequest, DietitianReview, SystemNotification, Reminder

from .models import PatientNote

#   SMART RESOURCES (The Translation Layer)

# This handles the complex "Recipe <-> Ingredient" link
class RecipeIngredientResource(resources.ModelResource):
    # Instead of asking for an ID, we ask for the Recipe Title
    recipe = fields.Field(
        column_name='recipe_name',
        attribute='recipe',
        widget=ForeignKeyWidget(Recipe, 'title')
    )
    # Instead of asking for an ID, we ask for the Ingredient Name
    ingredient = fields.Field(
        column_name='ingredient_name',
        attribute='ingredient',
        widget=ForeignKeyWidget(Ingredient, 'name')
    )

    class Meta:
        model = RecipeIngredient
        # These are the columns she needs in her CSV
        fields = ('recipe', 'ingredient', 'quantity', 'unit')
        # This allows importing without a primary key ID column
        import_id_fields = ('recipe', 'ingredient')

#   ADMIN VIEWS

@admin.register(Ingredient)
class IngredientAdmin(ImportExportModelAdmin):
    list_display = ('name', 'price_lkr', 'calories', 'is_local')
    search_fields = ('name',)
    list_editable = ('price_lkr', 'is_local')

@admin.register(Recipe)
class RecipeAdmin(ImportExportModelAdmin):
    list_display = ('title', 'prep_time_mins')
    search_fields = ('title',)

# Register the "Linker" table
@admin.register(RecipeIngredient)
class RecipeIngredientAdmin(ImportExportModelAdmin):
    resource_class = RecipeIngredientResource
    list_display = ('recipe', 'ingredient', 'quantity','unit')
    list_filter = ('recipe',)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'gender', 'country', 'primary_goal', 'profile_picture')
    search_fields = ('user__username', 'country')

    # Explicitly defining the detail view layout
    fieldsets = (
        (None, {
            'fields': ('user', 'profile_picture', 'role', 'current_streak')
        }),
        ('Physical Information', {
            'fields': ('gender', 'date_of_birth', 'country', 'weight', 'height', 'target_weight')
        }),
        ('Goals & Preferences', {
            'fields': ('primary_goal', 'activity_level', 'dietary_preference', 'meals_per_day', 'target_calories')
        }),
        ('Health Data', {
            'fields': ('allergies', 'foods_to_avoid', 'medical_conditions', 'medications')
        }),
    )

@admin.register(PatientNote)
class PatientNoteAdmin(admin.ModelAdmin):
    list_display = ('dietitian', 'patient', 'created_at', 'updated_at')
    search_fields = ('dietitian__username', 'patient__username', 'note_text')
    list_filter = ('dietitian',)


# registration
admin.site.register(WeeklyPlan)
admin.site.register(DailyPlan)
admin.site.register(CustomUser)
admin.site.register(ShoppingList)
admin.site.register(ShoppingListItem)
admin.site.register(ChatMessage)
admin.site.register(PriceUpdate)
admin.site.register(DieticianProfile)
#grocerry cart
admin.site.register(GroceryCart)
admin.site.register(GroceryCartItem)

#appoinments
admin.site.register(Appointment)
admin.site.register(ConsultationRequest)
admin.site.register(DietitianReview)
admin.site.register(SystemNotification)
admin.site.register(Reminder)