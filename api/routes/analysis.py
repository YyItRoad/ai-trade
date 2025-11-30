import logging
import math
import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Query
from core.database import get_db_connection, TradeAnalysis

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/asset-symbols", response_model=List[str], summary="获取所有资产符号")
def get_all_assets_symbols() -> List[str]:
    """获取数据库中所有资产的符号列表，用于前端下拉框"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败。")
        
        cursor = conn.cursor()
        cursor.execute("SELECT symbol FROM assets ORDER BY symbol ASC")
        assets = [item[0] for item in cursor.fetchall()]
        return assets
    except Exception as e:
        logger.error(f"获取资产符号时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取资产符号失败。")
    finally:
        if conn:
            conn.close()

@router.get("/analysis", summary="获取行情分析结果列表")
def get_analysis_history(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页大小"),
    asset: str = Query(None, description="按资产符号筛选 (例如: BTCUSDT)")
) -> Dict[str, Any]:
    """
    获取行情分析历史记录，支持分页和按资产筛选。
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败。")

        cursor = conn.cursor(dictionary=True)

        # --- 动态构建查询 ---
        count_query = "SELECT COUNT(*) as total FROM trade_analysis"
        data_query = "SELECT * FROM trade_analysis"
        
        params = []
        
        if asset:
            data_query += " WHERE asset = %s"
            count_query += " WHERE asset = %s"
            params.append(asset)

        # 计算总记录数
        cursor.execute(count_query, tuple(params))
        total_records = cursor.fetchone()['total']
        total_pages = math.ceil(total_records / page_size)

        # 获取分页数据
        data_query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
        offset = (page - 1) * page_size
        params.extend([page_size, offset])
        
        cursor.execute(data_query, tuple(params))
        results = cursor.fetchall()

        # 序列化 datetime
        for row in results:
            if isinstance(row.get('timestamp'), datetime.datetime):
                row['timestamp'] = row['timestamp'].isoformat()

        return {
            "page": page,
            "page_size": page_size,
            "total_pages": total_pages,
            "total_records": total_records,
            "data": results
        }

    except Exception as e:
        logger.error(f"获取分析历史记录时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="发生内部错误。")
    finally:
        if conn:
            conn.close()