# 北京师范大学招生智能体 Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build a full-stack AI-powered admission chatbot for Beijing Normal University with Vue 3 frontend, FastAPI backend, PostgreSQL+pgvector, Redis, and Celery.

**Architecture:** Monolithic FastAPI app with Celery async workers, PostgreSQL+pgvector for structured data and vector search, Redis for caching/sessions/rate-limiting. Vue 3 SPA frontend with Element Plus. Docker Compose deployment.

**Tech Stack:** Python 3.12, FastAPI, SQLAlchemy 2.0, Alembic, Celery, Redis, PostgreSQL 16+pgvector, Vue 3, Vite, TypeScript, Pinia, Element Plus, SCSS, Docker Compose

**Design doc:** `docs/plans/2026-02-15-bnu-admission-chatbot-design.md`

---

## Phase 1: 项目脚手架与基础设施

### Task 1: 后端项目初始化

**Files:**
- Create: `server/app/__init__.py`
- Create: `server/app/main.py`
- Create: `server/app/config.py`
- Create: `server/requirements.txt`
- Create: `server/.env.example`
- Create: `server/Dockerfile`

**Step 1: 创建后端目录结构**

```bash
mkdir -p server/app/{models,schemas,api/v1,services,core,tasks}
mkdir -p server/{migrations,tests}
touch server/app/__init__.py
touch server/app/models/__init__.py
touch server/app/schemas/__init__.py
touch server/app/api/__init__.py
touch server/app/api/v1/__init__.py
touch server/app/services/__init__.py
touch server/app/core/__init__.py
touch server/app/tasks/__init__.py
touch server/tests/__init__.py
```

**Step 2: 创建 requirements.txt**

```txt
# Web framework
fastapi==0.115.6
uvicorn[standard]==0.34.0
python-multipart==0.0.18

# Database
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
alembic==1.14.1
pgvector==0.3.6

# Redis
redis[hiredis]==5.2.1

# Celery
celery[redis]==5.4.0

# Auth
pyjwt==2.10.1
bcrypt==4.2.1
pyotp==2.9.0

# Validation
pydantic==2.10.4
pydantic-settings==2.7.1
email-validator==2.2.0

# File parsing
pypdf2==3.0.1
pdfplumber==0.11.4
python-docx==1.1.2

# LLM clients
openai==1.58.1
httpx==0.28.1

# Utils
python-jose[cryptography]==3.3.0

# Testing
pytest==8.3.4
pytest-asyncio==0.25.0
pytest-cov==6.0.0
httpx==0.28.1
```

**Step 3: 创建 config.py**

```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # App
    APP_NAME: str = "BNU Admission Chatbot"
    DEBUG: bool = False
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql+asyncpg://postgres:postgres@db:5432/bnu_admission"

    # Redis
    REDIS_URL: str = "redis://redis:6379/0"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production"
    JWT_ALGORITHM: str = "HS256"
    USER_TOKEN_EXPIRE_DAYS: int = 7
    ADMIN_TOKEN_EXPIRE_HOURS: int = 2

    # SMS
    SMS_MOCK: bool = True

    # LLM
    LLM_PRIMARY_PROVIDER: str = "qwen"
    LLM_PRIMARY_API_KEY: str = ""
    LLM_PRIMARY_BASE_URL: str = ""
    LLM_PRIMARY_MODEL: str = ""
    LLM_REVIEW_PROVIDER: str = "qwen"
    LLM_REVIEW_MODEL: str = ""

    # File storage
    UPLOAD_DIR: str = "/data/uploads"
    MAX_UPLOAD_SIZE_MB: int = 50

    # Celery
    CELERY_BROKER_URL: str = "redis://redis:6379/1"
    CELERY_RESULT_BACKEND: str = "redis://redis:6379/2"

    class Config:
        env_file = ".env"

settings = Settings()
```

**Step 4: 创建 main.py**

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings

def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
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

    @app.get("/health")
    async def health_check():
        return {"status": "ok"}

    return app

app = create_app()
```

**Step 5: 创建 .env.example**

```env
DEBUG=true
DATABASE_URL=postgresql+asyncpg://postgres:postgres@db:5432/bnu_admission
REDIS_URL=redis://redis:6379/0
JWT_SECRET_KEY=change-me-in-production
SMS_MOCK=true
LLM_PRIMARY_PROVIDER=qwen
LLM_PRIMARY_API_KEY=
LLM_PRIMARY_BASE_URL=
LLM_PRIMARY_MODEL=
CELERY_BROKER_URL=redis://redis:6379/1
CELERY_RESULT_BACKEND=redis://redis:6379/2
```

**Step 6: 创建 Dockerfile**

```dockerfile
FROM python:3.12-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

**Step 7: Commit**

```bash
git add server/
git commit -m "feat: scaffold backend project with FastAPI, config, and Dockerfile"
```

---

### Task 2: Docker Compose 编排

**Files:**
- Create: `docker-compose.yml`
- Create: `nginx/nginx.conf`
- Create: `nginx/Dockerfile`

**Step 1: 创建 docker-compose.yml**

```yaml
version: "3.9"

services:
  nginx:
    build: ./nginx
    ports:
      - "80:80"
    depends_on:
      - app
    volumes:
      - ./client/dist:/usr/share/nginx/html:ro
    networks:
      - frontend

  app:
    build: ./server
    env_file: ./server/.env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - upload_data:/data/uploads
      - app_logs:/data/logs
    networks:
      - frontend
      - backend

  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: bnu_admission
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
    volumes:
      - pg_data:/var/lib/postgresql/data
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U postgres"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - backend

  redis:
    image: redis:7-alpine
    command: redis-server --appendonly yes
    volumes:
      - redis_data:/data
    healthcheck:
      test: ["CMD", "redis-cli", "ping"]
      interval: 5s
      timeout: 5s
      retries: 5
    networks:
      - backend

  worker:
    build: ./server
    command: celery -A app.tasks.celery_app worker --loglevel=info --concurrency=4
    env_file: ./server/.env
    depends_on:
      db:
        condition: service_healthy
      redis:
        condition: service_healthy
    volumes:
      - upload_data:/data/uploads
    networks:
      - backend

volumes:
  pg_data:
  redis_data:
  upload_data:
  app_logs:

networks:
  frontend:
  backend:
```

**Step 2: 创建 nginx/nginx.conf**

