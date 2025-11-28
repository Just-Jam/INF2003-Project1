# order_services.py
from .mongo.mongo_repositories import product_repo
from django.db import transaction
from decimal import Decimal


class OrderService:
    @staticmethod
    def validate_order_items(items_data):
        """
        Validate all order items against MongoDB products
        Returns: (is_valid, errors, products_data)
        """
        errors = []
        products_data = {}

        for item in items_data:
            sku = item['product_sku']
            quantity = item['quantity']

            # Get product from MongoDB
            product = product_repo.get_product_by_sku(sku)

            if not product:
                errors.append(f"Product with SKU {sku} not found")
                continue

            if not product.get('is_active', False):
                errors.append(f"Product {sku} is not active")
                continue

            if product['stock_quantity'] < quantity:
                errors.append(f"Insufficient stock for product {sku}. Available: {product['stock_quantity']}")
                continue

            # Store product data for later use
            products_data[sku] = {
                'name': product['name'],
                'price': Decimal(str(product['price'])),
                'current_stock': product['stock_quantity']
            }

        return len(errors) == 0, errors, products_data

    @staticmethod
    @transaction.atomic
    def create_order(order_data, user, items_data):
        """
        Create order with MongoDB product validation
        """
        from .models import Order, OrderItem

        # Validate items against MongoDB
        is_valid, errors, products_data = OrderService.validate_order_items(items_data)
        if not is_valid:
            raise ValueError(f"Order validation failed: {', '.join(errors)}")

        # Create order
        order = Order.objects.create(
            user=user,
            shipping_address=order_data['shipping_address'],
            billing_address=order_data['billing_address']
        )

        # Create order items and update MongoDB stock
        for item_data in items_data:
            sku = item_data['product_sku']
            quantity = item_data['quantity']
            product_data = products_data[sku]

            # Create order item
            OrderItem.objects.create(
                order=order,
                product_sku=sku,
                product_name=product_data['name'],
                product_price=product_data['price'],
                quantity=quantity,
                unit_price=product_data['price']
            )

            # Update MongoDB stock
            new_stock = product_data['current_stock'] - quantity
            product_repo.update_stock(sku, new_stock)

        # Update order total
        order.update_total_amount()

        return order

    @staticmethod
    def get_product_details_for_order(order):
        """
        Enrich order items with current product details from MongoDB
        """
        enriched_items = []

        for item in order.order_items.all():
            current_product = product_repo.get_product_by_sku(item.product_sku)

            enriched_item = {
                'order_item_id': item.order_item_id,
                'product_sku': item.product_sku,
                'product_name': item.product_name,  # Use historical name
                'ordered_quantity': item.quantity,
                'unit_price_at_order': float(item.unit_price),
                'subtotal': float(item.subtotal),
                'current_product_details': {
                    'current_name': current_product.get('name') if current_product else item.product_name,
                    'current_price': float(current_product.get('price', 0)) if current_product else float(
                        item.unit_price),
                    'is_active': current_product.get('is_active', False) if current_product else False,
                    'current_stock': current_product.get('stock_quantity', 0) if current_product else 0
                } if current_product else None
            }
            enriched_items.append(enriched_item)

        return enriched_items