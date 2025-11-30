import logging
from typing import List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from core.database import get_db_connection

router = APIRouter()
logger = logging.getLogger(__name__)

# --- Pydantic 模型 ---

class Asset(BaseModel):
    id: int
    symbol: str
    type: int # 0: 现货, 1: U本位, 2: 币本位

class CreateAssetRequest(BaseModel):
    symbol: str = Field(..., description="例如: BTCUSDT")
    type: int = Field(..., description="0: 现货, 1: U本位, 2: 币本位")

class UpdateAssetRequest(BaseModel):
    symbol: str = Field(..., description="例如: BTCUSDT")
    type: int = Field(..., description="0: 现货, 1: U本位, 2: 币本位")

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
        cursor.execute("SELECT id, symbol, `type` FROM assets ORDER BY symbol ASC")
        assets = cursor.fetchall()
        return assets
    except Exception as e:
        logger.error(f"获取资产时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="获取资产失败。")
    finally:
        if conn:
            conn.close()

@router.post("/assets", response_model=Asset)
def add_asset(asset_data: CreateAssetRequest):
    """添加一个新的资产到数据库"""
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
            cursor.execute("SELECT id, symbol, `type` FROM assets WHERE id = %s", (new_asset_id,))
            new_asset = cursor.fetchone()
            if new_asset:
                return new_asset
        
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

@router.put("/assets/{asset_id}", response_model=Asset)
def update_asset(asset_id: int, asset_data: UpdateAssetRequest):
    """更新数据库中一个资产的信息"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="数据库连接失败。")
        
        cursor = conn.cursor(dictionary=True)
        
        # 检查资产是否存在
        cursor.execute("SELECT id FROM assets WHERE id = %s", (asset_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"未找到 ID 为 {asset_id} 的资产。")
        
        # 检查更新后的 symbol 和 type 是否会与其他资产冲突
        cursor.execute(
            "SELECT id FROM assets WHERE symbol = %s AND `type` = %s AND id != %s",
            (asset_data.symbol, asset_data.type, asset_id)
        )
        if cursor.fetchone():
            raise HTTPException(
                status_code=409,
                detail=f"类型为 '{asset_data.type}' 的资产 '{asset_data.symbol}' 已存在于其他记录中。"
            )

        sql = "UPDATE assets SET symbol = %s, `type` = %s WHERE id = %s"
        params = (asset_data.symbol, asset_data.type, asset_id)
        cursor.execute(sql, params)
        conn.commit()
        
        cursor.execute("SELECT id, symbol, `type` FROM assets WHERE id = %s", (asset_id,))
        updated_asset = cursor.fetchone()
        if updated_asset:
            return updated_asset
        
        raise HTTPException(status_code=500, detail="未能检索到更新后的资产。")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新资产 ID {asset_id} 时出错: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="更新资产失败。")
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
        
        cursor = conn.cursor()
        
        # 检查资产是否存在
        cursor.execute("SELECT id FROM assets WHERE id = %s", (asset_id,))
        if not cursor.fetchone():
            raise HTTPException(status_code=404, detail=f"未找到 ID 为 {asset_id} 的资产。")
        
        # 删除与该资产关联的定时任务 (级联删除)
        # 注意：数据库外键需要设置为 ON DELETE CASCADE
        
        cursor.execute("DELETE FROM assets WHERE id = %s", (asset_id,))
        conn.commit()
            
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