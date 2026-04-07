from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status 
from .models import Account

class AuthTestCase(APITestCase):
    def setUp(self):
        self.register_url = "/api/register/"
        self.login_url = "/api/login/"
        self.user_url = "/api/user/"
        self.user_data = {
            "username": "zahra_auth_test",
            "password": "StrongPass123!",
            "email": "zahra_auth_test@example.com",
            "first_name": "Zahra",
            "last_name": "Test",
        }

        self.user = User.objects.create_user(
            username="existinguser",
            password="ExistingPass123!",
            email="existing@example.com",
            first_name="Existing",
            last_name="User",
        )

    def test_register_user_success(self):
        # simulate http post request to register url (a fake test client acting like a frontend)
        response = self.client.post(self.register_url, self.user_data, format="json")

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertIn("message", response.data)
        self.assertIn("user_id", response.data)
        self.assertIn("accounts", response.data)

        self.assertTrue(User.objects.filter(username="zahra_auth_test").exists())

        #### important: check if exactly two accounts were created for the new user
        user = User.objects.get(username="zahra_auth_test")
        self.assertEqual(Account.objects.filter(user=user).count(), 2)

    def test_login_returns_access_and_refresh_for_valid_credentials(self):
        payload = {
            "username": "existinguser",
            "password": "ExistingPass123!",
        }

        response = self.client.post(self.login_url, payload, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("access", response.data)
        self.assertIn("refresh", response.data)
        self.assertIn("user", response.data)
        self.assertIn("accounts", response.data)
        self.assertEqual(response.data["user"]["username"], "existinguser")

    def test_user_endpoitn_requires_authentication(self):
        response = self.client.get(self.user_url, fromat="json")

        self.assertIn( 
            response.status_code, [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN]
        )

    def test_user_endpoitn_returns_userdata_when_aunthenticated(self):
        self.client.force_authenticate(user=self.user)
        response = self.client.get(self.user_url, format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("user", response.data)
        self.assertIn("accounts", response.data)
        self.assertEqual(response.data["user"]["username"], "existinguser")

    def test_register_fails_when_username_or_password_missing(self):
        payload = {
            "username": "",
            "password": "",
        }
        response = self.client.post(self.register_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
