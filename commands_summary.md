# 构建和运行命令

## 后端

### 本地开发

**选项 1: 使用 `uv` (如果已安装，推荐)**
```bash
cd backend
uv run fastapi dev app/main.py
```

**选项 2: 使用现有的虚拟环境**
```bash
# 首先激活虚拟环境
source backend/venv/bin/activate
cd backend
fastapi dev app/main.py
```
*或者直接运行:*
```bash
./backend/venv/bin/python -m fastapi dev backend/app/main.py
```

### 使用 Docker 构建/运行
```bash
docker compose build backend
docker compose up -d backend
```

## 前端

### 本地开发 (使用 `npm`)
```bash
cd frontend
npm install
npm run dev
```

### 生产环境构建
```bash
cd frontend
npm run build
```

### 使用 Docker 构建/运行
```bash
docker compose build frontend
docker compose up -d frontend
```

## 整个技术栈
一次性构建并运行所有内容:
```bash
docker compose up -d --build
```
监听变更 (开发模式):
```bash
docker compose watch
```
