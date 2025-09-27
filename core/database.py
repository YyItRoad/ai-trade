import logging
import mysql.connector
from mysql.connector import pooling
from urllib.parse import urlparse
from core.config import settings

logger = logging.getLogger(__name__)

connection_pool = None

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
            pool_size=10,  # 可根据应用负载调整
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
        # mysql-connector-python 的连接池没有显式的 close 方法
        # 它会在程序退出时自动管理
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
    此函数是幂等的：它只会创建尚不存在的表。
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Could not get database connection to initialize.")
            return

        cursor = conn.cursor()

        # 从 schema.sql 读取并执行创建语句
        logger.info("Ensuring database schema is up to date...")
        with open('schema.sql', 'r', encoding='utf-8') as f:
            sql_script = f.read()

        # 逐条执行SQL语句 (MySQL原生支持)
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
            conn.close() # 将连接归还到池中
