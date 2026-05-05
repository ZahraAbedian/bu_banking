from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import AccountViewSet, TransactionViewSet, BusinessViewSet, UserRegistrationView
from .test_view import TestView
from django.http import JsonResponse

router = DefaultRouter()
router.register(r'accounts', AccountViewSet, basename='account')
router.register(r'transactions', TransactionViewSet, basename='transaction')
router.register(r'businesses', BusinessViewSet)

urlpatterns = [
    path('register/', UserRegistrationView.as_view(), name='user-registration'),
    path('', include(router.urls)),
    
    # Diagnostic
    path('test-view/', TestView.as_view(), name='banking-test-view'),
    path('url-test/', lambda request: JsonResponse({"message": "Banking app URLs active"})),
]