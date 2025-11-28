# src/mongo_scripts/import_all_data.py
import os, sys
from datetime import datetime
import csv
from pathlib import Path
from pymongo import MongoClient

if len(sys.argv) > 1 and sys.argv[1] == "local":
    # Mongo connection(local)
    client = MongoClient("mongodb://localhost:27017/")
    db = client["mongo_database"]
else:
    # --- Connection Setup ---
    # Always use environment variables and default MONGO_HOST to 'mongo' for Docker.
    MONGO_HOST = os.getenv('MONGO_HOST', 'mongo')
    MONGO_PORT = int(os.getenv('MONGO_PORT', 27017))
    MONGO_USER = os.getenv('MONGO_USER')
    MONGO_PASSWORD = os.getenv('MONGO_PASSWORD')
    MONGO_DB = os.getenv('MONGO_DB', 'mongo_database')

    # Connect to MongoDB
    client = MongoClient(
        host=MONGO_HOST,
        port=MONGO_PORT,
        username=MONGO_USER,
        password=MONGO_PASSWORD,
        authSource='admin'
    )
    db = client[MONGO_DB]

# External data collections
amazon_categories_col = db["amazon_categories"]
amazon_products_col = db["amazon_products"]
fashion_items_col = db["fashion_items"]

# Your app collections (don't touch these during import)
app_categories_col = db["categories"]
app_products_col = db["products"]

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "datasets"


def parse_float(value):
    try:
        v = str(value).strip()
        if v == "" or v.lower() == "nan":
            return None
        return float(v)
    except Exception:
        return None


def parse_int(value):
    try:
        v = str(value).strip()
        if v == "" or v.lower() == "nan":
            return None
        return int(float(v))
    except Exception:
        return None


def import_amazon_categories():
    print("Importing amazon_categories.csv ...")
    # Only drop if you want fresh import each time, otherwise consider updating
    amazon_categories_col.drop()

    path = DATA_DIR / "amazon_categories.csv"
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        docs = []
        for row in reader:
            doc = {
                "category_id": parse_int(row["id"]),
                "name": row["category_name"],
                "data_source": "amazon",  # Add source identifier
                "imported_at": datetime.now()
            }
            docs.append(doc)

        if docs:
            amazon_categories_col.insert_many(docs)

    print(f"Inserted {amazon_categories_col.count_documents({})} amazon_categories documents.")


def import_amazon_products(batch_size=1000):
    print("Importing amazon_products.csv ...")
    amazon_products_col.drop()

    path = DATA_DIR / "amazon_products.csv"
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        batch = []
        count = 0
        for row in reader:
            doc = {
                "asin": row["asin"],
                "title": row["title"],
                "image_url": row["imgUrl"],
                "product_url": row["productURL"],
                "category_id": parse_int(row["category_id"]),
                "pricing": {
                    "price": parse_float(row["price"]),
                    "list_price": parse_float(row["listPrice"]),
                },
                "rating": {
                    "stars": parse_float(row["stars"]),
                    "reviews": parse_int(row["reviews"]),
                    "is_best_seller": str(row["isBestSeller"]).strip().lower() == "true",
                    "bought_last_month": parse_int(row["boughtInLastMonth"]),
                },
                "data_source": "amazon",  # Add source identifier
                "imported_at": datetime.now()
            }

            batch.append(doc)
            if len(batch) >= batch_size:
                amazon_products_col.insert_many(batch)
                count += len(batch)
                batch = []

        if batch:
            amazon_products_col.insert_many(batch)
            count += len(batch)

    print(f"Inserted {count} amazon_products documents.")


def import_fashion_dataset(batch_size=1000):
    print("Importing FashionDataset.csv ...")
    fashion_items_col.drop()

    path = DATA_DIR / "FashionDataset.csv"
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)

        batch = []
        count = 0
        for row in reader:
            # Clean MRP like "Rs\n1699"
            mrp_raw = row["MRP"]
            mrp_val = None
            if mrp_raw:
                parts = str(mrp_raw).split("\n")
                num_part = parts[-1].strip()
                mrp_val = parse_float(num_part)

            sell_price_val = parse_float(row["SellPrice"])

            # Discount like "50% off"
            discount_percent = None
            discount_raw = row.get("Discount", "")
            if discount_raw:
                d = str(discount_raw).lower().replace("off", "").replace("%", "").strip()
                discount_percent = parse_float(d)

            # Sizes like "Size:Large,Medium,Small"
            sizes_raw = row.get("Sizes", "") or ""
            sizes_clean = []
            if "Size:" in sizes_raw:
                sizes_str = sizes_raw.split("Size:")[-1]
            else:
                sizes_str = sizes_raw
            for s in sizes_str.split(","):
                s = s.strip()
                if s:
                    sizes_clean.append(s)

            doc = {
                "brand": row["BrandName"],
                "details": row["Deatils"],
                "sizes": sizes_clean,
                "mrp": mrp_val,
                "sell_price": sell_price_val,
                "discount_percent": discount_percent,
                "category": row["Category"],
                "data_source": "fashion_dataset",  # Add source identifier
                "imported_at": datetime.now()
            }

            batch.append(doc)
            if len(batch) >= batch_size:
                fashion_items_col.insert_many(batch)
                count += len(batch)
                batch = []

        if batch:
            fashion_items_col.insert_many(batch)
            count += len(batch)

    print(f"Inserted {count} fashion_items documents.")


def create_indexes():
    """Create indexes for better query performance"""
    print("Creating indexes...")

    # Amazon collections
    amazon_categories_col.create_index("category_id", unique=True)
    amazon_products_col.create_index("asin", unique=True)
    amazon_products_col.create_index("category_id")

    # Fashion collection
    fashion_items_col.create_index("brand")
    fashion_items_col.create_index("category")

    # Your app collections
    app_categories_col.create_index("category_name", unique=True)
    app_products_col.create_index("sku", unique=True)
    app_products_col.create_index("categories")

    print("Indexes created successfully.")


if __name__ == "__main__":
    from datetime import datetime

    import_amazon_categories()
    import_amazon_products()
    import_fashion_dataset()
    create_indexes()
    print("All CSV data imported into mongo_database.")
