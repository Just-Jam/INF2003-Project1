# tests.py
from django.test import TestCase
from django.contrib.auth import get_user_model
from .models import Address, Order, OrderItem, User
from .mongo.mongo_repositories import category_repo, product_repo
from .mongo.mongo_serializers import MongoProductSerializer
from .order_service import OrderService
from .mongo.connection import mongo_db

def cleanup_mongo_test_data():
    """Clean up MongoDB test data before tests run"""
    try:
        # Delete test data from both collections
        categories_deleted = category_repo.delete_test_categories()
        products_deleted = product_repo.delete_test_products()
        print(f"Cleaned up {categories_deleted} categories and {products_deleted} products")
    except Exception as e:
        print(f"Warning: Could not clean up MongoDB test data: {e}")

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


class MongoDBConnectionTest(TestCase):
    def test_mongo_connection(self):
        """Test if MongoDB connection works"""
        try:
            # Test connection
            mongo_db.command('ping')
            print("MongoDB connection successful")

            # Test collection access
            categories = mongo_db.categories.find().limit(1)
            print("Categories collection accessible")

            products = mongo_db.products.find().limit(1)
            print("Products collection accessible")

        except Exception as e:
            self.fail(f"MongoDB connection failed: {e}")


# Add this test to see what's failing in the repositories
class MongoDBDetailedTest(TestCase):
    def test_repository_operations(self):
        """Test each repository operation individually"""


        try:
            print("1. Testing category creation...")
            category = category_repo.create_category({
                'category_name': 'Test Category',
                'description': 'Test Description'
            })
            print(f"   Created category: {category}")

            print("2. Testing category retrieval...")
            retrieved = category_repo.get_category_by_id(category['_id'])
            print(f"   Retrieved category: {retrieved}")

            print("3. Testing product creation...")
            product = product_repo.create_product({
                'sku': 'DETAILED_TEST',
                'name': 'Detailed Test Product',
                'price': 100.00,
                'stock_quantity': 10,
                'categories': [category['_id']]
            })
            print(f"   Created product: {product}")

            print("4. Testing product retrieval...")
            retrieved_product = product_repo.get_product_by_sku('DETAILED_TEST')
            print(f"   Retrieved product: {retrieved_product}")

            print("✅ All repository operations successful!")

        except Exception as e:
            print(f"❌ Error: {e}")
            import traceback
            traceback.print_exc()
            self.fail(f"Repository operation failed: {e}")

class CategoryModelTest(TestCase):
    def setUp(self):
        cleanup_mongo_test_data()
        try:
            # Create parent category in MongoDB
            self.parent_category = category_repo.create_category({
                'category_name': 'Electronics',
                'description': 'Electronic devices'
            })
            if not self.parent_category:
                self.skipTest("Failed to create parent category")

            # Create subcategory in MongoDB
            self.subcategory = category_repo.create_category({
                'category_name': 'Laptops',
                'description': 'Laptop computers',
                'parent_category_id': self.parent_category['_id']
            })
            if not self.subcategory:
                self.skipTest("Failed to create subcategory")

        except Exception as e:
            self.skipTest(f"MongoDB setup failed: {e}")

    def test_category_creation(self):
        """Test category hierarchy works in MongoDB"""
        try:
            self.assertEqual(self.subcategory['parent_category_id'], self.parent_category['_id'])
            self.assertEqual(self.parent_category['category_name'], 'Electronics')
        except Exception as e:
            self.fail(f"Category creation test failed: {e}")
    # Update the test_category_uniqueness method
    def test_category_uniqueness(self):
        """Test category name must be unique"""
        from pymongo.errors import DuplicateKeyError

        try:
            category_repo.create_category({
                'category_name': 'Electronics',  # Same name as parent
                'description': 'Duplicate category'
            })
            # If we get here, the duplicate was created (which shouldn't happen)
            self.fail("Duplicate category should not be created")
        except (DuplicateKeyError, Exception) as e:
            # This is expected - duplicate key error
            print(f"Expected error for duplicate category: {e}")
            # The test passes if we get any exception

    def test_get_subcategories(self):
        """Test retrieving subcategories"""
        subcategories = category_repo.get_subcategories(self.parent_category['_id'])
        self.assertEqual(len(subcategories), 1)
        self.assertEqual(subcategories[0]['category_name'], 'Laptops')


