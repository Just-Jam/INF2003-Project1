from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["mongo_database"]

amazon_categories = db["amazon_categories"]
amazon_products = db["amazon_products"]
fashion_items = db["fashion_items"]

#amazon_categories
amazon_categories.create_index("category_id", unique=True)

#amazon_products
amazon_products.create_index("asin", unique=True)
amazon_products.create_index("category_id")
amazon_products.create_index("pricing.price")
amazon_products.create_index("rating.stars")
amazon_products.create_index("rating.reviews")
 
#fashion_items
fashion_items.create_index("category")
fashion_items.create_index("brand")
fashion_items.create_index("sell_price")
fashion_items.create_index("discount_percent")

print("Indexes created on amazon_categories, amazon_products, fashion_items.")
