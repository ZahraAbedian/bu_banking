"""
A simple test view to verify routing is working.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from decimal import Decimal

class TestView(APIView):
    """
    Simple test view to verify URL routing.
    """
    permission_classes = [AllowAny]
    
    def get(self, request, *args, **kwargs):
        """
        Simple GET handler to test that the view is accessible.
        """
        return Response({
            "message": "Test view is working!",
            "path": request.path,
            "method": request.method
        }, status=status.HTTP_200_OK)
        
    def post(self, request, *args, **kwargs):
        """
        Simple POST handler to test that the view is accessible.
        """
        return Response({
            "message": "Test view POST is working!",
            "data_received": request.data,
            "path": request.path,
            "method": request.method
        }, status=status.HTTP_200_OK)


# Transaction API Test

from django.contrib.auth.models import User
from rest_framework import status
from rest_framework.test import APITestCase
from .models import Account, Business

class TransactionAPITest(APITestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser', password='pass1234')
        self.client.force_authenticate(user=self.user)
        
        self.account1 = Account.objects.create(
            user=self.user,
            name='Main',
            starting_balance=1000
        )
        self.account2 = Account.objects.create(
            user=self.user,
            name='Savings',
            starting_balance=500
        )
        self.business = Business.objects.create(
            name='Coffee Shop',
            category='food',
            sanctioned=False
        )

        self.url = '/api/transactions/'
        
    # test 1: valid transfer succeeds
    def test_create_valid_transfer(self):
        payload = {
            'transaction_type': 'transfer',
            'amount': '50.00',
            'from_account': str(self.account1.id),
            'to_account' : str(self.account2.id),
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertIn(response.status_code, [status.HTTP_201_CREATED, status.HTTP_200_OK])
        
    # test 2: invalide transfer fails
    def test_create_transfer_without_to_account_fails(self):
        payload = {
            'transaction_type': 'transfer',
            'amount': '50.00',
            'from_account': str(self.account1.id),
        }
        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn('to_account', response.data)

    # test 3: ensure transfer amount is removed from sender account
    def test_create_transfer_funds_removed_from_account(self):
        original_balance = self.account1.starting_balance
        transfer_amount = Decimal('50.00')
        
        payload = {
            'transaction_type': 'transfer',
            'amount': str(transfer_amount),
            'from_account': str(self.account1.id),
            'to_account': str(self.account2.id),
        }

        response = self.client.post(self.url, payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.account1.refresh_from_db()
        self.account2.refresh_from_db()

        self.assertEqual(self.account1.starting_balance, original_balance - transfer_amount)
        self.assertEqual(self.account2.starting_balance, Decimal(500.00) + transfer_amount)

    # test 4: monthly insights returns summary data
    def test_monthly_insights_returns_summary_data(self):
        # create a business for categorised spending
        business = Business.objects.create(
            id="coffee_shop_test",
            name="Coffee Shop",
            category="food",
            sanctioned=False
        )

        # create a payment transaction for the authenticated user's account
        self.client.post(
        self.url,
            {
                "transaction_type": "payment",
                "amount": "25.00",
                "from_account": str(self.account1.id),
                "business": business.id,
            },
            format="json"
        )

        response = self.client.get("/api/transactions/monthly-insights/", format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("month", response.data)
        self.assertIn("total_spent", response.data)
        self.assertIn("categories", response.data)
        self.assertIn("transaction_count", response.data)
        self.assertIn("insights", response.data)
        self.assertEqual(response.data["total_spent"], "25.00")
        self.assertEqual(response.data["transaction_count"], 1)
