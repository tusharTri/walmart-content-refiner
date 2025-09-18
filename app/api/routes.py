from fastapi import APIRouter
from typing import List
from app.models import ProductInput, RefinedProduct
from app.services.refiner_service import refine_product

router = APIRouter()


@router.post("/refine", response_model=RefinedProduct)
def refine(item: ProductInput) -> RefinedProduct:
    refined = refine_product(item.dict())
    return RefinedProduct(**refined)
