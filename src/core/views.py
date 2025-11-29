# core/views.py
import math
import traceback

from django.contrib.auth.decorators import user_passes_test
from django.core.exceptions import PermissionDenied
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q
from django.http import JsonResponse, Http404
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic import TemplateView
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework import permissions, generics
from rest_framework.reverse import reverse

from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.authtoken.models import Token

from .serializers import *
from .models import Order, OrderItem, Address

from django.contrib.auth import authenticate, get_user_model, login as django_login
from django.contrib.auth import logout as auth_logout
from django.shortcuts import redirect
from django.contrib import messages

from .mongo.unified_repositories import UnifiedProductRepository
from functools import wraps
from .models import Address
from .mongo.mongo_repositories import product_repo

#Get your custom User model
User = get_user_model()

def admin_required(function=None):
    """Decorator to ensure user is admin/superuser"""
    actual_decorator = user_passes_test(
        lambda u: u.is_authenticated and (u.is_staff or u.is_superuser),
        login_url='/login/'
    )
    if function:
        return actual_decorator(function)
    return actual_decorator

def admin_required_api(view_func):
    """Decorator for API views to ensure user is admin/superuser"""
    @wraps(view_func)
    def _wrapped_view(self, request, *args, **kwargs):
        if not request.user.is_authenticated or not (request.user.is_staff or request.user.is_superuser):
            return Response(
                {'detail': 'You do not have permission to perform this action.'},
                status=status.HTTP_403_FORBIDDEN
            )
        return view_func(self, request, *args, **kwargs)
    return _wrapped_view

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

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response({"detail": "Invalid credentials."}, status=400)

        user = authenticate(request, username=email, password=password)
        if not user:
            return Response({"detail": "Invalid credentials."}, status=400)

        if not user.is_active:
            return Response({"detail": "Account is deactivated. Please contact support."}, status=403)

        # Establish a Django session so template views see the user as logged in
        django_login(request, user)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user_id": str(user.user_id),
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

        # Create session for template auth
        django_login(request, user)

        token, _ = Token.objects.get_or_create(user=user)
        return Response({
            "token": token.key,
            "user_id": str(user.user_id),
            "email": user.email,
            "first_name": user.first_name,
            "last_name": user.last_name
        }, status=200)



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

from rest_framework.authentication import TokenAuthentication

class LogoutView(APIView):
    authentication_classes = [TokenAuthentication]  # ✅ Add this
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        print(f"Logout requested by user: {request.user.email}")  # Debug
        if request.auth:
            request.auth.delete()
            print("Token deleted successfully")  # Debug
        return Response(
            {"detail": "Logged out successfully."},
            status=status.HTTP_200_OK,
        )





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
def admin_order_list(request):
    """Admin view to see all orders from all users"""
    orders = Order.objects.all().prefetch_related('order_items', 'user').order_by('-order_date')

    # Search functionality
    search_query = request.GET.get('search', '')
    if search_query:
        orders = orders.filter(
            Q(order_id__icontains=search_query) |
            Q(user__email__icontains=search_query) |
            Q(user__first_name__icontains=search_query) |
            Q(user__last_name__icontains=search_query) |
            Q(status__icontains=search_query)
        )

    # Filter by status
    status_filter = request.GET.get('status', '')
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Pagination
    paginator = Paginator(orders, 20)  # 20 orders per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'search_query': search_query,
        'status_filter': status_filter,
        'status_choices': Order.ORDER_STATUS,
        'total_count': orders.count(),
    }
    return render(request, 'admin/order_management.html', context)

@admin_required
def admin_order_detail(request, order_id):
    """Admin view to see detailed order information"""
    order = get_object_or_404(Order, order_id=order_id)

    # Add product details from MongoDB for each order item
    items_with_products = []
    for item in order.order_items.all():
        product = product_repo.get_product_by_sku(item.product_id)
        item_with_product = {
            'order_item': item,
            'product_name': product.get('name', 'Unknown Product') if product else 'Unknown Product',
            'product_sku': product.get('sku', item.product_id) if product else item.product_id,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'subtotal': item.quantity * item.unit_price,
            'product_id': item.product_id
        }
        items_with_products.append(item_with_product)

    context = {
        'order': order,
        'items': items_with_products,
        'is_admin_view': True
    }
    return render(request, 'admin/order_detail.html', context)

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


