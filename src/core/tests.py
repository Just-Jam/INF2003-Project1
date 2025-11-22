# tests.py
import uuid
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Category, Product, Order, Address
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction

User = get_user_model()

class UserModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='test@example.com',
            password='testpass123',
            first_name='John',
            last_name='Doe'
        )

    def test_user_creation(self):
        """Test user creation works correctly"""
        self.assertEqual(self.user.email, 'test@example.com')
        self.assertEqual(self.user.first_name, 'John')
        self.assertTrue(self.user.is_active)
        self.assertFalse(self.user.is_staff)

    def test_user_str_representation(self):
        """Test string representation"""
        self.assertEqual(str(self.user), 'test@example.com')


class CategoryModelTest(TestCase):
    def setUp(self):
        self.parent_category = Category.objects.create(
            category_name='Electronics',
            description='Electronic devices'
        )
        self.subcategory = Category.objects.create(
            category_name='Laptops',
            description='Laptop computers',
            parent_category=self.parent_category
        )

    def test_category_creation(self):
        """Test category hierarchy works"""
        self.assertEqual(self.subcategory.parent_category, self.parent_category)
        self.assertEqual(str(self.parent_category), 'Electronics')


class ProductModelTest(TestCase):
    def setUp(self):
        self.category = Category.objects.create(category_name='Electronics')
        self.valid_product_data = {
            'sku': 'TEST001',
            'name': 'Test Product',
            'description': 'Test Description',
            'price': 999.99,
            'stock_quantity': 10
        }

    def test_product_creation(self):
        """Test product creation works correctly"""
        product = Product.objects.create(**self.valid_product_data)
        product.categories.add(self.category)

        self.assertEqual(product.sku, 'TEST001')
        self.assertEqual(product.categories.count(), 1)
        self.assertIn(self.category, product.categories.all())

    def test_product_price_validation_negative(self):
        """Test that negative prices raise ValidationError"""
        product = Product(
            sku='NEGATIVE001',
            name='Negative Price Product',
            price=-100.00
        )

        # Test full_clean() raises ValidationError
        with self.assertRaises(ValidationError) as context:
            product.full_clean()

        self.assertIn('price', context.exception.error_dict)

    def test_product_price_validation_zero(self):
        """Test that zero price is allowed (free products)"""
        product = Product(
            sku='FREE001',
            name='Free Product',
            price=0.00
        )

        # This should not raise an exception
        try:
            product.full_clean()
        except ValidationError:
            self.fail("Zero price should be allowed for free products")

    def test_product_stock_validation(self):
        """Test that negative stock raises ValidationError"""
        product = Product(
            sku='NEGSTOCK001',
            name='Negative Stock Product',
            price=100.00,
            stock_quantity=-5
        )

        with self.assertRaises(ValidationError) as context:
            product.full_clean()

        self.assertIn('stock_quantity', context.exception.error_dict)

    def test_product_sku_uniqueness(self):
        """Test that SKU must be unique"""
        Product.objects.create(**self.valid_product_data)

        # Try to create another product with same SKU
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Product.objects.create(
                    sku='TEST001',  # Same SKU
                    name='Duplicate Product',
                    price=50.00,
                    stock_quantity=5
                )

    def test_product_string_representation(self):
        """Test the __str__ method"""
        product = Product.objects.create(**self.valid_product_data)
        self.assertEqual(str(product), "Test Product (TEST001)")



class OrderModelTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='testpass123'
        )
        self.address = Address.objects.create(
            user=self.user,
            street='123 Main St',
            city='Test City',
            state='TS',
            zip_code='12345',
            country='US',
            is_default=True
        )
        self.product = Product.objects.create(
            sku='ORDER001',
            name='Order Test Product',
            price=49.99,
            stock_quantity=5
        )

    def test_order_creation(self):
        """Test complete order workflow"""
        order = Order.objects.create(
            user=self.user,
            total_amount=49.99,
            shipping_address=self.address,
            billing_address=self.address
        )

        self.assertEqual(order.status, 'pending')
        self.assertEqual(order.user.email, 'customer@example.com')

# Run with: python manage.py test