# core/views.py
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from django.contrib.auth import get_user_model
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, permissions, generics
from rest_framework.authtoken.models import Token

from .serializers import (
    DeactivateAccountSerializer,
    RegisterSerializer,
    UserSerializer,
    ProfileSerializer,
    ChangePasswordSerializer,
)


class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email,
                    "first_name": user.first_name,
                    "last_name": user.last_name,
                    "token": token.key,
                },
                status=status.HTTP_201_CREATED,
            )
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"detail": "Email and password required."}, status=400)

        # 1. Check if email exists
        try:
            user_obj = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials."}, status=400)

        # 2. Authenticate using username (since Django uses username internally)
        user = authenticate(username=user_obj.username, password=password)

        # 3. Invalid password
        if not user:
            return Response({"detail": "Invalid credentials."}, status=400)

        # 4. Check if account is deactivated
        if not user.is_active:
            return Response({"detail": "Account is deactivated. Please contact support."},
                            status=403)

        # 5. Create or get token
        token, _ = Token.objects.get_or_create(user=user)

        return Response({"token": token.key}, status=200)
    
class ProfileView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)

    def patch(self, request):
        serializer = UserSerializer(
            request.user, data=request.data, partial=True
        )
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=400)
    
User = get_user_model() # type: ignore

class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET    /api/profile/   -> retrieve logged-in user's profile
    PUT    /api/profile/   -> full update
    PATCH  /api/profile/   -> partial update
    """
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        # always return the currently authenticated user
        return self.request.user
    
class ChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_password = serializer.validated_data["new_password"]

        # Set new password
        user.set_password(new_password)
        user.save()

        # 🔐 Optional but recommended: invalidate old token and create a new one
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response(
            {
                "detail": "Password changed successfully.",
                "token": token.key,  # tell frontend to use this new token
            },
            status=status.HTTP_200_OK,
        )
    
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # request.auth is the Token instance for TokenAuthentication
        if request.auth:
            request.auth.delete()

        return Response(
            {"detail": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )
    
class DeactivateAccountView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = DeactivateAccountSerializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.is_active = False
        user.save()

        # delete token so user is logged out
        Token.objects.filter(user=user).delete()

        return Response(
            {"detail": "Account deactivated successfully."},
            status=status.HTTP_200_OK,
        )