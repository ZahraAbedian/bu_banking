from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.contrib.auth import authenticate
from django.core.signing import TimestampSigner, BadSignature, SignatureExpired
from django_otp import devices_for_user
from django.contrib.auth.models import User
from rest_framework_simplejwt.tokens import RefreshToken
from .models import Account
from .serializers import AccountSerializer

signer = TimestampSigner()

class LoginView(APIView):
    permission_classes = []
    
    def post(self, request, *args, **kwargs):
        # Explicitly use the DRF request object's data
        # We rename the local variables to avoid any chance of shadowing
        try:
            passed_username = request.data.get('username')
            passed_password = request.data.get('password')
        except AttributeError:
            # This triggers if 'request' isn't what we think it is
            return Response({"error": "Malformed request"}, status=400)

        user_obj = authenticate(username=passed_username, password=passed_password)
        
        if user_obj is not None:
            # We use 'user_obj' instead of 'user' to stay safe
            device = next(devices_for_user(user_obj), None)
        
            if not device:
                return Response({"error": "2FA setup required."}, status=status.HTTP_403_FORBIDDEN)
            
            # Sign the ID
            pre_auth_token = signer.sign(user_obj.id)

            return Response({
                "2fa_required": True,
                "pre_auth_token": pre_auth_token,
                "message": "Step 1 complete. Please enter your 6-digit code."
            }, status=status.HTTP_200_OK)
        
        return Response({"error": "Invalid credentials"}, status=status.HTTP_401_UNAUTHORIZED)
    
class Verify2FAView(APIView):
    permission_classes = []

    def post(self, request):
        pre_auth_token = request.data.get('pre_auth_token')
        otp_token = request.data.get('otp_token')

        try:
            user_id = signer.unsign(pre_auth_token, max_age=300)
            user = User.objects.get(id=user_id)
        except (BadSignature, SignatureExpired, User.DoesNotExist):
            return Response({"error": "Session expired or invalid"}, status=status.HTTP_401_UNAUTHORIZED)
        
        device = next(devices_for_user(user), None)
        if device and device.verify_token(otp_token):
            refresh = RefreshToken.for_user(user)
            accounts = Account.objects.filter(user=user)
            account_data = AccountSerializer (accounts, many=True).data

            return Response({
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff
                },
                'accounts': account_data,
                'access': str(refresh.access_token),
                'refresh': str(refresh)

            }, status=status.HTTP_200_OK)

        return Response({"error": "Invalid verification code."}, status=status.HTTP_401_UNAUTHORIZED)            



class UserAccountsView(APIView):
    permission_classes = [IsAuthenticated]
    
    def get(self, request, *args, **kwargs):
        """
        Get the current user's profile and accounts
        """
        user = request.user
        accounts = Account.objects.filter(user=user)
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_staff': user.is_staff,
            },
            'accounts': AccountSerializer(accounts, many=True).data
        })