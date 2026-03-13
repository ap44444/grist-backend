# bmi_calculator

def calculate_bmi(weight, height):
    """
    Calculate BMI using the formula:
    BMI = weight (kg) / height^2 (m^2)
    """
    return weight / (height ** 2)


def bmi_category(bmi):
    """
    Return BMI category based on standard WHO classification.
    """
    if bmi < 18.5:
        return "Underweight"
    elif 18.5 <= bmi < 24.9:
        return "Normal weight"
    elif 25 <= bmi < 29.9:
        return "Overweight"
    else:
        return "Obese"


def main():
    print("=== BMI Calculator ===")

    try:
        height = float(input("Enter height in meters (e.g., 1.75): "))
        weight = float(input("Enter weight in kilograms (e.g., 70): "))
        gender = input("Enter gender (Male/Female): ").strip().capitalize()

        if height <= 0 or weight <= 0:
            print("Height and weight must be positive numbers.")
            return

        bmi = calculate_bmi(weight, height)
        category = bmi_category(bmi)

        print("\n----- Result -----")
        print(f"Gender: {gender}")
        print(f"BMI: {bmi:.2f}")
        print(f"Category: {category}")

    except ValueError:
        print("Invalid input. Please enter numeric values for height and weight.")


if __name__ == "__main__":
    main()


def calculate_bmr(weight_kg, height_cm, age_years, gender):
    """
    Calculates Basal Metabolic Rate using the Mifflin-St Jeor Equation.
    """
    if gender.lower() == 'male':
        return (10 * weight_kg) + (6.25 * height_cm) - (5 * age_years) + 5
    else:
        return (10 * weight_kg) + (6.25 * height_cm) - (5 * age_years) - 161


def calculate_tdee(bmr, activity_level):
    """
    Calculates Total Daily Energy Expenditure based on lifestyle.
    """
    multipliers = {
        'sedentary': 1.2,  # Desk job, little to no exercise
        'light': 1.375,  # Light exercise 1-3 days/week
        'moderate': 1.55,  # Moderate exercise 3-5 days/week
        'active': 1.725,  # Heavy exercise 6-7 days/week
        'very_active': 1.9  # Physical job or training twice a day
    }
    # Default to sedentary if the string doesn't match
    return bmr * multipliers.get(activity_level.lower(), 1.2)


def calculate_target_calories(tdee, goal_intensity, gender):
    """
    Applies the deficit/surplus to reach the user's goal.
    """
    adjustments = {
        'maintain': 0,
        'mild_weight_loss': -250,  # ~0.25 kg loss per week
        'weight_loss': -500,  # ~0.5 kg loss per week
        'extreme_weight_loss': -1000,  # ~1.0 kg loss per week
        'mild_weight_gain': 250,
        'weight_gain': 500
    }

    target = tdee + adjustments.get(goal_intensity.lower(), 0)

    # SAFETY NET: Medical standard limits so the app doesn't starve the user
    min_calories = 1500 if gender.lower() == 'male' else 1200

    return max(round(target), min_calories)