# core/urls.py
# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    AuthViewSet,
    UserViewSet,
    AdminUserViewSet,
    LogoutView,
    RegisterView,
    LoginView,
    ProfileView,
    ChangePasswordView,
    DeactivateAccountView
)

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserViewSet, basename='users')
router.register(r'admin-users', AdminUserViewSet, basename='admin-users')

# API URL patterns
urlpatterns = [
    # Include router URLs
    path('', include(router.urls)),

    # Explicit API endpoints (alternative to viewset actions)
    path('auth/register/', RegisterView.as_view(), name='api-register'),
    path('auth/login/', LoginView.as_view(), name='api-login'),
    path('auth/logout/', LogoutView.as_view(), name='api-logout'),
    path('users/profile/', ProfileView.as_view(), name='api-profile'),
    path('users/change-password/', ChangePasswordView.as_view(), name='api-change-password'),
    path('users/deactivate/', DeactivateAccountView.as_view(), name='api-deactivate'),
]

# Add additional API endpoints manually:
# urlpatterns += [
#     path('custom-endpoint/', some_view, name='custom-endpoint'),
# ]