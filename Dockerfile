# 使用官方 Python 镜像作为基础
FROM python:3.10-slim

# 设置工作目录
WORKDIR /app

# 安装构建依赖 (如果需要)
# RUN apt-get update && apt-get install -y --no-install-recommends gcc

# 复制依赖文件并安装
COPY requirements.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# 复制所有项目文件到工作目录
COPY . .

# 暴露应用程序运行的端口
EXPOSE 8000

# 容器启动时执行的命令
# 使用 uvicorn 启动 FastAPI 应用
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]