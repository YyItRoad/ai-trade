from fastapi import APIRouter, HTTPException
from typing import List
import logging

from core.database import get_db_connection, Dictionary

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/dictionary", response_model=List[Dictionary], summary="获取所有字典映射数据")
def get_dictionary_data():
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, category, code, label, description FROM dictionary")
        dictionary_entries = cursor.fetchall()
        return dictionary_entries
    except Exception as e:
        logger.error(f"获取字典数据时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch dictionary data")
    finally:
        if conn:
            conn.close()