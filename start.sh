#!/bin/bash

# 退出程序时的清理函数
cleanup() {
    echo "正在停止所有服务..."
    kill $(jobs -p) 2>/dev/null
    exit
}

# 捕获 Ctrl+C (SIGINT) 信号并调用清理函数
trap cleanup SIGINT

# 启动数据库
echo "正在启动数据库..."
docker compose up -d db

# 确保数据库准备就绪 (简单延时，生产环境建议使用健康检查循环)
echo "正在等待数据库准备就绪..."

# 如果存在 NVM 则加载
export NVM_DIR="$HOME/.nvm"
[ -s "$NVM_DIR/nvm.sh" ] && \. "$NVM_DIR/nvm.sh"

# 启动后端
echo "正在启动后端..."
(
    cd backend
    # 确保虚拟环境存在并已激活
    if [ ! -d "venv" ]; then
        echo "正在创建虚拟环境..."
        python3 -m venv venv
        source venv/bin/activate
        pip install -e .
    else
        source venv/bin/activate
    fi
    
    # 运行 FastAPI
    fastapi dev app/main.py
) &

# 启动前端
echo "正在启动前端..."
(
    cd frontend
    # 如果需要，检查/创建 .env 文件
    if [ ! -f ".env" ]; then
        echo "正在为前端创建 .env 文件..."
        echo "VITE_API_URL=" > .env
    fi
    
    npm run dev
) &

# 等待所有后台进程
wait
