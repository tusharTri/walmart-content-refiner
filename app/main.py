"""
Walmart Content Refiner API v3.0
Author: Tushar Tripathi

FastAPI application for Walmart content compliance refinement.
Version 3.0 features improved violation handling with post-processing fixes.
"""

from fastapi import FastAPI
from app.api.routes import router
from app.config import get_settings, get_logger

settings = get_settings()
logger = get_logger()
app = FastAPI(
    title="Walmart Content Refiner v3.0",
    description="AI-powered content refinement for Walmart compliance",
    version="3.0"
)

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"message": "Walmart Content Refiner API"}
