from pymongo import MongoClient

client = MongoClient("mongodb://localhost:27017/")
db = client["mongo_database"]

amazon_categories = db["amazon_categories"]
amazon_products = db["amazon_products"]
fashion_items = db["fashion_items"]


def top_categories_by_product_count(limit=10):
    pipeline = [
        {
            "$group": {
                "_id": "$category_id",
                "product_count": {"$sum": 1}
            }
        },
        {"$sort": {"product_count": -1}},
        {"$limit": limit},
        {
            "$lookup": {
                "from": "amazon_categories",
                "localField": "_id",
                "foreignField": "category_id",
                "as": "category_info"
            }
        },
        {
            "$unwind": {
                "path": "$category_info",
                "preserveNullAndEmptyArrays": True
            }
        },
        {
            "$project": {
                "_id": 0,
                "category_id": "$_id",
                "category_name": "$category_info.name",
                "product_count": 1
            }
        }
    ]
    print("\n== Top categories by product count ==")
    for doc in amazon_products.aggregate(pipeline):
        print(doc)


def top_rated_products(min_reviews=100, limit=10):
    pipeline = [
        {
            "$match": {
                "rating.stars": {"$ne": None},
                "rating.reviews": {"$gte": min_reviews}
            }
        },
        {"$sort": {"rating.stars": -1, "rating.reviews": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "asin": 1,
                "title": 1,
                "category_id": 1,
                "stars": "$rating.stars",
                "reviews": "$rating.reviews",
                "price": "$pricing.price"
            }
        }
    ]
    print(f"\n== Top {limit} rated products (min {min_reviews} reviews) ==")
    for doc in amazon_products.aggregate(pipeline):
        print(doc)


def fashion_avg_price_by_category(limit=10):
    pipeline = [
        {
            "$match": {
                "sell_price": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": "$category",
                "avg_price": {"$avg": "$sell_price"},
                "min_price": {"$min": "$sell_price"},
                "max_price": {"$max": "$sell_price"},
                "item_count": {"$sum": 1}
            }
        },
        {"$sort": {"avg_price": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "category": "$_id",
                "avg_price": 1,
                "min_price": 1,
                "max_price": 1,
                "item_count": 1
            }
        }
    ]
    print("\n== Fashion categories by average sell price ==")
    for doc in fashion_items.aggregate(pipeline):
        print(doc)


def fashion_discount_stats(limit=10):
    pipeline = [
        {
            "$match": {
                "discount_percent": {"$ne": None}
            }
        },
        {
            "$group": {
                "_id": "$brand",
                "avg_discount": {"$avg": "$discount_percent"},
                "max_discount": {"$max": "$discount_percent"},
                "item_count": {"$sum": 1}
            }
        },
        {"$sort": {"avg_discount": -1}},
        {"$limit": limit},
        {
            "$project": {
                "_id": 0,
                "brand": "$_id",
                "avg_discount": 1,
                "max_discount": 1,
                "item_count": 1
            }
        }
    ]
    print("\n== Fashion brands by average discount ==")
    for doc in fashion_items.aggregate(pipeline):
        print(doc)


if __name__ == "__main__":
    top_categories_by_product_count()
    top_rated_products()
    fashion_avg_price_by_category()
    fashion_discount_stats()
