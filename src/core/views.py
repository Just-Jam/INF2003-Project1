# core/views.py
from django.contrib import messages
from django.contrib.auth.decorators import user_passes_test
from django.core.paginator import Paginator
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import render, get_object_or_404, redirect
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import status, permissions, generics
from rest_framework.decorators import permission_classes

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from django.contrib.auth import authenticate, get_user_model
from rest_framework.authtoken.models import Token
from .serializers import *

from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.contrib import messages

#Get your custom User model
User = get_user_model()

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response(
                {
                    "user_id": user.user_id,  # ✅ Use user_id instead of id
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

        # ✅ Use custom User model with email lookup
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials."}, status=400)

        # ✅ Authenticate using email (since your custom user uses email as USERNAME_FIELD)
        user = authenticate(request, username=email, password=password)  # Use email as username

        if not user:
            return Response({"detail": "Invalid credentials."}, status=400)

        if not user.is_active:
            return Response({"detail": "Account is deactivated. Please contact support."},
                            status=403)

        token, _ = Token.objects.get_or_create(user=user)

        return Response({
            "token": token.key,
            "user_id": str(user.user_id),  # ✅ Include UUID
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        }, status=200)


class ProfileView(generics.RetrieveUpdateAPIView):
    """
    GET    /api/profile/   -> retrieve logged-in user's profile
    PUT    /api/profile/   -> full update
    PATCH  /api/profile/   -> partial update
    """
    serializer_class = ProfileSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
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

        user.set_password(new_password)
        user.save()

        # Update token
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response(
            {
                "detail": "Password changed successfully.",
                "token": token.key,
            },
            status=status.HTTP_200_OK,
        )


class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
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

        Token.objects.filter(user=user).delete()

        return Response(
            {"detail": "Account deactivated successfully."},
            status=status.HTTP_200_OK,
        )


class AuthViewSet(viewsets.ViewSet):
    permission_classes = [permissions.AllowAny]

    @action(detail=False, methods=['post'])
    def register(self, request):
        # Prevent superuser creation via API
        if any(key in request.data for key in ['is_staff', 'is_superuser', 'is_active']):
            return Response(
                {"detail": "Cannot set privileged fields via registration."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = RegisterSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.save()
            token, _ = Token.objects.get_or_create(user=user)
            return Response({
                "user_id": user.user_id,
                "email": user.email,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "token": token.key,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=['post'])
    def login(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        if not email or not password:
            return Response({"detail": "Email and password required."}, status=400)

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials."}, status=400)

        user = authenticate(request, username=email, password=password)

        if not user:
            return Response({"detail": "Invalid credentials."}, status=400)

        if not user.is_active:
            return Response({"detail": "Account is deactivated. Please contact support."}, status=403)

        token, _ = Token.objects.get_or_create(user=user)

        # Return complete user data
        return Response({
            "token": token.key,
            "user_id": str(user.user_id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        }, status=200)

    @action(detail=False, methods=['post'], permission_classes=[permissions.IsAuthenticated])
    def logout(self, request):
        if request.auth:
            request.auth.delete()
        return Response({"detail": "Logged out successfully."}, status=200)


class UserViewSet(viewsets.ModelViewSet):
    serializer_class = UserSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return User.objects.filter(pk=self.request.user.pk)

    def get_object(self):
        return self.request.user

    @action(detail=False, methods=['get', 'patch'])
    def profile(self, request):
        user = request.user
        if request.method == 'GET':
            serializer = ProfileSerializer(user)
            return Response(serializer.data)

        elif request.method == 'PATCH':
            serializer = ProfileSerializer(user, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()
                return Response(serializer.data)
            return Response(serializer.errors, status=400)

    @action(detail=False, methods=['post'])
    def change_password(self, request):
        serializer = ChangePasswordSerializer(
            data=request.data,
            context={"request": request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        new_password = serializer.validated_data["new_password"]
        user.set_password(new_password)
        user.save()

        # Update token
        Token.objects.filter(user=user).delete()
        token = Token.objects.create(user=user)

        return Response({
            "detail": "Password changed successfully.",
            "token": token.key,
        })

    @action(detail=False, methods=['post'])
    def deactivate(self, request):
        serializer = DeactivateAccountSerializer(
            data=request.data,
            context={'request': request}
        )
        serializer.is_valid(raise_exception=True)

        user = request.user
        user.is_active = False
        user.save()

        Token.objects.filter(user=user).delete()
        return Response({"detail": "Account deactivated successfully."})

def logout_view(request):
    """Logout view for template-based logout"""
    auth_logout(request)
    messages.success(request, "You have been logged out successfully.")
    return redirect('login')

# API Logout view (for token-based logout)
class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        if request.auth:
            request.auth.delete()
        return Response(
            {"detail": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )



def admin_required(function=None):
    """Decorator to ensure user is admin/superuser"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (u.is_staff or u.is_superuser),
        login_url='/admin/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator


@admin_required
def admin_dashboard(request):
    """Admin dashboard overview"""
    total_users = User.objects.count()
    active_users = User.objects.filter(is_active=True).count()
    staff_users = User.objects.filter(is_staff=True).count()

    context = {
        'total_users': total_users,
        'active_users': active_users,
        'staff_users': staff_users,
    }
    return render(request, 'admin/dashboard.html', context)


@admin_required
def user_management(request):
    """User management page with search and filtering"""
    users = User.objects.all().order_by('-created_at')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        users = users.filter(
            Q(email__icontains=search_query) |
            Q(first_name__icontains=search_query) |
            Q(last_name__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter == 'active':
        users = users.filter(is_active=True)
    elif status_filter == 'inactive':
        users = users.filter(is_active=False)
    elif status_filter == 'staff':
        users = users.filter(is_staff=True)

    # Pagination
    paginator = Paginator(users, 20)  # 20 users per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'search_query': search_query,
        'status_filter': status_filter,
        'total_count': users.count(),
    }
    return render(request, 'admin/user_management.html', context)


@admin_required
def user_detail(request, user_id):
    """User detail view"""
    user = get_object_or_404(User, user_id=user_id)

    if request.method == 'POST':
        # Handle user updates
        user.first_name = request.POST.get('first_name', user.first_name)
        user.last_name = request.POST.get('last_name', user.last_name)
        user.email = request.POST.get('email', user.email)
        user.is_active = 'is_active' in request.POST
        user.is_staff = 'is_staff' in request.POST

        # Only superusers can grant superuser status
        if request.user.is_superuser:
            user.is_superuser = 'is_superuser' in request.POST

        user.save()
        messages.success(request, f'User {user.email} updated successfully')
        return redirect('admin_user_detail', user_id=user_id)

    context = {
        'managed_user': user,
        'can_edit_superuser': request.user.is_superuser,
    }
    return render(request, 'admin/user_detail.html', context)


@admin_required
def toggle_user_status(request, user_id):
    """Toggle user active status (AJAX)"""
    if request.method == 'POST' and request.headers.get('x-requested-with') == 'XMLHttpRequest':
        user = get_object_or_404(User, user_id=user_id)
        user.is_active = not user.is_active
        user.save()

        return JsonResponse({
            'success': True,
            'is_active': user.is_active,
            'message': f'User {"activated" if user.is_active else "deactivated"} successfully'
        })
    return JsonResponse({'success': False}, status=400)


@admin_required
def create_user(request):
    """Create new user (admin only)"""
    if request.method == 'POST':
        email = request.POST.get('email')
        first_name = request.POST.get('first_name')
        last_name = request.POST.get('last_name')
        password = request.POST.get('password')
        is_staff = 'is_staff' in request.POST
        is_active = 'is_active' in request.POST

        if User.objects.filter(email=email).exists():
            messages.error(request, 'A user with this email already exists.')
        else:
            user = User.objects.create_user(
                email=email,
                password=password,
                first_name=first_name,
                last_name=last_name,
                is_staff=is_staff,
                is_active=is_active
            )
            messages.success(request, f'User {email} created successfully')
            return redirect('admin_user_management')

    return render(request, 'admin/create_user.html')


# API Views for Admin
class AdminUserViewSet(viewsets.ViewSet):
    permission_classes = [permissions.IsAdminUser]

    @action(detail=False, methods=['get'])
    def user_stats(self, request):
        """Get user statistics for admin dashboard"""
        total_users = User.objects.count()
        active_users = User.objects.filter(is_active=True).count()
        new_today = User.objects.filter(created_at__date=timezone.now().date()).count()

        return Response({
            'total_users': total_users,
            'active_users': active_users,
            'new_today': new_today,
        })

    @action(detail=False, methods=['post'])
    def bulk_action(self, request):
        """Perform bulk actions on users"""
        user_ids = request.data.get('user_ids', [])
        action_type = request.data.get('action')

        if not user_ids:
            return Response({'error': 'No users selected'}, status=400)

        users = User.objects.filter(user_id__in=user_ids)

        if action_type == 'activate':
            users.update(is_active=True)
            message = f'{users.count()} users activated'
        elif action_type == 'deactivate':
            users.update(is_active=False)
            message = f'{users.count()} users deactivated'
        elif action_type == 'delete':
            count = users.count()
            users.delete()
            message = f'{count} users deleted'
        else:
            return Response({'error': 'Invalid action'}, status=400)

        return Response({'message': message})