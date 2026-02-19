#!/usr/bin/env bash
# =============================================================
# 本地开发一键启动脚本（不依赖 Docker）
# 适用于 Debian/Ubuntu 环境
# 用法: sudo bash start-local.sh
# =============================================================
set -e

PROJECT_ROOT="$(cd "$(dirname "$0")" && pwd)"
SERVER_DIR="$PROJECT_ROOT/server"
CLIENT_DIR="$PROJECT_ROOT/client"

# 颜色输出
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

info()  { echo -e "${GREEN}[INFO]${NC} $1"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $1"; }
error() { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

# ----------------------------------------------------------
# 1. 安装系统依赖
# ----------------------------------------------------------
install_system_deps() {
    info "检查并安装系统依赖..."

    local NEED_UPDATE=false

    if ! command -v pg_isready &>/dev/null; then
        NEED_UPDATE=true
    fi
    if ! command -v redis-server &>/dev/null; then
        NEED_UPDATE=true
    fi
    if ! command -v python3 &>/dev/null || ! python3 -c "import venv" 2>/dev/null; then
        NEED_UPDATE=true
    fi

    if $NEED_UPDATE; then
        info "安装缺失的系统包..."
        apt-get update -qq
        apt-get install -y -qq postgresql postgresql-client redis-server python3-venv 2>/dev/null || \
        sudo apt-get install -y -qq postgresql postgresql-client redis-server python3-venv 2>/dev/null
    fi

    info "系统依赖就绪 ✓"
}

# ----------------------------------------------------------
# 2. 启动 PostgreSQL
# ----------------------------------------------------------
start_postgres() {
    info "启动 PostgreSQL..."

    if pg_isready -q 2>/dev/null; then
        info "PostgreSQL 已在运行"
    else
        # 尝试多种启动方式（兼容不同环境）
        local PG_VER
        PG_VER=$(pg_lsclusters -h 2>/dev/null | head -1 | awk '{print $1}') || PG_VER="15"
        local PG_CLUSTER
        PG_CLUSTER=$(pg_lsclusters -h 2>/dev/null | head -1 | awk '{print $2}') || PG_CLUSTER="main"

        sudo pg_ctlcluster "$PG_VER" "$PG_CLUSTER" start 2>/dev/null \
            || sudo -u postgres pg_ctlcluster "$PG_VER" "$PG_CLUSTER" start 2>/dev/null \
            || sudo service postgresql start 2>/dev/null \
            || error "无法启动 PostgreSQL，请手动启动"

        # 等待就绪
        for _ in $(seq 1 10); do
            pg_isready -q 2>/dev/null && break
            sleep 1
        done
        pg_isready -q 2>/dev/null || error "PostgreSQL 启动超时"
    fi

    # 创建数据库（如果不存在）
    sudo -u postgres psql -tc "SELECT 1 FROM pg_database WHERE datname='bnu_admission'" 2>/dev/null | grep -q 1 \
        || sudo -u postgres psql -c "CREATE DATABASE bnu_admission" 2>/dev/null

    # 设置密码
    sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres'" 2>/dev/null || true

    info "PostgreSQL 就绪 ✓"
}

# ----------------------------------------------------------
# 3. 启动 Redis
# ----------------------------------------------------------
start_redis() {
    info "启动 Redis..."

    if timeout 2 redis-cli ping 2>/dev/null | grep -q PONG; then
        info "Redis 已在运行"
    else
        redis-server --daemonize yes --appendonly yes --dir /tmp 2>/dev/null
        sleep 1
        timeout 2 redis-cli ping 2>/dev/null | grep -q PONG || error "无法启动 Redis"
    fi

    info "Redis 就绪 ✓"
}

# ----------------------------------------------------------
# 4. 配置后端
# ----------------------------------------------------------
setup_backend() {
    info "配置后端..."

    cd "$SERVER_DIR"

    # 生成最小必要 .env（保留短信相关配置）
    local EXISTING_ENV=".env"
    local TMP_ENV=".env.minimal.tmp"
    local SMS_MOCK_VALUE="true"
    local SMS_ALIYUN_ACCESS_KEY_ID_VALUE=""
    local SMS_ALIYUN_ACCESS_KEY_SECRET_VALUE=""
    local SMS_ALIYUN_SIGN_NAME_VALUE=""
    local SMS_ALIYUN_TEMPLATE_CODE_VALUE=""
    local SMS_ALIYUN_TEMPLATE_MIN_VALUE="5"
    local SMS_ALIYUN_SCHEME_NAME_VALUE=""
    local SMS_ALIYUN_ENDPOINT_VALUE="dypnsapi.aliyuncs.com"

    read_env_value() {
        local key="$1"
        local file="$2"
        if [ ! -f "$file" ]; then
            return
        fi
        grep -E "^${key}=" "$file" | tail -n 1 | cut -d'=' -f2-
    }

    if [ -f "$EXISTING_ENV" ]; then
        SMS_MOCK_VALUE="$(read_env_value SMS_MOCK "$EXISTING_ENV")"
        SMS_ALIYUN_ACCESS_KEY_ID_VALUE="$(read_env_value SMS_ALIYUN_ACCESS_KEY_ID "$EXISTING_ENV")"
        SMS_ALIYUN_ACCESS_KEY_SECRET_VALUE="$(read_env_value SMS_ALIYUN_ACCESS_KEY_SECRET "$EXISTING_ENV")"
        SMS_ALIYUN_SIGN_NAME_VALUE="$(read_env_value SMS_ALIYUN_SIGN_NAME "$EXISTING_ENV")"
        SMS_ALIYUN_TEMPLATE_CODE_VALUE="$(read_env_value SMS_ALIYUN_TEMPLATE_CODE "$EXISTING_ENV")"
        SMS_ALIYUN_TEMPLATE_MIN_VALUE="$(read_env_value SMS_ALIYUN_TEMPLATE_MIN "$EXISTING_ENV")"
        SMS_ALIYUN_SCHEME_NAME_VALUE="$(read_env_value SMS_ALIYUN_SCHEME_NAME "$EXISTING_ENV")"
        SMS_ALIYUN_ENDPOINT_VALUE="$(read_env_value SMS_ALIYUN_ENDPOINT "$EXISTING_ENV")"
    fi

    SMS_MOCK_VALUE="${SMS_MOCK_VALUE:-true}"
    SMS_ALIYUN_TEMPLATE_MIN_VALUE="${SMS_ALIYUN_TEMPLATE_MIN_VALUE:-5}"
    SMS_ALIYUN_ENDPOINT_VALUE="${SMS_ALIYUN_ENDPOINT_VALUE:-dypnsapi.aliyuncs.com}"

    cat > "$TMP_ENV" <<EOF
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/bnu_admission
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=change-me-in-production
JWT_ALGORITHM=HS256
SMS_MOCK=${SMS_MOCK_VALUE}
SMS_ALIYUN_ACCESS_KEY_ID=${SMS_ALIYUN_ACCESS_KEY_ID_VALUE}
SMS_ALIYUN_ACCESS_KEY_SECRET=${SMS_ALIYUN_ACCESS_KEY_SECRET_VALUE}
SMS_ALIYUN_SIGN_NAME=${SMS_ALIYUN_SIGN_NAME_VALUE}
SMS_ALIYUN_TEMPLATE_CODE=${SMS_ALIYUN_TEMPLATE_CODE_VALUE}
SMS_ALIYUN_TEMPLATE_MIN=${SMS_ALIYUN_TEMPLATE_MIN_VALUE}
SMS_ALIYUN_SCHEME_NAME=${SMS_ALIYUN_SCHEME_NAME_VALUE}
SMS_ALIYUN_ENDPOINT=${SMS_ALIYUN_ENDPOINT_VALUE}
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
EOF
    mv "$TMP_ENV" "$EXISTING_ENV"
    info "已写入最小 server/.env（保留短信配置）"

    # 创建虚拟环境
    if [ ! -d .venv ]; then
        python3 -m venv .venv
        info "已创建 Python 虚拟环境"
    fi

    # 安装依赖
    info "安装 Python 依赖..."
    .venv/bin/pip install -q -r requirements.txt

    # 建表：先尝试 Alembic，失败则用 create_all
    info "初始化数据库表..."
    .venv/bin/alembic upgrade head 2>/dev/null || {
        warn "Alembic 迁移无可用版本，使用 create_all 建表..."
        # 确保 pgvector 扩展已启用
        PGPASSWORD=postgres psql -h localhost -U postgres -d bnu_admission -c "CREATE EXTENSION IF NOT EXISTS vector;" 2>/dev/null || true
        .venv/bin/python3 -c "
import asyncio
from app.core.database import get_engine, Base
from app.models import user, admin, role, conversation, message, knowledge, calendar, sensitive_word, media, audit_log
async def create_tables():
    engine = get_engine()
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    await engine.dispose()
asyncio.run(create_tables())
"
        # 确保 embedding 列存在
        PGPASSWORD=postgres psql -h localhost -U postgres -d bnu_admission -c \
            "ALTER TABLE knowledge_chunks ADD COLUMN IF NOT EXISTS embedding vector(1536);" 2>/dev/null || true
    }

    # 放权 /data 下所有路径（本地开发环境）
    sudo mkdir -p /data 2>/dev/null || true
    sudo chmod -R 777 /data 2>/dev/null || true

    info "后端配置完成 ✓"
}

# ----------------------------------------------------------
# 5. 配置前端
# ----------------------------------------------------------
setup_frontend() {
    info "配置前端..."

    cd "$CLIENT_DIR"

    if [ ! -f .env ]; then
        if [ -f .env.example ]; then
            cp .env.example .env
            info "已创建 client/.env"
        else
            cat > .env <<'EOF'
VITE_API_BASE=/api/v1
EOF
            warn "未找到 client/.env.example，已创建最小 client/.env"
        fi
    fi

    if [ ! -d node_modules ]; then
        info "安装前端依赖..."
        npm install --silent
    fi

    info "前端配置完成 ✓"
}

# ----------------------------------------------------------
# 6. 启动所有开发服务器
# ----------------------------------------------------------
start_services() {
    echo ""
    info "=========================================="
    info "启动开发服务器..."
    info "=========================================="

    # 后端
    cd "$SERVER_DIR"
    info "启动后端 (http://localhost:8001)..."
    .venv/bin/uvicorn app.main:app --reload --host 0.0.0.0 --port 8001 &
    BACKEND_PID=$!

    # Celery Worker
    info "启动 Celery Worker..."
    .venv/bin/celery -A app.tasks.celery_app worker --loglevel=warning --concurrency=2 &
    CELERY_PID=$!

    # 前端
    cd "$CLIENT_DIR"
    info "启动前端 (http://localhost:5173)..."
    npx vite --host 0.0.0.0 &
    FRONTEND_PID=$!

    # 等待后端启动
    sleep 3

    local SMS_STATUS="真实短信模式"
    if grep -E '^SMS_MOCK=true$' "$SERVER_DIR/.env" >/dev/null 2>&1; then
        SMS_STATUS="Mock 模式 (验证码 123456)"
    fi

    echo ""
    info "=========================================="
    info "  所有服务已启动"
    info ""
    info "  前端:         http://localhost:5173"
    info "  后端 API:     http://localhost:8001"
    info "  API 文档:     http://localhost:8001/api/docs"
    info ""
    info "  默认管理员:   admin / admin123"
    info "  短信配置:     ${SMS_STATUS}"
    info "=========================================="
    info "  按 Ctrl+C 停止所有服务"
    echo ""

    # 优雅退出
    cleanup() {
        echo ""
        info "正在停止服务..."
        kill $BACKEND_PID $CELERY_PID $FRONTEND_PID 2>/dev/null
        wait $BACKEND_PID $CELERY_PID $FRONTEND_PID 2>/dev/null
        info "已停止"
        exit 0
    }
    trap cleanup INT TERM

    wait
}

# ----------------------------------------------------------
# 主流程
# ----------------------------------------------------------
main() {
    info "=========================================="
    info "京师小智 · 本地开发环境启动"
    info "=========================================="
    echo ""

    install_system_deps
    start_postgres
    start_redis
    setup_backend
    setup_frontend
    start_services
}

main "$@"
