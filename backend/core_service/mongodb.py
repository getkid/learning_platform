from pymongo import MongoClient
import os

MONGO_URL = os.getenv("MONGO_URL", "mongodb://mongo_db:27017/")
client = MongoClient(MONGO_URL)
db = client.learning_platform # Название базы данных
submissions_collection = db.submissions # Название коллекции