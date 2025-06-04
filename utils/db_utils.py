from pymongo import MongoClient
from pymongo.errors import ConnectionFailure
import os
from dotenv import load_dotenv

load_dotenv()

MONGODB_USER = os.getenv("MONGODB_USER")
MONGODB_PASS = os.getenv("MONGODB_PASS")
MONGODB_CLUSTER = os.getenv("MONGODB_CLUSTER")
MONGODB_URI = f"mongodb+srv://{MONGODB_USER}:{MONGODB_PASS}@{MONGODB_CLUSTER}/"

def get_mongo_client():
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        client.admin.command('ping')
        return client
    except ConnectionFailure as e:
        raise Exception(f"MongoDB connection failed: {str(e)}")