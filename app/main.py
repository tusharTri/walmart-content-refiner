from fastapi import FastAPI
from app.api.routes import router
from app.config import get_settings

settings = get_settings()
app = FastAPI(title="Walmart Content Refiner")

app.include_router(router, prefix="/api")


@app.get("/")
def health() -> dict:
    return {"status": "ok", "log_level": settings.log_level}
