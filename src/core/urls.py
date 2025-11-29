# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import *

router = DefaultRouter()
router.register(r'auth', AuthViewSet, basename='auth')
router.register(r'users', UserViewSet, basename='users')
router.register(r'admin-users', AdminUserViewSet, basename='admin-users')
router.register(r'orders', OrderViewSet, basename='order')
router.register(r'admin/orders', AdminOrderViewSet, basename='admin-order')

# API URL patterns
# ALL urls preceded by /api/
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

    path('products/', ProductListView.as_view(), name='product-list'),
    path('products/<int:page>/', ProductListView.as_view(), name='product-list-paginated'),
    path('products/search/', UnifiedSearchView.as_view(), name='products-unified-search'),

    path('populate-products/', populate_sample_products, name='populate-products'),
    path('debug-products/', debug_products, name='debug-products'),

    # User endpoints
    path('addresses/', AddressListCreateAPIView.as_view(), name='address-list-create'),
    path('addresses/<uuid:address_id>/', AddressDetailAPIView.as_view(), name='address-detail'),
    path('addresses/<uuid:address_id>/set-default/', SetDefaultAddressAPIView.as_view(),
         name='set-default-address'),

    # Admin-only endpoints
    path('admin/addresses/', AdminAddressManagementAPIView.as_view(), name='admin-address-list'),
    path('admin/addresses/user/<int:user_id>/', AdminAddressManagementAPIView.as_view(),
         name='admin-user-addresses'),


]

# Add additional API endpoints manually:
# urlpatterns += [
#     path('custom-endpoint/', some_view, name='custom-endpoint'),
# ]