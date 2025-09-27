#!/bin/bash
# 该脚本用于启动仅有 backend 服务的环境。
# 它假定您已经在 .env 文件中配置了 DATABASE_URL 以连接到外部数据库。

echo "Starting backend service ONLY (for remote database connection)..."
docker compose -f docker-compose.yml up --build -d