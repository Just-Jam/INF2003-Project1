from django.urls import path
from django.urls import path

app_name = "core"

from .views import (
    DeactivateAccountView,
    ProfileView,
    RegisterView,
    LoginView,
    ChangePasswordView,
    LogoutView,
)

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),
    path("login/", LoginView.as_view(), name="login"),
    path("profile/", ProfileView.as_view(), name="profile"), 
    path("change-password/", ChangePasswordView.as_view(), name="change_password"),
    path("logout/", LogoutView.as_view(), name="logout"),
    path("deactivate-account/", DeactivateAccountView.as_view(), name="deactivate-account"),
]