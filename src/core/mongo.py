from pymongo import MongoClient
from django.conf import settings
import os

_client = MongoClient(
    host=os.getenv('MONGO_HOST', 'mongo_db'),
    port=int(os.getenv('MONGO_PORT', '27017')),
    username=os.getenv('MONGO_USER'),
    password=os.getenv('MONGO_PASSWORD'),
    authSource='admin'
)

# pick the same database name you used with djongo
mongo_db = _client[os.getenv('MONGO_DB', 'my_db')]