```nginx
upstream fastapi {
    server app:8000;
}

server {
    listen 80;
    server_name _;

    client_max_body_size 50M;

    # Rate limiting
    limit_req_zone $binary_remote_addr zone=api:10m rate=60r/m;
    limit_conn_zone $binary_remote_addr zone=conn:10m;

    # Static files (Vue SPA)
    location / {
        root /usr/share/nginx/html;
        try_files $uri $uri/ /index.html;
        expires 1y;
        add_header Cache-Control "public, immutable";
    }

    # Index should not be cached
    location = /index.html {
        root /usr/share/nginx/html;
        expires -1;
        add_header Cache-Control "no-store, no-cache, must-revalidate";
    }

    # API proxy
    location /api/ {
        limit_req zone=api burst=20 nodelay;
        limit_conn conn 100;
        proxy_pass http://fastapi;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket proxy
    location /ws/ {
        proxy_pass http://fastapi;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 86400;
    }
}
```

**Step 3: 创建 nginx/Dockerfile**

```dockerfile
FROM nginx:alpine
COPY nginx.conf /etc/nginx/conf.d/default.conf
```

**Step 4: Commit**

```bash
git add docker-compose.yml nginx/
git commit -m "feat: add Docker Compose orchestration with Nginx, PG, Redis, Celery"
```

---

### Task 3: 数据库连接与 Alembic 迁移初始化

**Files:**
- Create: `server/app/core/database.py`
- Create: `server/app/core/redis.py`
- Create: `server/alembic.ini`
- Create: `server/migrations/env.py`

**Step 1: 创建 database.py**

```python
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from app.config import settings

engine = create_async_engine(settings.DATABASE_URL, echo=settings.DEBUG)
async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

class Base(DeclarativeBase):
    pass

async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
        finally:
            await session.close()
```

**Step 2: 创建 redis.py**

```python
import redis.asyncio as aioredis
from app.config import settings

redis_client = aioredis.from_url(settings.REDIS_URL, decode_responses=True)

async def get_redis() -> aioredis.Redis:
    return redis_client
```

**Step 3: 初始化 Alembic**

```bash
cd server && alembic init migrations
```

配置 `alembic.ini` 中 `sqlalchemy.url` 为同步连接串（Alembic 迁移用），配置 `migrations/env.py` 导入 `Base.metadata`。

**Step 4: Commit**

```bash
git add server/app/core/database.py server/app/core/redis.py server/alembic.ini server/migrations/
git commit -m "feat: add database and Redis connection infrastructure with Alembic"
```

---

## Phase 2: 数据模型与迁移

### Task 4: 用户与管理员 ORM 模型

**Files:**
- Create: `server/app/models/user.py`
- Create: `server/app/models/admin.py`
- Test: `server/tests/test_models.py`

**Step 1: 编写 User 模型测试**

```python
# server/tests/test_models.py
from app.models.user import User

def test_user_model_has_required_fields():
    """验证 User 模型具有设计文档中定义的所有字段"""
    columns = {c.name for c in User.__table__.columns}
    required = {"id", "phone", "nickname", "avatar_url", "gender", "province",
                "birth_year", "school", "status", "last_login_at", "last_login_ip",
                "token_expire_at", "created_at", "updated_at"}
    assert required.issubset(columns)
```

**Step 2: 运行测试验证失败**

```bash
cd server && python -m pytest tests/test_models.py::test_user_model_has_required_fields -v
```

Expected: FAIL — `ModuleNotFoundError: No module named 'app.models.user'`

**Step 3: 实现 User 模型**

```python
# server/app/models/user.py
import uuid
from datetime import datetime
from sqlalchemy import String, Integer, Boolean, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    phone: Mapped[str] = mapped_column(String(11), unique=True, nullable=False)
    nickname: Mapped[str] = mapped_column(String(50), nullable=False)
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    gender: Mapped[str | None] = mapped_column(String(10))
    province: Mapped[str | None] = mapped_column(String(20))
    birth_year: Mapped[int | None] = mapped_column(Integer)
    school: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(INET)
    token_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
```

**Step 4: 实现 AdminUser 模型**

```python
# server/app/models/admin.py
import uuid
from datetime import datetime
from sqlalchemy import String, ForeignKey, DateTime, text
from sqlalchemy.dialects.postgresql import UUID, INET
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class AdminUser(Base):
    __tablename__ = "admin_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    real_name: Mapped[str] = mapped_column(String(50), nullable=False)
    employee_id: Mapped[str | None] = mapped_column(String(30), unique=True)
    department: Mapped[str | None] = mapped_column(String(100))
    title: Mapped[str | None] = mapped_column(String(50))
    phone: Mapped[str | None] = mapped_column(String(11))
    email: Mapped[str | None] = mapped_column(String(100))
    avatar_url: Mapped[str] = mapped_column(String(500), default="")
    mfa_secret: Mapped[str | None] = mapped_column(String(100))
    status: Mapped[str] = mapped_column(String(10), nullable=False, default="active")
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_login_ip: Mapped[str | None] = mapped_column(INET)
    token_expire_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
```

**Step 5: 运行测试验证通过**

```bash
cd server && python -m pytest tests/test_models.py -v
```

Expected: PASS

**Step 6: Commit**

```bash
git add server/app/models/ server/tests/
git commit -m "feat: add User and AdminUser ORM models"
```

---

### Task 5: RBAC 权限模型

**Files:**
- Create: `server/app/models/role.py`
- Test: `server/tests/test_models.py` (追加)

**Step 1: 编写 Role 模型测试**

```python
def test_rbac_tables_exist():
    from app.models.role import Role, Permission, RolePermission, UserRole, AdminRole
    assert Role.__tablename__ == "roles"
    assert Permission.__tablename__ == "permissions"
    assert RolePermission.__tablename__ == "role_permissions"
    assert UserRole.__tablename__ == "user_roles"
    assert AdminRole.__tablename__ == "admin_roles"
```

**Step 2: 运行测试验证失败**

**Step 3: 实现 RBAC 5 表模型**

```python
# server/app/models/role.py
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class Role(Base):
    __tablename__ = "roles"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(String(30), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(50), nullable=False)
    role_type: Mapped[str] = mapped_column(String(10), nullable=False)  # user / admin
    description: Mapped[str | None] = mapped_column(String(500))
    is_system: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

class Permission(Base):
    __tablename__ = "permissions"
    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    code: Mapped[str] = mapped_column(String(60), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    resource: Mapped[str] = mapped_column(String(30), nullable=False)
    action: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str | None] = mapped_column(String(500))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

class RolePermission(Base):
    __tablename__ = "role_permissions"
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    permission_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("permissions.id", ondelete="CASCADE"), primary_key=True)

class UserRole(Base):
    __tablename__ = "user_roles"
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

class AdminRole(Base):
    __tablename__ = "admin_roles"
    admin_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("admin_users.id", ondelete="CASCADE"), primary_key=True)
    role_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("roles.id", ondelete="CASCADE"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
```

**Step 4: 运行测试，Commit**

```bash
git add server/app/models/role.py server/tests/
git commit -m "feat: add RBAC models (Role, Permission, RolePermission, UserRole, AdminRole)"
```

