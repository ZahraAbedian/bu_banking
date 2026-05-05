from django.contrib import admin
from django.urls import path, include
from rest_framework_simplejwt.views import TokenRefreshView
from banking.auth_views import LoginView, Verify2FAView
from banking.template_views import register_api

urlpatterns = [
    path('admin/', admin.site.urls),

    # --- STEP 1: LOGIN ALIASES ---
    path('api/auth/login/', LoginView.as_view(), name='login'),
    path('api/token/', LoginView.as_view(), name='token_obtain_pair'),

    # --- STEP 2: VERIFICATION ALIASES ---
    # These cover all common patterns to prevent 404s
    path('api/verify-2fa/', Verify2FAView.as_view(), name='verify_2fa'),
    path('api/auth/verify-2fa/', Verify2FAView.as_view(), name='verify_2fa_auth'),
    path('auth/verify-2fa/', Verify2FAView.as_view(), name='verify_2fa_root'),
    
    # --- OTHER API ROUTES ---
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('api/', include('banking.urls')),

    # --- REGISTRATION ---
    path('api/register/', register_api, name='api-register'),
    path('api/auth/register/', register_api, name='auth-register'),
]