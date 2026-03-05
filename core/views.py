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