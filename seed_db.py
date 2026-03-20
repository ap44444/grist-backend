import os
import django
import random

# 1. Setup Django environment
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'grist_project.settings')
django.setup()

from core.models import CustomUser, UserProfile, DietitianReview


def seed_database():
    print(" Starting the Database Seeder...")

    # 2. Create or Get Test Patient
    patient, created = CustomUser.objects.get_or_create(username="test_patient", email="patient@grist.com")
    patient.set_password("GristDemo123!")
    patient.first_name = "Demo"
    patient.last_name = "Patient"
    patient.save()

    # SAFELY get the profile (whether it was auto-created or not) and update it
    patient_profile, p_created = UserProfile.objects.get_or_create(user=patient)
    patient_profile.weight = 70.0
    patient_profile.height = 175.0
    patient_profile.target_calories = 2000
    patient_profile.save()

    print(" Created Test Patient (Username: test_patient, PW: GristDemo123!)")

    # 3. Create 3 Expert Dietitians
    dietitians_data = [
        {"username": "dr_sarah", "first": "Sarah", "last": "Jenkins", "email": "sarah@grist.com"},
        {"username": "dr_david", "first": "David", "last": "Chen", "email": "david@grist.com"},
        {"username": "dr_amanda", "first": "Amanda", "last": "Silva", "email": "amanda@grist.com"}
    ]

    created_dietitians = []
    for d_data in dietitians_data:
        dietitian, d_created = CustomUser.objects.get_or_create(username=d_data["username"], email=d_data["email"])
        dietitian.set_password("GristDemo123!")
        dietitian.first_name = d_data["first"]
        dietitian.last_name = d_data["last"]
        dietitian.save()

        # Safely ensure they have a profile
        UserProfile.objects.get_or_create(user=dietitian)
        created_dietitians.append(dietitian)

    print(" Created 3 Dietitians")

    # 4. Generate Fake Reviews!
    comments = [
        "Absolutely changed my life! The meal plans are so easy to follow.",
        "Very professional and kind. Highly recommend.",
        "Helped me hit my target weight in just 2 months!",
        "Great advice on managing my macros.",
        "The best dietitian on this app by far."
    ]

    print(" Generating Reviews...")
    for dietitian in created_dietitians:
        # Check if they already have reviews to avoid doubling up if you run this twice
        if dietitian.received_reviews.count() == 0:
            for _ in range(random.randint(3, 5)):
                DietitianReview.objects.create(
                    dietitian=dietitian,
                    patient=patient,
                    rating=random.choice([4, 5]),
                    comment=random.choice(comments)
                )

    print(" Seeding Complete! Your database is now populated.")


if __name__ == "__main__":
    seed_database()