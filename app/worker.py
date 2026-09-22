import asyncio
import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.services.reminder_engine import reminder_engine

logger = logging.getLogger("guvi.worker")

scheduler = AsyncIOScheduler()


async def scheduled_reminder_job():
    """Background task executed on a recurring interval to dispatch reminders"""
    logger.info("Executing scheduled reminder evaluation job...")
    async with AsyncSessionLocal() as db:
        try:
            result = await reminder_engine.evaluate_and_send_all_reminders(db, force=False)
            logger.info(
                f"Scheduler run complete: evaluated={result.evaluated_count}, "
                f"pending_sent={result.pending_reminders_sent}, "
                f"overdue_sent={result.overdue_alerts_sent}, "
                f"dp_team_sent={result.dp_team_alerts_sent}, "
                f"failed={result.failed_count}"
            )
        except Exception as e:
            logger.error(f"Error executing scheduled reminder job: {e}", exc_info=True)


def start_scheduler():
    if not scheduler.running:
        scheduler.add_job(
            scheduled_reminder_job,
            "interval",
            seconds=settings.SCHEDULER_INTERVAL_SECONDS,
            id="reminder_scan_job",
            replace_existing=True,
        )
        scheduler.start()
        logger.info(
            f"Scheduler started. Running scan every {settings.SCHEDULER_INTERVAL_SECONDS} seconds."
        )


def stop_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("Scheduler shut down.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting standalone reminder worker...")
    start_scheduler()
    try:
        asyncio.get_event_loop().run_forever()
    except (KeyboardInterrupt, SystemExit):
        stop_scheduler()
