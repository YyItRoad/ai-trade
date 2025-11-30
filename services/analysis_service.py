import logging
import json
import os
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

from core.market_data import fetch_all_kline_data_concurrently
from core.ai_client import get_ai_response, _extract_json_from_response
from core.database import get_db_connection

logger = logging.getLogger(__name__)

ASSET_TYPE_MAP = {
    0: "现货 (Spot)",
    1: "U本位合约 (USD-M Futures)",
    2: "币本位合约 (COIN-M Futures)"
}

def _setup_task_logger(symbol: str, cycle: str):
    """为单个分析任务设置专用的文件日志记录器。"""
    date_str = datetime.now().strftime("%Y-%m-%d")
    log_dir = f"logs/tasks-{date_str}"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{symbol}_{cycle}_{timestamp}.log")
    
    task_logger_name = f"task.{symbol}.{cycle}.{timestamp}"
    task_logger = logging.getLogger(task_logger_name)
    task_logger.setLevel(logging.INFO)
    task_logger.propagate = False
    
    handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    task_logger.addHandler(handler)
    
    return task_logger, handler

def _get_prompt_from_db(prompt_id: int, task_logger) -> Tuple[Optional[str], Optional[str]]:
    """根据 prompt_id 从数据库获取指定的提示词内容。"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            task_logger.error("未能获取数据库连接以加载提示词。")
            return None, None
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT content FROM prompts WHERE id = %s", (prompt_id,))
        prompt_row = cursor.fetchone()
        
        if not prompt_row:
            task_logger.error(f"数据库中未找到 ID 为 {prompt_id} 的提示词。")
            return None, None

        content = str(prompt_row['content'])
            
        parts = content.split('---JSON---', 1)
        system_prompt = parts[0].strip() if parts else content.strip()
        json_structure = parts[1].strip() if len(parts) > 1 else ""

        return system_prompt, json_structure

    except Exception as e:
        task_logger.error(f"从数据库加载提示词 ID {prompt_id} 时出错: {e}", exc_info=True)
        return None, None
    finally:
        if conn:
            conn.close()

def _save_results_to_db(data: Dict[str, Any], symbol: str, cycle: str, prompt_id: int, task_logger):
    """将AI分析结果分别保存到 trade_analysis 和 trade_plan 表中。"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            task_logger.error("未能获取数据库连接以保存分析。")
            return

        cursor = conn.cursor()
        
        # 1. 保存到 trade_analysis 表
        analysis_data = data.get('analysis', {})
        analysis_sql = """
        INSERT INTO trade_analysis (asset, timestamp, prompt_id, cycle, trend, confidence, conclusion, extra_info)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
        analysis_params = (
            symbol,
            datetime.now(),
            prompt_id,
            cycle,
            analysis_data.get('trend'),
            analysis_data.get('confidence'),
            analysis_data.get('conclusion'),
            json.dumps(data) # 将完整原始响应存入 extra_info
        )
        cursor.execute(analysis_sql, analysis_params)
        analysis_id = cursor.lastrowid
        task_logger.info(f"成功将分析摘要保存到 trade_analysis，获得 ID: {analysis_id}")

        # 2. 保存到 trade_plan 表
        trade_plan_data = data.get('tradePlan', {})
        if not trade_plan_data:
            task_logger.warning("AI响应中未包含 tradePlan 部分，不创建交易计划。")
            conn.commit()
            return

        plan_sql = """
        INSERT INTO trade_plan (
            asset, cycle, created_at, direction, confidence, entry_price, 
            stop_loss, take_profit_1, take_profit_2, risk_reward_ratio, 
            analysis_id, prompt_id, extra_info, status
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        plan_params = (
            symbol,
            cycle,
            datetime.now(),
            trade_plan_data.get('direction'),
            trade_plan_data.get('confidence'),
            trade_plan_data.get('entry_price'),
            trade_plan_data.get('stop_loss'),
            trade_plan_data.get('take_profit_1'),
            trade_plan_data.get('take_profit_2'),
            trade_plan_data.get('risk_reward_ratio'),
            analysis_id,
            prompt_id,
            json.dumps(trade_plan_data.get('extra_info', {})),
            'ACTIVE' # 默认状态
        )
        cursor.execute(plan_sql, plan_params)
        task_logger.info(f"成功将交易计划关联到 analysis_id {analysis_id} 并保存到 trade_plan。")

        conn.commit()

    except Exception as e:
        task_logger.error(f"保存分析结果时发生数据库错误: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

async def run_analysis_task(asset_id: int, prompt_id: int, cycle: str, symbol: str, asset_type: int):
    """执行单次分析任务的完整流程。"""
    task_logger, handler = _setup_task_logger(symbol, cycle)
    try:
        task_logger.info(f"启动分析任务: asset_id={asset_id}, prompt_id={prompt_id}, symbol={symbol}, cycle={cycle}")
        
        # 1. 从数据库加载指定的提示词
        system_prompt, json_structure = _get_prompt_from_db(prompt_id, task_logger)
        if not system_prompt:
            task_logger.error(f"未能从数据库加载 ID 为 {prompt_id} 的提示词，任务中止。")
            return

        # 2. 获取K线数据
        kline_data = fetch_all_kline_data_concurrently(symbol=symbol, asset_type=asset_type)
        if not any(kline_data.values()):
            task_logger.warning(f"未能为 {symbol} 获取到K线数据。正在中止任务。")
            return

        # 3. 构建Prompt并调用AI
        asset_type_str = ASSET_TYPE_MAP.get(asset_type, "未知类型")
        
        full_system_prompt = (
            f"{system_prompt.format(symbol=symbol, asset_type=asset_type_str, cycle=cycle)}\n\n"
            f"请严格按照以下JSON结构返回分析结果:\n"
            f"{json_structure}"
        )
        
        kline_data_str = json.dumps(kline_data, indent=2)
        user_prompt = (
            f"以下是最新的K线数据:\n"
            f"```json\n{kline_data_str}\n```"
        )
        
        task_logger.info("正在向AI模型发送请求...")
        ai_response_str = await get_ai_response(
            system_prompt=full_system_prompt,
            user_prompt=user_prompt
        )
        task_logger.info(f"原始AI响应:\n---\n{ai_response_str}\n---")

        if not ai_response_str or "错误：" in ai_response_str:
            task_logger.error(f"未能从AI获取有效响应: {ai_response_str}")
            return

        # 4. 解析并存储
        json_part = _extract_json_from_response(ai_response_str)
        if not json_part:
            task_logger.error(f"无法从AI响应中提取JSON: {ai_response_str}")
            return
            
        try:
            analysis_result = json.loads(json_part)
            _save_results_to_db(analysis_result, symbol, cycle, prompt_id, task_logger)
            task_logger.info(f"为 {symbol} ({cycle}) 的分析任务已成功完成。")
        except json.JSONDecodeError:
            task_logger.error(f"从AI响应解码JSON失败: {json_part}")
    finally:
        handler.close()
        task_logger.removeHandler(handler)