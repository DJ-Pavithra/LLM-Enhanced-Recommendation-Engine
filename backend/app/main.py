from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.config import settings
from app.db.mongodb import db
from app.db.redis import redis_client
from app.ml.recommender import recommender

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    await db.connect_to_database()
    await redis_client.connect_to_redis()
    yield
    # Shutdown
    await db.close_database_connection()
    await redis_client.close_redis_connection()

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(
    title=settings.PROJECT_NAME,
    lifespan=lifespan,
    openapi_url=f"{settings.API_V1_STR}/openapi.json"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

from app.api.routes import router as api_router

app.include_router(api_router, prefix=settings.API_V1_STR)

@app.get("/health")
async def health_check():
    return {"status": "ok", "db": "connected" if db.client else "disconnected", "models_loaded": recommender.initialized}

@app.get("/")
async def root():
    return {"message": "Welcome to LLM Recommendation Engine API"}
