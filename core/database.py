import logging
import mysql.connector
from mysql.connector import pooling
from urllib.parse import urlparse
from core.config import settings
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime
import enum

logger = logging.getLogger(__name__)

connection_pool = None

# --- Enums for Model Validation ---

class AssetType(enum.IntEnum):
    SPOT = 0
    USD_M = 1
    COIN_M = 2

class Cycle(str, enum.Enum):
    M1 = '1m'
    M5 = '5m'
    M15 = '15m'
    H1 = '1h'
    H4 = '4h'
    D1 = '1d'

class Direction(str, enum.Enum):
    LONG = 'LONG'
    SHORT = 'SHORT'
    NONE = 'NONE'

class PlanStatus(str, enum.Enum):
    ACTIVE = 'ACTIVE'
    EXECUTED = 'EXECUTED'
    CANCELLED = 'CANCELLED'
    EXPIRED = 'EXPIRED'

# --- Pydantic Models ---

class Asset(BaseModel):
    id: int
    symbol: str
    type: AssetType
    created_at: datetime

class Prompt(BaseModel):
    id: int
    name: str
    version: int
    content: str
    is_active: bool
    created_at: datetime

class ScheduledTask(BaseModel):
    id: int
    asset_id: int
    prompt_id: int
    cycle: Cycle
    cron_expression: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

class TradeAnalysis(BaseModel):
    id: int
    asset: str
    timestamp: datetime
    prompt_id: Optional[int] = None
    cycle: Cycle
    trend: Optional[str] = None
    confidence: Optional[float] = None
    conclusion: Optional[str] = None
    extra_info: Optional[dict] = None

class TradePlan(BaseModel):
    id: int
    asset: str
    cycle: Cycle
    created_at: datetime
    direction: Direction
    confidence: Optional[float] = None
    entry_price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit_1: Optional[float] = None
    take_profit_2: Optional[float] = None
    risk_reward_ratio: Optional[str] = None
    analysis_id: Optional[int] = None
    prompt_id: Optional[int] = None
    extra_info: Optional[dict] = None
    status: PlanStatus

class Dictionary(BaseModel):
    id: int
    category: str
    code: str
    label: str
    description: Optional[str] = None

# --- Database Connection ---

def init_connection_pool():
    """初始化 MySQL 数据库连接池。"""
    global connection_pool
    try:
        db_url = settings.DATABASE_URL
        if not db_url or not db_url.startswith("mysql"):
            logger.error("DATABASE_URL 未配置或不是有效的 MySQL URL。")
            return

        parsed_url = urlparse(db_url)
        db_config = {
            'host': parsed_url.hostname,
            'port': parsed_url.port,
            'user': parsed_url.username,
            'password': parsed_url.password,
            'database': parsed_url.path.lstrip('/')
        }

        connection_pool = pooling.MySQLConnectionPool(
            pool_name="mysql_pool",
            pool_size=10,
            **db_config
        )
        logger.info(f"MySQL connection pool '{connection_pool.pool_name}' created successfully.")

    except mysql.connector.Error as e:
        logger.error(f"Failed to create MySQL connection pool: {e}", exc_info=True)
        connection_pool = None

def close_connection_pool():
    """关闭数据库连接池。"""
    global connection_pool
    if connection_pool:
        logger.info("MySQL connection pool will be managed by the connector's lifecycle.")
        connection_pool = None

def get_db_connection():
    """从连接池获取一个数据库连接。"""
    if connection_pool is None:
        logger.error("Connection pool is not initialized.")
        return None
    try:
        return connection_pool.get_connection()
    except mysql.connector.Error as e:
        logger.error(f"Failed to get connection from pool: {e}", exc_info=True)
        return None

def init_db():
    """
    初始化数据库，确保 schema.sql 中定义的所有表都存在。
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Could not get database connection to initialize.")
            return

        cursor = conn.cursor()

        logger.info("Ensuring database schema is up to date...")
        with open('schema.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()

        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
        
        conn.commit()
        logger.info("Database schema checked/created successfully.")

    except mysql.connector.Error as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
