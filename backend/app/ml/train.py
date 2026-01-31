import asyncio
import pandas as pd
import os
import sys

# Add backend to path to import app modules
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from app.ml.recommender import recommender
from motor.motor_asyncio import AsyncIOMotorClient

async def train_model_task():
    print("Fetching data from MongoDB for training...")
    
    # We need a temporary client if running as script, or use app's db if running in app context
    # This script is designed to be imported or run standalone
    
    # Sanitize settings
    url = settings.MONGODB_URL.strip('"\'')
    db_name = settings.DATABASE_NAME.strip('"\'')
    
    client = AsyncIOMotorClient(url)
    database = client[db_name]
    
    # Fetch Transactions
    cursor = database["transactions"].find({}, {"user_id": 1, "stock_code": 1, "quantity": 1, "_id": 0})
    transactions = await cursor.to_list(length=None)
    
    if not transactions:
        print("No transactions found. Skipping training.")
        client.close()
        return
        
    transactions_df = pd.DataFrame(transactions)
    
    # Fetch Products
    cursor = database["products"].find({}, {"_id": 1, "description": 1})
    products = await cursor.to_list(length=None)
    products_df = pd.DataFrame(products)
    
    print(f"Training on {len(transactions_df)} transactions and {len(products_df)} products.")
    
    await recommender.train(transactions_df, products_df)
    print("Training task finished.")
    client.close()

if __name__ == "__main__":
    asyncio.run(train_model_task())
