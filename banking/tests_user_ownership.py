from django.contrib.auth.models import User
from decimal import Decimal
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Account, Business, Transaction 

class UserOwnershipTestCase(APITestCase):
    def setUp(self):
        self.user1 = User.objects.create_user(
            username="user1",
            password="password123",
            email="user1@example.com",
        )

        self.user1_token = str(RefreshToken.for_user(self.user1).access_token)
        self.user2_token = str(RefreshToken.for_user(self.user2).access_token)

        self.user1_accounts = Account.objects.filter(user=self.user1)
        self.user2_accounts = Account.objects.filter(user=self.user2)

    def test_user_can_view_only_own_accounts(self):

        