---

### Task 6: 对话与消息模型

**Files:**
- Create: `server/app/models/conversation.py`
- Create: `server/app/models/message.py`

**Step 1: 实现 Conversation 模型（含软删除）**

```python
# server/app/models/conversation.py
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, ForeignKey, DateTime, Index, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conv_user", "user_id", "updated_at", postgresql_where=text("is_deleted = FALSE")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    title: Mapped[str | None] = mapped_column(String(200))
    is_pinned: Mapped[bool] = mapped_column(Boolean, default=False)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    messages = relationship("Message", back_populates="conversation", lazy="selectin")
```

**Step 2: 实现 Message 模型（含软删除）**

```python
# server/app/models/message.py
import uuid
from datetime import datetime
from sqlalchemy import String, Boolean, Text, ForeignKey, DateTime, Index, text
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base

class Message(Base):
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_msg_conv", "conversation_id", "created_at", postgresql_where=text("is_deleted = FALSE")),
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, server_default=text("gen_random_uuid()"))
    conversation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    role: Mapped[str] = mapped_column(String(10), nullable=False)  # user / assistant / system
    content: Mapped[str] = mapped_column(Text, nullable=False)
    model_version: Mapped[str | None] = mapped_column(String(50))
    risk_level: Mapped[str | None] = mapped_column(String(10))
    review_passed: Mapped[bool | None] = mapped_column(Boolean)
    sources: Mapped[dict | None] = mapped_column(JSONB)
    is_deleted: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    deleted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, server_default=text("NOW()"))

    conversation = relationship("Conversation", back_populates="messages")
```

**Step 3: Commit**

```bash
git add server/app/models/conversation.py server/app/models/message.py
git commit -m "feat: add Conversation and Message models with soft delete"
```

---

### Task 7: 知识库、敏感词、多媒体、审计日志、日历模型

**Files:**
- Create: `server/app/models/knowledge.py`
- Create: `server/app/models/sensitive_word.py`
- Create: `server/app/models/media.py`
- Create: `server/app/models/audit_log.py`
- Create: `server/app/models/calendar.py`

**Step 1: 实现所有剩余模型**

按照设计文档 3.7–3.11 节的 SQL 定义，分别创建 ORM 模型：
- `KnowledgeDocument` + `KnowledgeChunk`（含 pgvector 向量列）
- `SensitiveWordGroup` + `SensitiveWord`
- `MediaResource`
- `AuditLog` + `FileUploadLog`
- `AdmissionCalendar`

**Step 2: 在 models/__init__.py 中汇总导出所有模型**

```python
# server/app/models/__init__.py
from app.models.user import User
from app.models.admin import AdminUser
from app.models.role import Role, Permission, RolePermission, UserRole, AdminRole
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.knowledge import KnowledgeDocument, KnowledgeChunk
from app.models.sensitive_word import SensitiveWordGroup, SensitiveWord
from app.models.media import MediaResource
from app.models.audit_log import AuditLog, FileUploadLog
from app.models.calendar import AdmissionCalendar
```

**Step 3: 生成 Alembic 迁移**

```bash
cd server && alembic revision --autogenerate -m "initial schema"
```

**Step 4: 运行迁移（需 Docker Compose 启动 DB）**

```bash
docker compose up db -d
cd server && alembic upgrade head
```

**Step 5: Commit**

```bash
git add server/app/models/ server/migrations/
git commit -m "feat: add all ORM models and initial Alembic migration"
```

---

### Task 8: 预置种子数据（角色 + 权限）

**Files:**
- Create: `server/app/core/seed.py`

**Step 1: 编写种子数据脚本**

创建脚本插入 8 个预置角色（super_admin, reviewer, admin, teacher, gaokao, kaoyan, international, parent）和权限矩阵（按设计文档 3.4 节）。

包含：
- 7 个资源 × 6 个操作 = 最多 42 个权限条目
- 4 个管理员角色的 role_permissions 关联
- 创建默认超级管理员账号（username: admin, 需首次登录修改密码）

**Step 2: 在 main.py 的 startup 事件中调用种子数据**

```python
@app.on_event("startup")
async def startup():
    from app.core.seed import seed_roles_and_permissions
    await seed_roles_and_permissions()
```

**Step 3: Commit**

```bash
git add server/app/core/seed.py server/app/main.py
git commit -m "feat: add seed data for RBAC roles, permissions, and default admin"
```

---

## Phase 3: 核心后端服务

### Task 9: 统一异常处理与中间件

**Files:**
- Create: `server/app/core/exceptions.py`
- Create: `server/app/core/middleware.py`
- Modify: `server/app/main.py`

**Step 1: 定义统一异常类**

```python
# server/app/core/exceptions.py
from fastapi import HTTPException

class BizError(HTTPException):
    def __init__(self, code: int, message: str, status_code: int = 400):
        super().__init__(status_code=status_code, detail={"code": code, "message": message})

class UnauthorizedError(BizError):
    def __init__(self, message: str = "未授权"):
        super().__init__(code=401, message=message, status_code=401)

class ForbiddenError(BizError):
    def __init__(self, message: str = "无权限"):
        super().__init__(code=403, message=message, status_code=403)

class NotFoundError(BizError):
    def __init__(self, message: str = "资源不存在"):
        super().__init__(code=404, message=message, status_code=404)
```

**Step 2: 实现审计日志中间件和限流中间件**

审计中间件：每个请求自动记录到 audit_logs。
限流中间件：基于 Redis 的 IP 限流（120次/分）。

**Step 3: 在 main.py 中注册中间件**

**Step 4: Commit**

```bash
git add server/app/core/exceptions.py server/app/core/middleware.py server/app/main.py
git commit -m "feat: add unified exceptions, audit logging, and rate limiting middleware"
```

---

### Task 10: JWT 安全与认证依赖

**Files:**
- Create: `server/app/core/security.py`
- Create: `server/app/dependencies.py`
- Test: `server/tests/test_security.py`

**Step 1: 编写 JWT 工具测试**

```python
def test_create_and_verify_token():
    from app.core.security import create_access_token, verify_token
    token = create_access_token({"sub": "user-123", "type": "user"})
    payload = verify_token(token)
    assert payload["sub"] == "user-123"

def test_password_hash():
    from app.core.security import hash_password, verify_password
    hashed = hash_password("test123")
    assert verify_password("test123", hashed)
    assert not verify_password("wrong", hashed)
```

**Step 2: 运行测试验证失败**

**Step 3: 实现 security.py**

包含：`create_access_token`, `verify_token`, `hash_password`, `verify_password`, `generate_mfa_secret`, `verify_mfa_code`

**Step 4: 实现 dependencies.py**

