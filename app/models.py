from pydantic import BaseModel, Field
from typing import Optional


class ProductInput(BaseModel):
    product_id: str = Field(..., description="Unique product identifier")
    title: str
    description: str
    category: Optional[str] = None


class RefinedProduct(BaseModel):
    product_id: str
    title: str
    description: str
    notes: Optional[str] = None
