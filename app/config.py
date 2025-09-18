from pydantic import BaseSettings


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
