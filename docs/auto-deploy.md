# 全自动部署说明（GitHub Actions + Docker Compose）

本文档对应以下文件：
- `.github/workflows/ci.yml`
- `.github/workflows/cd.yml`
- `deploy/docker-compose.prod.yml`
- `deploy/scripts/deploy.sh`
- `deploy/scripts/rollback.sh`

## 1. 服务器准备（仅首次）

首次初始化请直接按第 6 节执行（含 Docker 安装、目录创建、`.env` 配置和环境验证）。

本节只强调两个上线前前置条件：
- 服务器已完成第 6 节初始化。
- 服务器存在 `/opt/bnu-admission-chatbot/deploy/.env` 且变量完整。

> 注意：向量数据库必须启用。部署脚本会自动执行 `CREATE EXTENSION IF NOT EXISTS vector;`。

## 2. GitHub Secrets 配置

在仓库 `Settings -> Secrets and variables -> Actions` 添加：

- `DEPLOY_HOST`：服务器 IP 或域名
- `DEPLOY_USER`：SSH 用户
- `DEPLOY_SSH_KEY`：用于登录服务器的私钥（建议专用 deploy key）
- `GHCR_PAT`：用于服务器拉取 GHCR 镜像的 Token（至少 `read:packages`）

可选（腾讯云 TCR，推荐腾讯云服务器配置）：
- `TCR_REGISTRY`：如 `ccr.ccs.tencentyun.com`
- `TCR_NAMESPACE`：TCR 命名空间
- `TCR_USERNAME`：TCR 用户名
- `TCR_PASSWORD`：TCR 密码/令牌

## 3. 自动化流程

### CI（`.github/workflows/ci.yml`）
- 触发：`pull_request`
- 执行：
  - 后端 `pytest -v`
  - 前端 `npm ci && npm run build`

### CD（`.github/workflows/cd.yml`）
- 触发：`push main` / 手动 `workflow_dispatch`
- 执行顺序：
  1. 质量门禁（后端测试 + 前端构建）
  2. 构建并推送镜像到 GHCR（`app`、`nginx`）
  3. 若配置了 TCR Secrets，则额外推送到 TCR
  4. SSH 到服务器执行 `deploy/scripts/deploy.sh`（优先使用 TCR 镜像，否则回退 GHCR）

部署脚本行为：
- `docker login ghcr.io`
- 拉取新镜像
- 启动 `db/redis`
- 确保 `pgvector` 扩展
- 执行 `alembic upgrade head`
- 启动 `app/worker/nginx`
- 健康检查 `http://127.0.0.1/health`
- 失败自动回滚到上一版本

## 4. 手动回滚

登录服务器后执行：

```bash
cd /opt/bnu-admission-chatbot/deploy
./scripts/rollback.sh
```

## 5. 常见注意事项

- 服务器上必须存在 `/opt/bnu-admission-chatbot/deploy/.env`，CI 不会自动上传密钥配置。
- 如果 GHCR 包是私有的，务必使用 `GHCR_PAT`。
- 如需 HTTPS，请在服务器前再加一层证书终止（如 Caddy/Nginx/云负载均衡）。
- 多应用同机部署时，不建议每个应用都直接绑定公网 `80/443`。

### 5.1 多应用服务器推荐方式（共享 80/443）

本项目默认已改为：`nginx` 仅监听本机 `127.0.0.1:18080`（见 `BIND_IP`、`HTTP_PORT`）。

推荐做法：
- 让一个“总入口反向代理”（宿主机 Nginx/Caddy/Traefik）统一占用 `80/443`
- 按域名把流量转发到各应用的本地端口

例如本项目可转发到：
- `127.0.0.1:18080`

如果端口冲突，可在服务器 `.env` 里改为：

```bash
BIND_IP=127.0.0.1
HTTP_PORT=18081
```

宿主机 Nginx 配置模板见：`deploy/nginx/host-bnu.conf.example`

强制 HTTPS + Certbot 模板见：`deploy/nginx/host-bnu-https-certbot.conf.example`

使用步骤（宿主机）：

```bash
sudo cp deploy/nginx/host-bnu.conf.example /etc/nginx/conf.d/bnu.conf
sudo sed -i 's/admissions.example.com/你的域名/g' /etc/nginx/conf.d/bnu.conf
sudo nginx -t
sudo systemctl reload nginx
```

