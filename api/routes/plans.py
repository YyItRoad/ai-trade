from fastapi import APIRouter, HTTPException, Query
from typing import List
import logging

from core.database import get_db_connection, TradePlan
from models.request import UpdatePlanStatusRequest

router = APIRouter()
logger = logging.getLogger(__name__)

@router.get("/plans", response_model=List[TradePlan], summary="获取交易计划列表")
def get_all_plans(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量")
):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        cursor = conn.cursor(dictionary=True)
        offset = (page - 1) * page_size
        query = "SELECT * FROM trade_plan ORDER BY created_at DESC LIMIT %s OFFSET %s"
        cursor.execute(query, (page_size, offset))
        plans = cursor.fetchall()
        return plans
    except Exception as e:
        logger.error(f"获取交易计划列表时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch trade plans")
    finally:
        if conn:
            conn.close()

@router.put("/plans/{plan_id}/status", summary="更新指定交易计划的状态")
def update_plan_status(plan_id: int, status_data: UpdatePlanStatusRequest):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
            
        cursor = conn.cursor()
        sql = "UPDATE trade_plan SET status = %s WHERE id = %s"
        params = (status_data.status.value, plan_id)
        cursor.execute(sql, params)
        conn.commit()
        
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Trade plan not found")
            
        logger.info(f"交易计划 {plan_id} 状态更新为: {status_data.status.value}")
        return {"message": f"Trade plan {plan_id} status updated successfully"}
    except Exception as e:
        logger.error(f"更新交易计划 {plan_id} 状态时出错: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Failed to update trade plan status")
    finally:
        if conn:
            conn.close()