# core/serializers.py
from decimal import Decimal

from django.contrib.auth import get_user_model
from rest_framework import serializers
from django.contrib.auth.password_validation import validate_password
from .models import Order, OrderItem, Address
from .mongo.mongo_repositories import product_repo
from .order_service import OrderService

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
        validated_data.update({
            'is_staff': False,
            'is_superuser': False,
            'is_active': True
        })
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


class AddressSerializer(serializers.ModelSerializer):
    address_id = serializers.UUIDField(read_only=True)
    user = serializers.UUIDField(source='user.id', read_only=True)

    class Meta:
        model = Address
        fields = (
            'address_id',
            'user',
            'street',
            'city',
            'state',
            'zip_code',
            'country',
            'is_default',
            'address_type',
        )
        read_only_fields = ('address_id', 'user')

    def validate_address_type(self, value):
        allowed = [choice[0] for choice in Address.ADDRESS_TYPES]
        if value not in allowed:
            raise serializers.ValidationError("Invalid address_type")
        return value

    def validate_zip_code(self, value):
        if not value or not value.strip():
            raise serializers.ValidationError("zip_code is required")
        return value.strip()

    def validate(self, data):
        """
        Additional validation that requires multiple fields
        """
        required_fields = ['street', 'city', 'state', 'zip_code', 'country']
        for field in required_fields:
            if field not in data or not data[field] or not str(data[field]).strip():
                raise serializers.ValidationError({field: f"{field.replace('_', ' ').title()} is required"})
        return data

    def create(self, validated_data):
        request = self.context.get('request')
        if not request or not request.user.is_authenticated:
            raise serializers.ValidationError("Authenticated request required")

        user = request.user
        is_default = validated_data.get('is_default', False)

        # Create the address
        address = Address.objects.create(user=user, **validated_data)

        return address

    def update(self, instance, validated_data):
        """
        Custom update method
        """
        return super().update(instance, validated_data)



# serializers.py - Add these serializers
# ========== ORDER SERIALIZERS ==========

class OrderItemCreateSerializer(serializers.Serializer):
    product_sku = serializers.CharField(max_length=50)
    quantity = serializers.IntegerField(min_value=1)

    def validate_product_sku(self, value):
        """Ensure product exists and is active in MongoDB."""
        product = product_repo.get_product_by_sku(value)
        if not product:
            raise serializers.ValidationError("Product with this SKU does not exist")
        if not product.get('is_active', False):
            raise serializers.ValidationError("Product is not active")
        return value


class OrderItemSerializer(serializers.ModelSerializer):
    product_details = serializers.SerializerMethodField()

    class Meta:
        model = OrderItem
        fields = ['order_item_id', 'product_id', 'quantity', 'unit_price', 'product_details']
        read_only_fields = ['order_item_id']

    def get_product_details(self, obj):
        """Get full product details from MongoDB"""
        product = product_repo.get_product_by_sku(obj.product_id)
        return product if product else None


class OrderCreateSerializer(serializers.ModelSerializer):
    items = OrderItemCreateSerializer(many=True, required=True)
    shipping_address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.all())
    billing_address = serializers.PrimaryKeyRelatedField(queryset=Address.objects.all())

    class Meta:
        model = Order
        fields = ['shipping_address', 'billing_address', 'items']

    def validate_shipping_address(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Shipping address must belong to the authenticated user")
        if value.address_type not in ('shipping', 'both'):
            raise serializers.ValidationError("Address is not a shipping address")
        return value

    def validate_billing_address(self, value):
        user = self.context['request'].user
        if value.user != user:
            raise serializers.ValidationError("Billing address must belong to the authenticated user")
        if value.address_type not in ('billing', 'both'):
            raise serializers.ValidationError("Address is not a billing address")
        return value

    def validate(self, data):
        """Validate items and attach current product price/name for order creation."""
        items_data = data.get('items', [])
        if not items_data:
            raise serializers.ValidationError("Order must contain at least one item")

        enriched_items = []
        errors = {}
        for idx, item in enumerate(items_data):
            sku = item.get('product_sku')
            product = product_repo.get_product_by_sku(sku)
            if not product:
                errors[idx] = f"Product {sku} does not exist"
                continue
            if not product.get('is_active', False):
                errors[idx] = f"Product {sku} is not active"
                continue

            # attach unit_price and product_name for downstream create
            unit_price = Decimal(str(product.get('price', 0)))
            enriched = {
                'product_sku': sku,
                'quantity': item.get('quantity'),
                'unit_price': unit_price,
                'product_name': product.get('name')
            }
            enriched_items.append(enriched)

        if errors:
            raise serializers.ValidationError({'items': errors})

        # Optionally still use OrderService.validate_order_items if you have additional rules
        is_valid, svc_errors, _ = OrderService.validate_order_items([{'product_sku': i['product_sku'], 'quantity': i['quantity']} for i in enriched_items])
        if not is_valid:
            raise serializers.ValidationError({'items': svc_errors})

        # replace items in validated data with enriched items used by create()
        data['items'] = enriched_items
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

        # Create order
        order = Order.objects.create(
            user=user,
            shipping_address=validated_data['shipping_address'],
            billing_address=validated_data['billing_address']
        )

        # Create order items and calculate total
        total = 0
        for item_data in items_data:
            product = product_repo.get_product_by_sku(item_data['product_id'])
            if not product:
                order.delete()
                raise serializers.ValidationError(f"Product {item_data['product_id']} not found")

            order_item = OrderItem.objects.create(
                order=order,
                product_id=item_data['product_id'],
                quantity=item_data['quantity'],
                unit_price=product.get('price', 0)
            )
            total += (order_item.quantity * order_item.unit_price)

        order.total_amount = total
        order.save()
        return order


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True, source='order_items')  # Add source='order_items'
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
