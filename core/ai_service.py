import os
import requests
import json
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List
from django.utils import timezone
import random
# Importing the Django models

from core.models import Recipe, Ingredient, RecipeIngredient, GroceryCart, GroceryCartItem, WeeklyPlan, DailyPlan, MealSlot


# Data schemas to enforce strict JSON formatting from the OpenAI API
class GeneratedIngredient(BaseModel):
    name: str = Field(description="Name of the ingredient in lowercase")
    quantity: float = Field(description="Amount needed for the recipe")
    unit: str = Field(description="Unit of measurement (e.g., g, ml, cups, pieces)")
    calories_per_100g: int = Field(description="Caloric value per 100 grams")
    protein: float = Field(description="Protein in grams per 100g")
    carbs: float = Field(description="Carbohydrates in grams per 100g")
    fats: float = Field(description="Fats in grams per 100g")
    price_lkr: float = Field(description="Estimated current market price in LKR for the quantity used")
    is_local: bool = Field(description="True if commonly grown/produced in Sri Lanka, False if mostly imported")

class GeneratedRecipe(BaseModel):
    title: str = Field(description="Name of the dish")
    image_search_query: str = Field(description="A highly generic 3-word food category to guarantee finding a stock photo (e.g., 'Sri Lankan Rice Curry', 'Sri Lankan Roti Plate'). DO NOT use specific ingredient names.")
    total_calories: int = Field(description="Total calories for the entire prepared meal")
    prep_time_mins: int
    instructions: str = Field(description="Step by step cooking instructions")
    ingredients: List[GeneratedIngredient]

class SubstitutedRecipe(BaseModel):
    new_ingredient_name: str = Field(description="Name of the new local ingredient")
    reasoning: str = Field(description="Why this is a good, affordable Sri Lankan swap")
    new_recipe_title: str = Field(description="Updated title of the dish")
    updated_instructions: str = Field(description="Updated cooking instructions including the new ingredient")

def get_web_image(optimized_query):
    api_key = os.getenv("SERPER_API_KEY")
    search_query = f"{optimized_query} Sri Lankan food"
    url = "https://google.serper.dev/images"

    payload = json.dumps({
        "q": search_query,
        "num": 10,
        "gl": "lk"  # Sets location to Sri Lanka for better results
    })

    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload, timeout=10)

        if response.status_code == 200:
            data = response.json()
            images = data.get('images', [])
            for img in images:
                img_url = img.get('imageUrl', '')
                # A blocklist of domains that break mobile apps
                bad_domains = [
                    "instagram.com",
                    "pinterest.com",
                    "facebook.com",
                    "fbcdn.net",
                    "fbsbx.com",
                    "lookaside",
                    "tiktok.com"
                ]
                # If ANY of the bad domains are in the URL, skip it!
                if any(domain in img_url for domain in bad_domains):
                    continue

                print(f" Exact Image Found: {img_url}")
                return img_url

    except Exception as e:
        print(f" Serper Error: {e}")

    return "https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg"
#getting the API key fron the .env file
load_dotenv()

