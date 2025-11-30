import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.jobstores.base import JobLookupError
from apscheduler.triggers.cron import CronTrigger
from services.analysis_service import run_analysis_task
from core.database import get_db_connection

logger = logging.getLogger(__name__)

job_defaults = {
    'coalesce': False,
    'max_instances': 5,
    'misfire_grace_time': 300
}

scheduler = AsyncIOScheduler(timezone="Asia/Shanghai", job_defaults=job_defaults)

def _schedule_all_tasks():
    """从数据库加载所有激活的定时任务并安排它们。"""
    logger.info("正在从数据库加载并安排所有激活的定时任务...")
    conn = None
    try:
        conn = get_db_connection()
        if not conn:
            logger.error("无法安排任务，数据库连接失败。")
            return

        cursor = conn.cursor(dictionary=True)
        
        # 从 scheduled_tasks 表中查询所有激活的任务
        query = """
            SELECT 
                st.id, 
                st.asset_id, 
                st.prompt_id, 
                st.cycle, 
                st.cron_expression,
                a.symbol,
                a.type as asset_type
            FROM scheduled_tasks st
            JOIN assets a ON st.asset_id = a.id
            WHERE st.is_active = TRUE
        """
        cursor.execute(query)
        tasks = cursor.fetchall()
        
        if not tasks:
            logger.warning("在数据库中未找到激活的定时任务。")
            return

        for task in tasks:
            try:
                task_id = task['id']
                job_id = f"analysis_task_{task_id}"
                cron_string = task['cron_expression']
                
                # 将 cron 字符串拆分为秒、分、时、日、月、周
                cron_parts = cron_string.split()
                if len(cron_parts) != 6:
                    raise ValueError("Cron 表达式必须包含 6 个字段 (秒 分 时 日 月 周)。")

                trigger = CronTrigger(
                    second=cron_parts[0],
                    minute=cron_parts[1],
                    hour=cron_parts[2],
                    day=cron_parts[3],
                    month=cron_parts[4],
                    day_of_week=cron_parts[5],
                    timezone="Asia/Shanghai"
                )
                
                # 准备传递给 run_analysis_task 的参数
                task_kwargs = {
                    "asset_id": task['asset_id'],
                    "prompt_id": task['prompt_id'],
                    "cycle": task['cycle'],
                    "symbol": task['symbol'],
                    "asset_type": task['asset_type']
                }

                scheduler.add_job(
                    run_analysis_task,
                    trigger=trigger,
                    id=job_id,
                    name=f"Task {task_id}: {task['symbol']} ({task['cycle']})",
                    replace_existing=True,
                    kwargs=task_kwargs
                )
                logger.info(f"成功为任务 '{job_id}' (ID: {task_id}) 设置定时: '{cron_string}'")

            except ValueError as e:
                logger.error(f"为任务ID {task.get('id')} 提供的 cron 字符串无效: '{task.get('cron_expression')}'。跳过该任务。错误: {e}")
            except Exception as e:
                logger.error(f"在启动时为任务ID {task.get('id')} 安排任务时发生未知错误: {e}", exc_info=True)
            
    except Exception as e:
        logger.error(f"安排定时任务时出错: {e}", exc_info=True)
    finally:
        if conn:
            conn.close()

def reload_scheduler_tasks():
    """清空现有任务并从数据库重新加载所有任务。"""
    logger.info("正在重新加载所有调度器任务...")
    scheduler.remove_all_jobs()
    _schedule_all_tasks()
    logger.info("调度器任务重新加载完成。")

def start_scheduler():
    """启动调度器并添加定时任务。"""
    if scheduler.running:
        logger.warning("调度器已在运行中。")
        return

    _schedule_all_tasks()
    
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
        # 假设数据库已初始化
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