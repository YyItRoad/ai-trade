import logging
import mysql.connector
import sqlite3
import re
from urllib.parse import urlparse
from core.config import settings

logger = logging.getLogger(__name__)

def get_db_connection():
    """根据 DATABASE_URL 建立并返回数据库连接, 支持 mysql 和 sqlite。"""
    try:
        db_url = settings.DATABASE_URL
        if not db_url:
            logger.error("DATABASE_URL not configured.")
            return None
        
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
        elif parsed_url.scheme == "sqlite":
            db_path = parsed_url.path.lstrip('/')
            conn = sqlite3.connect(db_path)
            logger.info(f"Successfully connected to SQLite database at: {db_path}")
            return conn
        else:
            logger.error(f"Unsupported database scheme: {parsed_url.scheme}. Only 'mysql' and 'sqlite' are supported.")
            return None
            
    except (mysql.connector.Error, sqlite3.Error) as e:
        logger.error(f"Database connection failed to '{settings.DATABASE_URL}': {e}", exc_info=True)
        return None

def init_db():
    """
    初始化数据库，确保 schema.sql 中定义的所有表都存在。
    此函数是幂等的：它只会创建尚不存在的表。
    该函数会适配 schema.sql 以兼容 MySQL 和 SQLite。
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
        
        # 如果是 SQLite，需要对 SQL 脚本进行一些转换以确保兼容性
        if settings.DATABASE_URL and settings.DATABASE_URL.startswith("sqlite"):
            logger.info("Adapting schema for SQLite...")
            # 移除所有 COMMENT 子句 (包括列和表)
            sql_script = re.sub(r"COMMENT\s*'.*?'", "", sql_script)
            # 将 AUTO_INCREMENT 替换为 AUTOINCREMENT
            sql_script = re.sub(r"AUTO_INCREMENT", "AUTOINCREMENT", sql_script, flags=re.IGNORECASE)
            # 转换 UNIQUE KEY 语法
            sql_script = re.sub(r"UNIQUE KEY `.*?` \((.*?)\)", r"UNIQUE (\1)", sql_script)
            # SQLite 没有 JSON 类型, 用 TEXT 代替
            sql_script = re.sub(r"\bJSON\b", "TEXT", sql_script, flags=re.IGNORECASE)
            # SQLite 没有 DATETIME 类型, 用 TEXT 代替
            sql_script = re.sub(r"\bDATETIME\b", "TEXT", sql_script, flags=re.IGNORECASE)
            # SQLite 没有 DECIMAL 类型, 用 REAL 代替
            sql_script = re.sub(r"DECIMAL\(\d+,\s*\d+\)", "REAL", sql_script, flags=re.IGNORECASE)

        # 逐条执行SQL语句
        for statement in sql_script.split(';'):
            if statement.strip():
                cursor.execute(statement)
        
        conn.commit()
        logger.info("Database schema created successfully.")

    except (mysql.connector.Error, sqlite3.Error) as e:
        logger.error(f"Failed to initialize database: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()
