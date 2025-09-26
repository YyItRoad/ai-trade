import logging
import json
import os
from datetime import datetime

# 导入项目内的模块
from core.market_data import fetch_all_kline_data_concurrently
from core.ai_client import get_ai_response, _extract_json_from_response
from core.database import get_db_connection

# 全局 logger，用于服务级别的信息
logger = logging.getLogger(__name__)

def _setup_task_logger(symbol: str):
    """为单个分析任务设置专用的文件日志记录器。"""
    log_dir = "logs/tasks"
    os.makedirs(log_dir, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    log_file = os.path.join(log_dir, f"{symbol}_{timestamp}.log")
    
    # 创建一个唯一的 logger 名称以避免冲突
    task_logger_name = f"task.{symbol}.{timestamp}"
    task_logger = logging.getLogger(task_logger_name)
    task_logger.setLevel(logging.INFO)
    
    # 防止将日志传播到根 logger
    task_logger.propagate = False
    
    # 创建文件处理器
    handler = logging.FileHandler(log_file, encoding='utf-8')
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)
    
    # 添加处理器
    task_logger.addHandler(handler)
    
    return task_logger, handler

def _load_prompt_parts(task_logger) -> tuple[str, str]:
    """从文件加载提示词的两个部分：系统指令和JSON结构。"""
    try:
        with open('prompts/system_prompt.txt', 'r', encoding='utf-8') as f:
            system_prompt = f.read()
        with open('prompts/json_structure.txt', 'r', encoding='utf-8') as f:
            json_structure = f.read()
        return system_prompt, json_structure
    except FileNotFoundError as e:
        task_logger.error(f"提示词文件未找到: {e.filename}")
        return "", ""

def _save_to_db(data: dict, task_logger):
    """将分析结果保存到数据库"""
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            task_logger.error("未能获取数据库连接以保存分析。")
            return

        cursor = conn.cursor()
        
        # 从解析后的JSON中提取数据
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
            wave_analysis_1h, wave_analysis_15m, rationale, raw_response
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            json.dumps(data) # 存储原始JSON
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
        
        # 1. 获取K线数据
        kline_data = fetch_all_kline_data_concurrently(symbol=symbol, asset_type=asset_type)
        if not any(kline_data.values()):
            task_logger.warning(f"未能为 {symbol} 获取到K线数据。正在中止任务。")
            return

        # 2. 构建Prompt并调用AI
        system_prompt, json_structure = _load_prompt_parts(task_logger)
        if not system_prompt or not json_structure:
            task_logger.error("因缺少提示词部分而中止任务。")
            return

        # 1. 格式化系统指令
        formatted_system_prompt = system_prompt.format(symbol=symbol)
        
        # 2. 准备K线数据
        kline_data_str = json.dumps(kline_data, indent=2)
        
        # 3. 拼接成最终的完整提示词
        full_prompt = (
            f"{formatted_system_prompt}\n"
            f"{json_structure}\n\n"
            f"以下是最新的K线数据:\n"
            f"```json\n{kline_data_str}\n```"
        )
        
        task_logger.info("正在向AI模型发送请求...")
        ai_response_str = await get_ai_response(prompt=full_prompt, force_json=True)
        task_logger.info(f"原始AI响应:\n---\n{ai_response_str}\n---")

        if not ai_response_str or "错误：" in ai_response_str:
            task_logger.error(f"未能从AI获取有效响应: {ai_response_str}")
            return

        # 3. 解析并存储
        json_part = _extract_json_from_response(ai_response_str)
        if not json_part:
            task_logger.error(f"无法从AI响应中提取JSON: {ai_response_str}")
            return
            
        try:
            analysis_result = json.loads(json_part)
            _save_to_db(analysis_result, task_logger)
            task_logger.info(f"为 {symbol} 的分析任务已成功完成。")
        except json.JSONDecodeError:
            task_logger.error(f"从AI响应解码JSON失败: {json_part}")
    finally:
        # 确保关闭并移除处理器以释放文件句柄
        handler.close()
        task_logger.removeHandler(handler)

if __name__ == '__main__':
    # 用于测试的异步执行入口
    import asyncio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
    # 示例: asyncio.run(run_analysis_task(symbol="BTCUSDT", asset_type="USD_M"))
    pass