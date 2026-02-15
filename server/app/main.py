from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    from app.core.seed import seed_roles_and_permissions
    await seed_roles_and_permissions()
    yield
    # Shutdown


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        lifespan=lifespan,
        docs_url="/api/docs" if settings.DEBUG else None,
        redoc_url="/api/redoc" if settings.DEBUG else None,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # 生产环境应限制
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    from app.core.middleware import AuditLogMiddleware, RateLimitMiddleware
    app.add_middleware(AuditLogMiddleware)
    app.add_middleware(RateLimitMiddleware)

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    # Register all API routes
    from app.api.router import api_router
    app.include_router(api_router)

    return app


app = create_app()
