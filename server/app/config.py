from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # App
    APP_NAME: str = "BNU Admission Chatbot"
    APP_VERSION: str = "0.0.1"
    GIT_COMMIT: str = ""
    BUILD_TIME: str = ""
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"
    TRUST_PROXY_HEADERS: bool = True
    TRUSTED_PROXY_CIDRS: str = "127.0.0.1/32,::1/128,10.0.0.0/8,172.16.0.0/12,192.168.0.0/16"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/bnu_admission"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    USER_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_TOKEN_EXPIRE_HOURS: int = 2
    ADMIN_PHONE_VERIFY_IP_CHANGE_HOURS: int = 6
    ADMIN_PHONE_VERIFY_IDLE_HOURS: int = 72

    # SMS
    SMS_MOCK: bool = True

    # IP geolocation
    IP_GEO_LOOKUP_ENABLED: bool = True
    IP_GEO_LOOKUP_TIMEOUT_SEC: float = 2.0
    IP_GEO_LOOKUP_PRIMARY_URL: str = "http://ip-api.com/json/{ip}?lang=zh-CN"
    IP_GEO_LOOKUP_SECONDARY_URL: str = "https://ipwho.is/{ip}"

    # Aliyun Dypns SMS Verify
    SMS_ALIYUN_ACCESS_KEY_ID: str = ""
    SMS_ALIYUN_ACCESS_KEY_SECRET: str = ""
    SMS_ALIYUN_SIGN_NAME: str = ""
    SMS_ALIYUN_TEMPLATE_CODE: str = ""
    SMS_ALIYUN_TEMPLATE_MIN: str = "5"
    SMS_ALIYUN_SCHEME_NAME: str = ""
    SMS_ALIYUN_ENDPOINT: str = "dypnsapi.aliyuncs.com"

    # LLM
    LLM_PRIMARY_PROVIDER: str = "qwen"
    LLM_PRIMARY_API_KEY: str = ""
    LLM_PRIMARY_BASE_URL: str = ""
    LLM_PRIMARY_MODEL: str = ""
    LLM_REVIEW_PROVIDER: str = "qwen"
    LLM_REVIEW_MODEL: str = ""
    LLM_REVIEW_BASE_URL: str = ""

    # Embedding
    EMBEDDING_MODEL: str = "text-embedding-v1"
    EMBEDDING_BASE_URL: str = ""
    EMBEDDING_API_KEY: str = ""

    # File storage
    UPLOAD_DIR: str = "/data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 100

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    # Audit (daily sqlite shards)
    AUDIT_SQLITE_DIR: str = "/data/audit_logs"

    # Tavily web search API
    TAVILY_API_KEY: str = ""



settings = Settings()
