from motor.motor_asyncio import AsyncIOMotorClient
from app.core.config import settings

class MongoDB:
    client: AsyncIOMotorClient = None
    db = None

    async def connect_to_database(self):
        url = settings.MONGODB_URL.strip('"\'')
        db_name = settings.DATABASE_NAME.strip('"\'')
        self.client = AsyncIOMotorClient(url)
        self.db = self.client[db_name]
        print(f"Connected to MongoDB: {db_name}")

    async def close_database_connection(self):
        if self.client:
            self.client.close()
            print("Closed MongoDB connection")

db = MongoDB()

async def get_database():
    return db.db
