from django.test import TestCase
from rest_framework import status
from rest_framework.test import APITestCase
from django.contrib.auth.models import User
from .models import Account, Business 
from decimal import Decimal
from .serializers import TransactionSerializer

class TransactionSerializerTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username='testuser')
        self.account1 = Account.objects.create(
            user=self.user,
            name='Main'
            starting_balance=1000
        )
        self.account2 = Account.objects.create(
            user=self.user,
            name='Savings'
            starting_balance=500
        )
        self.business = Business.objects.create(
            name='Coffee Shop',
            category='food',
            sanctioned=False
        )

    def test_valid_transfer_passes(self):
        data = {
            'transaction_type': 'transfer',
            'amount':Decimal('50.00'),
            'from_account':self.account1.id,
            'to_account': self.account2.id
        }      
        serializer = TransactionSerializer(data=data)
        self.assertTrue(serializer.is_valid())

    def test_negative_amount_fails(self):
        data = {
            'transaction_type': 'transfer',
            'amount': Decimal('-10.00'),
            'from_account': self.account1.id,
            'to_account': self.account2.id,
        }
        serializer = TransactionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('amount', serializer.errors)
        
    def test_transfer_without_to_account_fails(self):
        data = {
            'transaction_type': 'transfer',
            'amount': Decimal('10.00'),
            'from_account': self.account1.id,
        }
        serializer = TransactionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('to_account', serializer.errors)

    def test_payment_without_business_fails(self):
        data = {
            'transaction_type': 'payment',
            'amount': Decimal('10.00'),
            'from_account': self.account1.id,
        }
        serializer = TransactionSerializer(data=data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('business', serializer.errors)