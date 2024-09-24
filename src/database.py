from pymongo import MongoClient

# MongoDB 連線
client = MongoClient("mongodb://localhost:27017/")
db = client.myDatabase