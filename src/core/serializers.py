# core/serializers.py
from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Order, OrderItem
from .mongo.mongo_repositories import product_repo

User = get_user_model()

class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, validators=[validate_password])
    password_confirm = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'password_confirm')
        # Note: NO is_staff, is_superuser fields!

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        # Ensure new users are never staff/superuser by default
        validated_data.update({
            'is_staff': False,
            'is_superuser': False,
            'is_active': True  # Or your business logic
        })
        user = User.objects.create_user(**validated_data)
        return user

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def validate_first_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("First name must be at least 2 characters long.")
        return value.strip()

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({"password": "Password fields didn't match."})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('user_id', 'email', 'first_name', 'last_name', 'created_at', 'last_login')
        read_only_fields = ('user_id', 'created_at', 'last_login')

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('user_id', 'email', 'first_name', 'last_name', 'created_at', 'last_login')
        read_only_fields = ('user_id', 'email', 'created_at', 'last_login')

    def validate_first_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("First name must be at least 2 characters long.")
        return value.strip()

    def validate_last_name(self, value):
        if len(value.strip()) < 2:
            raise serializers.ValidationError("Last name must be at least 2 characters long.")
        return value.strip()

class ChangePasswordSerializer(serializers.Serializer):
    old_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate_old_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Old password is not correct")
        return value

    def validate(self, data):
        if data['new_password'] != data['new_password_confirm']:
            raise serializers.ValidationError({"new_password": "New passwords don't match"})
        return data

class DeactivateAccountSerializer(serializers.Serializer):
    password = serializers.CharField(required=True)

    def validate_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError("Password is not correct")
        return value

class StaffUserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('email', 'first_name', 'last_name', 'password', 'is_staff')

    def create(self, validated_data):
        password = validated_data.pop('password')
        user = User.objects.create_user(**validated_data)
        user.set_password(password)
        user.save()
        return user


# serializers.py - Add these serializers
class OrderItemCreateSerializer(serializers.Serializer):
    product_sku = serializers.CharField(max_length=50)
    quantity = serializers.IntegerField(min_value=1)

    def validate_product_sku(self, value):
        """Validate product exists in MongoDB"""
        product = product_repo.get_product_by_sku(value)
        if not product:
            raise serializers.ValidationError("Product with this SKU does not exist")
        if not product.get('is_active', False):
            raise serializers.ValidationError("Product is not active")
        return value


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True)

    class Meta:
        model = Order
        fields = ['shipping_address', 'billing_address', 'items']

    def validate(self, data):
        """Validate the entire order"""
        items_data = data.get('items', [])

        if not items_data:
            raise serializers.ValidationError("Order must contain at least one item")

        # Validate items against MongoDB
        is_valid, errors, _ = OrderService.validate_order_items(items_data)
        if not is_valid:
            raise serializers.ValidationError(errors)

        return data

    def create(self, validated_data):
        items_data = validated_data.pop('items')
        user = self.context['request'].user

        try:
            order = OrderService.create_order(validated_data, user, items_data)
            return order
        except ValueError as e:
            raise serializers.ValidationError(str(e))


class OrderItemSerializer(serializers.ModelSerializer):
    current_product_details = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = [
            'order_item_id', 'product_sku', 'product_name',
            'product_price', 'quantity', 'unit_price', 'subtotal',
            'current_product_details'
        ]
        read_only_fields = fields

    def get_current_product_details(self, obj):
        """Get current product info from MongoDB"""
        product = product_repo.get_product_by_sku(obj.product_sku)
        if product:
            return {
                'current_name': product.get('name'),
                'current_price': float(product.get('price', 0)),
                'is_active': product.get('is_active', False),
                'in_stock': product.get('stock_quantity', 0) > 0
            }
        return None


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    user_email = serializers.EmailField(source='user.email', read_only=True)
    shipping_address_details = serializers.SerializerMethodField()
    billing_address_details = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            'order_id', 'user', 'user_email', 'order_date', 'total_amount',
            'status', 'shipping_address', 'billing_address', 'items',
            'shipping_address_details', 'billing_address_details'
        ]
        read_only_fields = ['order_id', 'order_date', 'total_amount']

    def get_shipping_address_details(self, obj):
        return self._get_address_details(obj.shipping_address)

    def get_billing_address_details(self, obj):
        return self._get_address_details(obj.billing_address)

    def _get_address_details(self, address):
        return {
            'street': address.street,
            'city': address.city,
            'state': address.state,
            'zip_code': address.zip_code,
            'country': address.country
        }