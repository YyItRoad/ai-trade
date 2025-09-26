# AI 交易分析工具

这是一个使用 FastAPI、MySQL 和大语言模型（LLM）构建的自动化交易分析工具。它能够定时获取指定交易对的 K 线数据，调用 AI 模型进行分析，并将结果存储和展示。

## 技术栈

- **后端**: Python 3.8+, FastAPI, Uvicorn
- **数据库**: MySQL / SQLite
- **任务调度**: APScheduler
- **AI**: OpenAI API (或其他兼容的 LLM API)
- **前端**: HTML, CSS, Vanilla JavaScript

## 环境准备

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd ai-trade
```

### 2. 安装 Python 依赖

确保你已经安装了 Python 3.8 或更高版本。建议使用虚拟环境。

```bash
python -m venv venv
source venv/bin/activate  # 在 Windows 上使用 `venv\Scripts\activate`
pip install -r requirements.txt
```

### 3. 数据库设置

本项目同时支持 MySQL 和 SQLite 数据库，并提供灵活的配置选项。

- **对于生产环境 (Docker)**: 推荐使用 MySQL。`docker-compose` 会自动为你创建一个 MySQL 容器并初始化数据库。
- **对于本地开发**: 你可以使用外部的 MySQL 实例，或者 **无需任何配置**，系统会自动回退使用一个本地的 `default_trade_analysis.db` SQLite 文件，实现零配置快速启动。

## 配置

项目通过根目录下的 `.env` 文件进行配置。请根据 `.env.example` 创建你自己的 `.env` 文件。

```bash
cp .env.example .env
```

打开并编辑 `.env` 文件，填入你的配置信息。

### 数据库配置 (选择一种方式)

系统会按照以下优先级顺序来确定数据库连接：

#### 方式 A: 使用 `DATABASE_URL` (最高优先级)

这是最灵活的方式。你可以提供一个完整的数据库连接字符串。

- **示例 (MySQL):**
  ```dotenv
  DATABASE_URL="mysql://your_user:your_password@localhost:3306/ai_trade_db"
  ```

- **示例 (SQLite):**
  ```dotenv
  DATABASE_URL="sqlite:///./my_trade_analysis.db"
  ```

#### 方式 B: 使用独立变量 (Docker Compose 推荐)

如果你没有设置 `DATABASE_URL`，系统会尝试使用以下变量来构建一个 MySQL 连接字符串。这是 `docker-compose` 使用的默认方式。

```dotenv
DB_HOST=db
DB_PORT=3306
DB_USER=your_db_user
DB_PASSWORD=your_db_password
DB_NAME=ai_trade_db
```

#### 方式 C: 零配置回退 (本地开发默认)

如果你既没有设置 `DATABASE_URL`，也没有提供完整的 `DB_*` 变量，系统会自动创建一个名为 `default_trade_analysis.db` 的 SQLite 数据库文件在项目根目录，并使用它。这允许你在本地环境中无需任何数据库配置即可快速启动项目。

### 其他配置

```dotenv
# K线数据 API (例如 Binance)
KLINE_API_KEY="your_binance_api_key"
KLINE_API_SECRET="your_binance_api_secret"

# 大语言模型 API
OPENAI_API_KEY="your_openai_api_key"
OPENAI_API_BASE="https://api.openai.com/v1" # 如果使用代理或第三方服务，请修改此地址

# 应用登录密钥
APP_LOGIN_KEY="a_strong_secret_key_for_login"
```

## 运行项目

### 方式一：使用 Docker Compose (推荐)

这是最简单、最推荐的启动方式，可以一键启动后端服务和数据库。

1.  **确保 Docker 已安装并运行**。

2.  **配置 `.env` 文件**:
    -   复制 `.env.example` 为 `.env`。
    -   填写所有必要的 API 密钥和数据库密码。
    -   **重要**: 确保 `DB_HOST` 设置为 `db`，这是 Docker 网络内部的数据库服务名。

3.  **构建并启动容器**:
    在项目根目录下运行以下命令：
    ```bash
    docker-compose up --build
    ```
    -   `--build` 参数会强制重新构建镜像，确保代码更新生效。
    -   初次启动时，Docker 会下载 MySQL 镜像并根据 `schema.sql` 初始化数据库，这可能需要一些时间。

4.  **访问服务**:
    -   服务启动后，可以通过 [http://localhost:8000](http://localhost:8000) 访问前端页面。
    -   数据库将通过主机的 3307 端口暴露，方便使用外部工具连接调试。

5.  **停止服务**:
    在终端中按 `Ctrl+C`，然后运行 `docker-compose down` 来停止并移除容器。

### 方式二：本地直接运行 (用于开发)

1.  **配置数据库 (可选)**:
    -   如果你想连接到一个外部的 MySQL 数据库，请在 `.env` 文件中配置 `DATABASE_URL` 或 `DB_*` 变量。
    -   如果你想使用默认的 SQLite 数据库，**无需任何配置**。

2.  **启动后端服务**:
    在激活了 Python 虚拟环境的终端中，运行：
    ```bash
    python manage.py run
    ```
    或者直接使用 uvicorn:
    ```bash
    uvicorn main:app --reload
    ```

### 访问前端页面

- **主页 (数据展示)**: [http://127.0.0.1:8000/](http://127.0.0.1:8000/)
- **资产管理页面**: [http://127.0.0.1:8000/manage](http://127.0.0.1:8000/manage)

首次访问时，你需要输入在 `.env` 文件中设置的 `APP_LOGIN_KEY`。

## 功能说明

### 主页 (`/`)

- 默认展示最新的一条 AI 分析结果。
- 可以通过下拉菜单选择查看所有已分析过的资产的历史结果。
- 结果按分析时间倒序排列。

### 资产管理页面 (`/manage`)

- **登录**: 使用 `APP_LOGIN_KEY` 访问。
- **资产列表**:
    - 显示所有已添加的资产及其符号、类型（现货、U本位、币本位）和当前的定时任务（Cron 表达式）。
    - 可以根据资产类型进行筛选。
- **添加资产**:
    - 点击“添加资产”按钮。
    - 输入交易对符号（例如 `BTCUSDT`）。
    - 选择资产类型。
- **设置定时任务**:
    - 点击任意资产所在行的“设置定时”按钮。
    - 输入一个有效的 Cron 表达式来定义分析任务的执行频率。
    - 示例: `0 * * * *` (每小时的第0分钟执行), `*/30 * * * *` (每30分钟执行一次)。
    - 将输入框留空并保存，可以清除该资产的定时任务。
- **手动触发分析**:
    - 点击“立即分析”按钮，可以立即为该资产执行一次 K 线数据获取和 AI 分析。
- **删除资产**:
    - 点击“删除”按钮，将从系统中移除该资产及其相关的定时任务。