from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.config import settings


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: ensure all tables exist (handles new models added since last deploy)
    from app.core.database import get_engine, Base
    import app.models  # noqa: F401 — register all models on Base.metadata
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    # Ensure schema migrations for workflow state-machine columns
    from sqlalchemy import text as _text
    async with engine.begin() as conn:
        # review_records.step may still be NOT NULL from old schema
        await conn.execute(_text(
            "ALTER TABLE review_records ALTER COLUMN step DROP NOT NULL"
        ))
        await conn.execute(_text(
            "ALTER TABLE review_records ALTER COLUMN step SET DEFAULT 0"
        ))

    # Ensure kb_id column on knowledge_documents
    async with engine.begin() as conn:
        await conn.execute(_text("""
            DO $$ BEGIN
                ALTER TABLE knowledge_documents ADD COLUMN kb_id UUID REFERENCES knowledge_bases(id);
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """))

    # Ensure level and word_list columns on sensitive_word_groups
    async with engine.begin() as conn:
        await conn.execute(_text("""
            DO $$ BEGIN
                ALTER TABLE sensitive_word_groups ADD COLUMN level VARCHAR(10) DEFAULT 'block';
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """))
        await conn.execute(_text("""
            DO $$ BEGIN
                ALTER TABLE sensitive_word_groups ADD COLUMN word_list TEXT;
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """))

    # Ensure additional_prompt column on admission_calendar
    async with engine.begin() as conn:
        await conn.execute(_text("""
            DO $$ BEGIN
                ALTER TABLE admission_calendar ADD COLUMN additional_prompt TEXT;
            EXCEPTION WHEN duplicate_column THEN NULL;
            END $$;
        """))

    from app.core.seed import (
        seed_roles_and_permissions,
        seed_calendar_periods,
        seed_model_config,
        seed_review_workflows,
        seed_default_knowledge_base,
        seed_system_configs,
    )
    await seed_roles_and_permissions()
    await seed_calendar_periods()
    await seed_model_config()
    await seed_system_configs()
    await seed_review_workflows()
    await seed_default_knowledge_base()

    # Initialize LLM router from DB config
    from app.core.database import get_session_factory
    from app.services import model_config_service
    session_factory = get_session_factory()
    async with session_factory() as db:
        await model_config_service.reload_router(db)

    # Ensure KB vector schema + backfill embeddings for existing chunks
    from app.services.knowledge_embedding_service import ensure_embedding_schema, backfill_missing_embeddings
    async with session_factory() as db:
        await ensure_embedding_schema(db)
        await backfill_missing_embeddings(db, limit=2000)
        await db.commit()

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

    # Serve uploaded files
    import os
    os.makedirs(settings.UPLOAD_DIR, exist_ok=True)
    app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

    return app


app = create_app()
