# mongo_scripts/migrate_amazon_to_app.py
from ..core.mongo.connection import mongo_db


def migrate_amazon_categories_to_app():
    """Migrate Amazon categories to your app's category structure"""
    amazon_categories = mongo_db.amazon_categories.find()
    migrated_count = 0

    for amazon_cat in amazon_categories:
        # Check if category already exists
        existing = mongo_db.categories.find_one({
            'category_name': amazon_cat['name']
        })

        if not existing:
            from ..core.mongo.mongo_repositories import CategoryRepository
            CategoryRepository.create_category({
                'category_name': amazon_cat['name'],
                'description': f"Imported from Amazon: {amazon_cat['name']}",
                'source': 'amazon_import'
            })
            migrated_count += 1

    print(f"Migrated {migrated_count} Amazon categories to app categories")


def migrate_amazon_products_to_app():
    """Migrate Amazon products to your app's product structure"""
    amazon_products = mongo_db.amazon_products.find().limit(1000)  # Limit for demo
    migrated_count = 0

    for amazon_prod in amazon_products:
        # Generate SKU from ASIN
        sku = f"AMZ_{amazon_prod['asin']}"

        # Check if product already exists
        existing = mongo_db.products.find_one({'sku': sku})

        if not existing:
            from ..core.mongo.mongo_repositories import ProductRepository

            # Find corresponding category in app
            amazon_cat = mongo_db.amazon_categories.find_one({
                'category_id': amazon_prod['category_id']
            })

            app_category = None
            if amazon_cat:
                app_category = mongo_db.categories.find_one({
                    'category_name': amazon_cat['name']
                })

            product_data = {
                'sku': sku,
                'name': amazon_prod['title'],
                'description': f"Amazon product: {amazon_prod['title']}",
                'price': amazon_prod['pricing']['price'] or 0,
                'stock_quantity': 10,  # Default stock
                'is_active': True,
                'categories': [app_category['_id']] if app_category else [],
                'source': 'amazon_import',
                'external_data': {
                    'asin': amazon_prod['asin'],
                    'image_url': amazon_prod['image_url'],
                    'product_url': amazon_prod['product_url'],
                    'original_price': amazon_prod['pricing']['price'],
                    'rating': amazon_prod['rating']['stars']
                }
            }

            ProductRepository.create_product(product_data)
            migrated_count += 1

    print(f"Migrated {migrated_count} Amazon products to app products")