from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework.throttling import AnonRateThrottle
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User
from django_otp.plugins.otp_totp.models import TOTPDevice
from .models import Account

class LoginView(TokenObtainPairView):
    """
    Step 1 of login. Validates credentials and signals that MFA is required.
    """
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        try:
            serializer.is_valid(raise_exception=True)
            # We don't return tokens here because 2FA is mandatory.
            return Response(
                {
                    "detail": "MFA_REQUIRED", 
                    "username": request.data.get('username')
                }, 
                status=status.HTTP_202_ACCEPTED
            )
        except Exception:
            return Response(
                {"detail": "Invalid username or password"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

class Verify2FAView(APIView):
    """
    Step 2 of login. Verifies the 6-digit TOTP code and issues JWT tokens.
    """
    permission_classes = [AllowAny]
    throttle_classes = [AnonRateThrottle]

    def post(self, request):
        username = request.data.get('username')
        otp_code = request.data.get('code')

        if not username or not otp_code:
            return Response({"detail": "Username and PIN required"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response({"detail": "User not found"}, status=status.HTTP_404_NOT_FOUND)

        # Look for the confirmed TOTP device for this user
        device = TOTPDevice.objects.filter(user=user, confirmed=True).first()

        if device and device.verify_token(otp_code):
            # Generate JWT tokens
            refresh = RefreshToken.for_user(user)
            
            # Fetch associated accounts
            accounts = Account.objects.filter(user=user)
            accounts_data = [
                {
                    "id": acc.id,
                    "name": acc.name,
                    "starting_balance": str(acc.starting_balance),
                    "account_type": acc.account_type,
                } for acc in accounts
            ]

            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
                'user': {
                    "username": user.username,
                    "email": user.email
                },
                'accounts': accounts_data
            }, status=status.HTTP_200_OK)
        
        return Response({"detail": "Invalid Authenticator Code"}, status=status.HTTP_401_UNAUTHORIZED)