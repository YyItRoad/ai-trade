import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse

from api.routes import analysis, assets, auth
from core.scheduler import scheduler, start_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理，在应用启动时启动调度器。
    """
    # 启动
    print("应用启动，开始调度任务...")
    start_scheduler()
    yield
    # 关闭
    print("应用关闭，停止调度任务...")
    scheduler.shutdown()

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

# 挂载静态文件目录
app.mount("/static", StaticFiles(directory="static"), name="static")

# --- 页面路由 ---

@app.get("/login", response_class=FileResponse, include_in_schema=False)
async def read_login_page():
    """提供登录页面"""
    return "static/login.html"

@app.get("/", response_class=FileResponse, include_in_schema=False)
async def read_root():
    """提供前端主页面"""
    return "static/index.html"

@app.get("/manage", response_class=FileResponse, include_in_schema=False)
async def manage_assets_page():
    """提供资产管理页面"""
    return "static/manage.html"