包含：`get_current_user` (从 JWT 解析用户), `get_current_admin` (从 JWT 解析管理员), `get_db`, `get_redis`

**Step 5: 运行测试验证通过，Commit**

```bash
git add server/app/core/security.py server/app/dependencies.py server/tests/test_security.py
git commit -m "feat: add JWT auth, password hashing, MFA, and auth dependencies"
```

---

### Task 11: RBAC 权限校验装饰器

**Files:**
- Create: `server/app/core/permissions.py`
- Test: `server/tests/test_permissions.py`

**Step 1: 编写权限校验测试**

测试场景：有权限时通过、无权限时抛 ForbiddenError、Redis 缓存命中时跳过 DB 查询。

**Step 2: 实现 `require_permission` 装饰器**

```python
# server/app/core/permissions.py
from functools import wraps
from app.core.exceptions import ForbiddenError

def require_permission(*permission_codes: str):
    """RBAC 权限校验装饰器"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            admin = kwargs.get("current_admin")
            if not admin:
                raise ForbiddenError("需要管理员登录")
            # 1. 先查 Redis 缓存
            # 2. 缓存未命中则查 DB: admin_roles → role_permissions → permissions
            # 3. 校验 permission_codes 是否命中
            # 4. 写入 Redis 缓存
            return await func(*args, **kwargs)
        return wrapper
    return decorator
```

**Step 3: 运行测试，Commit**

```bash
git add server/app/core/permissions.py server/tests/test_permissions.py
git commit -m "feat: add RBAC permission checking decorator with Redis caching"
```

---

### Task 12: 短信服务（Mock）与用户认证 API

**Files:**
- Create: `server/app/services/sms_service.py`
- Create: `server/app/services/auth_service.py`
- Create: `server/app/api/v1/auth.py`
- Create: `server/app/schemas/user.py`
- Test: `server/tests/test_auth.py`

**Step 1: 编写认证 API 测试**

```python
# server/tests/test_auth.py
import pytest
from httpx import AsyncClient

@pytest.mark.asyncio
async def test_send_sms_code(client: AsyncClient):
    resp = await client.post("/api/v1/auth/sms/send", json={"phone": "13800138000"})
    assert resp.status_code == 200

@pytest.mark.asyncio
async def test_login_with_sms(client: AsyncClient):
    # 先发送验证码
    await client.post("/api/v1/auth/sms/send", json={"phone": "13800138000"})
    # Mock 模式下验证码固定为 123456
    resp = await client.post("/api/v1/auth/login", json={
        "phone": "13800138000",
        "code": "123456",
        "nickname": "测试用户",
        "user_role": "gaokao"
    })
    assert resp.status_code == 200
    assert "token" in resp.json()
```

**Step 2: 实现 sms_service.py（Mock 模式返回固定验证码 123456）**

**Step 3: 实现 auth_service.py**

包含：`send_sms_code`, `verify_sms_and_login`（含频率限制检查、用户自动注册、JWT 生成）

**Step 4: 实现 schemas/user.py（Pydantic 请求/响应模型）**

**Step 5: 实现 api/v1/auth.py 路由**

```
POST /api/v1/auth/sms/send    — 发送验证码
POST /api/v1/auth/login        — 验证码登录/注册
POST /api/v1/auth/logout       — 登出
GET  /api/v1/auth/me           — 获取当前用户信息
PUT  /api/v1/auth/me           — 更新用户信息
```

**Step 6: 运行测试，Commit**

```bash
git add server/app/services/sms_service.py server/app/services/auth_service.py \
        server/app/api/v1/auth.py server/app/schemas/user.py server/tests/test_auth.py
git commit -m "feat: add SMS mock service and user auth API (send code, login, logout)"
```

---

### Task 13: 管理员认证 API（用户名 + 密码 + MFA）

**Files:**
- Create: `server/app/api/v1/admin_auth.py`
- Create: `server/app/schemas/admin.py`
- Test: `server/tests/test_admin_auth.py`

**Step 1: 编写管理员登录测试**

测试场景：正确密码+MFA 登录成功、密码错误 401、MFA 错误 401。

**Step 2: 实现 admin_auth.py 路由**

```
POST /api/v1/admin/auth/login     — 管理员登录（username + password + mfa_code）
POST /api/v1/admin/auth/logout    — 管理员登出
GET  /api/v1/admin/auth/me        — 获取管理员信息 + 权限列表
```

**Step 3: 运行测试，Commit**

```bash
git add server/app/api/v1/admin_auth.py server/app/schemas/admin.py server/tests/test_admin_auth.py
git commit -m "feat: add admin auth API with password + MFA verification"
```

---

### Task 14: 对话历史管理 API

**Files:**
- Create: `server/app/api/v1/conversation.py`
- Create: `server/app/schemas/chat.py`
- Test: `server/tests/test_conversation.py`

**Step 1: 编写对话 CRUD 测试**

测试：创建对话、列表查询（分页）、更新标题、置顶、软删除、已删除对话不出现在列表中。

**Step 2: 实现路由**

```
GET    /api/v1/conversations           — 对话列表（分页，排除软删除）
POST   /api/v1/conversations           — 新建对话
GET    /api/v1/conversations/{id}      — 对话详情 + 消息列表
PUT    /api/v1/conversations/{id}      — 更新标题/置顶
DELETE /api/v1/conversations/{id}      — 软删除
GET    /api/v1/conversations/{id}/messages — 消息列表（分页）
```

**Step 3: 运行测试，Commit**

```bash
git add server/app/api/v1/conversation.py server/app/schemas/chat.py server/tests/test_conversation.py
git commit -m "feat: add conversation CRUD API with soft delete and pagination"
```

---

### Task 15: LLM 接入层（策略模式 + 路由）

**Files:**
- Create: `server/app/services/llm_service.py`
- Test: `server/tests/test_llm_service.py`

**Step 1: 编写 LLM 服务测试**

测试：Mock provider 返回流式响应、LLMRouter failover 逻辑。

**Step 2: 实现 LLMProvider 抽象类 + QwenProvider + GLMProvider + LocalProvider**

每个 provider 实现 `chat(messages, stream)` 和 `embed(texts)` 接口。

**Step 3: 实现 LLMRouter**

支持 round_robin / weighted / failover 策略，管理员可通过 API 切换。

**Step 4: 运行测试，Commit**

```bash
git add server/app/services/llm_service.py server/tests/test_llm_service.py
git commit -m "feat: add LLM service with strategy pattern and router (failover/load balancing)"
```

---

### Task 16: 敏感词过滤服务

**Files:**
- Create: `server/app/services/sensitive_service.py`
- Test: `server/tests/test_sensitive_service.py`

**Step 1: 编写敏感词过滤测试**

测试：block 级别词命中时返回 blocked、warn 级别词命中时返回 warned、无命中时放行、Redis 缓存命中逻辑。