# Fetch recipe data from OpenAI based on user constraints
def generate_and_save_meal(user_profile, meal_type="lunch"):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    type_map = {
        'breakfast': 'B', 'b': 'B',
        'morning snack': 'S1', 's1': 'S1',
        'lunch': 'L', 'l': 'L',
        'mid day snack': 'S2', 's2': 'S2',
        'dinner': 'D', 'd': 'D'
    }

    #  Gather all the data from the Kotlin frontend
    total_target = getattr(user_profile, 'target_calories', 2000)

    # Calculate portions based on if it's a snack or main meal
    if meal_type.lower() in ['s1', 's2', 'morning snack', 'mid day snack']:
        target_calories = round(total_target * 0.12)
        snack_vibes = [
            "a traditional herbal drink (like Kola Kenda, Belimal, or Ranawara) with a tiny sweet",
            "a refreshing local fruit plate (like Papaya, Pineapple, or Mango) with chili/salt",
            "a small portion of spiced boiled legumes (like Mung Beans, Kaupi, or Kadala) with fresh coconut",
            "a small portion of traditional steamed roots (like Manioc or Sweet Potato) with a light sambol",
            "a very light, healthy Sri Lankan traditional sweet (like Thala Guli or Aggala) paired with plain tea"
        ]
        chosen_vibe = random.choice(snack_vibes)

        context_header = f"""
                *** CURRENT MEAL CONTEXT: This is a LIGHT SNACK ({meal_code}). ***
                Style: Light, quick, and refreshing. 
                CRITICAL DIRECTION: For this specific request, please focus on generating {chosen_vibe}.
                Do NOT generate a massive main meal.
                """
    else:
        target_calories = round(total_target * 0.28)
        context_header = f"CURRENT MEAL CONTEXT: This is a BALANCED MAIN MEAL ({meal_type}). Style: Strictly follow the Protein + Complex Carb + Veg structure."
    allergies = ", ".join(user_profile.allergies) if user_profile.allergies else "None"
    avoid_foods = ", ".join(user_profile.foods_to_avoid) if user_profile.foods_to_avoid else "None"
    medical = ", ".join(user_profile.medical_conditions) if user_profile.medical_conditions else "None"
    goal = user_profile.primary_goal
    activity = user_profile.activity_level

    prompt = f"""
    
        {context_header}
        You are an elite Sri Lankan clinical nutritionist...

        USER HEALTH PROFILE:
        - Primary Goal: {goal}
        - Activity Level: {activity}
        - Medical Conditions to consider: {medical}

        STRICT CONSTRAINTS:
        - Target Calories: {target_calories} kcal.
        - Mandatory Exclusions (Allergies): {allergies}.
        - User Dislikes (Avoid): {avoid_foods}.
        CULINARY DIRECTION:
        - If this is a SNACK (S1/S2): Strictly follow the "CURRENT MEAL CONTEXT" instructions at the top of this prompt.
        - If this is a MAIN MEAL (B/L/D): Follow the lean protein + complex carb + green vegetable rule.
            
        CRITICAL HEALTH & CULINARY INSTRUCTIONS:
        - NO BORING MEALS: Absolutely no generic "boiled chicken and white rice" or "plain dhal". Elevate the dish.
        - HEALTH FIRST: Zero deep-frying. Strictly minimize thick coconut milk and oil.
        - MANDATORY MACRO STRUCTURE (CRITICAL): Every single meal MUST explicitly contain three distinct components to be considered balanced: 
            1. A lean protein source. 
            2. A dedicated complex local carbohydrate (e.g., traditional red rice, kurakkan roti, bathala/sweet potato, or manioc). 
            3. A vegetable/green side (e.g., mallum, sambol, or spiced veg). 
        - FLAVOR, SPICES & MOISTURE (CRITICAL): Sri Lankan food is never bland or bone-dry. You MUST explicitly include standard aromatics (onions, garlic, ginger, curry leaves, pandan) and spices (roasted/unroasted curry powder, turmeric, chili, black pepper, salt). Do not serve dry rice with dry meat. You MUST include a healthy, low-calorie wet component (e.g., a light spiced gravy/hodi using tomato or thin milk, a wet marinade, or a juicy sambol) so the meal is enjoyable to eat.
        - REALISTIC PORTIONS: Do not suggest eating 150g+ of raw leaves for a mallum. Keep ingredient proportions realistic and appetizing for a single human serving.
          Do NOT generate a meal that is missing a dedicated carb component.
        - CULINARY HARMONY & AUTHENTICITY: Use ingredients in their traditional, culturally authentic contexts. Pairings must make logical culinary sense.
        - COOKING TECHNIQUES: Heavily recommend healthy but intensely flavorful preparation methods like charring, roasting, traditional clay pot simmering with goraka, or grilling.
        
        IMAGE SEARCH OPTIMIZATION (CRITICAL):
        - Stock photos for highly customized plate combinations do not exist. 
        - The 'image_search_query' field MUST be a broad, generic food category so a web scraper can easily find a high-quality stock photo.
        - DO NOT include specific protein names or local vegetable names in the search query.
        - Example 1: "Spicy Grilled Chicken with Kurakkan Roti and Mallum" -> "Sri Lankan Roti Plate"
        - Example 2: "Black Pork Curry with Red Rice" -> "Sri Lankan Rice Curry"
        - Example 3: "Baked Fish with Sweet Potato Mash" -> "Healthy Sri Lankan plate"
        
        NAMING CONVENTION & NO HALLUCINATION (CRITICAL):
        - DO NOT invent fake, fusion, or nonsense dish names. 
        - The recipe title MUST be either a highly accurate, literal descriptive name or a 100% authentic traditional Sri Lankan name.

        STRICT RECIPE COHESION:
        - Every single ingredient mentioned in the recipe title MUST be actively used in the step-by-step instructions.
        - The instructions must logically match the generated ingredients list exactly.

        Strict Constraints:
        - Target Calories: Strictly around {target_calories} kcal.
        - Allergies to avoid: {allergies}.

        DATA ACCURACY: 
        - Calculate highly accurate macronutrients (protein, carbs, fats) per 100g for every single ingredient.
        - Estimate realistic, current retail market prices in LKR specifically for Western Province suburbs.
        """

    try:
        print("Sending request to OpenAI API...")

        # Force structured JSON response matching GeneratedRecipe
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a backend JSON data generator."},
                {"role": "user", "content": prompt}
            ],
            response_format=GeneratedRecipe,
        )

        ai_recipe = completion.choices[0].message.parsed
        print(f"Success! AI generated: {ai_recipe.title}")

        recipe_image = get_web_image(ai_recipe.image_search_query)


        # --- DATABASE INJECTION ---
        # 1. Save the Recipe
        new_recipe = Recipe.objects.create(
            title=ai_recipe.title,
            calories=ai_recipe.total_calories,
            prep_time_mins=ai_recipe.prep_time_mins,
            instructions=ai_recipe.instructions,
            is_ai_generated=True
        )
        # Grab the user's personal grocery cart (or create a blank one)
        user_cart, cart_created = GroceryCart.objects.get_or_create(user=user_profile.user)

        # 1.5 Link to the User's Private Plan Hierarchy
        from datetime import timedelta
        today = timezone.now().date()
        day_name_str = today.strftime("%A")  # e.g., "Wednesday"

        # A. Find or create their Weekly Plan
        week_plan, _ = WeeklyPlan.objects.get_or_create(
            user=user_profile,
            defaults={
                'start_date': today,
                'end_date': today + timedelta(days=6)
            }
        )

        # B. Find or create today's Daily Plan
        daily_plan, _ = DailyPlan.objects.get_or_create(
            week_plan=week_plan,
            day_name=day_name_str
        )

        # C. Map the Recipe to the MealSlot
        # Map the incoming type to match the 5 database choices exactly

        meal_code = type_map.get(meal_type.lower(), 'L')

        meal_slot, slot_created = MealSlot.objects.get_or_create(
            day_plan=daily_plan,
            meal_type=meal_code,
            defaults={'recipe': new_recipe}
        )

        # If they already had a lunch planned, overwrite it with this fresh AI meal!
        if not slot_created:
            meal_slot.recipe = new_recipe
            meal_slot.is_substituted = False
            meal_slot.is_consumed = False
            meal_slot.save()


        # 2. Save Ingredients and Link Them
        for item in ai_recipe.ingredients:
            clean_name = item.name.lower().strip()

            ingredient_obj, created = Ingredient.objects.get_or_create(
                name=clean_name,
                defaults={
                    'calories': item.calories_per_100g,
                    'protein': item.protein,
                    'carbs': item.carbs,
                    'fats': item.fats,
                    'price_lkr': item.price_lkr,
                    'is_local': item.is_local
                }
            )

            RecipeIngredient.objects.create(
                recipe=new_recipe,
                ingredient=ingredient_obj,
                quantity=item.quantity,
                unit=item.unit
            )
            # the grocery cart
            cart_item, item_created = GroceryCartItem.objects.get_or_create(
                cart=user_cart,
                ingredient=ingredient_obj,
                defaults={
                    'quantity': item.quantity,
                    'unit': item.unit,
                    'is_purchased': False
                }
            )

            # If the ingredient was ALREADY in the cart, just increase the weight!
            if not item_created:
                cart_item.quantity += item.quantity
                # Uncheck the box so they know they need to buy more!
                cart_item.is_purchased = False
                cart_item.save()

        print(f"Saved '{ai_recipe.title}' to DB!")
        # Convert to dictionary and attach the image URL
        #  ADD THE IMAGE TO THE DICTIONARY FOR KOTLIN
        final_recipe_data = ai_recipe.model_dump()
        final_recipe_data['image_url'] = recipe_image
        final_recipe_data['recipe_id'] = new_recipe.id
        return final_recipe_data

    except Exception as e:
        print(f"AI API Failed: {e}")
        return None


