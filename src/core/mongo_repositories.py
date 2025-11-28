# mongo_repositories.py
from .mongo import mongo_db  # Import your existing connection
from bson import ObjectId
import uuid
from datetime import datetime
from typing import List, Dict, Optional


class CategoryRepository:
    def __init__(self):
        self.collection = mongo_db['categories']  # Use your existing connection

    def create_indexes(self):
        # Create indexes for better performance
        self.collection.create_index('category_name', unique=True)
        self.collection.create_index('parent_category_id')
        self.collection.create_index('created_at')

    def create_category(self, category_data: Dict) -> Dict:
        try:
            category_data['_id'] = str(uuid.uuid4())
            category_data['created_at'] = datetime.utcnow()

            result = self.collection.insert_one(category_data)
            if result.inserted_id:
                return self.get_category_by_id(category_data['_id'])
            else:
                raise Exception("Failed to insert category")
        except Exception as e:
            print(f"Error creating category: {e}")
            raise

    def get_category_by_id(self, category_id: str) -> Optional[Dict]:
        try:
            return self.collection.find_one({'_id': category_id})
        except Exception as e:
            print(f"Error getting category {category_id}: {e}")
            return None

    def get_category_by_name(self, category_name: str) -> Optional[Dict]:
        return self.collection.find_one({'category_name': category_name})

    def get_all_categories(self, skip: int = 0, limit: int = 100, filters: Dict = None) -> List[Dict]:
        query = filters or {}
        return list(self.collection.find(query).skip(skip).limit(limit))

    def get_subcategories(self, parent_category_id: str) -> List[Dict]:
        return list(self.collection.find({'parent_category_id': parent_category_id}))

    def update_category(self, category_id: str, update_data: Dict) -> Optional[Dict]:
        update_data['updated_at'] = datetime.utcnow()
        result = self.collection.update_one(
            {'_id': category_id},
            {'$set': update_data}
        )
        if result.modified_count > 0:
            return self.get_category_by_id(category_id)
        return None

    def delete_category(self, category_id: str) -> bool:
        result = self.collection.delete_one({'_id': category_id})
        return result.deleted_count > 0

    def get_categories_by_ids(self, category_ids: List[str]) -> List[Dict]:
        return list(self.collection.find({'_id': {'$in': category_ids}}))

    def delete_all_categories(self):
        """Delete all categories - for testing only"""
        result = self.collection.delete_many({})
        return result.deleted_count

    def delete_test_categories(self):
        """Delete test categories by name pattern"""
        result = self.collection.delete_many({
            'category_name': {'$in': ['Electronics', 'Laptops', 'Test Category']}
        })
        return result.deleted_count


class ProductRepository:
    def __init__(self):
        self.collection = mongo_db['products']  # Use your existing connection

    def create_indexes(self):
        # Create indexes for better performance
        self.collection.create_index('sku', unique=True)
        self.collection.create_index('name')
        self.collection.create_index('price')
        self.collection.create_index('categories')
        self.collection.create_index('is_active')
        self.collection.create_index([('name', 'text'), ('description', 'text')])

    def create_product(self, product_data: Dict) -> Dict:
        product_data['created_at'] = datetime.utcnow()
        product_data['updated_at'] = datetime.utcnow()

        # Ensure categories is a list
        if 'categories' not in product_data:
            product_data['categories'] = []

        result = self.collection.insert_one(product_data)
        return self.get_product_by_sku(product_data['sku'])

    def get_product_by_sku(self, sku: str) -> Optional[Dict]:
        return self.collection.find_one({'sku': sku})

    def get_product_by_id(self, product_id: str) -> Optional[Dict]:
        return self.collection.find_one({'_id': product_id})

    def get_all_products(self, skip: int = 0, limit: int = 100, filters: Dict = None) -> List[Dict]:
        query = filters or {}
        return list(self.collection.find(query).skip(skip).limit(limit))

    def update_product(self, sku: str, update_data: Dict) -> Optional[Dict]:
        update_data['updated_at'] = datetime.utcnow()
        result = self.collection.update_one(
            {'sku': sku},
            {'$set': update_data}
        )
        if result.modified_count > 0:
            return self.get_product_by_sku(sku)
        return None

    def delete_product(self, sku: str) -> bool:
        result = self.collection.delete_one({'sku': sku})
        return result.deleted_count > 0

    def add_category_to_product(self, sku: str, category_id: str) -> Optional[Dict]:
        result = self.collection.update_one(
            {'sku': sku},
            {'$addToSet': {'categories': category_id}}
        )
        if result.modified_count > 0:
            return self.get_product_by_sku(sku)
        return None

    def remove_category_from_product(self, sku: str, category_id: str) -> Optional[Dict]:
        result = self.collection.update_one(
            {'sku': sku},
            {'$pull': {'categories': category_id}}
        )
        if result.modified_count > 0:
            return self.get_product_by_sku(sku)
        return None

    def get_products_by_category(self, category_id: str, skip: int = 0, limit: int = 100) -> List[Dict]:
        return list(self.collection.find({
            'categories': category_id,
            'is_active': True
        }).skip(skip).limit(limit))

    def search_products(self, search_term: str, skip: int = 0, limit: int = 100) -> List[Dict]:
        return list(self.collection.find({
            '$or': [
                {'name': {'$regex': search_term, '$options': 'i'}},
                {'description': {'$regex': search_term, '$options': 'i'}},
                {'sku': {'$regex': search_term, '$options': 'i'}}
            ]
        }).skip(skip).limit(limit))

    def get_low_stock_products(self, threshold: int = 10) -> List[Dict]:
        return list(self.collection.find({
            'stock_quantity': {'$lt': threshold},
            'is_active': True
        }))

    def update_stock(self, sku: str, new_quantity: int) -> Optional[Dict]:
        return self.update_product(sku, {'stock_quantity': new_quantity})

    def delete_all_products(self):
        """Delete all products - for testing only"""
        result = self.collection.delete_many({})
        return result.deleted_count

    def delete_test_products(self):
        """Delete test products by SKU pattern"""
        result = self.collection.delete_many({
            'sku': {'$regex': 'TEST|DEBUG|ORDER|SERVICE'}
        })
        return result.deleted_count


# Singleton instances
category_repo = CategoryRepository()
product_repo = ProductRepository()


# Initialize indexes when module is imported
def initialize_indexes():
    """Call this function to create indexes"""
    category_repo.create_indexes()
    product_repo.create_indexes()


# Auto-initialize indexes when the module is imported
initialize_indexes()