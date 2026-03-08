import os
import requests
import json
from openai import OpenAI
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from typing import List

# Importing the Django models

from core.models import Recipe, Ingredient, RecipeIngredient


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
    total_calories: int = Field(description="Total calories for the entire prepared meal")
    prep_time_mins: int
    instructions: str = Field(description="Step by step cooking instructions")
    ingredients: List[GeneratedIngredient]


def get_web_image(recipe_title):
    api_key = os.getenv("SERPER_API_KEY")
    search_query = f"{recipe_title} Sri Lankan food"
    url = "https://google.serper.dev/images"

    payload = json.dumps({
        "q": search_query,
        "num": 1,
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
            if 'images' in data and len(data['images']) > 0:
                image_url = data['images'][0]['imageUrl']
                print(f" Image Found: {image_url}")
                return image_url
        else:
            print(f" Serper Error {response.status_code}: {response.text}")

    except Exception as e:
        print(f" Serper Connection Error: {e}")

    # Fallback image
    return "https://images.pexels.com/photos/1640772/pexels-photo-1640772.jpeg"
#getting the API key fron the .env file
load_dotenv()

# Fetch recipe data from OpenAI based on user constraints
def generate_and_save_meal(user_profile, meal_type="lunch"):
    client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

    #  Gather all the data from the Kotlin frontend
    target_calories = getattr(user_profile, 'target_calories', 600)  # Teammate's calculated value
    allergies = ", ".join(user_profile.allergies) if user_profile.allergies else "None"
    avoid_foods = ", ".join(user_profile.foods_to_avoid) if user_profile.foods_to_avoid else "None"
    medical = ", ".join(user_profile.medical_conditions) if user_profile.medical_conditions else "None"
    goal = user_profile.primary_goal
    activity = user_profile.activity_level

    prompt = f"""
        You are an elite Sri Lankan clinical nutritionist...

        USER HEALTH PROFILE:
        - Primary Goal: {goal}
        - Activity Level: {activity}
        - Medical Conditions to consider: {medical}

        STRICT CONSTRAINTS:
        - Target Calories: {target_calories} kcal.
        - Mandatory Exclusions (Allergies): {allergies}.
        - User Dislikes (Avoid): {avoid_foods}.
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

        recipe_image = get_web_image(ai_recipe.title)


        # --- DATABASE INJECTION ---
        # 1. Save the Recipe
        new_recipe = Recipe.objects.create(
            title=ai_recipe.title,
            calories=ai_recipe.total_calories,
            prep_time_mins=ai_recipe.prep_time_mins,
            instructions=ai_recipe.instructions,
            is_ai_generated=True
        )

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
