from pydantic_settings import BaseSettings
import logging
import json as _json
from typing import Optional


class Settings(BaseSettings):
    gemini_api_key: Optional[str] = "AIzaSyAraOParqW53WwvEbA1y35BTWRwqRLx7xk"
    huggingface_api_key: Optional[str] = None
    cloud_bucket: Optional[str] = None
    gcp_project: Optional[str] = None
    log_level: str = "INFO"

    class Config:
        env_file = ".env"
        env_prefix = ""
        case_sensitive = False


def get_settings() -> Settings:
    return Settings()


def get_logger(name: str = "walmart-content-refiner") -> logging.Logger:
    logger = logging.getLogger(name)
    if not logger.handlers:
        handler = logging.StreamHandler()
        class JsonFormatter(logging.Formatter):
            def format(self, record: logging.LogRecord) -> str:
                payload = {
                    "ts": self.formatTime(record, datefmt="%Y-%m-%dT%H:%M:%S"),
                    "level": record.levelname,
                    "logger": record.name,
                    "message": record.getMessage(),
                }
                return _json.dumps(payload, ensure_ascii=False)
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    settings = get_settings()
    level = getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO)
    logger.setLevel(level)
    return logger

# Placeholders for external logging providers
def get_sentry_client():
    return None

def get_cloud_logger():
    return None
