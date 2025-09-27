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

        # 移除 dictionary=True 以兼容 sqlite3
        # cursor = conn.cursor(dictionary=True) # type: ignore
        cursor = conn.cursor()

        # --- 动态构建查询 ---
        # 使用 LEFT JOIN 关联 prompts 表
        count_query = "SELECT COUNT(*) as total FROM trade_analysis ta"
        data_query = """
            SELECT
                ta.id, ta.asset, ta.timestamp, ta.conclusion, ta.direction,
                ta.confidence, ta.risk_reward_ratio, ta.entry_point, ta.stop_loss,
                ta.take_profit_1, ta.take_profit_2, ta.analysis_summary,
                ta.wave_analysis_4h, ta.wave_analysis_1h, ta.wave_analysis_15m,
                ta.rationale, ta.raw_response, ta.prompt_id,
                p.name as prompt_name,
                p.version as prompt_version
            FROM trade_analysis ta
            LEFT JOIN prompts p ON ta.prompt_id = p.id
        """
        
        count_params = []
        data_params = []
        
        # 处理筛选条件
        where_clauses = []
        if asset:
            where_clauses.append("ta.asset = %s")
            count_params.append(asset)
            data_params.append(asset)

        if where_clauses:
            where_str = " WHERE " + " AND ".join(where_clauses)
            count_query += where_str
            data_query += where_str

        # 计算总记录数
        cursor.execute(count_query, tuple(count_params))
        count_result = cursor.fetchone()
        # total_records = int(count_result['total']) if count_result else 0 # type: ignore
        total_records = int(count_result[0]) if count_result else 0 # type: ignore
        total_pages = math.ceil(total_records / size) if total_records > 0 else 0

        results = []
        if total_records > 0:
            # 添加排序和分页
            # 兼容 MySQL 和 SQLite 的占位符
            placeholder = "?" if conn.__class__.__module__ == "sqlite3" else "%s"
            
            # 动态构建 LIMIT 和 OFFSET
            if conn.__class__.__module__ == "sqlite3":
                 data_query += f" ORDER BY timestamp DESC LIMIT {placeholder} OFFSET {placeholder}"
            else: # mysql
                 data_query += f" ORDER BY timestamp DESC LIMIT {placeholder} OFFSET {placeholder}"

            offset = (page - 1) * size
            data_params.extend([size, offset])
            
            cursor.execute(data_query, tuple(data_params))
            
            # 手动将元组转换为字典
            if not cursor.description:
                logger.warning("分析历史查询未返回任何列信息。")
                # 在这种情况下，results 保持为空列表，是正确的行为
            else:
                column_names = [desc[0] for desc in cursor.description]
                raw_results = cursor.fetchall()
                results = [dict(zip(column_names, row)) for row in raw_results]

            # 序列化 datetime
            for row in results:
                for key, value in row.items():
                    if isinstance(value, datetime.datetime):
                        row[key] = value.isoformat()

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