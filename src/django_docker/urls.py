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
from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView

urlpatterns = [
    path("", TemplateView.as_view(template_name="home.html"), name="home"),
    path("register/", TemplateView.as_view(template_name="auth/register.html"), name="register"),
    path("login/", TemplateView.as_view(template_name="auth/login.html"), name="login"),
    path("profile/", TemplateView.as_view(template_name="auth/profile.html"), name="profile"),
    path("change-password/", TemplateView.as_view(template_name="auth/change_password.html"), name="change_password"),
    path("deactivate/", TemplateView.as_view(template_name="auth/deactivate.html"), name="deactivate"),
    path("admin/", admin.site.urls),
    path("api/", include(("core.urls", "core"), namespace="api")),
]
