from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any

class User(BaseModel):
    user_id: str = Field(..., alias="_id")
    metadata: Dict[str, Any] = {}
    profile_embedding: Optional[List[float]] = None
    purchase_history: List[str] = []  # List of stock_codes

    class Config:
        populate_by_name = True
