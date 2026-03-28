from rest_framework import serializers
from .models import UserProfile
from core.models import CustomUser
from .models import GroceryCart, GroceryCartItem
from .models import DietitianReview
from .models import Appointment
from rest_framework import serializers

from .models import PatientNote

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ['user']


class RegisterSerializer(serializers.ModelSerializer):
    role = serializers.CharField(required=False, default='PATIENT')

    class Meta:
        model = CustomUser
        fields = ('username', 'password', 'email', 'role')
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        role = validated_data.pop('role', 'PATIENT')
        user = CustomUser.objects.create_user(**validated_data)

        # Ensure the profile created by signals gets the correct role immediately
        user.profile.role = role
        user.profile.save()
        return user
# --- GROCERY CART SERIALIZERS ---
class GroceryCartItemSerializer(serializers.ModelSerializer):
    # This automatically runs get_item_name() function so the frontend gets the real text!
    name = serializers.CharField(source='get_item_name', read_only=True)

    class Meta:
        model = GroceryCartItem
        fields = ['id', 'ingredient', 'custom_name', 'name', 'quantity', 'unit', 'is_purchased']
        read_only_fields = ['cart'] # Security: don't let users assign items to other people's carts

class GroceryCartSerializer(serializers.ModelSerializer):
    items = GroceryCartItemSerializer(many=True, read_only=True)

    class Meta:
        model = GroceryCart
        fields = ['id', 'updated_at', 'items']

class AppointmentSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.username', read_only=True)
    dietitian_name = serializers.CharField(source='dietitian.username', read_only=True)

    class Meta:
        model = Appointment
        fields = [
            'id', 'patient', 'patient_name', 'dietitian', 'dietitian_name',
            'date', 'time', 'status', 'appointment_type', 'meeting_type',
            'meeting_link', 'created_at'
        ]
        read_only_fields = ['patient', 'status', 'meeting_link']

class DietitianReviewSerializer(serializers.ModelSerializer):
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)

    class Meta:
        model = DietitianReview
        fields = [
            'id', 'patient_name', 'dietitian',
            'dietitian_rating', 'call_quality_rating',
            'tags', 'comment', 'created_at'
        ]
        read_only_fields = ['id', 'patient_name', 'created_at']

#Mihindi - dietician
class PatientNoteSerializer(serializers.ModelSerializer):
    dietitian_name = serializers.CharField(source='dietitian.username', read_only=True)
    patient_name = serializers.CharField(source='patient.username', read_only=True)

    # This lets the frontend SEND a username string instead of a numeric ID
    patient_username = serializers.SlugRelatedField(
        slug_field='username',
        queryset=CustomUser.objects.all(),
        source='patient',
        write_only=True
    )

    class Meta:
        model = PatientNote
        fields = ['id', 'dietitian', 'dietitian_name', 'patient', 'patient_name',
                  'patient_username', 'note_text', 'created_at', 'updated_at']
        read_only_fields = ['dietitian', 'patient', 'created_at', 'updated_at']


# --- MEMBER 5: CUSTOM USER REMINDERS ---
from .models import Reminder

class ReminderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Reminder
        fields = ['id', 'user', 'title', 'time_to_trigger', 'is_active']
        read_only_fields = ['id', 'user']

# PERSON A: DIETITIAN PROFESSIONAL IDENTITY SERIALIZER

from .models import DieticianProfile

class DieticianProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = DieticianProfile
        fields = ['license_number', 'bio', 'is_verified']
        read_only_fields = ['is_verified']