**Step 2: 实现 sensitive_service.py**

从 Redis 加载敏感词集合，使用 Aho-Corasick 或简单遍历匹配。

**Step 3: 运行测试，Commit**

```bash
git add server/app/services/sensitive_service.py server/tests/test_sensitive_service.py
git commit -m "feat: add sensitive word filtering service with Redis caching"
```

---

### Task 17: 风险分级 + 情感识别 + 时间感知服务

**Files:**
- Create: `server/app/services/risk_service.py`
- Create: `server/app/services/emotion_service.py`
- Create: `server/app/services/calendar_service.py`
- Test: `server/tests/test_chat_services.py`

**Step 1: 实现 risk_service.py**

使用关键词规则 + LLM 辅助分类，将问题分为 low/medium/high。

**Step 2: 实现 emotion_service.py**

关键词匹配检测焦虑/迷茫/挫败等情绪，返回情感标签。

**Step 3: 实现 calendar_service.py**

查询 admission_calendar 表，返回当前阶段的 tone_config（话术风格、关键词、重点内容）。结果缓存到 Redis `calendar:current`。

**Step 4: 编写测试，运行测试，Commit**

```bash
git add server/app/services/risk_service.py server/app/services/emotion_service.py \
        server/app/services/calendar_service.py server/tests/test_chat_services.py
git commit -m "feat: add risk classification, emotion detection, and calendar-aware tone services"
```

---

### Task 18: 知识库检索服务

**Files:**
- Create: `server/app/services/knowledge_service.py`
- Create: `server/app/services/embedding_service.py`
- Test: `server/tests/test_knowledge_service.py`

**Step 1: 实现 embedding_service.py**

调用 LLMProvider.embed() 生成向量。

**Step 2: 实现 knowledge_service.py**

`search(query, top_k=5)`: 将 query Embedding 后，用 pgvector 做余弦相似度检索。

**Step 3: 编写测试（Mock embedding），运行，Commit**

```bash
git add server/app/services/knowledge_service.py server/app/services/embedding_service.py \
        server/tests/test_knowledge_service.py
git commit -m "feat: add knowledge base vector search with pgvector"
```

---

### Task 19: 双模型审查服务

**Files:**
- Create: `server/app/services/review_service.py`
- Test: `server/tests/test_review_service.py`

**Step 1: 实现 review_service.py**

`verify(question, answer, sources)`: 调用轻量审查模型，判断回答与知识库来源的事实一致性。返回 passed/flagged。

**Step 2: 编写测试，Commit**

```bash
git add server/app/services/review_service.py server/tests/test_review_service.py
git commit -m "feat: add dual-model review service for hallucination prevention"
```

---

### Task 20: 智能对话 API（核心编排 + 流式输出）

**Files:**
- Create: `server/app/services/chat_service.py`
- Create: `server/app/api/v1/chat.py`
- Test: `server/tests/test_chat.py`

**Step 1: 实现 chat_service.py — 对话编排主链路**

按设计文档 4.3 节的 9 步链路实现：
1. 敏感词预过滤
2. 风险分级
3. 时间感知话术注入
4. 情感识别
5. 知识库检索
6. Prompt 组装（角色差异化 + 上下文）
7. LLM 流式调用
8. 异步双模型审查（Celery）
9. 消息持久化 + 审计日志

**Step 2: 实现 api/v1/chat.py — WebSocket 端点**

```
WS /ws/chat/{conversation_id}   — 流式对话
POST /api/v1/chat/send           — 同步发送（备用）
```

WebSocket 处理：接收用户消息 → 调用 chat_service → 流式推送 token → 推送完成标记。

**Step 3: 实现对话标题自动生成（首轮对话后 Celery 异步任务）**

**Step 4: 编写测试，Commit**

```bash
git add server/app/services/chat_service.py server/app/api/v1/chat.py server/tests/test_chat.py
git commit -m "feat: add core chat orchestration with streaming, RAG, and hallucination prevention"
```

---

### Task 21: Celery 异步任务（文档解析 + Embedding + 审查 + 清理）

**Files:**
- Create: `server/app/tasks/celery_app.py`
- Create: `server/app/tasks/parse_task.py`
- Create: `server/app/tasks/embedding_task.py`
- Create: `server/app/tasks/review_task.py`
- Create: `server/app/tasks/cleanup_task.py`
- Create: `server/app/services/file_parser_service.py`

**Step 1: 配置 Celery 实例**

```python
# server/app/tasks/celery_app.py
from celery import Celery
from celery.schedules import crontab
from app.config import settings

celery = Celery("bnu_admission", broker=settings.CELERY_BROKER_URL, backend=settings.CELERY_RESULT_BACKEND)

celery.conf.beat_schedule = {
    "refresh-calendar-daily": {"task": "app.tasks.cleanup_task.refresh_calendar", "schedule": crontab(hour=0, minute=0)},
    "cleanup-expired-daily": {"task": "app.tasks.cleanup_task.cleanup_expired", "schedule": crontab(hour=3, minute=0)},
    "archive-logs-weekly": {"task": "app.tasks.cleanup_task.archive_logs", "schedule": crontab(day_of_week=0, hour=4)},
}
```

**Step 2: 实现 file_parser_service.py**

PDF → pdfplumber, Word → python-docx, TXT/MD → 直接读取。

**Step 3: 实现 parse_task + embedding_task + review_task + cleanup_task**

**Step 4: Commit**

```bash
git add server/app/tasks/ server/app/services/file_parser_service.py
git commit -m "feat: add Celery tasks for document parsing, embedding, review, and cleanup"
```

---

### Task 22: 知识库管理 API（含审核流）

**Files:**
- Create: `server/app/api/v1/knowledge.py`
- Create: `server/app/schemas/knowledge.py`
- Test: `server/tests/test_knowledge_api.py`

**Step 1: 实现路由**

```
POST   /api/v1/admin/knowledge/upload        — 上传文档（需 knowledge:create）
GET    /api/v1/admin/knowledge                — 文档列表（分页筛选）
GET    /api/v1/admin/knowledge/{id}           — 文档详情 + 切片预览
POST   /api/v1/admin/knowledge/{id}/review    — 审核通过/拒绝（需 knowledge:approve）
DELETE /api/v1/admin/knowledge/{id}           — 归档文档
```

**Step 2: 上传流程**

接收文件 → SHA-256 哈希 → 加密存储 → 写入 knowledge_documents（pending）→ 写入 file_upload_logs → 返回 doc_id。

**Step 3: 审核流程**

审核通过 → 触发 Celery parse_task → parse 完成自动触发 embedding_task → 完成后 status=approved。

**Step 4: 编写测试，Commit**

