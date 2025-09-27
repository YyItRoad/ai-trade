import logging
from typing import List, Optional
from enum import Enum

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator
from croniter import croniter

from core.database import get_db_connection
from core.scheduler import update_asset_schedule, remove_asset_schedule

router = APIRouter()
logger = logging.getLogger(__name__)

# --- 常量 ---
TYPE_MAPPING = {"SPOT": 0, "USD_M": 1, "COIN_M": 2}

# --- Pydantic 模型与枚举 ---

class Asset(BaseModel):
    id: int
    symbol: str
    type: int # 0: 现货, 1: U本位, 2: 币本位
    schedule_cron: Optional[str] = None

class CreateAssetRequest(BaseModel):
    symbol: str = Field(..., description="例如: BTCUSDT")
    type: int = Field(..., description="0: 现货, 1: U本位, 2: 币本位")

class UpdateScheduleRequest(BaseModel):
    schedule_cron: Optional[str] = Field(None, description="Cron表达式, 例如 '0 * * * *'。null 表示禁用")

    @field_validator('schedule_cron')
    @classmethod
    def validate_cron_string(cls, v: Optional[str]) -> Optional[str]:
        if v is not None and v.strip() and not croniter.is_valid(v):
            raise ValueError("无效的 Cron 字符串格式")
        # 允许空字符串被视为空值以禁用定时任务
        if v is not None and not v.strip():
            return None
        return v

# --- API 端点 ---

@router.get("/assets", response_model=List[Asset])
def get_all_assets():
    """获取数据库中所有已配置的资产列表"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败。")
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, symbol, `type`, schedule_cron FROM assets ORDER BY symbol ASC")
        assets = cursor.fetchall()
        return assets # type: ignore
    except Exception as e:
        logger.error(f"获取资产时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取资产失败。")
    finally:
        if conn:
            conn.close()

@router.post("/assets", response_model=Asset)
def add_asset(asset_data: CreateAssetRequest):
    """添加一个新的资产到数据库 (默认禁用调度)"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败。")
            
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute(
            "SELECT id FROM assets WHERE symbol = %s AND `type` = %s",
            (asset_data.symbol, asset_data.type)
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=409,
                detail=f"类型为 '{asset_data.type}' 的资产 '{asset_data.symbol}' 已存在。"
            )

        sql = "INSERT INTO assets (symbol, `type`) VALUES (%s, %s)"
        params = (asset_data.symbol, asset_data.type)
        cursor.execute(sql, params)
        conn.commit()
        
        new_asset_id = cursor.lastrowid
        
        if new_asset_id:
            # 从数据库重新获取新创建的资产以确保数据完整性
            cursor.execute("SELECT id, symbol, `type`, schedule_cron FROM assets WHERE id = %s", (new_asset_id,))
            new_asset = cursor.fetchone()
            if new_asset:
                return new_asset # type: ignore

        # 如果重新获取失败，则回退
        raise HTTPException(status_code=500, detail="未能检索到新创建的资产。")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"添加资产 '{asset_data.symbol}' 时出错: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail=f"添加资产失败。")
    finally:
        if conn:
            conn.close()

@router.put("/assets/{asset_id}/schedule", response_model=Asset)
def update_asset_schedule_endpoint(asset_id: int, schedule_data: UpdateScheduleRequest):
    """更新指定资产的调度周期"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败。")
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("UPDATE assets SET schedule_cron = %s WHERE id = %s", (schedule_data.schedule_cron, asset_id))
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail=f"未找到 ID 为 {asset_id} 的资产。")
        conn.commit()
        
        cursor.execute("SELECT id, symbol, `type`, schedule_cron FROM assets WHERE id = %s", (asset_id,))
        updated_asset = cursor.fetchone()
        
        if updated_asset:
            update_asset_schedule(
                symbol=str(updated_asset['symbol']), # type: ignore
                cron_string=updated_asset['schedule_cron'], # type: ignore
                asset_type=int(updated_asset['type']) # type: ignore
            )
            return updated_asset # type: ignore
        else:
            raise HTTPException(status_code=404, detail="未能检索到更新后的资产详情。")

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"为资产 ID {asset_id} 更新定时任务时出错: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="更新定时任务失败。")
    finally:
        if conn:
            conn.close()

@router.delete("/assets/{asset_id}", status_code=204)
def delete_asset(asset_id: int):
    """从数据库中删除一个资产"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败。")
        
        cursor = conn.cursor(dictionary=True)
        
        cursor.execute("SELECT symbol FROM assets WHERE id = %s", (asset_id,))
        asset = cursor.fetchone()
        if not asset:
            raise HTTPException(status_code=404, detail=f"未找到 ID 为 {asset_id} 的资产。")
        
        symbol_to_delete = asset['symbol'] # type: ignore
        
        cursor.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
        conn.commit()
        
        remove_asset_schedule(symbol_to_delete) # type: ignore
            
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"删除资产 ID {asset_id} 时出错: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="删除资产失败。")
    finally:
        if conn:
            conn.close()