def substitute_ingredient_in_meal(user, meal_slot_id, old_ingredient_name):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    try:
        # 1. Find the exact meal slot the user is trying to change
        meal_slot = MealSlot.objects.get(id=meal_slot_id, day_plan__week_plan__user__user=user)
        original_recipe = meal_slot.recipe

        # 2. Ask the AI for a localized swap
        prompt = f"""
        You are an expert Sri Lankan dietician.
        A user is making the recipe: "{original_recipe.title}"
        They need to substitute this ingredient because it is too expensive or hard to find in Sri Lanka: "{old_ingredient_name}"

        Provide a locally available Sri Lankan alternative that:
        1. Is significantly cheaper or easier to find.
        2. Closely matches the calorie and macronutrient profile of the original.
        3. Fits the flavor profile of the dish.
        """

        print(f"Requesting AI substitution for {old_ingredient_name}...")

        # Force structured JSON response matching SubstitutedRecipe
        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a backend JSON data generator."},
                {"role": "user", "content": prompt}
            ],
            response_format=SubstitutedRecipe,
        )

        ai_data = completion.choices[0].message.parsed

        # 3. Database Magic: Clone and Swap
        new_recipe = Recipe.objects.create(
            title=ai_data.new_recipe_title,
            calories=original_recipe.calories,
            instructions=ai_data.updated_instructions,
            prep_time_mins=original_recipe.prep_time_mins,
            is_ai_generated=True
        )

        # Map the new recipe to the user's meal slot
        meal_slot.recipe = new_recipe
        meal_slot.is_substituted = True
        meal_slot.save()

        # Handle the Grocery Cart Swap
        cart, _ = GroceryCart.objects.get_or_create(user=user)

        # Remove the expensive item from their cart
        GroceryCartItem.objects.filter(
            cart=cart,
            ingredient__name__icontains=old_ingredient_name.lower()
        ).delete()

        # Add the cheap local item to their cart
        GroceryCartItem.objects.create(
            cart=cart,
            custom_name=ai_data.new_ingredient_name,
            quantity=1,
            unit="portion"
        )

        return {
            "status": "success",
            "new_recipe": new_recipe.title,
            "swap_details": ai_data.model_dump()
        }

    except MealSlot.DoesNotExist:
        return {"status": "error", "message": "Meal slot not found."}
    except Exception as e:
        return {"status": "error", "message": str(e)}