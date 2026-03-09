from rest_framework import serializers
from .models import UserProfile
from core.models import CustomUser
from .models import GroceryCart, GroceryCartItem

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = '__all__'
        read_only_fields = ['user']

class RegisterSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ('username', 'password', 'email')
        #  ensures the password is never sent back in an API response
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):

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