# views.py - Update your OrderViewSet
class OrderViewSet(viewsets.ModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related('order_items')

    def get_serializer_class(self):
        if self.action == 'create':
            return OrderCreateSerializer
        return OrderSerializer

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data, context={'request': request})
            serializer.is_valid(raise_exception=True)
            order = serializer.save()

            # Use OrderSerializer for the response, not OrderCreateSerializer
            response_serializer = OrderSerializer(order)
            return Response(response_serializer.data, status=status.HTTP_201_CREATED)

        except serializers.ValidationError as e:
            return Response(e.detail, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            print(f"Order creation error: {str(e)}")
            print(traceback.format_exc())
            return Response(
                {'error': str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    @action(detail=True, methods=['get'])
    def enriched_items(self, request, pk=None):
        """Get order items enriched with current MongoDB product data"""
        order = self.get_object()
        enriched_items = OrderService.get_product_details_for_order(order)
        return Response(enriched_items)

    @action(detail=False, methods=['get'])
    def by_product(self, request):
        """Get orders containing a specific MongoDB product"""
        product_sku = request.query_params.get('product_sku')
        if not product_sku:
            return Response(
                {'error': 'product_sku parameter is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        orders = Order.objects.filter(
            order_items__product_sku=product_sku,
            user=request.user
        ).distinct()

        serializer = self.get_serializer(orders, many=True)
        return Response(serializer.data)


class AdminOrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all().prefetch_related('order_items')
    serializer_class = OrderSerializer
    permission_classes = [permissions.IsAdminUser]

    @action(detail=True, methods=['post'])
    def update_status(self, request, pk=None):
        """Update order status"""
        order = self.get_object()
        new_status = request.data.get('status')

        if new_status not in dict(Order.ORDER_STATUS):
            return Response(
                {'error': 'Invalid status'},
                status=status.HTTP_400_BAD_REQUEST
            )

        order.status = new_status
        order.save()

        serializer = self.get_serializer(order)
        return Response(serializer.data)


class UnifiedSearchView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request):
        search_term = request.query_params.get('q', '')
        source = request.query_params.get('source')  # 'app', 'amazon', 'fashion', or None for all
        limit = int(request.query_params.get('limit', 50))

        if not search_term:
            return Response(
                {'error': 'Search term is required'},
                status=status.HTTP_400_BAD_REQUEST
            )

        repo = UnifiedProductRepository()

        try:
            if source:
                results = repo.search_products_by_source(search_term, source, limit)
            else:
                results = repo.search_all_products(search_term, limit)

            return Response({
                'search_term': search_term,
                'source': source or 'all',
                'results': results,
                'total_count': len(results)
            })

        except Exception as e:
            return Response(
                {'error': f'Search failed: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )


# ========== TEMPLATE VIEWS FOR ORDERS ==========
from django.contrib.auth.decorators import login_required

@login_required(login_url='/login/')
def order_list(request):
    """Display paginated list of user's orders"""
    orders = Order.objects.filter(user=request.user).prefetch_related('order_items').order_by('-order_date')

    paginator = Paginator(orders, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'page_obj': page_obj,
        'orders': page_obj.object_list,
        'total_orders': orders.count()
    }
    return render(request, 'orders/order_list.html', context)


@login_required(login_url='/login/')
def order_detail(request, order_id):
    """Display detailed view of a specific order"""
    order = get_object_or_404(Order, order_id=order_id, user=request.user)

    # Add product details from MongoDB for each order item
    items_with_products = []
    for item in order.order_items.all():
        product = product_repo.get_product_by_sku(item.product_id)
        # Create a dictionary with item info + product details
        item_with_product = {
            'order_item': item,
            'product_name': product.get('name', 'Unknown Product') if product else 'Unknown Product',
            'product_sku': product.get('sku', item.product_id) if product else item.product_id,
            'quantity': item.quantity,
            'unit_price': item.unit_price,
            'subtotal': item.quantity * item.unit_price,
            'product_id': item.product_id
        }
        items_with_products.append(item_with_product)

    context = {
        'order': order,
        'items': items_with_products
    }
    return render(request, 'orders/order_detail.html', context)


@login_required(login_url='/login/')
def order_create(request):
    """Create a new order"""
    if request.method == 'POST':
        shipping_address_id = request.POST.get('shipping_address')
        billing_address_id = request.POST.get('billing_address')

        try:
            shipping_address = Address.objects.get(address_id=shipping_address_id, user=request.user)
            billing_address = Address.objects.get(address_id=billing_address_id, user=request.user)
        except Address.DoesNotExist:
            messages.error(request, 'Invalid address selected')
            return redirect('order_create')

        # Collect items from form
        items = []
        item_count = int(request.POST.get('item_count', 0))

        for i in range(item_count):
            product_id = request.POST.get(f'product_sku_{i}')
            quantity_str = request.POST.get(f'quantity_{i}')

            if product_id and quantity_str:
                try:
                    quantity = int(quantity_str)
                    if quantity > 0:
                        items.append({'product_id': product_id, 'quantity': quantity})
                except (ValueError, TypeError):
                    continue

        if not items:
            messages.error(request, 'Order must contain at least one item')
            return redirect('order_create')

        # Create order using serializer
        serializer = OrderCreateSerializer(
            data={
                'shipping_address': shipping_address_id,
                'billing_address': billing_address_id,
                'items': items
            },
            context={'request': request}
        )

        if serializer.is_valid():
            order = serializer.save()
            messages.success(request, f'Order {order.order_id} created successfully!')
            return redirect('order_detail', order_id=order.order_id)
        else:
            for error in serializer.errors.values():
                messages.error(request, str(error))
            return redirect('order_create')

    # GET request - show form
    user_addresses = Address.objects.filter(user=request.user)

    # Debug: Check if products exist in MongoDB directly
    from .mongo.connection import mongo_db
    products_col = mongo_db['products']
    direct_count = products_col.count_documents({'is_active': True})
    print(f"DEBUG: Direct MongoDB count: {direct_count}")

    products = product_repo.get_all_products(filters={'is_active': True})
    print(f"DEBUG: Products from repo: {len(products) if products else 0}")
    if products:
        print(f"DEBUG: First product: {products[0]}")

    # Convert MongoDB documents to JSON-serializable format
    products_list = []
    if products:
        for product in products:
            # Convert ObjectId to string if present
            product_dict = {
                'sku': product.get('sku', ''),
                'name': product.get('name', ''),
                'price': float(product.get('price', 0)),
                'stock_quantity': product.get('stock_quantity', 0),
                'description': product.get('description', ''),
                'is_active': product.get('is_active', True)
            }
            products_list.append(product_dict)

    context = {
        'addresses': user_addresses,
        'products': products_list
    }
    return render(request, 'orders/order_create.html', context)


def debug_products(request):
    """Debug endpoint to check products"""
    from .mongo.connection import mongo_db

    # Check direct MongoDB
    products_col = mongo_db['products']
    direct_products = list(products_col.find({'is_active': True}))

    # Check via repository
    repo_products = product_repo.get_all_products(filters={'is_active': True})

    return JsonResponse({
        'direct_mongo_count': len(direct_products),
        'repo_count': len(repo_products) if repo_products else 0,
        'direct_products': [{'sku': p.get('sku'), 'name': p.get('name'), 'price': p.get('price')} for p in direct_products[:3]],
        'repo_products': repo_products[:3] if repo_products else []
    })

def populate_sample_products(request):
    """Quick endpoint to populate sample products"""
    from .mongo.connection import mongo_db
    from datetime import datetime

    products_col = mongo_db['products']

    # Sample products
    products = [
        {
            'sku': 'PROD001',
            'name': 'Premium Laptop',
            'description': 'High-performance laptop for professionals',
            'price': 999.99,
            'stock_quantity': 10,
            'is_active': True,
            'categories': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'sku': 'PROD002',
            'name': 'Wireless Mouse',
            'description': 'Ergonomic wireless mouse with precision tracking',
            'price': 29.99,
            'stock_quantity': 50,
            'is_active': True,
            'categories': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'sku': 'PROD003',
            'name': 'Bluetooth Headphones',
            'description': 'Premium noise-cancelling headphones',
            'price': 149.99,
            'stock_quantity': 25,
            'is_active': True,
            'categories': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        },
        {
            'sku': 'PROD004',
            'name': 'Wireless Keyboard',
            'description': 'Mechanical keyboard with RGB lighting',
            'price': 79.99,
            'stock_quantity': 30,
            'is_active': True,
            'categories': [],
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
        }
    ]

    # Clear existing and insert new
    products_col.delete_many({})
    result = products_col.insert_many(products)

    # Create indexes
    try:
        products_col.create_index('sku', unique=True)
        products_col.create_index('name')
        products_col.create_index('is_active')
    except:
        pass  # Indexes might already exist

    # Verify the products were actually inserted
    count = products_col.count_documents({'is_active': True})

    # Also test the product_repo
    repo_products = product_repo.get_all_products(filters={'is_active': True})

    return JsonResponse({
        'success': True,
        'message': f'Successfully added {len(result.inserted_ids)} products',
        'products_inserted': len(products),
        'direct_mongo_count': count,
        'repo_count': len(repo_products) if repo_products else 0,
        'sample_product': repo_products[0] if repo_products else None
    })

@admin_required
def order_edit(request, order_id):
    """Edit an existing order - ADMIN ONLY"""
    order = get_object_or_404(Order, order_id=order_id)  # Removed user filter - admins can edit any order

    if request.method == 'POST':
        status_new = request.POST.get('status')

        if status_new and status_new in dict(Order.ORDER_STATUS):
            order.status = status_new
            order.save()
            messages.success(request, f'Order {order.order_id} status updated to {status_new}')
        else:
            messages.error(request, 'Invalid status')

        return redirect('order_detail', order_id=order.order_id)

    context = {
        'order': order,
        'status_choices': Order.ORDER_STATUS
    }
    return render(request, 'orders/order_edit.html', context)




# API ViewSet for addresses
class AddressListCreateAPIView(APIView):
    """
    API endpoints for listing and creating addresses
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Get queryset based on user role"""
        if self.request.user.is_staff or self.request.user.is_superuser:
            return Address.objects.all().order_by('user', '-is_default', 'city')
        return Address.objects.filter(user=self.request.user).order_by('-is_default', 'city')

    def get(self, request):
        """List addresses - user sees own, admin sees all"""
        addresses = self.get_queryset()
        serializer = AddressSerializer(addresses, many=True, context={'request': request})  # Add context
        return Response(serializer.data)

    def post(self, request):
        """Create a new address - users can only create for themselves"""
        serializer = AddressSerializer(data=request.data, context={'request': request})  # Add context
        if serializer.is_valid():
            address = serializer.save()  # Let serializer handle user assignment

            # If created as default, clear other defaults for that user
            if address.is_default:
                Address.objects.filter(user=address.user).exclude(pk=address.pk).update(is_default=False)

            return Response(AddressSerializer(address, context={'request': request}).data,
                            status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AddressDetailAPIView(APIView):
    """
    API endpoints for retrieving, updating, and deleting specific addresses
    """
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self, address_id):
        """Helper method to get address with proper permission checking"""
        address = get_object_or_404(Address, address_id=address_id)

        # Users can only access their own addresses unless they're admin
        if not self.request.user.is_staff and not self.request.user.is_superuser:
            if address.user != self.request.user:
                raise PermissionDenied("You can only access your own addresses.")

        return address

    def get(self, request, address_id):
        """Retrieve a specific address"""
        address = self.get_object(address_id)
        serializer = AddressSerializer(address, context={'request': request})  # Add context
        return Response(serializer.data)

    def put(self, request, address_id):
        """Update a specific address (full update)"""
        address = self.get_object(address_id)
        serializer = AddressSerializer(address, data=request.data, context={'request': request})  # Add context
        if serializer.is_valid():
            updated_address = serializer.save()

            # If updated to default, clear other defaults for that user
            if updated_address.is_default:
                Address.objects.filter(user=updated_address.user).exclude(pk=updated_address.pk).update(
                    is_default=False)

            return Response(AddressSerializer(updated_address, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def patch(self, request, address_id):
        """Partial update of a specific address"""
        address = self.get_object(address_id)
        serializer = AddressSerializer(address, data=request.data, partial=True,
                                       context={'request': request})  # Add context
        if serializer.is_valid():
            updated_address = serializer.save()

            # If updated to default, clear other defaults for that user
            if updated_address.is_default:
                Address.objects.filter(user=updated_address.user).exclude(pk=updated_address.pk).update(
                    is_default=False)

            return Response(AddressSerializer(updated_address, context={'request': request}).data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, address_id):
        """Delete a specific address"""
        address = self.get_object(address_id)
        address.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class SetDefaultAddressAPIView(APIView):
    """
    API endpoint to set an address as default
    - Users can only set their own addresses as default
    - Admins can set any address as default
    """
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, address_id):
        """Set a specific address as default"""
        address = get_object_or_404(Address, address_id=address_id)

        # Users can only set their own addresses as default unless they're admin
        if not request.user.is_staff and not request.user.is_superuser:
            if address.user != request.user:
                return Response(
                    {'detail': 'You can only set your own addresses as default.'},
                    status=status.HTTP_403_FORBIDDEN
                )

        # Clear all other defaults for that user and set this one as default
        Address.objects.filter(user=address.user).exclude(pk=address.pk).update(is_default=False)
        address.is_default = True
        address.save(update_fields=['is_default'])

        return Response({
            'success': True,
            'detail': 'Address set as default',
            'address': AddressSerializer(address).data
        })


class AdminAddressManagementAPIView(APIView):
    """
    Admin-only endpoints for address management
    """
    permission_classes = [permissions.IsAuthenticated]

    @admin_required_api
    def get(self, request, user_id=None):
        """Admin: Get all addresses or addresses for a specific user"""
        if user_id:
            addresses = Address.objects.filter(user__id=user_id).order_by('-is_default', 'city')
        else:
            addresses = Address.objects.all().order_by('user', '-is_default', 'city')

        serializer = AddressSerializer(addresses, many=True)
        return Response(serializer.data)

    @admin_required_api
    def post(self, request):
        """Admin: Create an address for any user"""
        serializer = AddressSerializer(data=request.data)
        if serializer.is_valid():
            address = serializer.save()

            # If created as default, clear other defaults for that user
            if address.is_default:
                Address.objects.filter(user=address.user).exclude(pk=address.pk).update(is_default=False)

            return Response(AddressSerializer(address).data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# views.py
class ProductListView(APIView):
    permission_classes = [permissions.AllowAny]

    def get(self, request, page=None):
        # Get page from URL parameter or query parameter
        page = page or int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 50))
        category = request.GET.get('category')

        repo = UnifiedProductRepository()
        products, total_count = repo.get_all_products_paginated(
            page=page,
            page_size=page_size,
            category=category
        )

        return Response({
            'results': products,
            'count': total_count,
            'total_pages': math.ceil(total_count / page_size),
            'current_page': page,
            'page_size': page_size
        })


class ProductDetailView(APIView):
    """
    API endpoint to retrieve a single product by its MongoDB _id
    """
    permission_classes = [permissions.AllowAny]

    def get(self, request, product_id):
        """
        Get a single product by _id

        Query parameters:
        - source: Optional. Specify 'app', 'amazon', or 'fashion' to search specific collection
        """
        source = request.query_params.get('source')

        repo = UnifiedProductRepository()
        product = repo.get_product_by_id(product_id, source=source)

        if not product:
            raise Http404("Product not found")

        return Response(product)
