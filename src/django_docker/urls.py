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

from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from core.views import logout_view  # Import the logout view

urlpatterns = [
    # Frontend pages
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("register/", TemplateView.as_view(template_name="auth/register.html"), name="register"),
    path("login/", TemplateView.as_view(template_name="auth/login.html"), name="login"),
    path("profile/", TemplateView.as_view(template_name="auth/profile.html"), name="profile"),
    path("change-password/", TemplateView.as_view(template_name="auth/change_password.html"), name="change_password"),
    path("deactivate/", TemplateView.as_view(template_name="auth/deactivate.html"), name="deactivate"),
    path("logout/", logout_view, name="logout"),  # Add this line

    # Admin pages
    path("admin/", include([
        path("", TemplateView.as_view(template_name="admin/dashboard.html"), name="admin_home"),
        path("users/", TemplateView.as_view(template_name="admin/user_management.html"), name="admin_users"),
    ])),

    # Django admin
    path("django-admin/", admin.site.urls),

    # API routes
    path("api/", include("core.urls")),
]
