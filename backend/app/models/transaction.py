from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional

class Transaction(BaseModel):
    invoice: str = Field(..., alias="Invoice")
    stock_code: str = Field(..., alias="StockCode")
    description: Optional[str] = Field(None, alias="Description")
    quantity: int = Field(..., alias="Quantity")
    invoice_date: datetime = Field(..., alias="InvoiceDate")
    price: float = Field(..., alias="Price")
    customer_id: Optional[float] = Field(None, alias="Customer ID")
    country: str = Field(..., alias="Country")

    class Config:
        populate_by_name = True
        json_schema_extra = {
            "example": {
                "Invoice": "489434",
                "StockCode": "85048",
                "Description": "15CM CHRISTMAS GLASS BALL 20 LIGHTS",
                "Quantity": 12,
                "InvoiceDate": "2009-12-01T07:45:00",
                "Price": 6.95,
                "Customer ID": 13085.0,
                "Country": "United Kingdom"
            }
        }
