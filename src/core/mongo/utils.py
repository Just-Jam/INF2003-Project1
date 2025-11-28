# core/mongo/utils.py
import json
from bson import ObjectId
from datetime import datetime, date


class MongoDBJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder that handles MongoDB ObjectId and datetime"""

    def default(self, obj):
        if isinstance(obj, ObjectId):
            return str(obj)  # Convert ObjectId to string
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()  # Convert datetime to ISO format string
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()  # Use object's serialization method if available
        return super().default(obj)


def serialize_mongo_document(doc):
    """Convert MongoDB document to JSON-serializable dict"""
    if not doc:
        return doc

    if isinstance(doc, list):
        return [serialize_mongo_document(item) for item in doc]

    if isinstance(doc, dict):
        result = {}
        for key, value in doc.items():
            if isinstance(value, ObjectId):
                result[key] = str(value)
            elif isinstance(value, (datetime, date)):
                result[key] = value.isoformat()
            elif isinstance(value, dict):
                result[key] = serialize_mongo_document(value)
            elif isinstance(value, list):
                result[key] = [serialize_mongo_document(item) for item in value]
            else:
                result[key] = value
        return result

    return doc