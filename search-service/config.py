"""Search microservice configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Meilisearch
    MEILISEARCH_URL: str = "http://meilisearch:7700"
    MEILISEARCH_API_KEY: str = ""
    CRAWL_INDEX_NAME: str = "web_pages"

    # Local storage
    SQLITE_DB_PATH: str = "/data/search-service.db"

    # Auth (shared secret between main backend and this service)
    API_KEY: str = ""

    # Crawl defaults
    CRAWL_USER_AGENT: str = "BNU-AdmissionBot/1.0"
    CRAWL_DEFAULT_MAX_DEPTH: int = 3
    CRAWL_DEFAULT_MAX_PAGES: int = 100
    CRAWL_CONCURRENCY: int = 3
    CRAWL_DELAY_MS: int = 500


settings = Settings()
