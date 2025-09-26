import logging
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from services.analysis_service import run_analysis_task
from core.database import get_db_connection

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai")

def _schedule_all_assets():
    """从数据库加载所有资产并为它们安排分析任务。"""
    logger.info("正在从数据库为所有资产安排分析任务...")
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("无法安排任务，数据库连接失败。")
            return

        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, symbol, `type`, schedule_cron FROM assets WHERE schedule_cron IS NOT NULL")
        assets = cursor.fetchall()
        
        if not assets:
            logger.warning("在数据库中未找到带有定时任务的资产。")
            return

        for asset in assets:
            symbol = str(asset['symbol']) # type: ignore
            raw_asset_type = asset['type'] # type: ignore
            cron_string = str(asset['schedule_cron']) # type: ignore

            asset_type_int: int
            if isinstance(raw_asset_type, int):
                asset_type_int = raw_asset_type
            else:
                # 兼容旧的字符串或字节格式数据
                type_mapping = {"SPOT": 0, "USD_M": 1, "COIN_M": 2}
                type_str = raw_asset_type.decode('utf-8') if isinstance(raw_asset_type, bytes) else str(raw_asset_type)
                asset_type_int = type_mapping.get(type_str.upper(), 0)

            if symbol and cron_string and asset_type_int is not None:
                update_asset_schedule(symbol=symbol, cron_string=cron_string, asset_type=asset_type_int)
            
    except Exception as e:
        logger.error(f"安排资产任务时出错: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

def update_asset_schedule(symbol: str, cron_string: str | None, asset_type: int):
    """
    添加或更新单个资产的调度任务。
    如果 cron_string 为 None 或空，则移除现有任务。
    """
    job_id = f"analysis_{symbol}"
    logger.info(f"正在为任务 '{job_id}' (类型: {asset_type}) 更新定时设置, cron: '{cron_string}'")

    if not cron_string:
        remove_asset_schedule(symbol)
        return

    try:
        # 使用 CronTrigger.from_crontab 来验证和创建触发器
        trigger = CronTrigger.from_crontab(cron_string, timezone="Asia/Shanghai")
        
        scheduler.add_job(
            run_analysis_task,
            trigger=trigger,
            id=job_id,
            replace_existing=True,
            kwargs={"symbol": symbol, "asset_type": asset_type} # 使用 kwargs 传递参数
        )
        logger.info(f"成功为任务 '{job_id}' 设置定时表达式: '{cron_string}'。")
    except ValueError as e:
        logger.error(f"为 {symbol} 提供的 cron 字符串无效: '{cron_string}'。错误: {e}")


def remove_asset_schedule(symbol: str):
    """移除单个资产的调度任务。"""
    job_id = f"analysis_{symbol}"
    try:
        scheduler.remove_job(job_id)
        logger.info(f"已为 {symbol} 移除定时任务。任务 ID: {job_id}")
    except JobLookupError:
        logger.warning(f"无法为 {symbol} 移除任务，未找到任务 ID {job_id}。")
    except Exception as e:
        logger.error(f"为 {symbol} 移除任务时出错: {e}", exc_info=True)


def start_scheduler():
    """启动调度器并添加定时任务。"""
    if scheduler.running:
        logger.warning("调度器已在运行中。")
        return

    _schedule_all_assets()
    
    scheduler.start()
    logger.info("调度器已启动。")

def shutdown_scheduler():
    """关闭调度器。"""
    if scheduler.running:
        scheduler.shutdown()
        logger.info("调度器已关闭。")

# 测试入口
if __name__ == '__main__':
    import asyncio
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    async def main():
        start_scheduler()
        try:
            while True:
                await asyncio.sleep(3600)
        except (KeyboardInterrupt, SystemExit):
            shutdown_scheduler()

    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("应用程序正在关闭。")