```bash
git add server/app/api/v1/knowledge.py server/app/schemas/knowledge.py server/tests/test_knowledge_api.py
git commit -m "feat: add knowledge base management API with upload, review, and embedding pipeline"
```

---

### Task 23: 管理后台 API（用户管理、角色管理、敏感词、模型配置、日历、日志、仪表盘）

**Files:**
- Create: `server/app/api/v1/admin_user.py`
- Create: `server/app/api/v1/admin_role.py`
- Create: `server/app/api/v1/admin_sensitive.py`
- Create: `server/app/api/v1/admin_model.py`
- Create: `server/app/api/v1/admin_calendar.py`
- Create: `server/app/api/v1/admin_log.py`
- Create: `server/app/api/v1/admin_dashboard.py`
- Create: `server/app/api/v1/media.py`

**Step 1: 用户管理 API**

```
GET    /api/v1/admin/users          — 用户列表
PUT    /api/v1/admin/users/{id}/ban — 封禁/解封
```

**Step 2: 管理员管理 API**

```
GET    /api/v1/admin/admins          — 管理员列表
POST   /api/v1/admin/admins          — 创建管理员（仅超管）
PUT    /api/v1/admin/admins/{id}     — 编辑管理员信息
DELETE /api/v1/admin/admins/{id}     — 禁用管理员
```

**Step 3: 角色权限管理 API**

```
GET    /api/v1/admin/roles           — 角色列表
POST   /api/v1/admin/roles           — 创建角色
PUT    /api/v1/admin/roles/{id}      — 编辑角色
PUT    /api/v1/admin/roles/{id}/permissions — 分配权限
GET    /api/v1/admin/permissions     — 权限列表
```

**Step 4: 敏感词库管理 API**

```
GET    /api/v1/admin/sensitive/groups       — 词库列表
POST   /api/v1/admin/sensitive/groups       — 创建词库
GET    /api/v1/admin/sensitive/groups/{id}  — 词库详情 + 词条列表
POST   /api/v1/admin/sensitive/words        — 添加词条
DELETE /api/v1/admin/sensitive/words/{id}   — 删除词条
```

**Step 5: 模型配置 API**

```
GET    /api/v1/admin/models             — 当前模型配置
PUT    /api/v1/admin/models             — 更新模型配置（主模型/审查模型/负载策略）
POST   /api/v1/admin/models/test        — 测试模型连通性
```

**Step 6: 招生日历 API**

```
GET    /api/v1/admin/calendar           — 日历配置列表
PUT    /api/v1/admin/calendar/{id}      — 更新日历阶段配置
```

**Step 7: 审计日志 API**

```
GET    /api/v1/admin/logs               — 审计日志（分页、筛选）
GET    /api/v1/admin/logs/export        — 导出 CSV
```

**Step 8: 多媒体资源 API**

```
GET    /api/v1/admin/media              — 资源列表
POST   /api/v1/admin/media/upload       — 上传资源
PUT    /api/v1/admin/media/{id}/approve — 审核资源
DELETE /api/v1/admin/media/{id}         — 删除资源
```

**Step 9: 仪表盘 API**

```
GET    /api/v1/admin/dashboard/stats    — 统计卡片（用户数、对话数、今日活跃等）
GET    /api/v1/admin/dashboard/trends   — 对话量趋势（近 30 天）
GET    /api/v1/admin/dashboard/hot      — 热门问题排行
```

**Step 10: 注册所有路由到 router.py**

```python
# server/app/api/router.py
from fastapi import APIRouter
from app.api.v1 import (auth, chat, conversation, knowledge, media,
    admin_auth, admin_user, admin_role, admin_sensitive,
    admin_model, admin_calendar, admin_log, admin_dashboard)

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router, prefix="/auth", tags=["用户认证"])
api_router.include_router(chat.router, prefix="/chat", tags=["智能对话"])
api_router.include_router(conversation.router, prefix="/conversations", tags=["对话管理"])
# ... 注册所有路由
```

**Step 11: Commit**

```bash
git add server/app/api/ server/app/schemas/
git commit -m "feat: add all admin APIs (users, roles, sensitive words, model config, calendar, logs, dashboard, media)"
```

---

## Phase 4: 前端项目搭建

### Task 24: 前端项目初始化

**Files:**
- Create: `client/` (Vite scaffold)
- Create: `client/src/styles/variables.scss`
- Create: `client/src/styles/reset.scss`

**Step 1: 使用 Vite 创建 Vue 3 + TypeScript 项目**

```bash
npm create vite@latest client -- --template vue-ts
cd client && npm install
```

**Step 2: 安装核心依赖**

```bash
npm install vue-router@4 pinia element-plus @element-plus/icons-vue axios sass
npm install -D unplugin-auto-import unplugin-vue-components
```

**Step 3: 创建目录结构**

```bash
mkdir -p src/{router,stores,api/admin,composables,components/{common,auth,chat,conversation,home,admin/{layout,dashboard,knowledge,sensitive,model,user,role,media,calendar,log}},styles,utils,types}
```

**Step 4: 配置 vite.config.ts（Element Plus 按需引入 + 代理）**

**Step 5: 创建 variables.scss（按设计文档 5.4 节色值）**

**Step 6: 创建 reset.scss 和全局样式**

**Step 7: Commit**

```bash
git add client/
git commit -m "feat: scaffold Vue 3 frontend with Vite, Element Plus, Pinia, and BNU design tokens"
```

---

### Task 25: 路由与全局守卫

**Files:**
- Create: `client/src/router/index.ts`
- Create: `client/src/router/user.ts`
- Create: `client/src/router/admin.ts`

**Step 1: 实现路由配置**

按设计文档 5.2 节路由表，所有页面组件使用懒加载 `() => import(...)`。

**Step 2: 实现路由守卫**

```typescript
router.beforeEach(async (to, from, next) => {
    // 1. 白名单放行
    // 2. Token 检查
    // 3. /admin/* RBAC 检查
    // 4. 放行
})
```

**Step 3: Commit**

```bash
git add client/src/router/
git commit -m "feat: add Vue Router with lazy loading, auth guards, and RBAC admin guards"
```

---

### Task 26: Pinia 状态管理

**Files:**
- Create: `client/src/stores/user.ts`
- Create: `client/src/stores/chat.ts`
- Create: `client/src/stores/conversation.ts`
- Create: `client/src/stores/theme.ts`
- Create: `client/src/stores/admin.ts`

**Step 1: 实现 user store**

管理 token、用户信息、登录态。

**Step 2: 实现 chat store**

管理当前对话消息列表、流式输出状态、发送中标记。

**Step 3: 实现 conversation store**

管理对话历史列表、搜索、分页。

**Step 4: 实现 theme store**

日间/夜间模式切换、字体大小调节（14/16/18/20px）。

