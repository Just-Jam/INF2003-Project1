"""
URL configuration for django_docker project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# django_project/urls.py

# django_project/urls.py
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from core.views import (
    logout_view,
    admin_dashboard,
    user_management,
    user_detail,
    create_user,
    toggle_user_status,
    order_list,
    order_detail,
    order_create,
    order_edit,
    admin_order_list,
    admin_order_detail
)

urlpatterns = [
    # Frontend pages (serving HTML templates)
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("register/", TemplateView.as_view(template_name="auth/register.html"), name="register"),
    path("login/", TemplateView.as_view(template_name="auth/login.html"), name="login"),
    path("profile/", TemplateView.as_view(template_name="auth/profile.html"), name="profile"),
    path("change-password/", TemplateView.as_view(template_name="auth/change_password.html"), name="change_password"),
    path("deactivate/", TemplateView.as_view(template_name="auth/deactivate.html"), name="deactivate"),
    path("logout/", logout_view, name="logout"),

    # Admin pages (using actual view functions with authentication)
    path("admin/", admin_dashboard, name="admin_home"),
    path("admin/users/", user_management, name="admin_user_management"),
    path("admin/users/create/", create_user, name="admin_create_user"),
    path("admin/users/<uuid:user_id>/", user_detail, name="admin_user_detail"),
    path("admin/users/<uuid:user_id>/toggle-status/", toggle_user_status, name="admin_toggle_user_status"),
    path("admin/orders/", admin_order_list, name="admin_order_list"),
    path("admin/orders/<uuid:order_id>/", admin_order_detail, name="admin_order_detail"),

    # Order pages (using actual view functions with authentication)
    path("orders/", order_list, name="order_list"),
    path("orders/<uuid:order_id>/", order_detail, name="order_detail"),
    path("orders/create/", order_create, name="order_create"),
    path("orders/<uuid:order_id>/edit/", order_edit, name="order_edit"),

    # Django admin (using different path to avoid conflict with custom admin)
    path("django-admin/", admin.site.urls),

    # API routes
    path("api/", include(("core.urls", "core"), namespace="api")),
]
