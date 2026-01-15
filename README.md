# Industrial Data Flow

**Industrial Data Flow** 是一个基于 FastAPI 和 React 的现代化全栈数据处理平台，专注于工业级数据清洗与 AI 自动化处理。

## 核心功能

- 🚀 **高性能后端**: 基于 FastAPI + SQLModel (PostgreSQL) 构建，并在 `api/routes/industrial_pipeline` 中实现了完整的数据处理管道。
- ⚛️ **现代化前端**: 使用 React 19 + Vite + Tailwind CSS + Radix UI 构建的响应式界面。
- 🤖 **AI 驱动**: 集成 AI 模型（如 DeepSeek）进行深度数据清洗与结构化提取。
- �️ **安全可靠**: 内置 JWT 认证、权限管理与安全最佳实践。
- � **可视化大屏**: 提供实时任务监控与数据统计仪表盘。

## 快速开始

详细开发文档请参阅 [开发指南 (Development Guide)](development.md)。

### 后端启动

```bash
cd backend
source venv/bin/activate
fastapi dev app/main.py
```

### 前端启动

```bash
cd frontend
nvm use 24
npm run dev
```

## 技术栈

| 模块 | 技术选型 |
|------|----------|
| **Backend** | Python 3.10+, FastAPI, SQLModel, Pydantic v2, Alembic |
| **Frontend** | React 19, TypeScript, Vite, TanStack Query/Router, Tailwind CSS |
| **Database** | PostgreSQL 17 |
| **Testing** | Pytest, Playwright |

## 许可证

Private / Proprietary
