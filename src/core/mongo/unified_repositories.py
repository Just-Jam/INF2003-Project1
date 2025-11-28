# mongo/unified_repository.py
from .connection import mongo_db
from .utils import serialize_mongo_document
from typing import List, Dict, Optional


class UnifiedProductRepository:
    def __init__(self):
        self.app_products = mongo_db["products"]
        self.amazon_products = mongo_db["amazon_products"]
        self.fashion_items = mongo_db["fashion_items"]

    def search_all_products(self, search_term: str, limit: int = 50) -> List[Dict]:
        """Search across all product collections"""
        all_results = []

        # Search your app products
        app_results = self.app_products.find({
            '$or': [
                {'name': {'$regex': search_term, '$options': 'i'}},
                {'description': {'$regex': search_term, '$options': 'i'}},
                {'sku': {'$regex': search_term, '$options': 'i'}}
            ],
            'is_active': True
        }).limit(limit)
        all_results.extend([{**serialize_mongo_document(item), 'source': 'app'} for item in app_results])

        # Search Amazon products
        amazon_results = self.amazon_products.find({
            'title': {'$regex': search_term, '$options': 'i'}
        }).limit(limit)
        all_results.extend([{**serialize_mongo_document(item), 'source': 'amazon'} for item in amazon_results])

        # Search fashion items
        fashion_results = self.fashion_items.find({
            '$or': [
                {'brand': {'$regex': search_term, '$options': 'i'}},
                {'details': {'$regex': search_term, '$options': 'i'}},
                {'category': {'$regex': search_term, '$options': 'i'}}
            ]
        }).limit(limit)
        all_results.extend([{**serialize_mongo_document(item), 'source': 'fashion'} for item in fashion_results])

        return all_results

    def get_products_by_category(self, category_name: str, source: str = None) -> List[Dict]:
        """Get products by category from specified source or all sources"""
        results = []

        if not source or source == 'amazon':
            amazon_cat = self.amazon_categories.find_one({'name': {'$regex': category_name, '$options': 'i'}})
            if amazon_cat:
                amazon_results = self.amazon_products.find({
                    'category_id': amazon_cat['category_id']
                })
                results.extend([{**serialize_mongo_document(item), 'source': 'amazon'} for item in amazon_results])

        if not source or source == 'fashion':
            fashion_results = self.fashion_items.find({
                'category': {'$regex': category_name, '$options': 'i'}
            })
            results.extend([{**serialize_mongo_document(item), 'source': 'fashion'} for item in fashion_results])

        return results

    def search_products_by_source(self, search_term: str, source: str, limit: int = 50) -> List[Dict]:
        """Search products from a specific source"""
        results = []

        if source == 'app':
            app_results = self.app_products.find({
                '$or': [
                    {'name': {'$regex': search_term, '$options': 'i'}},
                    {'description': {'$regex': search_term, '$options': 'i'}},
                    {'sku': {'$regex': search_term, '$options': 'i'}}
                ],
                'is_active': True
            }).limit(limit)
            results.extend([{**serialize_mongo_document(item), 'source': 'app'} for item in app_results])

        elif source == 'amazon':
            amazon_results = self.amazon_products.find({
                'title': {'$regex': search_term, '$options': 'i'}
            }).limit(limit)
            results.extend([{**serialize_mongo_document(item), 'source': 'amazon'} for item in amazon_results])

        elif source == 'fashion':
            fashion_results = self.fashion_items.find({
                '$or': [
                    {'brand': {'$regex': search_term, '$options': 'i'}},
                    {'details': {'$regex': search_term, '$options': 'i'}},
                    {'category': {'$regex': search_term, '$options': 'i'}}
                ]
            }).limit(limit)
            results.extend([{**serialize_mongo_document(item), 'source': 'fashion'} for item in fashion_results])

        return results