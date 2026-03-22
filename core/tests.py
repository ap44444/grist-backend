from django.urls import reverse
from rest_framework.test import APITestCase
from rest_framework import status
from django.contrib.auth import get_user_model

User = get_user_model()

class SecurityAndAuthTests(APITestCase):
    def setUp(self):
        # Using your CustomUser model instead of the default!
        self.user = User.objects.create_user(username='teststudent', password='securepassword123')

    def test_unauthorized_access_is_blocked(self):
        """Test that unauthenticated users cannot access secure endpoints."""
        url = reverse('dashboard_today')
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_user_login_returns_token(self):
        """Test that a valid user can log in and retrieve a JWT token."""
        url = reverse('login')
        data = {'username': 'teststudent', 'password': 'securepassword123'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)


class WaterTrackingTests(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='waterboy', password='password123')
        self.client.force_authenticate(user=self.user)

    def test_add_water_without_plan_fails_gracefully(self):
        """Test that adding water without a generated daily plan returns a safe 400 error."""
        url = reverse('track_water')
        data = {'amount_ml': 250}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('error', response.data)