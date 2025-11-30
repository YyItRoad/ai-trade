import asyncio
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import analysis, assets, auth, prompts, tasks, plans, dictionary
from core.scheduler import scheduler, start_scheduler
from core.database import init_db, init_connection_pool, close_connection_pool
from core.logger import setup_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理：
    1. 应用启动时，初始化数据库表结构。
    2. 应用启动时，启动后台任务调度器。
    """
    # 启动
    setup_logging()
    logging.info("应用启动，正在初始化数据库连接池...")
    init_connection_pool()
    logging.info("应用启动，正在检查/初始化数据库 schema...")
    init_db()
    
    logging.info("应用启动，开始调度任务...")
    start_scheduler()
    yield
    # 关闭
    logging.info("应用关闭，停止调度任务...")
    scheduler.shutdown()
    logging.info("应用关闭，正在关闭数据库连接池...")
    close_connection_pool()

app = FastAPI(
    title="AI 交易分析",
    description="一个使用AI进行K线数据分析的API",
    version="1.0.0",
    lifespan=lifespan
)

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 包含API路由
app.include_router(analysis.router, prefix="/api", tags=["分析"])
app.include_router(assets.router, prefix="/api", tags=["资产"])
app.include_router(auth.router, prefix="/api", tags=["认证"])
app.include_router(prompts.router, prefix="/api", tags=["提示词"])
app.include_router(tasks.router, prefix="/api", tags=["定时任务"])
app.include_router(plans.router, prefix="/api", tags=["交易计划"])
app.include_router(dictionary.router, prefix="/api", tags=["字典"])

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 页面路由 ---

@app.get("/login", response_class=FileResponse, include_in_schema=False)
async def read_login_page():
    """提供登录页面"""
    return "static/login.html"

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_root():
    """提供前端主页面 (重定向到分析页面)"""
    return "static/analysis.html"

@app.get("/analysis.html", response_class=FileResponse, include_in_schema=False)
async def analysis_page():
    """提供行情分析页面"""
    return "static/analysis.html"

@app.get("/plans.html", response_class=FileResponse, include_in_schema=False)
async def plans_page():
    """提供交易计划页面"""
    return "static/plans.html"

@app.get("/manage", response_class=FileResponse, include_in_schema=False)
async def manage_tasks_page():
    """提供任务管理页面"""
    return "static/manage.html"

@app.get("/prompts.html", response_class=FileResponse, include_in_schema=False)
async def prompts_page():
    """提供提示词管理页面"""
    return "static/prompts.html"

@app.get("/assets.html", response_class=FileResponse, include_in_schema=False)
async def assets_page():
    """提供资产管理页面"""
    return "static/assets.html"
