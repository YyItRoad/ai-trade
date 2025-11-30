from fastapi import APIRouter, HTTPException, Depends
from typing import List
import logging

from core.database import get_db_connection, ScheduledTask
from core.scheduler import reload_scheduler_tasks
from models.request import CreateTaskRequest

router = APIRouter()
logger = logging.getLogger(__name__)

@router.post("/tasks", summary="创建新的定时任务")
def create_task(task_data: CreateTaskRequest):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        cursor = conn.cursor()
        sql = """
        INSERT INTO scheduled_tasks (asset_id, prompt_id, cycle, cron_expression, is_active)
        VALUES (%s, %s, %s, %s, %s)
        """
        params = (task_data.asset_id, task_data.prompt_id, task_data.cycle, task_data.cron_expression, task_data.is_active)
        cursor.execute(sql, params)
        conn.commit()
        task_id = cursor.lastrowid
        logger.info(f"定时任务创建成功，ID: {task_id}")
        reload_scheduler_tasks() # 重新加载调度器以应用更改
        return {"message": "Task created successfully", "task_id": task_id}
    except Exception as e:
        logger.error(f"创建任务时出错: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Failed to create task")
    finally:
        if conn:
            conn.close()

@router.get("/tasks", response_model=List[ScheduledTask], summary="获取所有定时任务")
def get_all_tasks():
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM scheduled_tasks ORDER BY id DESC")
        tasks = cursor.fetchall()
        return tasks
    except Exception as e:
        logger.error(f"获取任务列表时出错: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to fetch tasks")
    finally:
        if conn:
            conn.close()

@router.put("/tasks/{task_id}", summary="更新指定的定时任务")
def update_task(task_id: int, task_data: CreateTaskRequest):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        cursor = conn.cursor()
        sql = """
        UPDATE scheduled_tasks
        SET asset_id = %s, prompt_id = %s, cycle = %s, cron_expression = %s, is_active = %s
        WHERE id = %s
        """
        params = (task_data.asset_id, task_data.prompt_id, task_data.cycle, task_data.cron_expression, task_data.is_active, task_id)
        cursor.execute(sql, params)
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        logger.info(f"定时任务 {task_id} 更新成功")
        reload_scheduler_tasks()
        return {"message": f"Task {task_id} updated successfully"}
    except Exception as e:
        logger.error(f"更新任务 {task_id} 时出错: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Failed to update task")
    finally:
        if conn:
            conn.close()

@router.delete("/tasks/{task_id}", summary="删除指定的定时任务")
def delete_task(task_id: int):
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            raise HTTPException(status_code=500, detail="Database connection failed")
        cursor = conn.cursor()
        cursor.execute("DELETE FROM scheduled_tasks WHERE id = %s", (task_id,))
        conn.commit()
        if cursor.rowcount == 0:
            raise HTTPException(status_code=404, detail="Task not found")
        logger.info(f"定时任务 {task_id} 删除成功")
        reload_scheduler_tasks()
        return {"message": f"Task {task_id} deleted successfully"}
    except Exception as e:
        logger.error(f"删除任务 {task_id} 时出错: {e}", exc_info=True)
        if conn:
            conn.rollback()
        raise HTTPException(status_code=500, detail="Failed to delete task")
    finally:
        if conn:
            conn.close()