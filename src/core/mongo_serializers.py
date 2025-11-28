# mongo_serializers.py
from rest_framework import serializers
from .mongo_repositories import category_repo, product_repo
from decimal import Decimal


class MongoCategorySerializer(serializers.Serializer):
    _id = serializers.CharField(read_only=True)
    category_name = serializers.CharField(max_length=100)
    description = serializers.CharField(required=False, allow_blank=True)
    parent_category_id = serializers.CharField(required=False, allow_null=True)
    created_at = serializers.DateTimeField(read_only=True)

    def validate_category_name(self, value):
        existing_category = category_repo.get_category_by_name(value)
        if existing_category:
            if hasattr(self, 'instance') and self.instance and existing_category['_id'] == self.instance['_id']:
                return value
            raise serializers.ValidationError("Category name already exists")
        return value

    def validate_parent_category_id(self, value):
        if value and not category_repo.get_category_by_id(value):
            raise serializers.ValidationError("Parent category does not exist")
        return value

    def create(self, validated_data):
        return category_repo.create_category(validated_data)

    def update(self, instance, validated_data):
        return category_repo.update_category(instance['_id'], validated_data)


class MongoProductSerializer(serializers.Serializer):
    sku = serializers.CharField(max_length=50)
    name = serializers.CharField(max_length=255)
    description = serializers.CharField(required=False, allow_blank=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2)
    stock_quantity = serializers.IntegerField(min_value=0)
    is_active = serializers.BooleanField(default=True)
    categories = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        default=list
    )
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)

    def validate_sku(self, value):
        if hasattr(self, 'instance') and self.instance and self.instance.get('sku') == value:
            return value
        if product_repo.get_product_by_sku(value):
            raise serializers.ValidationError("Product SKU already exists")
        return value

    def validate_categories(self, value):
        if value:
            existing_categories = category_repo.get_categories_by_ids(value)
            if len(existing_categories) != len(value):
                raise serializers.ValidationError("One or more categories do not exist")
        return value

    def validate_price(self, value):
        if value < Decimal('0'):
            raise serializers.ValidationError("Price cannot be negative")
        return value

    def create(self, validated_data):
        return product_repo.create_product(validated_data)

    def update(self, instance, validated_data):
        return product_repo.update_product(instance['sku'], validated_data)