import os
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

#getting the API key fron the .env file
load_dotenv()
client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))

# Fetch recipe data from OpenAI based on user constraints
def generate_and_save_meal(target_calories, allergies, meal_type="lunch"):
    prompt = f"""
    You are an expert Sri Lankan nutritionist. Generate a single {meal_type} recipe.
    Constraints:
    - Target Calories: Around {target_calories} kcal
    - Allergies to avoid: {allergies}
    - Cuisine: Authentic Sri Lankan or highly adaptable local ingredients.

    IMPORTANT: You must calculate accurate macros per 100g for each ingredient, and estimate the current Sri Lankan market price (LKR).
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

        # TODO: Integrate DB save operations
        return ai_recipe

    except Exception as e:
        print(f"AI API Failed: {e}")
        return None