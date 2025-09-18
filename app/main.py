from fastapi import FastAPI
from app.api.routes import router
from app.config import get_settings, get_logger

settings = get_settings()
logger = get_logger()
app = FastAPI(title="Walmart Content Refiner")

app.include_router(router)


@app.get("/")
def root() -> dict:
    return {"message": "Walmart Content Refiner API"}
