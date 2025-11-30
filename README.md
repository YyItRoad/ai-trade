# AI 交易分析工具

这是一个使用 FastAPI、MySQL 和大语言模型（LLM）构建的自动化交易分析工具。它能够定时获取指定交易对的 K 线数据，调用 AI 模型进行分析，并将结果存储和展示。项目内置了灵活的资产管理、动态任务调度和强大的提示词（Prompt）管理系统。

## ✨ 核心功能

- **动态资产管理**:
    - 通过 Web 界面轻松添加、删除、查看需要分析的交易对（如 `BTCUSDT`）。
    - 支持多种资产类型（现货、U本位、币本位）。
- **灵活的任务调度**:
    - 为每个资产独立设置 Cron 表达式，实现高度定制化的定时分析任务。
    - 支持动态更新、暂停或移除定时任务，无需重启服务。
- **手动触发分析**:
    - 对任何已配置的资产，可随时手动触发一次即时分析。
- **强大的提示词管理**:
    - **版本控制**: 可创建和管理多个版本的分析提示词（Prompt）。
    - **A/B 测试**: 可同时激活两个提示词进行对比测试，系统会为每个分析任务随机选用一个。
    - **激活与切换**: 随时在多个提示词版本之间切换，或指定用于 A/B 测试的版本。
    - **安全删除**: 只有未被激活的提示词才能被删除，确保系统稳定性。
- **数据可视化**:
    - 在主页清晰地展示最新或历史的 AI 分析结果。
    - 可按资产筛选查看历史分析记录。
- **容器化部署**:
    - 提供完整的 Docker 和 Docker Compose 配置，实现一键部署和环境隔离。
    - 支持连接到本地 Docker 数据库或外部远程数据库两种模式。
- **安全访问**:
    - 管理页面通过密钥进行访问控制。

## 🛠️ 技术栈

- **后端**: Python 3.8+, FastAPI, Uvicorn
- **数据库**: MySQL 8.0+
- **任务调度**: APScheduler
- **AI**: OpenAI API (或其他兼容的 LLM API)
- **前端**: HTML, CSS, Vanilla JavaScript
- **容器化**: Docker, Docker Compose

## 🚀 部署与运行

本项目推荐使用 Docker 进行部署，以获得最佳的兼容性和最简化的启动流程。

### 1. 环境准备

- 安装 [Docker](https://www.docker.com/get-started) 和 Docker Compose。
- 克隆本项目代码。

### 2. 项目配置

项目通过根目录下的 `.env` 文件进行配置。请根据 `.env.example` 创建你自己的 `.env` 文件。

```bash
cp .env.example .env
```

打开并编辑 `.env` 文件，至少需要填写以下信息：

```dotenv
# 数据库密码 (用于 docker-compose.db.yml)
DB_PASSWORD=your_strong_db_password

# K线数据 API (例如 Binance)
KLINE_API_KEY="your_binance_api_key"
KLINE_API_SECRET="your_binance_api_secret"

# 大语言模型 API
OPENAI_API_KEY="your_openai_api_key"
OPENAI_API_BASE="https://api.openai.com/v1" # 如果使用代理或第三方服务，请修改此地址

# 应用登录密钥
APP_LOGIN_KEY="a_strong_secret_key_for_login"
```

### 3. 启动服务 (选择一种模式)

我们提供了便捷的启动脚本来处理不同的部署场景。

#### 模式 A: 本地化部署 (后端 + 数据库均在 Docker 中)

这是最简单的启动方式，适用于快速体验和本地开发。

```bash
# 赋予脚本执行权限 (仅需首次)
chmod +x start-local.sh stop.sh

# 启动服务
./start-local.sh
```

此脚本会使用 `docker-compose.yml` 和 `docker-compose.db.yml` 文件，一键启动应用服务容器和一个独立的 MySQL 数据库容器。

- **应用访问**: [http://localhost:8000](http://localhost:8000)
- **数据库端口 (供外部调试)**: `localhost:3307`

#### 模式 B: 连接远程数据库 (仅后端在 Docker 中)

当您拥有一个外部的、可访问的 MySQL 数据库时，使用此模式。

1.  **配置 `.env` 文件**:
    修改数据库连接信息，使其指向您的远程数据库。特别注意 `DB_HOST`。
    ```dotenv
    # 将 DB_HOST 设置为您的远程数据库地址
    DB_HOST=your_remote_db_host
    DB_PORT=3306
    DB_USER=your_remote_db_user
    DB_PASSWORD=your_remote_db_password
    DB_NAME=your_remote_db_name
    ```

2.  **启动服务**:
    ```bash
    # 赋予脚本执行权限 (仅需首次)
    chmod +x start-remote.sh stop.sh

    # 启动服务
    ./start-remote.sh
    ```
    此脚本仅使用 `docker-compose.yml` 文件启动应用服务容器，该容器将连接到您在 `.env` 中配置的外部数据库。

### 4. 访问应用

- **主页 (数据展示)**: [http://localhost:8000/](http://localhost:8000/)
- **资产管理**: [http://localhost:8000/manage.html](http://localhost:8000/manage.html)
- **提示词管理**: [http://localhost:8000/prompts.html](http://localhost:8000/prompts.html)

首次访问管理页面时，你需要输入在 `.env` 文件中设置的 `APP_LOGIN_KEY`。

### 5. 停止服务

无论使用何种模式启动，都可以使用 `stop.sh` 脚本来安全地停止并移除所有相关的容器和网络。

```bash
./stop.sh
```

## 📝 配置文件 `.env` 详解

- `DB_HOST`: 数据库主机地址。在本地化部署模式下应为 `db` (Docker 服务名)，在远程模式下为您的数据库 IP 或域名。
- `DB_PORT`: 数据库端口。
- `DB_USER`: 数据库用户名。
- `DB_PASSWORD`: 数据库密码。
- `DB_NAME`: 数据库名称。
- `KLINE_API_KEY`, `KLINE_API_SECRET`: K 线数据源的 API 密钥。
- `OPENAI_API_KEY`, `OPENAI_API_BASE`: LLM 服务的 API 密钥和基础 URL。
- `APP_LOGIN_KEY`: 用于访问管理页面的密码。
- `LOG_LEVEL`: 应用日志级别，默认为 `INFO`。