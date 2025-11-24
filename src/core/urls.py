# core/urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register(r'auth', views.AuthViewSet, basename='auth')
router.register(r'users', views.UserViewSet, basename='users')
router.register(r'admin-users', views.AdminUserViewSet, basename='admin-users')

urlpatterns = [
    path('', include(router.urls)),

    # Admin pages
    # path('admin/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin/users/', views.user_management, name='admin_user_management'),
    path('admin/users/create/', views.create_user, name='admin_create_user'),
    path('admin/users/<uuid:user_id>/', views.user_detail, name='admin_user_detail'),
    path('admin/users/<uuid:user_id>/toggle-status/', views.toggle_user_status, name='admin_toggle_user_status'),

    path('auth/logout/', views.LogoutView.as_view(), name='api-logout'),
]

# Add additional API endpoints manually:
# urlpatterns += [
#     path('custom-endpoint/', some_view, name='custom-endpoint'),
# ]