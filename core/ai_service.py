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
