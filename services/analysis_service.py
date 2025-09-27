import logging
import json
import os
from datetime import datetime
from typing import Tuple, Optional, Dict, Any

# 导入项目内的模块
from core.market_data import fetch_all_kline_data_concurrently
from core.ai_client import get_ai_response, _extract_json_from_response
from core.database import get_db_connection

# 全局 logger，用于服务级别的信息
logger = logging.getLogger(__name__)

ASSET_TYPE_MAP = {
    0: "现货 (Spot)",
    1: "U本位合约 (USD-M Futures)",
    2: "币本位合约 (COIN-M Futures)"
}

def _setup_task_logger(symbol: str):
    """为单个分析任务设置专用的文件日志记录器。"""
    # 获取当前日期并格式化为 YYYY-MM-DD
    date_str = datetime.now().strftime("%Y-%m-%d")
    # 构建新的日志目录路径
    log_dir = f"logs/tasks-{date_str}"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{symbol}_{timestamp}.log")
    
    task_logger_name = f"task.{symbol}.{timestamp}"
    task_logger = logging.getLogger(task_logger_name)
    task_logger.setLevel(logging.INFO)
    task_logger.propagate = False
    
    handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    task_logger.addHandler(handler)
    
    return task_logger, handler

def _get_active_prompt_from_db(task_logger) -> Tuple[Optional[int], Optional[str], Optional[str]]:
    """从数据库获取当前激活的分析提示词。"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            task_logger.error("未能获取数据库连接以加载提示词。")
            return None, None, None
        
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, content FROM prompts WHERE is_active = TRUE LIMIT 1")
        prompt_row = cursor.fetchone()
        
        if not prompt_row:
            task_logger.error("数据库中未找到任何激活的提示词。")
            return None, None, None

        prompt_id = int(prompt_row['id']) # type: ignore
        content = str(prompt_row['content']) # type: ignore
            
        # 假设提示词内容包含系统指令和JSON结构，以特定分隔符分开
        parts = content.split('---JSON---', 1)
        if len(parts) == 2:
            system_prompt, json_structure = parts
        else:
            system_prompt = content
            json_structure = ""

        return prompt_id, system_prompt.strip(), json_structure.strip()

    except Exception as e:
        task_logger.error(f"从数据库加载提示词时出错: {e}", exc_info=True)
        return None, None, None
    finally:
        if conn:
            conn.close()

def _save_to_db(data: Dict[str, Any], prompt_id: int, task_logger):
    """将分析结果和使用的 prompt_id 保存到数据库"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            task_logger.error("未能获取数据库连接以保存分析。")
            return

        cursor = conn.cursor()
        
        trade_plan = data.get('tradePlan', {})
        levels = data.get('levels', {})
        take_profit = levels.get('takeProfit', {})
        analysis = data.get('analysis', {})
        wave_analysis = {item['timeframe']: item['status'] for item in analysis.get('waveAnalysis', [])}

        sql = """
        INSERT INTO trade_analysis (
            asset, timestamp, conclusion, direction, confidence,
            risk_reward_ratio, entry_point, stop_loss, take_profit_1,
            take_profit_2, analysis_summary, wave_analysis_4h,
            wave_analysis_1h, wave_analysis_15m, rationale, raw_response, prompt_id
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        params = (
            data.get('asset'),
            datetime.now(),
            trade_plan.get('conclusion'),
            trade_plan.get('direction'),
            trade_plan.get('confidence'),
            trade_plan.get('riskRewardRatio'),
            levels.get('entryPoint'),
            levels.get('stopLoss'),
            take_profit.get('tp1'),
            take_profit.get('tp2'),
            analysis.get('summary'),
            wave_analysis.get('4H'),
            wave_analysis.get('1H'),
            wave_analysis.get('15M'),
            analysis.get('rationale'),
            json.dumps(data),
            prompt_id
        )
        
        cursor.execute(sql, params)
        conn.commit()
        task_logger.info(f"成功将 {data.get('asset')} 的分析结果保存到数据库。")

    except Exception as e:
        task_logger.error(f"保存分析时发生数据库错误: {e}", exc_info=True)
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()

async def run_analysis_task(symbol: str, asset_type: int):
    """
    执行单次分析任务的完整流程，并为该任务创建独立的日志文件。
    """
    task_logger, handler = _setup_task_logger(symbol)
    try:
        task_logger.info(f"正在为 {symbol} (类型: {asset_type}) 启动分析任务...")
        
        # 1. 从数据库加载激活的提示词
        prompt_id, system_prompt, json_structure = _get_active_prompt_from_db(task_logger)
        if not prompt_id or not system_prompt:
            task_logger.error("未能从数据库加载有效的激活提示词，任务中止。")
            return

        # 2. 获取K线数据
        kline_data = fetch_all_kline_data_concurrently(symbol=symbol, asset_type=asset_type)
        if not any(kline_data.values()):
            task_logger.warning(f"未能为 {symbol} 获取到K线数据。正在中止任务。")
            return

        # 3. 构建Prompt并调用AI
        asset_type_str = ASSET_TYPE_MAP.get(asset_type, "未知类型")
        
        # a. 构建完整的系统提示词，包含指令、变量和JSON结构
        full_system_prompt = (
            f"{system_prompt.format(symbol=symbol, asset_type=asset_type_str)}\n\n"
            f"请严格按照以下JSON结构返回分析结果:\n"
            f"{json_structure}"
        )
        
        # b. 构建用户提示词，现在只包含K线数据
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
            _save_to_db(analysis_result, prompt_id, task_logger)
            task_logger.info(f"为 {symbol} 的分析任务已成功完成。")
        except json.JSONDecodeError:
            task_logger.error(f"从AI响应解码JSON失败: {json_part}")
    finally:
        handler.close()
        task_logger.removeHandler(handler)

if __name__ == '__main__':
    import asyncio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    pass