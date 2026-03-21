from rest_framework import serializers
from .models import UserProfile
from core.models import CustomUser
from .models import GroceryCart, GroceryCartItem
from .models import DietitianReview
from .models import Appointment
from rest_framework import serializers

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ['user']

class RegisterSerializer(serializers.ModelSerializer):

    height = serializers.FloatField(required=False, write_only=True)
    weight = serializers.FloatField(required=False, write_only=True)
    date_of_birth = serializers.DateField(required=False, write_only=True)
    gender = serializers.CharField(required=False, write_only=True)
    role = serializers.CharField(required=False, write_only=True, default='PATIENT')

    class Meta:
        model = CustomUser
        fields = ('username', 'password', 'email', 'height', 'weight', 'date_of_birth', 'gender', 'role')
        extra_kwargs = {
            'password': {'write_only': True},
            'email': {'required': True}
        }

    def create(self, validated_data):
        #  pop the profile data out so create_user doesn't get confused
        # create_user ONLY wants username, email, and password.
        user = CustomUser.objects.create_user(
            username=validated_data['username'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
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
    patient_name = serializers.CharField(source='patient.get_full_name', read_only=True)
    dietitian_name = serializers.CharField(source='dietitian.get_full_name', read_only=True)

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