### 5.2 强制 HTTPS + Certbot（Webroot）

```bash
# 1) 安装 nginx 和 certbot（Ubuntu）
sudo apt-get update
sudo apt-get install -y nginx certbot

# 2) 准备 ACME 验证目录
sudo mkdir -p /var/www/certbot
sudo chown -R www-data:www-data /var/www/certbot

# 3) 启用 HTTPS 模板（先替换域名）
sudo cp deploy/nginx/host-bnu-https-certbot.conf.example /etc/nginx/conf.d/bnu.conf
sudo sed -i 's/admissions.example.com/你的域名/g' /etc/nginx/conf.d/bnu.conf

# 4) 先申请证书（webroot 模式）
sudo nginx -t
sudo systemctl reload nginx
sudo certbot certonly --webroot -w /var/www/certbot -d 你的域名

# 5) 申请成功后重载 nginx（模板已强制 HTTP -> HTTPS）
sudo nginx -t
sudo systemctl reload nginx

# 6) 验证自动续期
sudo certbot renew --dry-run
```

说明：
- 模板已保留 `/.well-known/acme-challenge/` 放行，其余 HTTP 请求会 301 到 HTTPS。
- 若服务器有防火墙，请确保放行 `80/443`。
- 若你此前配置里包含 `include /etc/letsencrypt/options-ssl-nginx.conf;` 且文件不存在，会导致 `nginx -t` 失败。可改用本仓库最新 HTTPS 模板（已去除该硬依赖）。

## 6. 服务器首次初始化命令清单（Ubuntu 22.04/24.04）

### 6.1 安装 Docker + Compose 插件

```bash
sudo apt-get update
sudo apt-get install -y ca-certificates curl gnupg
sudo install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/debian/gpg | sudo gpg --dearmor -o /etc/apt/keyrings/docker.gpg
sudo chmod a+r /etc/apt/keyrings/docker.gpg

echo \
  "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] https://download.docker.com/linux/ubuntu \
  $(. /etc/os-release && echo $VERSION_CODENAME) stable" | \
  sudo tee /etc/apt/sources.list.d/docker.list > /dev/null

sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
sudo systemctl enable --now docker
```

### 6.2 创建部署目录与权限

```bash
sudo mkdir -p /opt/bnu-admission-chatbot/deploy/scripts
sudo chown -R $USER:$USER /opt/bnu-admission-chatbot
```

### 6.3 首次放置部署文件（只做一次）

方式 A：等 GitHub Actions 首次发布自动上传。

方式 B：先手动从本地上传（可选）：

```bash
scp deploy/docker-compose.prod.yml user@your-server:/opt/bnu-admission-chatbot/deploy/docker-compose.prod.yml
scp deploy/.env.example user@your-server:/opt/bnu-admission-chatbot/deploy/.env.example
scp deploy/scripts/deploy.sh deploy/scripts/rollback.sh user@your-server:/opt/bnu-admission-chatbot/deploy/scripts/
```

### 6.4 生成服务器环境变量

```bash
cd /opt/bnu-admission-chatbot/deploy
cp .env.example .env
nano .env
```

至少修改这些值：
- POSTGRES_PASSWORD
- DATABASE_URL
- REDIS_URL
- JWT_SECRET_KEY

### 6.5 验证基础环境

```bash
docker --version
docker compose version
docker info
```

如果以上命令正常，服务器就可以接收自动发布了。

## 7. 宿主机一键模拟生产部署（推荐发布前执行）

新增脚本：`deploy/scripts/host-prod-smoke.sh`

用途：
- 本地构建 `app/nginx` 镜像
- 使用生产 compose 启动 `db/redis`
- 执行 `alembic upgrade head`
- 启动 `app/worker/nginx`
- 做健康检查并输出关键日志

执行：

```bash
./deploy/scripts/host-prod-smoke.sh
```

常用参数：

```bash
./deploy/scripts/host-prod-smoke.sh --port 18081
./deploy/scripts/host-prod-smoke.sh --project bnu-hosttest-2 --keep
```

说明：
- 默认会清理测试容器与数据卷（不加 `--keep`）。
- 该脚本用于宿主机验证，CI 容器内若无 Docker 不可执行。
