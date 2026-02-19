# 快速启动指南

## 环境要求

### 方案一：Docker 部署

| 工具 | 最低版本 |
|------|----------|
| Docker | 20.10+ |
| Docker Compose | 2.0+ |
| Node.js | 18+ |

### 方案二：本地裸机开发（无 Docker）

| 工具 | 最低版本 |
|------|----------|
| Node.js | 18+ |
| Python | 3.11+ |
| 系统 | Debian/Ubuntu |

> PostgreSQL 和 Redis 会由启动脚本自动安装。

## 1. 克隆项目

```bash
git clone <仓库地址>
cd bnu-admission-chatbot
```

## 2. 配置环境变量

### 后端

```bash
cp server/.env.example server/.env
```

编辑 `server/.env`，**必须修改**以下配置：

```dotenv
# 大模型 API 密钥
LLM_PRIMARY_API_KEY=sk-your-api-key-here
```

可选调整：

```dotenv
# 生产环境务必更换
JWT_SECRET_KEY=your-random-secret-string

# 关闭短信 mock（接入真实短信服务时）
SMS_MOCK=false

# 阿里云 Dypns 短信认证
SMS_ALIYUN_ACCESS_KEY_ID=LTAIxxxxxxxx
SMS_ALIYUN_ACCESS_KEY_SECRET=xxxxxxxx
SMS_ALIYUN_SIGN_NAME=北京师范大学
SMS_ALIYUN_TEMPLATE_CODE=SMS_123456789
SMS_ALIYUN_SCHEME_NAME=
SMS_ALIYUN_ENDPOINT=dypnsapi.aliyuncs.com

# 审计日志 SQLite 分片目录（建议挂载持久卷）
# 默认 /data/audit_logs，若不可写会自动回退到可写目录
AUDIT_SQLITE_DIR=/data/audit_logs
```

> 生产环境建议将 `AUDIT_SQLITE_DIR` 挂载到独立持久化磁盘（例如 Docker Volume），避免容器重建导致审计文件丢失。

### 前端

```bash
cp client/.env.example client/.env
```

默认配置即可用于本地开发，无需修改。

---

## 方案一：Docker 一键启动

```bash
# 构建前端静态文件
cd client && npm install && npm run build && cd ..

# 启动所有服务
docker compose up -d

# 初始化数据库
docker compose exec app alembic upgrade head
```

启动后包含以下服务：

| 服务 | 端口 | 说明 |
|------|------|------|
| nginx | 80 | 反向代理，前端 + API |
| app | 8000（内部） | FastAPI 后端 |
| db | 5432（内部） | PostgreSQL 16 + pgvector |
| redis | 6379（内部） | 缓存 + 消息队列 |
| worker | — | Celery 异步任务 |

```bash
# 验证
docker compose ps
curl http://localhost/health
```

访问 http://localhost 即可看到前端页面。

---

## 方案二：本地裸机启动（无 Docker）

适用于没有 Docker 或需要更快热重载的开发场景。

### 一键启动

```bash
sudo bash start-local.sh
```

脚本会自动完成：
1. 安装 PostgreSQL、Redis（如未安装）
2. 启动数据库和缓存服务
3. 创建 Python 虚拟环境并安装依赖
4. 建表 + 种子数据（默认管理员、角色、权限）
5. 安装前端依赖
6. 启动后端、Celery Worker、前端开发服务器

启动完成后：

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 | http://localhost:8000/api/docs |

> 按 `Ctrl+C` 停止所有服务。

### 手动分步启动

如果需要分别控制各服务，可手动操作：

**1. 启动 PostgreSQL 和 Redis**

```bash
# PostgreSQL
sudo pg_ctlcluster 15 main start
sudo -u postgres psql -c "CREATE DATABASE bnu_admission"
sudo -u postgres psql -c "ALTER USER postgres PASSWORD 'postgres'"

# Redis
redis-server --daemonize yes
```

**2. 配置 `.env` — 连接改为 localhost**

将 `server/.env` 中的主机名改为 `localhost`：

```dotenv
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/bnu_admission
REDIS_URL=redis://localhost:6379/0
CELERY_BROKER_URL=redis://localhost:6379/1
CELERY_RESULT_BACKEND=redis://localhost:6379/2
```

**3. 启动后端**

```bash
cd server
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

**4. 启动 Celery Worker（新终端）**

```bash
cd server && source .venv/bin/activate
celery -A app.tasks.celery_app worker --loglevel=info
```

**5. 启动前端（新终端）**

```bash
cd client
npm install
npm run dev
```

前端开发服务器运行在 http://localhost:5173，API 请求会代理到后端 8000 端口。

---

## 默认账号

| 类型 | 账号 | 密码/验证码 |
|------|------|-------------|
| 管理员 | admin | admin123 |
| 用户短信验证码（Mock 模式） | 任意手机号 | 123456 |

## 运行测试

```bash
cd server
source .venv/bin/activate
pytest -v
```

## 常用命令

```bash
# --- Docker 模式 ---
docker compose logs -f app        # 查看后端日志
docker compose restart app         # 重启后端
docker compose down                # 停止所有服务
docker compose down -v             # 停止并清除数据（慎用）

# --- 前端 ---
cd client && npx vue-tsc --noEmit  # 类型检查
cd client && npm run build         # 生产构建

# --- 本地模式 ---
# 停止 PostgreSQL
sudo pg_ctlcluster 15 main stop
# 停止 Redis
redis-cli shutdown
```

## 项目结构

```
├── client/                # Vue 3 前端
│   ├── src/
│   │   ├── api/           # API 请求封装
│   │   ├── components/    # 通用及业务组件
│   │   ├── composables/   # 组合式函数
│   │   ├── router/        # 路由配置
│   │   ├── stores/        # Pinia 状态管理
│   │   ├── styles/        # 全局样式、主题变量
│   │   ├── types/         # TypeScript 类型定义
│   │   └── views/         # 页面视图
│   └── package.json
├── server/                # FastAPI 后端
│   ├── app/
│   │   ├── api/           # 路由端点
│   │   ├── core/          # 配置、安全、依赖注入
│   │   ├── models/        # SQLAlchemy ORM 模型
│   │   ├── schemas/       # Pydantic 数据模式
│   │   ├── services/      # 业务逻辑层
│   │   └── tasks/         # Celery 异步任务
│   ├── migrations/        # Alembic 数据库迁移
│   └── requirements.txt
├── nginx/                 # Nginx 反向代理配置
├── docs/                  # 项目文档
├── start-local.sh         # 本地一键启动脚本
└── docker-compose.yml
```

## 常见问题

**Q: 数据库连接失败？**
Docker 模式确认 `db` 容器健康：`docker compose ps`。本地模式确认 `server/.env` 中 `DATABASE_URL` 的主机为 `localhost` 而非 `db`。

**Q: 大模型调用无响应？**
检查 `server/.env` 中 `LLM_PRIMARY_API_KEY` 是否已填写。Mock 模式下短信验证码固定为 `123456`。

**Q: 前端构建报错？**
确认 Node.js ≥ 18，删除 `node_modules` 后重新 `npm install`。

**Q: `start-local.sh` 权限不足？**
需要 `sudo` 运行以安装系统包和启动 PostgreSQL：`sudo bash start-local.sh`。
