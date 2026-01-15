# 开发指南 (Development Guide)

本项目采用**本地开发**模式，前后端均在本地运行，仅数据库使用 Docker。

## 环境要求

- **Python**: 3.10+
- **Node.js**: 24+ (推荐使用 [nvm](https://github.com/nvm-sh/nvm) 管理)
- **Docker**: 仅用于 PostgreSQL 数据库

---

## 快速启动

### 1. 启动数据库

```bash
docker compose up -d db
```

数据库管理界面 (Adminer): http://localhost:8080

---

### 2. 启动后端 (Backend)

```bash
cd backend

# 首次运行：安装依赖
uv sync  # 或 pip install -e .

# 激活虚拟环境
source venv/bin/activate  # Linux/macOS
# 或 source .venv/bin/activate

# 启动开发服务器
fastapi dev app/main.py
```

后端地址: http://localhost:8000  
API 文档: http://localhost:8000/docs

---

### 3. 启动前端 (Frontend)

```bash
cd frontend

# 首次运行：切换 Node 版本并安装依赖
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 24  # 或 nvm install 24

npm install

# 启动开发服务器
npm run dev
```

前端地址: http://localhost:5173

---

## 常用 URL

| 服务 | 地址 |
|------|------|
| 前端 | http://localhost:5173 |
| 后端 API | http://localhost:8000 |
| API 文档 (Swagger) | http://localhost:8000/docs |
| 数据库管理 (Adminer) | http://localhost:8080 |

---

## 环境变量

项目根目录的 `.env` 文件包含所有配置。主要配置项：

```env
# 数据库
POSTGRES_SERVER=localhost
POSTGRES_PORT=5432
POSTGRES_DB=app
POSTGRES_USER=postgres
POSTGRES_PASSWORD=root

# 后端
SECRET_KEY=changethis
FIRST_SUPERUSER=admin@example.com
FIRST_SUPERUSER_PASSWORD=changethis

# AI 配置 (可选)
VOLC_API_KEY=your_key
VOLC_DEEPSEEK_MODEL_ID=your_model_id
```

---

## 数据库迁移

```bash
cd backend
source venv/bin/activate

# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

---

## 代码检查

```bash
# 后端
cd backend
uv run ruff check .
uv run mypy .

# 前端
cd frontend
npm run lint
```
