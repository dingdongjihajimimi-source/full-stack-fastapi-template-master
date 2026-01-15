# FastAPI Project - Frontend

基于 [Vite](https://vitejs.dev/) + [React](https://reactjs.org/) + [TypeScript](https://www.typescriptlang.org/) + [TanStack](https://tanstack.com/) + [Tailwind CSS](https://tailwindcss.com/)

## 环境要求

* Node.js 24+ (推荐使用 [nvm](https://github.com/nvm-sh/nvm))

## 快速启动

1. 切换 Node 版本:

```bash
cd frontend

# 使用 nvm
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"
nvm use 24  # 或 nvm install 24
```

2. 安装依赖:

```bash
npm install
```

3. 启动开发服务器:

```bash
npm run dev
```

前端地址: http://localhost:5173

## 项目结构

```
frontend/src/
├── assets/       # 静态资源
├── client/       # 自动生成的 OpenAPI 客户端
├── components/   # UI 组件
├── hooks/        # 自定义 Hooks
└── routes/       # 页面路由
```

## 生成 API 客户端

当后端 API 变更时，需要重新生成客户端:

```bash
# 方式一：使用脚本（推荐）
cd ..  # 回到项目根目录
./scripts/generate-client.sh

# 方式二：手动
# 1. 下载 http://localhost:8000/api/v1/openapi.json 到 frontend/openapi.json
# 2. 运行:
npm run generate-client
```

## 代码检查

```bash
npm run lint
```

## 端到端测试 (Playwright)

```bash
# 确保后端正在运行
npx playwright test

# UI 模式
npx playwright test --ui
```

## 远程 API

如需连接远程 API，在 `frontend/.env` 中设置:

```env
VITE_API_URL=https://api.your-domain.com
```
