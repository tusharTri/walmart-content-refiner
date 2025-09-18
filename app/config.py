from pydantic import BaseSettings
import logging


class Settings(BaseSettings):
    openai_api_key: str | None = None
    cloud_bucket: str | None = None
    gcp_project: str | None = None
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
        formatter = logging.Formatter(
            fmt="%(asctime)s %(levelname)s %(name)s - %(message)s",
            datefmt="%Y-%m-%d %H:%M:%S",
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    settings = get_settings()
    level = getattr(logging, (settings.log_level or "INFO").upper(), logging.INFO)
    logger.setLevel(level)
    return logger
