# FastAPI Project - Backend

## 环境要求

* [Python 3.10+](https://www.python.org/)
* [uv](https://docs.astral.sh/uv/) for Python package and environment management

## 快速启动

1. 安装依赖:

```bash
cd backend
uv sync
```

2. 激活虚拟环境:

```bash
source venv/bin/activate
# 或
source .venv/bin/activate
```

3. 启动开发服务器:

```bash
fastapi dev app/main.py
```

后端地址: http://localhost:8000  
API 文档: http://localhost:8000/docs

## 项目结构

```
backend/
├── app/
│   ├── api/          # API 路由
│   ├── core/         # 配置和核心功能
│   ├── models/       # SQLModel 数据模型
│   └── main.py       # 应用入口
├── alembic/          # 数据库迁移
└── tests/            # 测试文件
```

## 数据库迁移

```bash
# 创建迁移
alembic revision --autogenerate -m "描述"

# 执行迁移
alembic upgrade head
```

## 测试

```bash
bash ./scripts/test.sh
```

测试覆盖率报告: `htmlcov/index.html`

## 代码检查

```bash
uv run ruff check .
uv run mypy .
```

## VS Code 配置

已配置 VS Code 调试器，可直接使用断点调试。测试也可通过 VS Code Python 测试面板运行。
