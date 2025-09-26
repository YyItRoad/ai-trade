import logging
import mysql.connector
from urllib.parse import urlparse
from core.config import settings

logger = logging.getLogger(__name__)

def get_db_connection():
    """根据 DATABASE_URL 建立并返回数据库连接。"""
    try:
        db_url = settings.DATABASE_URL
        parsed_url = urlparse(db_url)

        if parsed_url.scheme == "mysql":
            conn = mysql.connector.connect(
                host=parsed_url.hostname,
                port=parsed_url.port,
                user=parsed_url.username,
                password=parsed_url.password,
                database=parsed_url.path.lstrip('/')
            )
            logger.info(f"Successfully connected to MySQL database at: {parsed_url.hostname}")
            return conn
        else:
            logger.error(f"Unsupported database scheme: {parsed_url.scheme}. Only 'mysql' is supported.")
            return None
            
    except mysql.connector.Error as e:
        logger.error(f"Database connection failed to '{settings.DATABASE_URL}': {e}", exc_info=True)
        return None

def init_db():
    """
    通过首先删除现有表，然后从 schema.sql 创建新表来初始化数据库。
    """
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            logger.error("Could not get database connection to initialize.")
            return

        cursor = conn.cursor() # type: ignore

        # 1. 先删除旧表以确保一个干净的状态
        logger.info("Dropping existing tables...")
        cursor.execute("DROP TABLE IF EXISTS trade_analysis;")
        cursor.execute("DROP TABLE IF EXISTS assets;")
        logger.info("Tables dropped successfully.")

        # 2. 从 schema.sql 读取并执行创建语句
        logger.info("Creating new tables from schema.sql...")
        with open('schema.sql', 'r') as f:
            sql_script = f.read()
        
        # 逐条执行SQL语句
        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
        
        conn.commit()
        logger.info("Database schema created successfully.")

    except mysql.connector.Error as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
