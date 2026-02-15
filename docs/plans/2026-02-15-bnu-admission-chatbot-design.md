# 北京师范大学招生宣传智能体系统 — 系统设计方案

> 文档版本：v1.0
> 日期：2026-02-15
> 状态：已批准

---

## 目录

1. [技术决策总结](#1-技术决策总结)
2. [系统总体架构](#2-系统总体架构)
3. [数据库设计](#3-数据库设计)
4. [后端模块详细设计](#4-后端模块详细设计)
5. [前端架构设计](#5-前端架构设计)
6. [安全设计与部署架构](#6-安全设计与部署架构)

---

## 1. 技术决策总结

| 决策项 | 选型 | 理由 |
|--------|------|------|
| 整体架构 | 单体应用 + Celery 异步任务队列 | 招生场景并发可控，开发效率高，Docker Compose 契合 |
| 后端框架 | Python (FastAPI) | AI/NLP 生态成熟，LangChain、向量库客户端丰富 |
| 前端框架 | Vue 3 + Vite + TypeScript + Pinia + Element Plus / Naive UI | 需求文档指定 |
| 数据库 | PostgreSQL 16 + pgvector | 一库两用（结构化数据 + 向量检索），运维简单 |
| 缓存/消息队列 | Redis 7 | 会话、验证码、限流、Celery broker |
| 部署方式 | Docker Compose | 单机/小集群，运维简洁 |
| 短信服务 | 先 Mock 后对接云服务商 | 开发阶段用模拟接口，后期接入阿里云/腾讯云短信 |
| 权限模型 | RBAC（角色-权限表） | 灵活动态调整，支持 8 种角色 |

---

## 2. 系统总体架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        客户端层                                  │
│   [Vue 3 SPA]  PC / 移动端 / 平板 (响应式)                       │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
┌──────────────────────────▼──────────────────────────────────────┐
│                     Nginx 反向代理                                │
│   静态资源托管 / SSL终止 / 限流 / CORS / 请求分发                   │
└──────┬───────────────────────────────────────┬──────────────────┘
       │ /api/*                                │ /ws/*
┌──────▼───────────────────────────────────────▼──────────────────┐
│                  FastAPI 单体应用                                 │
│                                                                  │
│  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌───────────┐          │
│  │ 用户模块  │ │ 对话模块  │ │ 知识库模块│ │ 管理后台模块│          │
│  │ auth     │ │ chat     │ │ knowledge│ │ admin     │          │
│  └────┬─────┘ └────┬─────┘ └────┬─────┘ └─────┬─────┘          │
│       │            │            │              │                 │
│  ┌────▼────────────▼────────────▼──────────────▼─────┐          │
│  │              公共服务层                              │          │
│  │  日志审计 / 权限校验 / 敏感词过滤 / 风险分级          │          │
│  └───────────────────────────────────────────────────┘          │
└──────┬──────────────┬──────────────┬───────────────────────────┘
       │              │              │
┌──────▼──────┐ ┌─────▼─────┐ ┌─────▼──────┐
│ PostgreSQL  │ │  Redis    │ │  Celery    │
│ + pgvector  │ │ 缓存/会话  │ │  Workers   │
│ 业务数据     │ │ 验证码     │ │ Embedding  │
│ 向量索引     │ │ 限流计数   │ │ 文档解析    │
└─────────────┘ └───────────┘ │ AI审查     │
                              └────────────┘
                                    │
                          ┌─────────▼─────────┐
                          │   LLM 接入层       │
                          │ 通义千问 / GLM /    │
                          │ 本地模型 (负载均衡)  │
                          └───────────────────┘
```

### 容器编排（Docker Compose）

| 容器 | 服务 | 说明 |
|------|------|------|
| `nginx` | Nginx | 反向代理、静态资源、SSL |
| `app` | FastAPI | 主应用（Uvicorn 多 worker） |
| `db` | PostgreSQL 16 + pgvector | 业务数据 + 向量存储 |
| `redis` | Redis 7 | 缓存、会话、验证码、Celery broker |
| `worker` | Celery Worker | 异步任务（Embedding、文档解析、AI审查） |
| `flower` | Flower（可选） | Celery 任务监控面板 |

### 核心通信模式

- **同步请求**：用户登录、管理操作 → REST API
- **流式响应**：AI 对话 → WebSocket / SSE，实时逐字输出
- **异步任务**：文档上传解析、Embedding 生成、双模型审查 → Celery 任务队列

---

## 3. 数据库设计

### 3.1 ER 关系总览

```
┌───────────┐     ┌───────────────┐     ┌──────────────┐
│   users   │────<│ conversations │────<│   messages   │
└─────┬─────┘     └───────────────┘     └──────────────┘
      │
      │  ┌─────────────┐      ┌──────────────┐
      ├─<│ user_roles   │─────>│    roles     │
      │  └─────────────┘      └──────┬───────┘
      │                              │
      │                       ┌──────▼───────┐
      │                       │role_permissions│
      │                       └──────┬───────┘
      │                              │
      │                       ┌──────▼───────┐
      │                       │ permissions  │
      │                       └──────────────┘
      │
      │           ┌───────────────┐
      └──────────<│  audit_logs   │
                  └───────────────┘

┌────────────┐      ┌──────────────┐
│admin_users │─────<│ admin_roles  │────> roles
└────────────┘      └──────────────┘
      │
      └────<┌───────────────────┐     ┌─────────────────┐
            │knowledge_documents│────<│ knowledge_chunks │
            └───────────────────┘     │ (含 pgvector)    │
                                      └─────────────────┘
```

### 3.2 用户表 `users`

```sql
CREATE TABLE users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    phone           VARCHAR(11) UNIQUE NOT NULL,       -- 中国手机号
    nickname        VARCHAR(50) NOT NULL,               -- 昵称
    avatar_url      VARCHAR(500) DEFAULT '',            -- 头像 URL
    gender          VARCHAR(10),                        -- male/female/unknown
    province        VARCHAR(20),                        -- 省份（用于招生区域匹配）
    birth_year      INTEGER,                            -- 出生年份
    school          VARCHAR(100),                       -- 就读学校
    status          VARCHAR(10) NOT NULL DEFAULT 'active', -- active/banned/inactive
    last_login_at   TIMESTAMP WITH TIME ZONE,
    last_login_ip   INET,
    token_expire_at TIMESTAMP WITH TIME ZONE,           -- 当前 token 过期时间
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.3 管理员表 `admin_users`

```sql
CREATE TABLE admin_users (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    username        VARCHAR(50) UNIQUE NOT NULL,
    password_hash   VARCHAR(255) NOT NULL,              -- bcrypt 哈希
    real_name       VARCHAR(50) NOT NULL,               -- 真实姓名
    employee_id     VARCHAR(30) UNIQUE,                 -- 工号
    department      VARCHAR(100),                       -- 所属部门/院系
    title           VARCHAR(50),                        -- 职称
    phone           VARCHAR(11),
    email           VARCHAR(100),
    avatar_url      VARCHAR(500) DEFAULT '',
    mfa_secret      VARCHAR(100),                       -- TOTP 二次验证密钥
    status          VARCHAR(10) NOT NULL DEFAULT 'active',
    last_login_at   TIMESTAMP WITH TIME ZONE,
    last_login_ip   INET,
    token_expire_at TIMESTAMP WITH TIME ZONE,
    created_by      UUID REFERENCES admin_users(id),    -- 由哪个超管创建
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.4 RBAC 权限模型

```sql
-- 角色表
CREATE TABLE roles (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(30) UNIQUE NOT NULL,             -- super_admin/reviewer/admin/teacher/gaokao/kaoyan/international/parent
    name        VARCHAR(50) NOT NULL,                    -- 角色显示名
    role_type   VARCHAR(10) NOT NULL,                    -- user / admin
    description TEXT,
    is_system   BOOLEAN NOT NULL DEFAULT FALSE,          -- 系统内置角色不可删除
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 权限表
CREATE TABLE permissions (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    code        VARCHAR(60) UNIQUE NOT NULL,             -- 如 knowledge:approve, user:ban
    name        VARCHAR(100) NOT NULL,
    resource    VARCHAR(30) NOT NULL,                    -- knowledge/user/model/log/media/...
    action      VARCHAR(20) NOT NULL,                    -- create/read/update/delete/approve/export
    description TEXT,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 角色-权限关联
CREATE TABLE role_permissions (
    role_id       UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    permission_id UUID NOT NULL REFERENCES permissions(id) ON DELETE CASCADE,
    PRIMARY KEY (role_id, permission_id)
);

-- 用户-角色关联
CREATE TABLE user_roles (
    user_id     UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (user_id, role_id)
);

-- 管理员-角色关联
CREATE TABLE admin_roles (
    admin_id    UUID NOT NULL REFERENCES admin_users(id) ON DELETE CASCADE,
    role_id     UUID NOT NULL REFERENCES roles(id) ON DELETE CASCADE,
    assigned_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    PRIMARY KEY (admin_id, role_id)
);
```

**预置角色权限矩阵：**

| 角色 | knowledge | user | model | log | media | sensitive_word | calendar |
|------|-----------|------|-------|-----|-------|----------------|----------|
| 超级管理员 | 全部 | 全部 | 全部 | 全部 | 全部 | 全部 | 全部 |
| 内容审核员 | read/approve | read | - | read | read/approve | read | - |
| 普通管理员 | read/create | read | read | read | read/create | read | read |
| 招生老师 | read | read | - | - | read | - | read |

### 3.5 对话表 `conversations`（支持软删除）

```sql
CREATE TABLE conversations (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id      UUID NOT NULL REFERENCES users(id),
    title        VARCHAR(200),                       -- 自动生成/可编辑
    is_pinned    BOOLEAN DEFAULT FALSE,
    is_deleted   BOOLEAN NOT NULL DEFAULT FALSE,     -- 软删除标记
    deleted_at   TIMESTAMP WITH TIME ZONE,           -- 删除时间
    created_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at   TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_conv_user ON conversations(user_id, updated_at DESC) WHERE is_deleted = FALSE;
```

### 3.6 消息表 `messages`（支持软删除）

```sql
CREATE TABLE messages (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    conversation_id UUID NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            VARCHAR(10) NOT NULL,             -- user / assistant / system
    content         TEXT NOT NULL,
    model_version   VARCHAR(50),                      -- 使用的模型标识
    risk_level      VARCHAR(10),                      -- low/medium/high
    review_passed   BOOLEAN,                          -- 审查模型校验结果
    sources         JSONB,                            -- [{doc_id, title, chunk}]
    is_deleted      BOOLEAN NOT NULL DEFAULT FALSE,
    deleted_at      TIMESTAMP WITH TIME ZONE,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_msg_conv ON messages(conversation_id, created_at) WHERE is_deleted = FALSE;
```

### 3.7 知识库相关表

```sql
-- 知识文档
CREATE TABLE knowledge_documents (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title           VARCHAR(300) NOT NULL,
    file_type       VARCHAR(20) NOT NULL,             -- pdf/docx/txt/md
    file_path       VARCHAR(500) NOT NULL,             -- 加密存储路径
    file_hash       VARCHAR(64) NOT NULL,              -- SHA-256
    status          VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/reviewing/approved/rejected/archived
    uploaded_by     UUID NOT NULL REFERENCES admin_users(id),
    reviewed_by     UUID REFERENCES admin_users(id),
    review_note     TEXT,
    effective_from  TIMESTAMP WITH TIME ZONE,
    effective_until TIMESTAMP WITH TIME ZONE,
    metadata        JSONB,                             -- 解析结果、页数等
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

-- 知识切片 + 向量
CREATE TABLE knowledge_chunks (
    id              UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id     UUID NOT NULL REFERENCES knowledge_documents(id) ON DELETE CASCADE,
    chunk_index     INTEGER NOT NULL,
    content         TEXT NOT NULL,
    embedding       vector(1536),                      -- pgvector 向量列
    token_count     INTEGER,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_chunk_embedding ON knowledge_chunks USING ivfflat (embedding vector_cosine_ops);
```

### 3.8 敏感词库表

```sql
CREATE TABLE sensitive_word_groups (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name        VARCHAR(100) NOT NULL,
    description TEXT,
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE sensitive_words (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    group_id    UUID NOT NULL REFERENCES sensitive_word_groups(id) ON DELETE CASCADE,
    word        VARCHAR(200) NOT NULL,
    level       VARCHAR(10) NOT NULL DEFAULT 'block',  -- block/warn/review
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.9 多媒体资源表

```sql
CREATE TABLE media_resources (
    id            UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    title         VARCHAR(300) NOT NULL,
    media_type    VARCHAR(20) NOT NULL,               -- image/video/vr
    file_path     VARCHAR(500) NOT NULL,
    thumbnail_url VARCHAR(500),
    tags          VARCHAR(200)[],                     -- 关键词标签
    source        VARCHAR(200),                       -- 来源（公众号/媒体库）
    is_approved   BOOLEAN NOT NULL DEFAULT FALSE,
    uploaded_by   UUID REFERENCES admin_users(id),
    created_at    TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.10 审计日志表

```sql
CREATE TABLE audit_logs (
    id          BIGSERIAL PRIMARY KEY,
    user_id     UUID,
    admin_id    UUID,
    action      VARCHAR(50) NOT NULL,                 -- login/chat/upload/admin_op/...
    resource    VARCHAR(50),
    resource_id UUID,
    ip_address  INET,
    user_agent  VARCHAR(500),
    detail      JSONB,
    created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
CREATE INDEX idx_audit_time ON audit_logs(created_at DESC);
CREATE INDEX idx_audit_user ON audit_logs(user_id, created_at DESC);

-- 文件上传日志
CREATE TABLE file_upload_logs (
    id              BIGSERIAL PRIMARY KEY,
    user_id         UUID,
    file_name       VARCHAR(300) NOT NULL,
    file_hash       VARCHAR(64) NOT NULL,
    file_type       VARCHAR(20) NOT NULL,
    parse_status    VARCHAR(20) NOT NULL DEFAULT 'pending', -- pending/success/failed
    conversation_id UUID,
    detail          JSONB,
    created_at      TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.11 招生日历表

```sql
CREATE TABLE admission_calendar (
    id          UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    period_name VARCHAR(50) NOT NULL,                 -- 备考期/报名期/录取期/常态
    start_month INTEGER NOT NULL,
    end_month   INTEGER NOT NULL,
    year        INTEGER NOT NULL,
    tone_config JSONB NOT NULL,                       -- {style, keywords, focus_topics}
    is_active   BOOLEAN NOT NULL DEFAULT TRUE,
    updated_by  UUID REFERENCES admin_users(id),
    updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

### 3.12 Redis 数据结构

| Key 模式 | 类型 | 用途 | TTL |
|----------|------|------|-----|
| `sms:{phone}` | STRING | 短信验证码 | 5 分钟 |
| `sms_limit:{phone}` | STRING (计数) | 短信发送频率限制 | 1 小时 |
| `session:{token}` | HASH | 用户会话 | 7 天 |
| `admin_session:{token}` | HASH | 管理员会话 | 2 小时 |
| `rate:{ip}` | STRING (计数) | IP 请求限流 | 1 分钟 |
| `sensitive_words:{group_id}` | SET | 敏感词缓存 | 手动刷新 |
| `calendar:current` | HASH | 当前招生阶段缓存 | 1 天 |

---

## 4. 后端模块详细设计

### 4.1 项目目录结构

```
server/
├── app/
│   ├── main.py                    # FastAPI 入口
│   ├── config.py                  # 配置管理
│   ├── dependencies.py            # 全局依赖注入
│   │
│   ├── models/                    # SQLAlchemy ORM 模型
│   │   ├── user.py
│   │   ├── admin.py
│   │   ├── role.py
│   │   ├── conversation.py
│   │   ├── message.py
│   │   ├── knowledge.py
│   │   ├── media.py
│   │   ├── sensitive_word.py
│   │   ├── audit_log.py
│   │   └── calendar.py
│   │
│   ├── schemas/                   # Pydantic 请求/响应模型
│   │   ├── user.py
│   │   ├── admin.py
│   │   ├── chat.py
│   │   ├── knowledge.py
│   │   └── ...
│   │
│   ├── api/                       # 路由层
│   │   ├── v1/
│   │   │   ├── auth.py            # 用户注册/登录/验证码
│   │   │   ├── chat.py            # 对话（含 WebSocket）
│   │   │   ├── conversation.py    # 对话历史管理
│   │   │   ├── knowledge.py       # 知识库 CRUD + 审核流
│   │   │   ├── media.py           # 多媒体资源管理
│   │   │   ├── admin_auth.py      # 管理员登录
│   │   │   ├── admin_user.py      # 管理员账号管理
│   │   │   ├── admin_role.py      # 角色与权限管理
│   │   │   ├── admin_sensitive.py # 敏感词库管理
│   │   │   ├── admin_model.py     # 大模型配置
│   │   │   ├── admin_calendar.py  # 招生日历配置
│   │   │   ├── admin_log.py       # 审计日志
│   │   │   └── admin_dashboard.py # 仪表盘
│   │   └── router.py              # 路由汇总
│   │
│   ├── services/                  # 业务逻辑层
│   │   ├── auth_service.py        # 登录注册、验证码、Token
│   │   ├── chat_service.py        # 对话编排（核心）
│   │   ├── llm_service.py         # 大模型调用
│   │   ├── knowledge_service.py   # 知识库检索与管理
│   │   ├── embedding_service.py   # Embedding 生成
│   │   ├── review_service.py      # 双模型审查
│   │   ├── risk_service.py        # 风险分级
│   │   ├── sensitive_service.py   # 敏感词过滤
│   │   ├── emotion_service.py     # 情感识别
│   │   ├── calendar_service.py    # 时间感知话术
│   │   ├── media_service.py       # 多媒体管理
│   │   ├── file_parser_service.py # 文件解析
│   │   ├── sms_service.py         # 短信服务（Mock → 真实）
│   │   └── audit_service.py       # 审计日志
│   │
│   ├── core/                      # 基础设施
│   │   ├── security.py            # JWT、密码哈希、MFA
│   │   ├── permissions.py         # RBAC 权限校验装饰器
│   │   ├── database.py            # 数据库连接
│   │   ├── redis.py               # Redis 连接
│   │   ├── exceptions.py          # 统一异常
│   │   └── middleware.py          # 限流、审计、CORS
│   │
│   └── tasks/                     # Celery 异步任务
│       ├── celery_app.py
│       ├── embedding_task.py
│       ├── parse_task.py
│       ├── review_task.py
│       └── cleanup_task.py
│
├── migrations/                    # Alembic 迁移
├── tests/
├── Dockerfile
├── requirements.txt
└── .env.example
```

### 4.2 用户认证模块

**普通用户（手机号 + 短信验证码）：**

```
[手机号输入] → [发送验证码]
     │              │
     │         sms_service.send()
     │         Redis SET sms:{phone} = code (TTL 5min)
     │         Redis INCR sms_limit:{phone} (TTL 1h, max 5次)
     │
[输入验证码] → [校验验证码]
     │              │
     │         Redis GET sms:{phone} 比对
     │         校验通过后 DEL sms:{phone}
     │
[判断用户是否存在]
     │
  ┌──┴───┐
 存在   不存在
  │      │
 登录   创建用户（选择角色）
  │      │
  └──┬───┘
     │
[生成 JWT Token]
存入 Redis session:{token}
更新 last_login_at / last_login_ip / token_expire_at
```

**管理员（用户名 + 密码 + MFA）：**

```
[用户名 + 密码] → bcrypt 校验 → [MFA TOTP 验证] → 生成 admin JWT → Redis admin_session:{token}
```

**Token 策略：**
- 普通用户：JWT 7 天有效，支持静默续期
- 管理员：JWT 2 小时有效，敏感操作需再次 MFA
- Token 黑名单：登出时加入 Redis（TTL = 剩余有效期）
- 并发控制：同一账号最多 3 设备同时在线

### 4.3 智能对话模块（核心）

```
[用户消息]
    │
    ▼
┌─────────────────┐
│ 1. 敏感词预过滤   │  sensitive_service.check(message)
│    命中 block？   │──── 是 ──→ 返回"该问题无法回答，请联系招生办"
└────────┬────────┘
         │ 否
         ▼
┌─────────────────┐
│ 2. 风险分级       │  risk_service.classify(message, context)
│                  │  → low / medium / high
└────────┬────────┘
         │
    ┌────┼─────────────┐
    │    │             │
   low  medium       high
    │    │             │
    ▼    ▼             ▼
  正常  正常生成+     仅返回预设标准答案
  生成  强制引用溯源   或引导联系招生办
    │    │
    ▼    ▼
┌─────────────────┐
│ 3. 时间感知       │  calendar_service.get_current_tone()
│    注入当前话术    │  → 系统 prompt 注入当前阶段话术风格
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 4. 情感识别       │  emotion_service.detect(message)
│    检测情绪       │  → 焦虑/迷茫/挫败 → 注入安慰话术
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 5. 知识库检索     │  knowledge_service.search(query, top_k=5)
│    向量相似度匹配  │  → 检索相关切片作为上下文
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 6. Prompt 组装   │  system_prompt（角色差异化 + 时间话术 + 情感指令）
│                  │  + 知识库上下文
│                  │  + 对话历史（最近 N 轮）
│                  │  + 用户当前消息
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 7. LLM 调用      │  llm_service.stream_chat(prompt)
│    流式输出       │  → WebSocket/SSE 逐字推送给前端
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 8. 双模型审查     │  review_service.verify(question, answer, sources)
│   （异步后置）    │  轻量模型校验事实一致性
│                  │  → passed / flagged
│                  │  flagged 时追加"此回答仅供参考"
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│ 9. 持久化         │  保存 message（含 model_version, risk_level,
│                  │  sources, review_passed）+ 审计日志
└─────────────────┘
```

**模糊意图处理**（步骤 5-6 之间）：
- 知识库检索置信度低于阈值且意图不明确时
- 生成 2-3 个细化问题返回用户选择

**对话标题自动生成**：
- 首轮对话完成后，Celery 异步调用 LLM 生成标题（≤ 20 字）

### 4.4 LLM 接入层

```python
# 统一接口（策略模式）
class LLMProvider(ABC):
    async def chat(self, messages, stream=False) -> AsyncGenerator
    async def embed(self, texts) -> list[list[float]]

class QwenProvider(LLMProvider): ...      # 通义千问
class GLMProvider(LLMProvider): ...       # 智谱 GLM
class LocalProvider(LLMProvider): ...     # 本地模型（Ollama/vLLM）

class LLMRouter:
    """模型路由：主备切换 + 负载均衡"""
    - 管理员配置主用/备用模型
    - 负载均衡策略：round_robin / weighted / failover
    - 审查模型单独配置（轻量模型）
    - 调用失败自动 failover
    - 记录每次调用的模型版本
```

### 4.5 知识库流水线

```
[管理员上传文件]
    │
    ▼
knowledge_documents 状态 = pending
文件加密存储，记录 file_upload_logs
    │
    ▼
[审核员审核] → rejected（退回 + 备注）
    │
  approved
    │
    ▼
[Celery: parse_task]
    │  PDF → PyPDF2/pdfplumber
    │  Word → python-docx
    │  TXT/MD → 直接读取
    │
    ▼
[Celery: embedding_task]
    │  文本切片（按段落/固定 token 数，overlap）
    │  Embedding 模型生成向量
    │  批量写入 knowledge_chunks
    │
    ▼
knowledge_documents 状态 = approved, effective_from = NOW()
```

### 4.6 RBAC 权限校验

```python
@require_permission("knowledge:approve")
async def approve_document(doc_id: UUID, admin = Depends(get_current_admin)):
    ...

# 校验流程：
# 1. JWT 解析 admin_id
# 2. 查询 admin_roles → roles → role_permissions → permissions
# 3. 检查是否包含所需 permission.code
# 4. Redis 缓存权限列表，角色变更时刷新
```

### 4.7 审计日志

```
中间件自动采集：
├── 用户/管理员 ID
├── IP + User-Agent
├── 请求路径 + 方法 + 参数
├── 响应状态码 + 时间戳

对话特殊记录：
├── 提问内容 + 模型响应
├── 模型版本 + 知识库命中
├── 风险等级 + 审查结果

管理后台：
├── 多维度筛选（时间、用户、操作类型）
├── 导出 CSV/Excel
└── 可视化看板
```

---

## 5. 前端架构设计

### 5.1 项目目录结构

```
client/
├── public/
│   ├── favicon.ico
│   └── assets/                        # 官方素材（校徽、主楼剪影、木铎等）
│       ├── images/
│       └── fonts/                     # 思源黑体
│
├── src/
│   ├── main.ts
│   ├── App.vue
│   │
│   ├── router/
│   │   ├── index.ts                   # 路由实例 + 全局守卫
│   │   ├── user.ts                    # 用户端路由
│   │   └── admin.ts                   # 管理后台路由
│   │
│   ├── stores/                        # Pinia
│   │   ├── user.ts                    # 用户认证
│   │   ├── chat.ts                    # 对话状态
│   │   ├── conversation.ts            # 对话历史
│   │   ├── theme.ts                   # 主题
│   │   └── admin.ts                   # 管理后台
│   │
│   ├── api/
│   │   ├── request.ts                 # Axios 实例
│   │   ├── ws.ts                      # WebSocket
│   │   ├── auth.ts
│   │   ├── chat.ts
│   │   ├── knowledge.ts
│   │   └── admin/
│   │       ├── user.ts
│   │       ├── role.ts
│   │       ├── knowledge.ts
│   │       ├── model.ts
│   │       ├── sensitive.ts
│   │       ├── calendar.ts
│   │       ├── media.ts
│   │       └── log.ts
│   │
│   ├── composables/
│   │   ├── useAuth.ts
│   │   ├── useChat.ts
│   │   ├── useTheme.ts
│   │   ├── useResponsive.ts
│   │   ├── useAccessibility.ts
│   │   └── useFileUpload.ts
│   │
│   ├── components/
│   │   ├── common/                    # 通用组件
│   │   │   ├── AppHeader.vue
│   │   │   ├── AppSidebar.vue
│   │   │   ├── AppFooter.vue
│   │   │   ├── LoadingSpinner.vue
│   │   │   ├── EmptyState.vue
│   │   │   └── FileUploader.vue
│   │   │
│   │   ├── auth/
│   │   │   ├── LoginForm.vue
│   │   │   ├── SmsCodeInput.vue
│   │   │   └── RoleSelector.vue
│   │   │
│   │   ├── chat/
│   │   │   ├── ChatContainer.vue
│   │   │   ├── MessageList.vue        # 虚拟滚动
│   │   │   ├── MessageBubble.vue
│   │   │   ├── MessageInput.vue
│   │   │   ├── StreamingText.vue
│   │   │   ├── SourceCitation.vue
│   │   │   ├── SuggestQuestions.vue
│   │   │   ├── EmotionSupport.vue
│   │   │   └── MediaEmbed.vue
│   │   │
│   │   ├── conversation/
│   │   │   ├── ConversationList.vue
│   │   │   ├── ConversationItem.vue
│   │   │   └── SearchBar.vue
│   │   │
│   │   ├── home/
│   │   │   ├── HeroSection.vue
│   │   │   ├── HotQuestions.vue
│   │   │   ├── QuickActions.vue
│   │   │   └── CampusShowcase.vue
│   │   │
│   │   └── admin/
│   │       ├── layout/
│   │       │   ├── AdminLayout.vue
│   │       │   ├── AdminSidebar.vue
│   │       │   └── AdminHeader.vue
│   │       ├── dashboard/
│   │       │   ├── StatCards.vue
│   │       │   ├── ChatChart.vue
│   │       │   └── HotTopics.vue
│   │       ├── knowledge/
│   │       │   ├── DocList.vue
│   │       │   ├── DocUpload.vue
│   │       │   ├── DocReview.vue
│   │       │   └── ChunkPreview.vue
│   │       ├── sensitive/
│   │       │   ├── WordGroupList.vue
│   │       │   └── WordEditor.vue
│   │       ├── model/
│   │       │   └── ModelConfig.vue
│   │       ├── user/
│   │       │   ├── UserList.vue
│   │       │   └── AdminList.vue
│   │       ├── role/
│   │       │   ├── RoleList.vue
│   │       │   └── PermissionMatrix.vue
│   │       ├── media/
│   │       │   ├── MediaLibrary.vue
│   │       │   └── MediaUpload.vue
│   │       ├── calendar/
│   │       │   └── CalendarConfig.vue
│   │       └── log/
│   │           ├── AuditLogTable.vue
│   │           └── LogExport.vue
│   │
│   ├── styles/
│   │   ├── variables.scss
│   │   ├── theme-light.scss
│   │   ├── theme-dark.scss
│   │   ├── reset.scss
│   │   ├── accessibility.scss
│   │   └── responsive.scss
│   │
│   ├── utils/
│   │   ├── format.ts
│   │   ├── validation.ts
│   │   ├── storage.ts
│   │   └── markdown.ts
│   │
│   └── types/
│       ├── user.ts
│       ├── chat.ts
│       ├── knowledge.ts
│       └── admin.ts
│
├── index.html
├── vite.config.ts
├── tsconfig.json
└── package.json
```

### 5.2 路由设计

```
用户端（需登录守卫）：
├── /login                          # 登录页
├── /                               # 首页（高频问题 + 快捷入口）
├── /chat                           # 新对话
├── /chat/:id                       # 指定对话
└── /settings                       # 用户设置

管理后台（需管理员登录 + RBAC 守卫）：
├── /admin/login                    # 管理员登录
├── /admin/dashboard                # 仪表盘
├── /admin/knowledge                # 知识库管理
├── /admin/knowledge/review         # 审核
├── /admin/sensitive                # 敏感词库
├── /admin/model                    # 模型配置
├── /admin/users                    # 用户管理
├── /admin/admins                   # 管理员管理
├── /admin/roles                    # 角色权限
├── /admin/media                    # 多媒体资源
├── /admin/calendar                 # 招生日历
└── /admin/logs                     # 审计日志
```

**路由守卫：**
1. 白名单（/login, /admin/login）→ 放行
2. Token 有效性检查 → 无效重定向登录
3. /admin/* → 管理员 Token + RBAC 权限检查 → 无权限 403
4. 放行

### 5.3 对话界面布局

**PC 端：**

```
┌──────────────────────────────────────────────────────────┐
│  [北师大 Logo]  招生智能助手   [🔍]       [主题] [夜间模式]│
├────────────┬─────────────────────────────────────────────┤
│            │                                             │
│ [+ 新对话]  │           对话主区域                          │
│            │                                             │
│ ─ 最近对话 ─│  ┌─────────────────────────────────┐       │
│            │  │ 🤖 你好！我是北师大招生助手        │       │
│ ┌────────┐ │  │    [了解专业] [查分数线] [报名指南]│       │
│ │心理学专..│ │  └─────────────────────────────────┘       │
│ ├────────┤ │                                             │
│ │录取分数..│ │  ┌─────────────────────────────────┐       │
│ ├────────┤ │  │ 👤 心理学专业怎么样？             │       │
│ │宿舍环境..│ │  └─────────────────────────────────┘       │
│ └────────┘ │                                             │
│            │  ┌─────────────────────────────────┐       │
│            │  │ 🤖 北京师范大学心理学部是全国…    │       │
│            │  │    📎 来源：2025年招生简章        │       │
│            │  └─────────────────────────────────┘       │
│            │                                             │
│            ├─────────────────────────────────────────────┤
│┌──────────┐│  [📎附件] [请输入您的问题...    ] [发送▶]    │
││ 🧑 张同学 ││                                             │
││ 高考生    ││                                             │
│├──────────┤│                                             │
││ ⚙ 设置   ││                                             │
│└──────────┘│                                             │
└────────────┴─────────────────────────────────────────────┘

侧边栏结构（从上到下）：
├── [+ 新对话] 按钮
├── ─ 最近对话 ─ 标签
├── 对话历史列表（自动填充）
├── （弹性空间）
├── 用户头像 + 昵称 + 角色标签
└── ⚙ 设置入口

搜索：顶部 Logo 旁 🔍 图标，点击展开搜索面板
```

**移动端：**

```
┌─────────────────────┐
│ [☰] 招生智能助手 [🔍]│
├─────────────────────┤
│  对话消息区域         │
│  （虚拟滚动）         │
├─────────────────────┤
│ [📎] [输入...]  [▶]  │
└─────────────────────┘

☰ 侧边栏展开：
┌────────────┐
│ [+ 新对话]  │
│ ─ 最近对话 ─│
│ 心理学专... │
│ 录取分数... │
│ （底部）    │
│ 🧑 张同学   │
│ ⚙ 设置     │
└────────────┘
```

### 5.4 设计系统（基于北师大 VIS）

北师大标准色：**师大蓝** Pantone 293C (CMYK: C100 M70 Y0 K0) → HEX `#003DA5`

```scss
// variables.scss

// 主色调 — 师大蓝 (Pantone 293C)
$color-primary:          #003DA5;    // 师大蓝 — 标志、标题、主按钮
$color-primary-light:    #1A5FBF;    // 浅蓝 — 悬停态、背景配色
$color-primary-lighter:  #E8F0FE;    // 极浅蓝 — 选中态背景
$color-primary-dark:     #002D7A;    // 深压蓝 — 按下态、侧边栏活跃项

// 辅助色（蓝灰体系）
$color-secondary:        #4A6FA5;    // 蓝灰 — 次要按钮
$color-tertiary:         #6B7B8D;    // 中灰 — 辅助文字

// 语义色
$color-success:          #2E7D32;
$color-warning:          #F57C00;
$color-danger:           #C62828;
$color-info:             #1565C0;

// 中性色 — 日间
$color-text-primary:     #1A1A2E;
$color-text-secondary:   #5A5A72;
$color-text-placeholder: #9E9EB3;
$color-bg-primary:       #FFFFFF;
$color-bg-secondary:     #F4F6FA;
$color-bg-chat:          #FAFBFD;
$color-border:           #E2E6ED;

// 中性色 — 夜间
$dark-bg-primary:        #0F1117;
$dark-bg-secondary:      #1A1D27;
$dark-bg-chat:           #141720;
$dark-text-primary:      #E4E4EC;
$dark-text-secondary:    #9CA3B4;
$dark-border:            #2A2D3A;

// 对话气泡
$bubble-user-bg:         #003DA5;
$bubble-user-text:       #FFFFFF;
$bubble-assistant-bg:    #F4F6FA;
$bubble-assistant-text:  #1A1A2E;
$dark-bubble-user-bg:    #1A5FBF;
$dark-bubble-user-text:  #FFFFFF;
$dark-bubble-assistant-bg: #1E2130;
$dark-bubble-assistant-text: #E4E4EC;

// 字体
$font-family: 'Source Han Sans SC', 'Noto Sans SC', -apple-system, sans-serif;
$font-size-base: 16px;    // 可调：14/16/18/20px

// 圆角
$radius-sm: 4px;
$radius-md: 8px;
$radius-lg: 16px;
$radius-bubble: 18px;

// 响应式断点
$breakpoint-mobile:  768px;
$breakpoint-tablet:  1024px;
$breakpoint-desktop: 1440px;
```

### 5.5 性能优化

| 策略 | 实现 | 目标 |
|------|------|------|
| 路由懒加载 | `() => import('./views/xxx.vue')` | 首屏 ≤ 1.5s |
| 组件库按需引入 | Element Plus auto-import | 减小 bundle |
| 虚拟滚动 | `vue-virtual-scroller` | 长对话不卡顿 |
| 静态资源缓存 | content hash + Nginx 强缓存 | 二次秒开 |
| 图片懒加载 | `IntersectionObserver` + 缩略图 | 节省带宽 |
| WebSocket 重连 | 指数退避 + 心跳 | 网络稳定 |
| SW 离线缓存 | 高频问题 + 图片缩略图 | 弱网可用 |

### 5.6 无障碍（WCAG 2.1）

- 键盘导航（Tab / Enter / Esc）
- aria-label
- 颜色对比度 ≥ 4.5:1 (AA)
- 字体大小可调（14/16/18/20px）
- `:focus-visible` 焦点指示
- 语义化 HTML

---

## 6. 安全设计与部署架构

### 6.1 安全防护层次

```
L1 — 网络层: Nginx HTTPS/TLS 1.3 + IP 限流 + 防爬
L2 — 应用层: CORS 白名单 / JWT / RBAC / 参数校验
L3 — 业务层: 敏感词过滤 / 风险分级 / 双模型审查 / 二次验证
L4 — 数据层: 数据库加密 / 文件加密 / 脱敏日志 / 定时备份
```

### 6.2 防刷防爬

```
Nginx 层：
├── IP 维度：60次/分钟
├── 连接数限制：100/IP

应用层（FastAPI 中间件）：
├── 全局：单 IP 120次/分
├── 短信发送：同号码 1次/60秒，5次/小时，同 IP 10次/小时
├── 登录尝试：同号码 5次/10分，失败锁定 30 分钟
├── AI 对话：单用户 30次/分，500次/天

防爬：
├── User-Agent 检测
├── 异常行为识别（高频相同请求）
```

### 6.3 数据安全与合规

**数据最小化：**
- 仅采集手机号 + 昵称 + 角色，不强制身份证
- 日志中手机号脱敏：138****5678
- 不记录用户上传文件原文

**传输安全：**
- 全站 HTTPS（TLS 1.3）
- WebSocket 使用 WSS
- 管理后台 CSRF Token

**存储安全：**
- 上传文件 AES-256 加密
- 敏感字段应用层加密
- 密码 bcrypt (cost=12)
- MFA 密钥加密存储

**数据生命周期：**
- 短信验证码：5 分钟过期
- 用户会话：7 天过期
- 审计日志：保留 180 天后归档
- 软删除对话：30 天后物理清除
- 用户注销：72 小时内清除个人数据

### 6.4 部署架构（Docker Compose）

```
宿主机 (Linux Server)
│
├── nginx          443/80 对外暴露
│   └── 反向代理 → app:8000
│
├── app            FastAPI (Uvicorn 4 workers)
│   └── 内部网络 :8000
│
├── db             PostgreSQL 16 + pgvector
│   └── 内部网络 :5432
│
├── redis          Redis 7
│   └── 内部网络 :6379
│
├── worker         Celery (2 workers, concurrency=4)
│   ├── 定时: 日历刷新(每天)
│   ├── 定时: 日志归档(每周)
│   └── 定时: 过期清理(每天)
│
└── volumes (持久化)
    ├── ./data/postgres    数据库
    ├── ./data/redis       Redis AOF
    ├── ./data/uploads     加密上传文件
    ├── ./data/logs        应用日志
    └── ./data/backups     定时备份

仅 nginx 暴露端口，其余服务通过 Docker 内部网络通信。
```

### 6.5 备份策略

- **数据库**：每日 3:00 全量 pg_dump，保留 7 天日备 + 4 周周备，加密存储
- **上传文件**：增量 rsync + 每周全量备份
- **恢复 RTO**：数据库 < 30 分钟，完整服务 < 1 小时

### 6.6 监控与告警

**内置端点：**
- `GET /health` → 健康检查
- `GET /metrics` → Prometheus 指标

**监控指标：**
- API 响应时间 P95/P99
- 对话响应延迟（含 LLM）
- Celery 队列积压数
- 数据库连接池使用率
- Redis 内存、LLM 失败率、短信成功率

**告警规则：**
- API P99 > 3s → WARN
- LLM 连续失败 > 3次 → CRITICAL
- DB 连接池 > 80% → WARN
- Celery 队列 > 100 → WARN
- 磁盘空间 < 20% → CRITICAL
