from fastapi import APIRouter, HTTPException, status
from typing import List, Dict
from models.prompt import Prompt, PromptCreate
from core.database import get_db_connection
import logging
import datetime

router = APIRouter()
logger = logging.getLogger(__name__)

# ==============================================================================
# 数据访问和转换层 (DAL)
# ==============================================================================

def _get_prompts_from_db(conn) -> List[Prompt]:
    """从数据库获取所有 prompts 并转换为 Prompt 对象列表。"""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, version, content, is_active, created_at FROM prompts ORDER BY name, version DESC")
    rows = cursor.fetchall()
    # Pydantic 将自动处理类型转换
    return [Prompt(**row) for row in rows] # type: ignore

def _create_prompt_in_db(conn, prompt_data: PromptCreate) -> Prompt:
    """在数据库中创建新的 prompt 并返回完整的 Prompt 对象。"""
    cursor = conn.cursor(dictionary=True)

    # 1. 获取最新版本号
    cursor.execute("SELECT MAX(version) as max_version FROM prompts WHERE name = %s", (prompt_data.name,))
    result = cursor.fetchone()
    latest_version = result['max_version'] if result and result['max_version'] is not None else 0 # type: ignore
    new_version = latest_version + 1

    # 2. 插入新记录
    sql = """
        INSERT INTO prompts (name, version, content, is_active)
        VALUES (%s, %s, %s, %s)
    """
    cursor.execute(sql, (prompt_data.name, new_version, prompt_data.content, False))
    
    new_id = cursor.lastrowid
    conn.commit()

    # 3. 获取并返回新创建的对象
    cursor.execute("SELECT id, name, version, content, is_active, created_at FROM prompts WHERE id = %s", (new_id,))
    new_row = cursor.fetchone()
    
    if not new_row:
        raise HTTPException(status_code=500, detail="Failed to retrieve newly created prompt.")
        
    return Prompt(**new_row) # type: ignore

# ==============================================================================
# API 路由层
# ==============================================================================

def _get_prompt_by_id_from_db(conn, prompt_id: int) -> Prompt | None:
    """通过 ID 从数据库获取单个 prompt 并转换为 Prompt 对象。"""
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, name, version, content, is_active, created_at FROM prompts WHERE id = %s", (prompt_id,))
    row = cursor.fetchone()
    
    if not row:
        return None
        
    return Prompt(**row) # type: ignore

@router.get("/prompts/{prompt_id}", response_model=Prompt)
def get_prompt_by_id(prompt_id: int):
    """获取指定ID的提示词的详细信息。"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        prompt = _get_prompt_by_id_from_db(conn, prompt_id)
        
        if prompt is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
            
        return prompt
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error fetching prompt with id {prompt_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.close()

@router.get("/prompts", response_model=Dict[str, List[Prompt]])
def get_all_prompts():
    """获取所有提示词，并按名称进行分组。"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        prompts_list = _get_prompts_from_db(conn)
        
        grouped_prompts: Dict[str, List[Prompt]] = {}
        for prompt in prompts_list:
            if prompt.name not in grouped_prompts:
                grouped_prompts[prompt.name] = []
            grouped_prompts[prompt.name].append(prompt)
            
        return grouped_prompts
    except Exception as e:
        logger.error(f"Error fetching prompts: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.close()

@router.post("/prompts", response_model=Prompt, status_code=status.HTTP_201_CREATED)
def create_prompt(prompt: PromptCreate):
    """创建一个新的提示词版本。"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        new_prompt = _create_prompt_in_db(conn, prompt)
        return new_prompt
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error creating prompt: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.close()


def _activate_prompt_in_db(conn, prompt_id: int) -> Prompt:
    """在数据库中激活一个 prompt 版本, 并取消激活所有其他的版本。"""
    cursor = conn.cursor(dictionary=True)

    # 1. 检查 prompt 是否存在
    cursor.execute("SELECT id FROM prompts WHERE id = %s", (prompt_id,))
    if not cursor.fetchone():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")

    # 2. 在一个事务中更新
    # a. 取消激活所有的 prompt
    cursor.execute("UPDATE prompts SET is_active = FALSE")
    # b. 激活指定的 prompt
    cursor.execute("UPDATE prompts SET is_active = TRUE WHERE id = %s", (prompt_id,))
    
    conn.commit()

    # 3. 获取并返回更新后的对象
    cursor.execute("SELECT id, name, version, content, is_active, created_at FROM prompts WHERE id = %s", (prompt_id,))
    updated_row = cursor.fetchone()

    if not updated_row:
        raise HTTPException(status_code=500, detail="Failed to retrieve the activated prompt.")

    return Prompt(**updated_row) # type: ignore

@router.post("/prompts/{prompt_id}/activate", response_model=Prompt)
def activate_prompt(prompt_id: int):
    """将指定的提示词版本设置为激活状态。"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        activated_prompt = _activate_prompt_in_db(conn, prompt_id)
        return activated_prompt
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error activating prompt {prompt_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.close()

def _delete_prompt_from_db(conn, prompt_id: int) -> bool:
    """从数据库中删除指定 ID 的 prompt。如果删除成功则返回 True。"""
    cursor = conn.cursor(dictionary=True)
    
    # 检查要删除的 prompt 是否是激活状态
    cursor.execute("SELECT is_active FROM prompts WHERE id = %s", (prompt_id,))
    result = cursor.fetchone()
    if result and result['is_active']: # type: ignore
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete an active prompt. Please activate another version first."
        )

    cursor.execute("DELETE FROM prompts WHERE id = %s", (prompt_id,))
    conn.commit()
    
    return cursor.rowcount > 0

@router.delete("/prompts/{prompt_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_prompt(prompt_id: int):
    """删除一个指定的提示词版本。"""
    conn = None
    try:
        conn = get_db_connection()
        if conn is None:
            raise HTTPException(status_code=500, detail="Database connection failed")
        
        success = _delete_prompt_from_db(conn, prompt_id)
        
        if not success:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Prompt not found")
            
        return
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        if conn:
            conn.rollback()
        logger.error(f"Error deleting prompt {prompt_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")
    finally:
        if conn:
            conn.close()
