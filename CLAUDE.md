# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

BNU (Beijing Normal University) Admission Chatbot — a full-stack AI-powered Q&A system for undergraduate and graduate admissions. Built with Vue 3 frontend + FastAPI backend, backed by PostgreSQL (with pgvector) and Redis.

## Development Commands

### One-command local setup
```bash
sudo bash start-local.sh
# Installs PostgreSQL, Redis, Python deps, Node deps, runs migrations, starts all services
```

### Frontend (client/)
```bash
cd client
npm install          # install dependencies
npm run dev          # dev server at http://localhost:5173 (proxies /api to :8001)
npm run build        # type-check + production build (vue-tsc -b && vite build)
npm run preview      # preview production build
```

### Backend (server/)
```bash
cd server
source .venv/bin/activate
uvicorn app.main:app --reload --port 8001   # dev server with auto-reload
celery -A app.tasks.celery_app worker --loglevel=info  # async task worker
```

### Database migrations (Alembic)
```bash
cd server && source .venv/bin/activate
alembic upgrade head     # apply all migrations
alembic downgrade -1     # rollback one migration
```

### Tests
```bash
cd server && source .venv/bin/activate
pytest -v                          # run all tests
pytest -v -k test_name             # run specific test
pytest --cov                       # with coverage
```
Tests are in `server/tests/` and use `pytest-asyncio` for async support.

### Docker (production)
```bash
docker-compose up --build          # starts nginx, app, db (pgvector/pg16), redis, celery worker
```

## Architecture

### Monorepo layout
- `client/` — Vue 3 + TypeScript + Vite + Pinia + Element Plus
- `server/` — FastAPI + SQLAlchemy (async) + Celery + pgvector
- `nginx/` — Reverse proxy for production

### Frontend structure (client/src/)
- `api/` — Axios-based API client. `request.ts` sets up base instance with auth interceptors. User APIs and `admin/` sub-directory for admin endpoints.
- `stores/` — Pinia stores: `user`, `chat`, `conversation`, `theme`, `admin`
- `views/` — Page components. `admin/` sub-directory for admin panel pages.
- `composables/` — `useTheme`, `useAccessibility`, `useResponsive`
- `styles/variables.scss` — Global SCSS variables, auto-injected via Vite config
- Path alias: `@` → `src/`
- Auto-imports: Vue/Pinia/Router APIs and Element Plus components are auto-imported (unplugin)

### Backend structure (server/app/)
- `api/v1/` — FastAPI route handlers. `router.py` aggregates all routes under `/api/v1`.
- `models/` — SQLAlchemy ORM models (10 models: user, admin, role, conversation, message, knowledge, media, sensitive_word, calendar, audit_log)
- `schemas/` — Pydantic request/response models
- `services/` — Business logic layer. Key services:
  - `chat_service` — Orchestrates: risk assessment → LLM call → review → response
  - `llm_service` — Multi-model routing (Qwen, GLM, local models) via OpenAI-compatible client
  - `review_service` — Dual-model fact-checking (hallucination prevention)
  - `risk_service` — Question risk classification (low/medium/high)
  - `sensitive_service` — Configurable word filtering
  - `embedding_service` — Vector embedding generation for knowledge retrieval
  - `file_parser_service` — PDF/DOCX/TXT text extraction
- `core/` — Infrastructure: database engine, Redis client, JWT/bcrypt security, RBAC permissions, middleware (audit logging, rate limiting, CORS)
- `tasks/` — Celery async tasks for document parsing, embedding generation, response review, cleanup
- `dependencies.py` — FastAPI `Depends()` providers: `current_user`, `current_admin`, `get_db`
- `config.py` — Pydantic Settings loaded from `.env`

### Chat pipeline flow
User query → `risk_service` (risk level) → `sensitive_service` (filter) → `llm_service` (generate) → `review_service` (fact-check) → response with knowledge source citations

### Auth model
- **Users**: Phone number + SMS verification code (mock code: `123456` when `SMS_MOCK=true`)
- **Admins**: Username + password (default: `admin` / `admin123`), managed by super admin only
- JWT tokens for both, separate auth flows (`/api/v1/auth` vs `/api/v1/admin/auth`)

### Database
- PostgreSQL with `pgvector` extension for vector similarity search on knowledge embeddings
- Async via `asyncpg` driver + SQLAlchemy AsyncSession
- DB name: `bnu_admission`

### Vite dev proxy
`/api/*` → `http://127.0.0.1:8001`, `/ws/*` → WebSocket proxy to same backend

## Domain Constraints

- All UI must follow BNU visual identity: academic blue primary color, Source Han Sans font
- WCAG 2.1 accessibility required, dark mode support
- No AI-generated images/videos — all visual content from official media library only
- Time-aware responses: system adjusts tone based on admission calendar phase (exam prep → application → enrollment)
- User roles affect responses: high school students, grad students, international students, parents
- High-risk questions return only verified answers or redirect to admissions office


## 注意，必须要安装并启用向量数据库