#!/bin/bash
# 该脚本用于启动带有本地数据库容器的完整开发环境。
# 它会同时加载 docker-compose.yml 和 docker-compose.db.yml 文件。

echo "Starting backend service with local database..."

# Step 1: Explicitly pull the MySQL image to show progress clearly
echo "Pulling MySQL image... This might take a few minutes for the first time."
docker pull mysql:8.4

# Step 2: Start the services. This will be much faster now.
echo "Starting services..."
docker compose -f docker-compose.yml -f docker-compose.db.yml up --build -d