**Step 5: 实现 admin store**

管理员登录态、权限列表。

**Step 6: Commit**

```bash
git add client/src/stores/
git commit -m "feat: add Pinia stores for user, chat, conversation, theme, and admin"
```

---

### Task 27: API 请求层与 WebSocket

**Files:**
- Create: `client/src/api/request.ts`
- Create: `client/src/api/ws.ts`
- Create: `client/src/api/auth.ts`
- Create: `client/src/api/chat.ts`
- Create: `client/src/api/admin/*.ts`

**Step 1: 实现 Axios 实例（request.ts）**

Token 自动注入、401 自动跳转登录、统一错误 toast。

**Step 2: 实现 WebSocket 管理（ws.ts）**

连接、断线重连（指数退避）、心跳、消息分发。

**Step 3: 实现所有 API 模块**

每个模块对应后端一组路由。

**Step 4: Commit**

```bash
git add client/src/api/
git commit -m "feat: add API request layer with Axios interceptors and WebSocket manager"
```

---

## Phase 5: 前端页面实现

### Task 28: 登录页

**Files:**
- Create: `client/src/views/Login.vue`
- Create: `client/src/components/auth/LoginForm.vue`
- Create: `client/src/components/auth/SmsCodeInput.vue`
- Create: `client/src/components/auth/RoleSelector.vue`

**Step 1: 实现 LoginForm（手机号输入 + 验证码发送按钮 + 倒计时）**

**Step 2: 实现 SmsCodeInput（6 位验证码输入框）**

**Step 3: 实现 RoleSelector（首次注册时选择角色）**

**Step 4: 组合到 Login.vue 页面，北师大品牌元素背景**

**Step 5: Commit**

```bash
git add client/src/views/Login.vue client/src/components/auth/
git commit -m "feat: add login page with SMS code input and role selection"
```

---

### Task 29: 对话主界面（核心页面）

**Files:**
- Create: `client/src/views/Chat.vue`
- Create: `client/src/components/common/AppHeader.vue`
- Create: `client/src/components/common/AppSidebar.vue`
- Create: `client/src/components/chat/ChatContainer.vue`
- Create: `client/src/components/chat/MessageList.vue`
- Create: `client/src/components/chat/MessageBubble.vue`
- Create: `client/src/components/chat/MessageInput.vue`
- Create: `client/src/components/chat/StreamingText.vue`
- Create: `client/src/components/chat/SourceCitation.vue`
- Create: `client/src/components/chat/SuggestQuestions.vue`
- Create: `client/src/components/conversation/ConversationList.vue`
- Create: `client/src/components/conversation/ConversationItem.vue`

**Step 1: 实现 AppHeader**

Logo + 标题 + 搜索图标（点击展开搜索面板）+ 主题切换 + 夜间模式。

**Step 2: 实现 AppSidebar**

布局顺序：[+ 新对话] → 最近对话列表 → (弹性空间) → 用户信息卡 → 设置按钮。

**Step 3: 实现 ConversationList + ConversationItem**

对话历史列表，支持标题编辑、置顶、软删除。

**Step 4: 实现 MessageList（虚拟滚动）**

使用 `vue-virtual-scroller` 处理长对话。

**Step 5: 实现 MessageBubble**

用户气泡（师大蓝背景白字）+ AI 气泡（浅灰背景深色字）。支持 Markdown 渲染。

**Step 6: 实现 StreamingText**

逐字显示动画 + 光标闪烁效果。

**Step 7: 实现 SourceCitation**

引用来源标签（"根据 2025 年招生简章"），可点击查看原文。

**Step 8: 实现 SuggestQuestions**

推荐问题卡片，点击直接发送。

**Step 9: 实现 MessageInput**

文本输入 + 文件附件按钮 + 发送按钮，支持 Enter 发送、Shift+Enter 换行。

**Step 10: 实现 ChatContainer 整合所有子组件**

**Step 11: 实现 Chat.vue 页面布局（Header + Sidebar + ChatContainer）**

**Step 12: Commit**

```bash
git add client/src/views/Chat.vue client/src/components/chat/ \
        client/src/components/common/ client/src/components/conversation/
git commit -m "feat: add chat interface with streaming, virtual scroll, sidebar, and BNU design"
```

---

### Task 30: 首页

**Files:**
- Create: `client/src/views/Home.vue`
- Create: `client/src/components/home/HeroSection.vue`
- Create: `client/src/components/home/HotQuestions.vue`
- Create: `client/src/components/home/QuickActions.vue`

**Step 1: 实现 HeroSection（北师大品牌 Banner）**

**Step 2: 实现 HotQuestions（十大高频问题卡片）**

**Step 3: 实现 QuickActions（快捷按钮）**

**Step 4: Commit**

```bash
git add client/src/views/Home.vue client/src/components/home/
git commit -m "feat: add home page with hero section, hot questions, and quick actions"
```

---

### Task 31: 管理后台布局与仪表盘

**Files:**
- Create: `client/src/views/admin/Dashboard.vue`
- Create: `client/src/components/admin/layout/AdminLayout.vue`
- Create: `client/src/components/admin/layout/AdminSidebar.vue`
- Create: `client/src/components/admin/layout/AdminHeader.vue`
- Create: `client/src/components/admin/dashboard/StatCards.vue`
- Create: `client/src/components/admin/dashboard/ChatChart.vue`
- Create: `client/src/components/admin/dashboard/HotTopics.vue`

**Step 1: 实现 AdminLayout 框架（顶栏 + 侧边导航 + 内容区）**

**Step 2: 实现 AdminSidebar（按权限动态渲染菜单项）**

**Step 3: 实现仪表盘组件**

**Step 4: Commit**

```bash
git add client/src/views/admin/ client/src/components/admin/layout/ client/src/components/admin/dashboard/
git commit -m "feat: add admin layout and dashboard with stats, charts, and hot topics"
```

---

### Task 32: 管理后台 — 知识库管理页

**Files:**
- Create: `client/src/views/admin/Knowledge.vue`
- Create: `client/src/views/admin/KnowledgeReview.vue`
- Create: `client/src/components/admin/knowledge/DocList.vue`
- Create: `client/src/components/admin/knowledge/DocUpload.vue`
- Create: `client/src/components/admin/knowledge/DocReview.vue`
- Create: `client/src/components/admin/knowledge/ChunkPreview.vue`

**Step 1: 实现文档列表（状态筛选、分页）+ 上传对话框**

**Step 2: 实现审核面板（通过/拒绝/备注）**

**Step 3: 实现切片预览（查看文档解析后的切片内容）**

**Step 4: Commit**

```bash
git add client/src/views/admin/Knowledge*.vue client/src/components/admin/knowledge/
git commit -m "feat: add knowledge base management pages with upload, review, and chunk preview"
```

