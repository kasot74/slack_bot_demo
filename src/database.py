from pymongo import MongoClient

#創建連線
def con_db(config):        
    user=config['MONGO_USER']
    pas=config['MONGO_USER']
    host=config['MONGO_HOST']
    port=config['MONGO_PORT']
    con_str=f"mongodb://{user}:{pas}@{host}:{port}/?authMechanism=SCRAM-SHA-1&authSource=admin"
    # MongoDB 連線
    client = MongoClient(con_str)
    db = client.myDatabase
    return db