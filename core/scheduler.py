import logging
from typing import Dict, Any
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from services.analysis_service import run_analysis_task
from core.database import get_db_connection

logger = logging.getLogger(__name__)

# 配置作业默认值，防止因任务同时到期而被合并执行
job_defaults = {
    'coalesce': False,  # 禁止合并执行
    'max_instances': 5, # 允许同一个作业有5个实例并行运行（适用于需要长时间运行的任务）
    'misfire_grace_time': 300 # 宽限时间增加到5分钟
}

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai", job_defaults=job_defaults)

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
            try:
                symbol = str(asset['symbol']) # type: ignore
                asset_type_int = int(asset['type']) # type: ignore
                cron_string = str(asset['schedule_cron']) # type: ignore

                if not (symbol and cron_string):
                    continue

                # --- 直接在此处添加任务，不再调用 update_asset_schedule ---
                job_id = f"analysis_{symbol}_{asset_type_int}"
                
                trigger = CronTrigger.from_crontab(cron_string, timezone="Asia/Shanghai")
                
                scheduler.add_job(
                    run_analysis_task,
                    trigger=trigger,
                    id=job_id,
                    name=f"Analysis for {symbol} (Type: {asset_type_int})", # 添加 name 参数以改善日志
                    replace_existing=True,
                    kwargs={"symbol": symbol, "asset_type": asset_type_int}
                )
                logger.info(f"成功为任务 '{job_id}' (启动时加载) 设置定时: '{cron_string}'")

            except ValueError as e:
                logger.error(f"为 {asset.get('symbol')} 提供的 cron 字符串无效: '{asset.get('schedule_cron')}'。跳过该任务。错误: {e}")
            except Exception as e:
                logger.error(f"在启动时为资产 {asset.get('id')} 安排任务时发生未知错误: {e}", exc_info=True)
            
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
    job_id = f"analysis_{symbol}_{asset_type}"
    logger.info(f"正在为任务 '{job_id}' (类型: {asset_type}) 更新定时设置, cron: '{cron_string}'")

    if not cron_string:
        remove_asset_schedule(symbol, asset_type)
        return

    try:
        # 使用 CronTrigger.from_crontab 来验证和创建触发器
        trigger = CronTrigger.from_crontab(cron_string, timezone="Asia/Shanghai")
        
        scheduler.add_job(
            run_analysis_task,
            trigger=trigger,
            id=job_id,
            name=f"Analysis for {symbol} (Type: {asset_type})", # 确保这里的 name 参数也存在
            replace_existing=True,
            kwargs={"symbol": symbol, "asset_type": asset_type} # 使用 kwargs 传递参数
        )
        logger.info(f"成功为任务 '{job_id}' 设置定时表达式: '{cron_string}'。")
    except ValueError as e:
        logger.error(f"为 {symbol} 提供的 cron 字符串无效: '{cron_string}'。错误: {e}")


def remove_asset_schedule(symbol: str, asset_type: int):
    """移除单个资产的调度任务。"""
    job_id = f"analysis_{symbol}_{asset_type}"
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