---

### Task 33: 管理后台 — 其余管理页面

**Files:**
- Create: 用户管理、管理员管理、角色权限、敏感词库、模型配置、招生日历、多媒体资源、审计日志对应的 views 和 components

**Step 1: 用户管理页（列表 + 封禁操作）**

**Step 2: 管理员管理页（列表 + 创建 + 编辑）**

**Step 3: 角色权限页（角色列表 + 权限矩阵编辑器）**

**Step 4: 敏感词库页（词库列表 + 词条编辑器）**

**Step 5: 模型配置页（主模型/审查模型/负载策略配置 + 连通性测试）**

**Step 6: 招生日历页（阶段配置编辑）**

**Step 7: 多媒体资源页（资源库浏览 + 上传 + 审核）**

**Step 8: 审计日志页（日志表格 + 筛选 + 导出）**

**Step 9: 管理员登录页**

**Step 10: Commit**

```bash
git add client/src/views/admin/ client/src/components/admin/
git commit -m "feat: add all admin management pages (users, roles, sensitive words, model, calendar, media, logs)"
```

---

## Phase 6: 主题、无障碍与响应式

### Task 34: 夜间模式与主题系统

**Files:**
- Create: `client/src/styles/theme-light.scss`
- Create: `client/src/styles/theme-dark.scss`
- Create: `client/src/composables/useTheme.ts`

**Step 1: 实现 CSS 变量主题切换**

Light/Dark 两套 CSS 变量，通过 `document.documentElement.setAttribute('data-theme', 'dark')` 切换。

**Step 2: 实现 useTheme composable**

读取 localStorage 偏好，监听系统主题变化，提供 toggle 方法。

**Step 3: Commit**

```bash
git add client/src/styles/theme-*.scss client/src/composables/useTheme.ts
git commit -m "feat: add light/dark theme system with CSS variables and system preference detection"
```

---

### Task 35: 无障碍与响应式

**Files:**
- Create: `client/src/styles/accessibility.scss`
- Create: `client/src/styles/responsive.scss`
- Create: `client/src/composables/useAccessibility.ts`
- Create: `client/src/composables/useResponsive.ts`

**Step 1: 实现无障碍样式（focus-visible、对比度、aria 支持）**

**Step 2: 实现字体大小调节（4 档）**

**Step 3: 实现响应式断点检测 composable**

**Step 4: 适配移动端布局（侧边栏抽屉、底部输入栏）**

**Step 5: Commit**

```bash
git add client/src/styles/ client/src/composables/
git commit -m "feat: add WCAG 2.1 accessibility, font scaling, and responsive mobile layout"
```

---

## Phase 7: 集成测试与部署

### Task 36: 后端集成测试

**Files:**
- Create: `server/tests/conftest.py`
- Create: `server/tests/test_integration.py`

**Step 1: 配置 pytest fixtures（测试数据库、测试 Redis、AsyncClient）**

**Step 2: 编写端到端测试**

- 完整注册登录流程
- 创建对话 → 发送消息 → 接收回复
- 知识库上传 → 审核 → Embedding → 检索命中
- 管理员 RBAC 权限校验

**Step 3: 运行全部测试**

```bash
cd server && python -m pytest tests/ -v --cov=app --cov-report=term-missing
```

**Step 4: Commit**

```bash
git add server/tests/
git commit -m "test: add integration tests for auth, chat, knowledge pipeline, and RBAC"
```

---

### Task 37: 前端构建与 Docker 部署验证

**Step 1: 前端构建**

```bash
cd client && npm run build
```

验证：dist/ 目录生成，index.html 存在。

**Step 2: Docker Compose 全量启动**

```bash
docker compose up --build -d
```

**Step 3: 验证所有服务**

```bash
# 健康检查
curl http://localhost/health

# API 可达
curl http://localhost/api/docs

# Nginx 静态资源
curl http://localhost/
```

**Step 4: 运行数据库迁移 + 种子数据**

```bash
docker compose exec app alembic upgrade head
```

**Step 5: Commit**

```bash
git add .
git commit -m "feat: complete Docker Compose deployment with all services verified"
```

---

### Task 38: 最终清理与文档

**Step 1: 确保所有 .env.example 完整**

**Step 2: 确认 .gitignore 排除 node_modules、__pycache__、.env、data/、dist/**

**Step 3: 最终提交**

```bash
git add .
git commit -m "chore: final cleanup, env examples, and gitignore"
```

---

## 任务依赖关系

```
Phase 1: 基础设施
  Task 1 (后端脚手架) ──→ Task 2 (Docker Compose) ──→ Task 3 (DB/Redis连接)

Phase 2: 数据模型
  Task 3 ──→ Task 4 (User/Admin) ──→ Task 5 (RBAC) ──→ Task 6 (对话) ──→ Task 7 (其余模型) ──→ Task 8 (种子数据)

Phase 3: 后端服务
  Task 8 ──→ Task 9 (异常/中间件)
         ──→ Task 10 (JWT/认证)  ──→ Task 11 (RBAC装饰器)
         ──→ Task 12 (用户认证API) ──→ Task 13 (管理员认证API)
         ──→ Task 14 (对话历史API)
         ──→ Task 15 (LLM接入) ──→ Task 16 (敏感词) ──→ Task 17 (风险/情感/日历)
                               ──→ Task 18 (知识库检索) ──→ Task 19 (双模型审查)
         ──→ Task 20 (智能对话API，依赖 15-19)
         ──→ Task 21 (Celery任务)
         ──→ Task 22 (知识库管理API) ──→ Task 23 (管理后台API)

Phase 4: 前端搭建
  Task 24 (前端脚手架) ──→ Task 25 (路由) ──→ Task 26 (Store) ──→ Task 27 (API层)

Phase 5: 前端页面 (依赖 Phase 4)
  Task 28 (登录) ──→ Task 29 (对话界面) ──→ Task 30 (首页)
  Task 31 (管理布局) ──→ Task 32 (知识库管理页) ──→ Task 33 (其余管理页)

Phase 6: 主题/无障碍 (依赖 Phase 5)
  Task 34 (夜间模式) ──→ Task 35 (无障碍/响应式)

Phase 7: 集成 (依赖全部)
  Task 36 (后端测试) ──→ Task 37 (部署验证) ──→ Task 38 (清理)
```

## 可并行执行的任务组

- **Phase 3 + Phase 4 可并行**：后端服务开发与前端脚手架搭建互不依赖
- **Task 15-19 可并行**：LLM接入、敏感词、风险分级、知识库检索、双模型审查互相独立
- **Task 28-30 与 Task 31-33 可并行**：用户端页面与管理端页面独立
- **Task 34-35 可并行**：夜间模式与无障碍独立
