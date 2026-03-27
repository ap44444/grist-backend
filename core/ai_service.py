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
    image_search_query: str = Field(description="A 2-4 word search query for a stock photo. Combine the main ingredient with 'Curry', 'Plate', or 'Dish' (e.g., 'Red Rice Curry Plate', 'Sweet Potato Dish').")
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
    try:
        print(f"--- STARTING AI CHEF FOR: {meal_type} ---")

        # 1. Check for the API key safely
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            print("CRITICAL ERROR: OPENAI_API_KEY is missing from Railway environment variables!")
            raise ValueError("API Key is missing from Railway")

        client = OpenAI(api_key=api_key)

        type_map = {
            'breakfast': 'B', 'b': 'B',
            'morning snack': 'S1', 's1': 'S1',
            'lunch': 'L', 'l': 'L',
            'mid day snack': 'S2', 's2': 'S2',
            'dinner': 'D', 'd': 'D'
        }
        meal_code = type_map.get(meal_type.lower(), 'L')

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
        - The 'image_search_query' MUST look like a complete, cooked meal, not a raw ingredient.
        - Always pair the main ingredient with words like "Curry", "Plate", or "Dish".
        - GOOD QUERIES: "Red Rice Curry Plate", "Boiled Sweet Potato Dish", "Jackfruit Curry".
        - BAD QUERIES (Too specific): "Red rice with spicy lunu miris and chicken".
        - BAD QUERIES (Too raw): "Red rice", "Sweet potato" (these will return images of raw, uncooked food).
        

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

        #  DATABASE INJECTION
        # 1. Save the Recipe
        new_recipe = Recipe.objects.create(
            title=ai_recipe.title,
            calories=ai_recipe.total_calories,
            prep_time_mins=ai_recipe.prep_time_mins,
            instructions=ai_recipe.instructions,
            image_url=recipe_image,
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

        import re
        total_protein = 0
        total_carbs = 0
        total_fats = 0
        ingredients_list = []

        # Pull the newly saved ingredients to calculate real macros
        recipe_ingredients = RecipeIngredient.objects.filter(recipe=new_recipe)

        for ri in recipe_ingredients:
            factor = ri.quantity / 100.0 if ri.unit.lower() in ['g', 'ml'] else 1.0
            total_protein += float(ri.ingredient.protein) * factor
            total_carbs += float(ri.ingredient.carbs) * factor
            total_fats += float(ri.ingredient.fats) * factor

            # This combines quantity and unit into "amount" for Maheen!
            ingredients_list.append({
                "name": ri.ingredient.name.title(),
                "amount": f"{ri.quantity} {ri.unit}"
            })

        directions_list = [step.strip() for step in re.split(r'\n|\d+\.', new_recipe.instructions) if step.strip()]

        # Return the exact JSON shape the Kotlin app expects
        return {
            "id": new_recipe.id,
            "title": new_recipe.title,
            "image_url": recipe_image,
            "ready_in_minutes": new_recipe.prep_time_mins or 20,
            "macros": {
                "calories": new_recipe.calories,
                "protein_g": int(total_protein),
                "carbs_g": int(total_carbs),
                "fats_g": int(total_fats)
            },
            "ingredients": ingredients_list,
            "directions": directions_list,
            "is_favorite": False
        }

    except Exception as e:

        print(f"CRITICAL AI ERROR CAUGHT: {str(e)}")
        return None

def substitute_ingredient_in_meal(user, meal_slot_id, old_ingredient_name):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    try:
        # 1. Find the exact meal slot the user is trying to change
        meal_slot = MealSlot.objects.get(
            id=meal_slot_id,
            day_plan__week_plan__user__user=user
        )
        original_recipe = meal_slot.recipe

        # 2. Ask the AI for a localized swap using strict constraints
        prompt = f"""
                You are an elite Sri Lankan clinical nutritionist.
                A user is modifying the following recipe: "{original_recipe.title}"

                ORIGINAL INSTRUCTIONS TO USE AS A TEMPLATE:
                "{original_recipe.instructions}"

                TASK:
                The user wants to remove "{old_ingredient_name}" because it is too expensive or hard to find.

                CRITICAL RULES FOR THE SUBSTITUTION:
                1. NO LAZY SWAPS: Do NOT suggest a different cut or variation of the exact same ingredient (e.g., do NOT swap "chicken breast" for "chicken legs", or "beef" for "minced beef"). It must be a completely different ingredient.
                2. THINK LOCAL & AFFORDABLE: Heavily favor cheap, culturally authentic Sri Lankan staples. 
                   - Good Protein Swaps: Soya meat (TVP), Mushrooms, Jackfruit (Polos), Chickpeas (Kadala), Dhal, Paneer, or cheap local fish (like Salaya/Canned fish).
                   - Good Carb/Veg Swaps: Manioc, Bathala (Sweet Potato), local greens.
                3. CULINARY HARMONY: The new ingredient must logically fit the flavor profile of a Sri Lankan dish and serve the same macro purpose (e.g., swap a protein for a protein).
                4. REWRITE INSTRUCTIONS: Rewrite the Original Instructions provided above. Keep them the EXACT same length and level of detail. Intelligently replace "{old_ingredient_name}" with your new ingredient and adjust specific prep steps if needed (e.g., "soak the soya meat in hot water" instead of "wash the chicken").
                """

        print(f"Requesting AI substitution for {old_ingredient_name}...")

        completion = client.beta.chat.completions.parse(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a backend JSON data generator."},
                {"role": "user", "content": prompt}
            ],
            response_format=SubstitutedRecipe,
        )

        ai_data = completion.choices[0].message.parsed

        # 3. Clone the recipe with the fix: copy image_url from original
        new_recipe = Recipe.objects.create(
            title=ai_data.new_recipe_title,
            calories=original_recipe.calories,
            instructions=ai_data.updated_instructions,
            prep_time_mins=original_recipe.prep_time_mins,
            image_url=original_recipe.image_url,  # FIX: carry over the image
            is_ai_generated=True
        )

        # 4. FIX: Copy all ingredients from the original recipe to the new one,
        #    EXCEPT the one being substituted
        old_name_lower = old_ingredient_name.lower().strip()
        original_ingredients = RecipeIngredient.objects.filter(recipe=original_recipe)

        for ri in original_ingredients:
            if old_name_lower not in ri.ingredient.name.lower():
                # Keep this ingredient as-is
                RecipeIngredient.objects.create(
                    recipe=new_recipe,
                    ingredient=ri.ingredient,
                    quantity=ri.quantity,
                    unit=ri.unit
                )
            else:
                # Create or get the new substitute ingredient
                new_ingredient, _ = Ingredient.objects.get_or_create(
                    name=ai_data.new_ingredient_name.lower().strip(),
                    defaults={
                        'calories': ri.ingredient.calories,
                        'protein': ri.ingredient.protein,
                        'carbs': ri.ingredient.carbs,
                        'fats': ri.ingredient.fats,
                        'price_lkr': float(ri.ingredient.price_lkr) * 0.6,
                        'is_local': True
                    }
                )
                RecipeIngredient.objects.create(
                    recipe=new_recipe,
                    ingredient=new_ingredient,
                    quantity=ri.quantity,
                    unit=ri.unit
                )

        # 5. Map the new recipe to the user's meal slot
        meal_slot.recipe = new_recipe
        meal_slot.is_substituted = True
        meal_slot.save()

        # 6. Handle the Grocery Cart Swap
        user_cart, _ = GroceryCart.objects.get_or_create(user=user)

        # Remove the expensive item from their cart
        GroceryCartItem.objects.filter(
            cart=user_cart,
            ingredient__name__icontains=old_name_lower
        ).delete()

        # Add the cheap local substitute to their cart
        new_ingredient_obj = Ingredient.objects.filter(
            name__icontains=ai_data.new_ingredient_name.lower().strip()
        ).first()

        GroceryCartItem.objects.create(
            cart=user_cart,
            ingredient=new_ingredient_obj,  # Link properly if found
            custom_name=ai_data.new_ingredient_name if not new_ingredient_obj else None,
            quantity=1,
            unit="portion",
            is_purchased=False
        )

        return {
            "status": "success",
            "meal_slot": {
                "id": meal_slot.id,
                "type_code": meal_slot.meal_type,
                "type_label": meal_slot.get_meal_type_display(),
                "title": new_recipe.title,
                "calories": new_recipe.calories,
                "image_url": new_recipe.image_url or "https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg",
                "is_consumed": meal_slot.is_consumed,
                "is_generated": True,
                "is_substituted": True
            },
            "swap_details": ai_data.model_dump()
        }


    except MealSlot.DoesNotExist:
        return {"status": "error", "message": "Meal slot not found or does not belong to this user."}
    except Exception as e:
        print(f"SUBSTITUTION ERROR: {str(e)}")
        return {"status": "error", "message": str(e)}