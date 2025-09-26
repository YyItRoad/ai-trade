import logging
import math
import datetime
from typing import List, Dict, Any

from fastapi import APIRouter, HTTPException, Query, BackgroundTasks

from core.database import get_db_connection
from core.config import settings
from services.analysis_service import run_analysis_task
from models.request import TriggerRequest

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/asset-symbols")
def get_all_assets_symbols() -> List[str]:
    """获取数据库中所有资产的符号列表，用于前端下拉框"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败。")
        
        cursor = conn.cursor() # type: ignore
        cursor.execute("SELECT symbol FROM assets ORDER BY symbol ASC")
        # cursor.fetchall() 的结果将是一个元组列表, 例如 [('BTCUSDT',), ('ETHUSDT',)]
        # 我们需要将其扁平化为一个简单的字符串列表。
        assets = [item[0] for item in cursor.fetchall()] # type: ignore
        return assets # type: ignore
    except Exception as e:
        logger.error(f"获取资产符号时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取资产符号失败。")
    finally:
        if conn:
            conn.close()

@router.get("/analysis-history")
def get_analysis_history(
    page: int = Query(1, ge=1, description="页码"),
    size: int = Query(20, ge=1, le=100, description="每页大小"),
    asset: str | None = Query(None, description="按资产符号筛选 (例如: BTCUSDT)")
) -> Dict[str, Any]:
    """
    获取分析历史记录，支持分页和按资产筛选。
    """
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败。")

        cursor = conn.cursor(dictionary=True) # type: ignore

        # --- 动态构建查询 ---
        count_query = "SELECT COUNT(*) as total FROM trade_analysis"
        data_query = "SELECT * FROM trade_analysis"
        
        count_params = []
        data_params = []
        if asset:
            count_query += " WHERE asset = %s"
            data_query += " WHERE asset = %s"
            count_params.append(asset)
            data_params.append(asset)

        # 计算总记录数
        cursor.execute(count_query, tuple(count_params))
        count_result = cursor.fetchone()
        total_records = int(count_result['total']) if count_result else 0 # type: ignore
        total_pages = math.ceil(total_records / size) if total_records > 0 else 0

        results = []
        if total_records > 0:
            # 添加排序和分页
            data_query += " ORDER BY timestamp DESC LIMIT %s OFFSET %s"
            offset = (page - 1) * size
            data_params.extend([size, offset])
            
            cursor.execute(data_query, tuple(data_params))
            results = cursor.fetchall()
            
            # 序列化 datetime
            for row in results:
                for key, value in row.items(): # type: ignore
                    if isinstance(value, datetime.datetime):
                        row[key] = value.isoformat() # type: ignore

        return {
            "page": page,
            "size": size,
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

@router.post("/trigger-analysis/{asset_type}/{symbol}")
async def trigger_analysis_for_symbol(asset_type: str, symbol: str, background_tasks: BackgroundTasks):
    """
    通过 URL 路径手动触发特定资产的分析任务。
    该任务将在后台运行。
    """
    asset_symbol_to_check = symbol.upper()
    asset_type_str = asset_type.upper()
    
    type_mapping = {"SPOT": 0, "USD_M": 1, "COIN_M": 2}
    asset_type_int = type_mapping.get(asset_type_str)

    if asset_type_int is None:
        raise HTTPException(
            status_code=400,
            detail=f"无效的资产类型 '{asset_type}'。必须是 {list(type_mapping.keys())} 中的一个。"
        )

    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败。")
        
        cursor = conn.cursor() # type: ignore
        cursor.execute(
            "SELECT COUNT(*) FROM assets WHERE symbol = %s AND `type` = %s",
            (asset_symbol_to_check, asset_type_int)
        )
        count = cursor.fetchone()[0] # type: ignore
        
        if count == 0:
            raise HTTPException(
                status_code=404,
                detail=f"未找到类型为 '{asset_type_str}' 的资产 '{asset_symbol_to_check}'。"
            )
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"验证资产 '{asset_symbol_to_check}' 时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="验证资产失败。")
    finally:
        if conn:
            conn.close()

    logger.info(f"通过 API 为 {asset_symbol_to_check} (类型: {asset_type_str}/{asset_type_int}) 手动触发了分析任务。")
    background_tasks.add_task(
        run_analysis_task,
        symbol=asset_symbol_to_check,
        asset_type=asset_type_int
    )
    return {"message": f"资产 {asset_symbol_to_check} 的分析任务已触发，正在后台运行。"}