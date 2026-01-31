import redis.asyncio as redis
from app.core.config import settings

class RedisClient:
    redis_client: redis.Redis = None

    async def connect_to_redis(self):
        url = settings.REDIS_URL.strip('"\'')
        if not url.startswith("redis://") and not url.startswith("rediss://"):
            url = f"redis://{url}"
        print(f"DEBUG: Attempting to connect to Redis with URL: '{url}'")
        self.redis_client = redis.from_url(url, encoding="utf-8", decode_responses=True)
        print("Connected to Redis")

    async def close_redis_connection(self):
        if self.redis_client:
            await self.redis_client.close()
            print("Closed Redis connection")

redis_client = RedisClient()

async def get_redis():
    return redis_client.redis_client
