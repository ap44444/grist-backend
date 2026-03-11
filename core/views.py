from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .serializers import UserProfileSerializer
from .ai_service import generate_and_save_meal
from rest_framework import generics
from rest_framework.permissions import AllowAny
from django.contrib.auth.models import User
from .serializers import RegisterSerializer
from core.models import CustomUser
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from django.shortcuts import get_object_or_404
from .models import GroceryCart, GroceryCartItem
from .serializers import GroceryCartSerializer, GroceryCartItemSerializer
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from .ai_service import substitute_ingredient_in_meal

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def update_profile(request):
    #find the profile for the logged-in user
    profile = request.user.profile
    serializer = UserProfileSerializer(profile, data=request.data, partial=True)

    if serializer.is_valid():
        serializer.save()
        return Response({"message": "Profile updated successfully!"}, status=status.HTTP_200_OK)

    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def request_recipe(request):
    # Get the profile of the user making the request
    user_profile = request.user.profile

    # Identify the meal type ( default to lunch)
    meal_type = request.query_params.get('type', 'lunch')
    pass

    # calling the ai function
    try:
        recipe_data = generate_and_save_meal(user_profile, meal_type=meal_type)
        return Response(recipe_data, status=200)
    except Exception as e:
        return Response({"error": str(e)}, status=500)

class RegisterView(generics.CreateAPIView):
    queryset = CustomUser.objects.all()
    permission_classes = (AllowAny,)
    serializer_class = RegisterSerializer


# 1. READ (GET)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_grocery_cart(request):
    """Fetches the user's current cart and all items inside it"""
    cart, created = GroceryCart.objects.get_or_create(user=request.user)
    serializer = GroceryCartSerializer(cart)
    return Response(serializer.data)


# 2. CREATE (POST)
@api_view(['POST'])
@permission_classes([IsAuthenticated])
def add_cart_item(request):
    """Adds a new item (either an Ingredient ID or a custom text name)"""
    cart, created = GroceryCart.objects.get_or_create(user=request.user)

    serializer = GroceryCartItemSerializer(data=request.data)
    if serializer.is_valid():
        # Save it and specifically link it to THIS user's cart
        serializer.save(cart=cart)
        return Response(serializer.data, status=status.HTTP_201_CREATED)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 3. UPDATE (PATCH)
@api_view(['PATCH'])
@permission_classes([IsAuthenticated])
def update_cart_item(request, item_id):
    """Updates quantity or ticks the 'is_purchased' checkbox"""
    cart = get_object_or_404(GroceryCart, user=request.user)
    item = get_object_or_404(GroceryCartItem, id=item_id, cart=cart)

    # partial=True means the frontend can send JUST the checkbox state, or JUST the quantity
    serializer = GroceryCartItemSerializer(item, data=request.data, partial=True)
    if serializer.is_valid():
        serializer.save()
        return Response(serializer.data)
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# 4. DELETE (DELETE)
@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_cart_item(request, item_id):
    """Removes an item completely from the cart"""
    cart = get_object_or_404(GroceryCart, user=request.user)
    item = get_object_or_404(GroceryCartItem, id=item_id, cart=cart)
    item.delete()
    return Response({"message": "Item deleted successfully"}, status=status.HTTP_204_NO_CONTENT)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def request_substitution(request, meal_slot_id):
    # The frontend will send the name of the ingredient they want to remove
    old_ingredient = request.data.get('ingredient_to_replace')

    if not old_ingredient:
        return Response({"error": "Please provide 'ingredient_to_replace' in the JSON body."}, status=400)

    result = substitute_ingredient_in_meal(request.user, meal_slot_id, old_ingredient)

    if result.get("status") == "success":
        return Response(result, status=200)
    else:
        return Response(result, status=400)