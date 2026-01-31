from pydantic import BaseModel, Field
from typing import List, Optional

class Product(BaseModel):
    stock_code: str = Field(..., alias="_id")
    description: str
    price: float
    frequency: int = 0
    embedding: Optional[List[float]] = None

    class Config:
        populate_by_name = True
