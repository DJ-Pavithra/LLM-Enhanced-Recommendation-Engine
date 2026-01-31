from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from app.ml.recommender import recommender
from app.llm.llm_service import llm_service
from app.ml.train import train_model_task
from app.db.mongodb import db
from app.db.redis import redis_client
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter()

class SearchQuery(BaseModel):
    query: str

class UserStats(BaseModel):
    total_spent: float
    order_count: int
    top_categories: List[str]
    llm_profile: Optional[dict] = None

class RecommendationResponse(BaseModel):
    stock_code: str
    description: str
    score: float
    explanation: Optional[dict] = None # JSON with reason, match_factors

@router.post("/train")
async def trigger_training(background_tasks: BackgroundTasks):
    """Trigger model training in background."""
    background_tasks.add_task(train_model_task)
    return {"message": "Training started in background."}

@router.get("/users/{user_id}/stats", response_model=UserStats)
async def get_user_stats(user_id: str):
    """Aggregate stats and get LLM profile."""
    # 1. Aggregation (Simulated using DB)
    pipeline = [
        {"$match": {"user_id": user_id}},
        {"$group": {
            "_id": "$user_id",
            "total_spent": {"$sum": "$price"}, # Assuming price is total line item price or price * quantity
            "order_count": {"$sum": 1},
            "descriptions": {"$push": "$description"}
        }}
    ]
    
    # Needs to be aggregation on transactions collection
    cursor = db.db["transactions"].aggregate(pipeline)
    stats_list = await cursor.to_list(length=1)
    
    if not stats_list:
        return UserStats(total_spent=0, order_count=0, top_categories=[])

    stats = stats_list[0]
    
    # 2. Derive Categories (Naive keyword based for now, or send detailed list to LLM)
    # Sending first 10 descriptions to LLM for profiling
    history_summary = f"Total Spent: {stats['total_spent']}, Orders: {stats['order_count']}. Recent items: " + ", ".join(stats['descriptions'][:20])
    
    llm_profile = await llm_service.analyze_user_profile(history_summary)
    
    return UserStats(
        total_spent=stats['total_spent'],
        order_count=stats['order_count'],
        top_categories=["Electronics", "Home"] if "White" in str(stats['descriptions']) else ["General"], # Mock category logic or improve later
        llm_profile=llm_profile
    )

@router.get("/users/{user_id}/recommendations", response_model=List[RecommendationResponse])
async def get_recommendations(user_id: str):
    """Get hybrid recommendations with structured explanations."""
    recs = recommender.recommend(user_id, top_k=5)
    
    if not recs:
        return []

    # Get User Context for better explanations
    # For demo, we do a quick lookup or just re-use the ID
    history_subset = "User loves " + recs[0]['name'] # Simplification
    
    # Parallelize Explanation Generation? For now, just explain the top 1 detailed, rest generic/quick
    # Optimization: Only explain top 1 or 2 to save tokens/latency
    
    response_items = []
    
    for i, item in enumerate(recs):
        explanation_data = None
        if i < 2: # Explain top 2
            explanation_data = await llm_service.explain_recommendation(
                f"User History ID: {user_id}", 
                item['name'], 
                item['score']
            )
        
        response_items.append(
            RecommendationResponse(
                stock_code=item['stock_code'], 
                description=item.get('name', 'Unknown'), 
                score=item['score'],
                explanation=explanation_data
            )
        )
            
    return response_items

@router.post("/search")
async def search_products(body: SearchQuery):
    """Natural Language Search."""
    # 1. Analyze Intent
    intent_data = await llm_service.analyze_query(body.query)
    print(f"Intent: {intent_data}")
    
    # 2. Semantic Search in FAISS
    # We can use the intent to filter or just use raw query on embeddings
    # Using raw query for now + metadata filtering if we implemented it
    results = recommender.search(body.query, top_k=10)
    
    return {
        "intent": intent_data,
        "results": results
    }

@router.post("/cold-start")
async def cold_start():
    """Return questions for new users."""
    questions = await llm_service.generate_cold_start_questions()
    # Also return popular items
    # (Assuming we precomputed popular items or fetch from DB)
    popular_cursor = db.db["products"].find().sort("frequency", -1).limit(5)
    popular = await popular_cursor.to_list(None)
    
    return {
        "questions": questions,
        "popular_products": [{"stock_code": p["_id"], "description": p["description"]} for p in popular]
    }
