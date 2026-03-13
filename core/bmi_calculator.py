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