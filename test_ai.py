import requests
import json
import time

# --- 1. FILL IN YOUR DETAILS HERE ---
BASE_URL = "http://127.0.0.1:8000"
USERNAME = "andy_jonson"  # Put your real test username here
PASSWORD = "20080903Mahee"  # Put your password here


# ------------------------------------

def run_full_test():
    print("=========================================")
    print("🚀 STARTING FULL AI PIPELINE TEST")
    print("=========================================\n")

    # --- STEP 1: LOG IN ---
    print("1️⃣ Logging in to get access token...")
    login_response = requests.post(
        f"{BASE_URL}/api/login/",
        json={"username": USERNAME, "password": PASSWORD}
    )

    if login_response.status_code != 200:
        print(f"❌ Login Failed! Check your username/password. {login_response.text}")
        return

    token = login_response.json().get("access")
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    print("✅ Login Successful!\n")

    # --- STEP 2: GENERATE A NEW MEAL ---
    print("2️⃣ Asking AI to generate a brand new Lunch...")
    print("   ⏳ (Please wait 15-25 seconds for OpenAI...)")
    start_time = time.time()

    gen_response = requests.get(f"{BASE_URL}/api/recipe/request/?type=lunch", headers=headers)

    if gen_response.status_code != 200:
        print(f"❌ Meal Generation Failed! {gen_response.text}")
        return

    gen_data = gen_response.json()
    print(f"✅ Meal Generated in {round(time.time() - start_time, 1)} seconds!")
    print(f"   🍲 Dish: {gen_data.get('title')}")

    # Grab the very first ingredient from the new recipe to use as our test swap
    old_ingredient = gen_data.get("ingredients")[0].get("name")
    print(f"   🥬 Target ingredient to substitute: '{old_ingredient}'\n")

    # --- STEP 3: FIND THE MEAL SLOT ID ---
    print("3️⃣ Fetching today's plan to find the Meal Slot ID...")
    plan_response = requests.get(f"{BASE_URL}/api/plan/today/", headers=headers)

    meal_slot_id = None
    for meal in plan_response.json().get("meals", []):
        if meal.get("type_code") == "L":  # "L" stands for Lunch
            meal_slot_id = meal.get("id")
            break

    if not meal_slot_id:
        print("❌ Could not find the Meal Slot ID for Lunch!")
        return

    print(f"✅ Found Meal Slot ID: {meal_slot_id}\n")

    # --- STEP 4: TEST THE SUBSTITUTION ---
    print(f"4️⃣ Asking AI to substitute '{old_ingredient}'...")
    print("   ⏳ (Please wait another 15-25 seconds...)")

    payload = {
        "ingredient_to_replace": old_ingredient
    }

    sub_response = requests.post(
        f"{BASE_URL}/api/meals/{meal_slot_id}/substitute/",
        headers=headers,
        json=payload
    )

    # --- STEP 5: VERIFY THE FIX! ---
    if sub_response.status_code == 200:
        print("\n🎉 SUCCESS! SUBSTITUTION COMPLETE! 🎉")