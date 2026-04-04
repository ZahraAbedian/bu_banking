from rest_framework import serializers
from .models import Account, Transaction, Business
from django.contrib.auth.models import User

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'first_name', 'last_name']
        read_only_fields = ['id']

class AccountSerializer(serializers.ModelSerializer):
    user_details = UserSerializer(source='user', read_only=True)
    account_type_display = serializers.CharField(source='get_account_type_display', read_only=True)
    
    class Meta:
        model = Account
        fields = [
            'id', 'name', 'starting_balance', 'round_up_enabled', 
            'postcode', 'user', 'user_details', 'account_type', 
            'account_type_display', 'round_up_pot'
        ]
        
class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ['id', 'transaction_type', 'amount', 'from_account', 'to_account', 'business', 'timestamp']
    
    # check one filed
    def validate_amount(self, value):
        if value <= 0:
            raise serializers.ValidationError("Amount must be greater than 0")
        return value
    
    # check relationships between fields
    def validate(self, attrs):
        transaction_type = attrs.get('transaction_type')
        from_account = attrs.get('from_account')
        to_account = attrs.get('to_account')
        business = attrs.get('business')

        if transaction_type == 'transfer':
            if not to_account:
                raise serilaizer.ValidationError({'to_account': 'A transfer must include a destination account.'})
            
            if from_account and to_account and from_account == to_account:
                raise serilaizer.ValidationError({'to_account': 'Source and destination accounts cannot be the same.'})

        if transaction_type == 'payment':
            if not business:
                raise serializer.ValidationError({'business': 'A payment must include a business.'}) 

        return attrs   


class BusinessSerializer(serializers.ModelSerializer):
    class Meta:
        model = Business
        fields = ['id', 'name', 'category', 'sanctioned']