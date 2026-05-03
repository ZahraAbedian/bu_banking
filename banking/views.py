from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated, IsAdminUser, AllowAny
from rest_framework.exceptions import PermissionDenied
from rest_framework.decorators import action
from django.db import transaction
from django.db import models
from django.db.models import Sum
from django.contrib.auth.models import User
from .models import Account, Transaction, Business, Card
from .serializers import AccountSerializer, TransactionSerializer, BusinessSerializer
from decimal import Decimal, InvalidOperation
from banking.services.spending_insights import get_monthly_spending_insights
from rest_framework.decorators import api_view
import os
import subprocess

class UserRegistrationView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        # Extract user data from request
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email', '')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        
        # Validate required fields
        if not username or not password:
            return Response(
                {"error": "Username and password are required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        # Check if username already exists
        if User.objects.filter(username=username).exists():
            return Response(
                {"error": "Username already exists"}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Create the user
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name
            )
            
            # # Create default Current Account with 1000 starting balance
            # current_account = Account.objects.create(
            #     name=f"{first_name or username}'s Current Account",
            #     starting_balance=Decimal('1000.00'),
            #     round_up_enabled=False,
            #     user=user,
            #     account_type='current'
            # )
            
            # # Create default Savings Account with 0 starting balance
            # savings_account = Account.objects.create(
            #     name=f"{first_name or username}'s Savings Account",
            #     starting_balance=Decimal('0.00'),
            #     round_up_enabled=True,  # Enable round-up for savings by default
            #     user=user,
            #     account_type='savings'
            # )

            ### Important change: Get accounts created automatically by the signal
            accounts = Account.objects.filter(user=user)
            
            # Return success response with account details
            return Response({
                "message": "User registered successfully",
                "user_id": user.id,
                # "accounts": [
                #     {
                #         "id": str(current_account.id),
                #         "name": current_account.name,
                #         "type": current_account.get_account_type_display(),
                #         "balance": str(current_account.starting_balance)
                #     },
                #     {
                #         "id": str(savings_account.id),
                #         "name": savings_account.name,
                #         "type": savings_account.get_account_type_display(),
                #         "balance": str(savings_account.starting_balance)
                #     }
                # ]

                ### Important change
                'accounts': [
                    {
                        'id': str(account.id),
                        'name': account.name,
                        'type': account.get_account_type_display(),
                        'balance': str(account.starting_balance)
                    }
                    for account in accounts
                ]
            }, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response(
                {"error": f"Error creating user: {str(e)}"}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


class AccountViewSet(viewsets.ModelViewSet):
    serializer_class = AccountSerializer
    
    def get_queryset(self):
        # If user is authenticated, return only their accounts
        # For admin users, return all accounts
        if self.request.user.is_authenticated:
            if self.request.user.is_staff:
                return Account.objects.all()
            # Return only accounts associated with the logged-in user
            return Account.objects.filter(user=self.request.user)
        return Account.objects.none()
    
    def get_permissions(self):
        # For list and retrieve actions, require authentication
        if self.action in ['list', 'retrieve', 'my_accounts', 'roundups', 'spending_trends', 'current_balance']:
            return [IsAuthenticated()]
        # For read actions, require authentication
        if self.action in ['list', 'retrieve', 'account_transactions', 'spending_summary', 'monthly_insights']:
            return [IsAuthenticated()]
        # For create, update, delete actions, require admin privileges
        elif self.action in ['create', 'update', 'partial_update', 'destroy', 'manager_list']:
            return [IsAdminUser()]
        return [AllowAny()]
        
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def my_accounts(self, request):
        """
        Get all accounts belonging to the currently authenticated user.
        This endpoint needs a valid JWT token in the Authorization header.
        """
        if not request.user.is_authenticated:
            return Response({"detail": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        accounts = Account.objects.filter(user=request.user)
        serializer = self.get_serializer(accounts, many=True)
        
        # Print debugging info
        print(f"User: {request.user}, Auth: {request.user.is_authenticated}")
        print(f"Found {accounts.count()} accounts")
        
        return Response(serializer.data)



class TransactionViewSet(viewsets.ModelViewSet):
    serializer_class = TransactionSerializer
    
    def get_queryset(self):
        # Return transactions for accounts owned by the user
        if self.request.user.is_authenticated:
            if self.request.user.is_staff:
                return Transaction.objects.all()
            user_accounts = Account.objects.filter(user=self.request.user)
            return Transaction.objects.filter(from_account__in=user_accounts)
        return Transaction.objects.none()
    
    def get_permissions(self):
        # For read actions, require authentication
        if self.action in ['list', 'retrieve', 'account_transactions', 'spending_summary']:
            return [IsAuthenticated()]
        # For write actions, also require authentication
        return [IsAuthenticated()]
    
    def perform_create(self, serializer):
        from_account = serializer.validated_data.get('from_account')

        # compare account owner to user making request
        if from_account.user != self.request.user:
            raise PermissionDenied('Access Denied.')

        # wrap function with atomic block, one part fails all fails
        with transaction.atomic():
            instance = serializer.save()

            # get sender account and subtract amount sent
            from_account = instance.from_account
            from_account.starting_balance -= instance.amount
            from_account.save()

            # if its a transfer, add money to recepient
            if instance.transaction_type == 'transfer' and instance.to_account:
                to_account = instance.to_account
                to_account.starting_balance += instance.amount
                to_account.save()

    @action(detail=False, methods=['get'], url_path='account/(?P<account_id>[^/.]+)')
    def account_transactions(self, request, account_id=None):
        # View all transactions related to a specific account
        try:
            account = Account.objects.get(id=account_id)
            
            # Check if the user has permission to access this account
            if account.user != request.user and not request.user.is_staff:
                return Response({"detail": "You don't have permission to access this account"}, 
                               status=status.HTTP_403_FORBIDDEN)
                
            transactions = Transaction.objects.filter(from_account=account)
            serializer = self.get_serializer(transactions, many=True)
            return Response(serializer.data)
        except Account.DoesNotExist:
            return Response({"detail": "Account not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='spending-summary/(?P<account_id>[^/.]+)')
    def spending_summary(self, request, account_id=None):
        # Summarize spending by category for a given account
        try:
            account = Account.objects.get(id=account_id)
            
            # Check if the user has permission to access this account
            if account.user != request.user and not request.user.is_staff:
                return Response({"detail": "You don't have permission to access this account"}, 
                               status=status.HTTP_403_FORBIDDEN)
                
            # Summarize spending by business category
            spending_summary = Transaction.objects.filter(
                from_account=account,
                transaction_type="payment"
            ).values('business__category').annotate(total=Sum('amount'))        
            return Response(spending_summary)
        except Account.DoesNotExist:
            return Response({"detail": "Account not found"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=['get'], url_path='top-10-spenders')
    def top_10_spenders(self, request):
        # Get the top 10 spenders by amount - admin only
        if not request.user.is_staff:
            return Response({"detail": "Admin privileges required"}, status=status.HTTP_403_FORBIDDEN)
            
        top_spenders = Transaction.objects.filter(transaction_type="payment") \
            .values('from_account__name') \
            .annotate(total_spent=Sum('amount')) \
            .order_by('-total_spent')[:10]
        return Response(top_spenders)

    @action(detail=False, methods=['get'], url_path='sanctioned-business-report')
    def sanctioned_business_report(self, request):
        # Report all transactions related to sanctioned businesses - admin only
        if not request.user.is_staff:
            return Response({"detail": "Admin privileges required"}, status=status.HTTP_403_FORBIDDEN)
            
        sanctioned_transactions = Transaction.objects.filter(business__sanctioned=True) \
            .values('business__name') \
            .annotate(total_spent=Sum('amount'))
        return Response(sanctioned_transactions)

    @action(detail=True, methods=['get'], url_path='spending-trends')
    def spending_trends(self, request, pk=None):
        return Response({"message": "Spending trends for account "})

    @action(detail=True, methods=['post'], url_path='enable-roundup')
    def enable_roundup(self, request, pk=None):
        return Response({"message": "Roundup enabled for account "})

    @action(detail=True, methods=['post'], url_path='reclaim-roundup')
    def reclaim_roundup(self, request, pk=None):
        return Response({"message": "Round-up reclaimed"})

    @action(detail=True, methods=['get'])
    def roundups(self, request, pk=None):
        return Response({"savings": True})

    @action(detail=False, methods=['get'], url_path='monthly-insights')
    def monthly_insights(self, request):
        """
        Return monthly spending insights for the authenticated user across their accounts.
        Includes total spending, category breakdown, transaction count, and AI-generated insight messages.
        Falls back to rule-based insights if the AI service is unavailable.
        """
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        try:
            month = int(month) if month else None
            year = int(year) if year else None
        except ValueError:
            return Response(
                {"detail": "month and year must be valid integers"},
                status=status.HTTP_400_BAD_REQUEST
            )
        data = get_monthly_spending_insights(
            user=request.user,
            month=month,
            year=year
        )
        return Response(data, status=status.HTTP_200_OK)

class BusinessViewSet(viewsets.ModelViewSet):
    queryset = Business.objects.all()
    serializer_class = BusinessSerializer
    
    def get_permissions(self):
        # For read operations, require authentication
        if self.action in ['list', 'retrieve']:
            return [IsAuthenticated()]
        # For write operations, require admin privileges
        return [IsAdminUser()]


@api_view(["POST"])
def record_nfc_payment(request): 
    """
    Record a new NFC payment.
    """
    data = request.data
    card_number = data.get("card_number")
    merchant_id = data.get("merchant_id")
    trnsaction_id = data.get("transaction_id")
    timestamp = data.get("timestamp")
    
    try:
        amount = Decimal(data.get("amount"))
    except InvalidOperation:
        return Response({"detail": "Invalid amount"}, status=status.HTTP_400_BAD_REQUEST)

    if amount <= 0:
        return Response({"detail": "Amount must be greater than zero"}, status=status.HTTP_400_BAD_REQUEST)
    
    try: 
        card = Card.objects.select_related('account').get(card_number=card_number, active=True)
    except Card.DoesNotExist:
        return Response({"error": "Card not found or inactive."}, status=status.HTTP_404_NOT_FOUND)
    
    with transaction.atomic():
        # update account balance
        account.starting_balance -= amount
        account.save()

        business, _ = Business.objects.get_or_create(
            id = merchant_id ,
            defaults={
                "name": merchant_id,
                "category": "NFC payment",
                "sanctioned": False,},)

        local_transaction = Transaction.objects.create(
            transaction_type = "payment",
            from_account = card.account,
            amount = amount,
            business=business,      
        )


    return Response(
        {
            "message": "NFC payment recorded successfully",
            "transaction_id": local_transaction.id,
            "card_number": card_number,
            "new_balance": str(account.starting_balance),
        },
        status=status.HTTP_201_CREATED,
    )