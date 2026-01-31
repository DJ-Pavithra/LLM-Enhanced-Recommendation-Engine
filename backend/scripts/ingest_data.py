import asyncio
import pandas as pd
import os
import sys

# Add backend to path to import app modules
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.core.config import settings
from motor.motor_asyncio import AsyncIOMotorClient

# Robust path finding
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE_PATH = os.path.join(BASE_DIR, "../data/online_retail_II.csv")

async def ingest_data():
    # Sanitize settings (remove quotes if pydantic kept them)
    mongo_url = settings.MONGODB_URL.strip('"\'')
    db_name = settings.DATABASE_NAME.strip('"\'')
    
    print(f"DEBUG: MONGODB_URL={repr(mongo_url)}")
    print(f"DEBUG: DATABASE_NAME={repr(db_name)}")
    print(f"Loading data from {DATA_FILE_PATH}...")
    
    if not os.path.exists(DATA_FILE_PATH):
        print(f"Error: File not found at {DATA_FILE_PATH}")
        print("Please place 'online_retail_II.csv' in 'backend/data/'")
        return

    # Load Data (using pandas)
    try:
        df = pd.read_csv(DATA_FILE_PATH, encoding="ISO-8859-1")
        print(f"Loaded {len(df)} rows.")
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    # Data Cleaning
    print("Cleaning data...")
    # Remove null CustomerID
    df = df.dropna(subset=['Customer ID'])
    # Remove invalid prices
    df = df[df['Price'] > 0]
    # Remove invalid quantity (returns are negative, we might want to keep or separate them. For reco, usually keep purchases)
    df = df[df['Quantity'] > 0]
    
    # Correct types
    df['Customer ID'] = df['Customer ID'].astype(str).str.replace(r'\.0$', '', regex=True)
    df['InvoiceDate'] = pd.to_datetime(df['InvoiceDate'])
    df['Description'] = df['Description'].fillna("").astype(str)
    
    print(f"Rows after cleaning: {len(df)}")
    
    # Helper to chunk list
    def chunker(seq, size):
        return (seq[pos:pos + size] for pos in range(0, len(seq), size))

    # Connect to DB
    try:
        client = AsyncIOMotorClient(mongo_url)
        database = client[db_name]
        print(f"Connected to DB: {db_name}")
    except Exception as e:
        print(f"DB Connection Error: {e}")
        return
    
    # 1. Ingest Transactions
    print("Ingesting Transactions...")
    transactions_collection = database["transactions"]
    await transactions_collection.delete_many({}) # Clear old data for idempotent run
    
    transaction_records = df.rename(columns={
        "Invoice": "invoice",
        "StockCode": "stock_code",
        "Description": "description",
        "Quantity": "quantity",
        "InvoiceDate": "invoice_date",
        "Price": "price",
        "Customer ID": "user_id",
        "Country": "country"
    }).to_dict(orient='records')
    
    # Chunk insert to avoid message size limits
    chunk_size = 1000
    total_inserted = 0
    
    for chunk in chunker(transaction_records, chunk_size):
        await transactions_collection.insert_many(chunk)
        total_inserted += len(chunk)
        print(f"Inserted {total_inserted} transactions...", end='\r')
    
    print(f"\nFinished ingesting {total_inserted} transactions.")

    # 2. Extract and Ingest Products (Unique StockCodes)
    print("Ingesting Products...")
    products_collection = database["products"]
    await products_collection.delete_many({})
    
    # Group by StockCode to find most common description and average price (or max)
    products_df = df.groupby('StockCode').agg({
        'Description': lambda x: pd.Series.mode(x)[0] if not pd.Series.mode(x).empty else x.iloc[0],
        'Price': 'mean', # Average price
        'Invoice': 'count' # Frequency
    }).reset_index()
    
    products_df.rename(columns={
        'StockCode': '_id',
        'Description': 'description',
        'Price': 'price',
        'Invoice': 'frequency'
    }, inplace=True)
    
    product_records = products_df.to_dict(orient='records')
    if product_records:
        await products_collection.insert_many(product_records)
    print(f"Ingested {len(product_records)} unique products.")

    # 3. Extract and Ingest Users (Unique CustomerIDs)
    print("Ingesting Users...")
    users_collection = database["users"]
    await users_collection.delete_many({})
    
    unique_users = df['Customer ID'].unique()
    user_records = [{"_id": uid, "metadata": {}, "purchase_history": []} for uid in unique_users]
    
    if user_records:
        await users_collection.insert_many(user_records)
    print(f"Ingested {len(user_records)} unique users.")

    print("Data Ingestion Complete.")
    client.close()

if __name__ == "__main__":
    asyncio.run(ingest_data())