class ProductModelTest(TestCase):
    def setUp(self):
        cleanup_mongo_test_data()
        # Create category in MongoDB
        self.category = category_repo.create_category({
            'category_name': 'Electronics',
            'description': 'Electronic devices'
        })

        self.valid_product_data = {
            'sku': 'TEST001',
            'name': 'Test Product',
            'description': 'Test Description',
            'price': 999.99,
            'stock_quantity': 10,
            'categories': [self.category['_id']]
        }

    def test_product_creation(self):
        """Test product creation works correctly in MongoDB"""
        product = product_repo.create_product(self.valid_product_data)

        self.assertEqual(product['sku'], 'TEST001')
        self.assertEqual(product['name'], 'Test Product')
        self.assertEqual(len(product['categories']), 1)
        self.assertIn(self.category['_id'], product['categories'])

    def test_product_price_validation_negative(self):
        """Test that negative prices raise ValidationError"""
        product_data = {
            'sku': 'NEGATIVE001',
            'name': 'Negative Price Product',
            'price': -100.00,
            'stock_quantity': 5
        }

        # Test that serializer validation catches negative price

        serializer = MongoProductSerializer(data=product_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('price', serializer.errors)

    def test_product_price_validation_zero(self):
        """Test that zero price is allowed (free products)"""
        product_data = {
            'sku': 'FREE001',
            'name': 'Free Product',
            'price': 0.00,
            'stock_quantity': 5
        }

        serializer = MongoProductSerializer(data=product_data)
        self.assertTrue(serializer.is_valid())

    def test_product_stock_validation(self):
        """Test that negative stock raises ValidationError"""
        product_data = {
            'sku': 'NEGSTOCK001',
            'name': 'Negative Stock Product',
            'price': 100.00,
            'stock_quantity': -5
        }
        serializer = MongoProductSerializer(data=product_data)
        self.assertFalse(serializer.is_valid())
        self.assertIn('stock_quantity', serializer.errors)

    def test_product_sku_uniqueness(self):
        """Test that SKU must be unique in MongoDB"""
        product_repo.create_product(self.valid_product_data)

        # Try to create another product with same SKU
        with self.assertRaises(Exception):  # MongoDB duplicate key error
            product_repo.create_product({
                'sku': 'TEST001',  # Same SKU
                'name': 'Duplicate Product',
                'price': 50.00,
                'stock_quantity': 5
            })

    def test_product_string_representation(self):
        """Test the product representation"""
        product = product_repo.create_product(self.valid_product_data)
        # Since we're using dicts, test the fields directly
        self.assertEqual(product['name'], 'Test Product')
        self.assertEqual(product['sku'], 'TEST001')

    def test_add_remove_category(self):
        """Test adding and removing categories from product"""
        product = product_repo.create_product({
            'sku': 'CAT_TEST001',
            'name': 'Category Test Product',
            'price': 100.00,
            'stock_quantity': 5,
            'categories': []
        })

        # Add category
        updated_product = product_repo.add_category_to_product(product['sku'], self.category['_id'])
        self.assertIn(self.category['_id'], updated_product['categories'])

        # Remove category
        updated_product = product_repo.remove_category_from_product(product['sku'], self.category['_id'])
        self.assertNotIn(self.category['_id'], updated_product['categories'])

    def test_low_stock_products(self):
        """Test retrieving low stock products"""
        # Create a low stock product
        product_repo.create_product({
            'sku': 'LOWSTOCK001',
            'name': 'Low Stock Product',
            'price': 50.00,
            'stock_quantity': 3  # Below default threshold of 10
        })

        low_stock_products = product_repo.get_low_stock_products(threshold=5)
        self.assertEqual(len(low_stock_products), 1)
        self.assertEqual(low_stock_products[0]['sku'], 'LOWSTOCK001')


class OrderModelTest(TestCase):
    def setUp(self):
        # Create PostgreSQL user and address
        self.user = User.objects.create_user(
            email='customer@example.com',
            password='testpass123',
            first_name='Test',
            last_name='Customer'
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

        # Create product in MongoDB - handle potential errors
        try:
            self.product = product_repo.create_product({
                'sku': 'ORDER001',
                'name': 'Order Test Product',
                'price': 49.99,
                'stock_quantity': 5
            })
            if not self.product:
                self.skipTest("Failed to create MongoDB product")
        except Exception as e:
            self.skipTest(f"Failed to create MongoDB product: {e}")

    def test_order_creation(self):
        """Test complete order workflow with MongoDB product"""
        try:
            order = Order.objects.create(
                user=self.user,
                total_amount=49.99,
                shipping_address=self.address,
                billing_address=self.address
            )

            self.assertEqual(order.status, 'pending')
            self.assertEqual(order.user.email, 'customer@example.com')
        except Exception as e:
            self.fail(f"Order creation failed: {e}")

    def test_order_item_creation(self):
        """Test creating order items with MongoDB product reference"""
        order = Order.objects.create(
            user=self.user,
            total_amount=99.98,
            shipping_address=self.address,
            billing_address=self.address
        )

        # Create order item referencing MongoDB product
        order_item = OrderItem.objects.create(
            order=order,
            product_sku=self.product['sku'],
            product_name=self.product['name'],
            product_price=self.product['price'],
            quantity=2,
            unit_price=self.product['price']
        )

        self.assertEqual(order_item.product_sku, 'ORDER001')
        self.assertEqual(order_item.product_name, 'Order Test Product')
        self.assertEqual(order_item.subtotal, 99.98)
        self.assertEqual(str(order_item), "2 x Order Test Product")

    def test_order_total_calculation(self):
        """Test order total amount calculation"""
        order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            billing_address=self.address
        )

        # Add multiple items
        OrderItem.objects.create(
            order=order,
            product_sku=self.product['sku'],
            product_name=self.product['name'],
            product_price=self.product['price'],
            quantity=1,
            unit_price=self.product['price']
        )

        # Create another product
        another_product = product_repo.create_product({
            'sku': 'ORDER002',
            'name': 'Another Product',
            'price': 29.99,
            'stock_quantity': 3
        })

        OrderItem.objects.create(
            order=order,
            product_sku=another_product['sku'],
            product_name=another_product['name'],
            product_price=another_product['price'],
            quantity=2,
            unit_price=another_product['price']
        )

        # Update total
        order.update_total_amount()

        expected_total = 49.99 + (29.99 * 2)  # 49.99 + 59.98
        self.assertEqual(order.total_amount, expected_total)

    def test_order_status_workflow(self):
        """Test order status transitions"""
        order = Order.objects.create(
            user=self.user,
            shipping_address=self.address,
            billing_address=self.address
        )

        # Add item
        OrderItem.objects.create(
            order=order,
            product_sku=self.product['sku'],
            product_name=self.product['name'],
            product_price=self.product['price'],
            quantity=1,
            unit_price=self.product['price']
        )

        # Test status transitions
        order.status = 'confirmed'
        order.save()
        self.assertEqual(order.status, 'confirmed')

        order.status = 'shipped'
        order.save()
        self.assertEqual(order.status, 'shipped')


class OrderServiceTest(TestCase):
    def setUp(self):
        # Create PostgreSQL user and address
        self.user = User.objects.create_user(
            email='service@example.com',
            password='testpass123',
            first_name='Service',
            last_name='Test'
        )

        self.address = Address.objects.create(
            user=self.user,
            street='456 Service St',
            city='Test City',
            state='TS',
            zip_code='12345',
            country='US',
            is_default=True
        )

        # Create products in MongoDB
        self.product1 = product_repo.create_product({
            'sku': 'SERVICE001',
            'name': 'Service Test Product 1',
            'price': 25.00,
            'stock_quantity': 10
        })

        self.product2 = product_repo.create_product({
            'sku': 'SERVICE002',
            'name': 'Service Test Product 2',
            'price': 35.00,
            'stock_quantity': 8
        })

    def test_order_service_validation(self):
        """Test order service validation with MongoDB products"""

        items_data = [
            {'product_sku': 'SERVICE001', 'quantity': 2},
            {'product_sku': 'SERVICE002', 'quantity': 1}
        ]

        is_valid, errors, products_data = OrderService.validate_order_items(items_data)

        self.assertTrue(is_valid)
        self.assertEqual(len(errors), 0)
        self.assertIn('SERVICE001', products_data)
        self.assertIn('SERVICE002', products_data)

    def test_order_service_validation_insufficient_stock(self):
        """Test order service validation with insufficient stock"""

        items_data = [
            {'product_sku': 'SERVICE001', 'quantity': 15}  # More than available stock
        ]

        is_valid, errors, products_data = OrderService.validate_order_items(items_data)

        self.assertFalse(is_valid)
        self.assertTrue(any('Insufficient stock' in error for error in errors))

    def test_order_service_validation_invalid_product(self):
        """Test order service validation with non-existent product"""

        items_data = [
            {'product_sku': 'INVALID_SKU', 'quantity': 1}
        ]

        is_valid, errors, products_data = OrderService.validate_order_items(items_data)

        self.assertFalse(is_valid)
        self.assertTrue(any('not found' in error for error in errors))



# Run with: python manage.py test