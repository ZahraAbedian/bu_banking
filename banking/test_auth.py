from django.urls import reverse
from django.contrib.auth.models import User
from rest_framework.test import APITestCase
from rest_framework import status
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.oath import TOTP
from .models import Account
import time

class ZenithAuthenticationTests(APITestCase):
    def setUp(self):
        self.username = 'dev_tester'
        self.password = 'securepassword123'
        self.user = User.objects.create_user(username=self.username, password=self.password, email="test@example.com")
        
        # Create a confirmed TOTP device for the user
        self.device = TOTPDevice.objects.create(
            user=self.user, 
            name="default", 
            confirmed=True
        )
        
        Account.objects.create(
            user=self.user,
            name="Main Checking",
            starting_balance=1000.00,
            account_type="Checking"
        )

    # --- Step 1: Login Tests ---

    def test_login_step_one_success(self):
        """Should return 202 and prompt for MFA."""
        url = reverse('token_obtain_pair')
        data = {'username': self.username, 'password': self.password}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(response.data['detail'], "MFA_REQUIRED")

    def test_login_invalid_credentials(self):
        """Should return 401 for an incorrect password."""
        url = reverse('token_obtain_pair')
        data = {'username': self.username, 'password': 'wrongpassword'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    # --- Step 2: 2FA Verification Tests ---

    def test_verify_2fa_success(self):
        """Should return JWT tokens and account data on valid TOTP."""
        self.device.refresh_from_db()
        totp = TOTP(key=self.device.bin_key, step=self.device.step, digits=self.device.digits)
        totp.time = time.time()
        token = str(totp.token()).zfill(6)
        
        url = reverse('verify_2fa')
        data = {'username': self.username, 'code': token}
        response = self.client.post(url, data, format='json')
            
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn('access', response.data)
        self.assertIn('refresh', response.data)
        self.assertTrue(len(response.data['accounts']) > 0)

    def test_verify_2fa_invalid_code(self):
        """Should return 401 for an incorrect TOTP code."""
        url = reverse('verify_2fa')
        data = {'username': self.username, 'code': '999999'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verify_2fa_no_device(self):
        """Should return 401 if the user has no confirmed 2FA device."""
        no_mfa_user = User.objects.create_user(username='no_mfa', password='password123')
        url = reverse('verify_2fa')
        data = {'username': 'no_mfa', 'code': '123456'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_verify_2fa_user_not_found(self):
        """Should return 404 for a non-existent username."""
        url = reverse('verify_2fa')
        data = {'username': 'fake_user', 'code': '123456'}
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_verify_2fa_missing_fields(self):
        """Should return 400 if required fields are missing."""
        url = reverse('verify_2fa')
        data = {'username': self.username} # Missing 'code'
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)