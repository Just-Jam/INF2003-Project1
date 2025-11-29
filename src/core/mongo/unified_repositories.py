# src/core/mongo/unified_repositories.py
from .connection import mongo_db
from .utils import serialize_mongo_document
from typing import List, Dict, Optional


class UnifiedProductRepository:
    def __init__(self):
        self.app_products = mongo_db["products"]
        self.amazon_products = mongo_db["amazon_products"]
        self.fashion_items = mongo_db["fashion_items"]
        self.amazon_categories = mongo_db["amazon_categories"]

    def get_all_products_paginated(self, page: int = 1, page_size: int = 50, category: Optional[str] = None) -> (List[Dict], int):
        """
        Fetches products from all sources with pagination and optional category filtering
        using a more performant aggregation pipeline.
        """
        skip = (page - 1) * page_size

        # Base pipelines
        app_products_pipeline = [
            {'$match': {'is_active': True}},
            {'$addFields': {'source': 'app'}}
        ]
        amazon_products_pipeline = [
            {'$addFields': {'source': 'amazon'}}
        ]
        fashion_items_pipeline = [
            {'$addFields': {'source': 'fashion'}}
        ]

        # Add category filtering if provided
        if category:
            # App products: category is in the 'categories' array
            app_products_pipeline.insert(1, {'$match': {'categories': category}})

            # Fashion items: category is a string field (case-insensitive match)
            fashion_items_pipeline.insert(0, {'$match': {'category': {'$regex': category, '$options': 'i'}}})

            # Amazon products: find category_id from 'amazon_categories' collection
            amazon_cat = self.amazon_categories.find_one({'name': {'$regex': category, '$options': 'i'}})
            if amazon_cat and 'category_id' in amazon_cat:
                amazon_products_pipeline.insert(0, {'$match': {'category_id': amazon_cat['category_id']}})
            else:
                # If category doesn't exist for Amazon, ensure no amazon products are returned
                amazon_products_pipeline.insert(0, {'$match': {'_id': -1}}) # This will not match any document

        # Main aggregation pipeline
        pipeline = [
            *app_products_pipeline,
            {'$unionWith': {'coll': 'amazon_products', 'pipeline': amazon_products_pipeline}},
            {'$unionWith': {'coll': 'fashion_items', 'pipeline': fashion_items_pipeline}},
            {
                '$facet': {
                    'metadata': [{'$count': 'total'}],
                    'data': [{'$skip': skip}, {'$limit': page_size}]
                }
            }
        ]

        result = list(self.app_products.aggregate(pipeline))

        if not result or not result[0]['metadata']:
            return [], 0

        paginated_products = [serialize_mongo_document(doc) for doc in result[0]['data']]
        total_items = result[0]['metadata'][0]['total']
        return paginated_products, total_items

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
