from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth.models import User

class LoginView(TokenObtainPairView):
    """
    Step 1: Validate password.
    Returns 202 Accepted to signal the frontend to show the OTP screen.
    """
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)

        try:
            # Standard password/user validation
            serializer.is_valid(raise_exception=True)
        except Exception:
            return Response(
                {"detail": "Invalid credentials"}, 
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Trigger the 2FA state on frontend without releasing JWTs yet
        return Response(
            {
                "detail": "MFA_REQUIRED",
                "username": request.data.get('username'),
            }, 
            status=status.HTTP_202_ACCEPTED
        )

class Verify2FAView(APIView):
    """
    Step 2: Validate the OTP code.
    If valid, finally issue the JWT tokens (access and refresh).
    """
    def post(self, request):
        username = request.data.get('username')
        otp_code = request.data.get('code')

        # 1. Basic input validation
        if not username or not otp_code:
            return Response(
                {"detail": "Username and code required"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            return Response(
                {"detail": "User not found"}, 
                status=status.HTTP_404_NOT_FOUND
            )

        # 2. OTP Logic (Hardcoded '000000' for demo/MVP testing)
        # In a production environment, this would verify against a code 
        # stored in a database or a temporary cache like Redis.
        if otp_code == "000000":
            refresh = RefreshToken.for_user(user)
            return Response({
                'refresh': str(refresh),
                'access': str(refresh.access_token),
            }, status=status.HTTP_200_OK)
        
        return Response(
            {"detail": "Invalid OTP code"}, 
            status=status.HTTP_401_UNAUTHORIZED
        )