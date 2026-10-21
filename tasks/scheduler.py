import os
import time
import threading
from datetime import datetime, timezone
from utils.logging_config import logger

_scheduler_thread = None
_scheduler_started = False
_lock = threading.Lock()

def _background_job_worker(app, interval_seconds: int):
    """
    Background worker loop that triggers job refreshes at the configured interval.
    Ensures daily and periodic job updates without manual intervention.
    """
    from tasks.refresh_jobs import run_job_refresh

    # Initial delay to let application start up cleanly
    time.sleep(15)

    while True:
        try:
            logger.info("Background job scheduler: Starting automated job sync cycle...")
            with app.app_context():
                from tasks.refresh_jobs import prune_dead_jobs
                stats = run_job_refresh(limit_per_source=25)
                logger.info(f"Background job sync finished: {stats}")
                
                # Also prune dead or expired job listings
                prune_stats = prune_dead_jobs(batch_size=50)
                logger.info(f"Background job pruner finished: {prune_stats}")
        except Exception as e:
            logger.error(f"Error during background automated job refresh: {e}")

        # Sleep for configured interval (default: e.g. 6 or 24 hours)
        time.sleep(interval_seconds)

def init_job_scheduler(app):
    """
    Starts the daemon background thread for automatic periodic job ingestion.
    Only starts in the main process (avoids double execution under Werkzeug reloader).
    """
    global _scheduler_started, _scheduler_thread

    # Avoid duplicate execution under Werkzeug debug reloader
    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    # Check if testing
    if app.config.get("TESTING", False):
        return

    with _lock:
        if _scheduler_started:
            return

        interval_hours = int(app.config.get("JOB_SYNC_INTERVAL_HOURS", 6))
        interval_seconds = interval_hours * 3600

        logger.info(f"Initializing automated job scheduler (Interval: {interval_hours} hours)...")
        _scheduler_thread = threading.Thread(
            target=_background_job_worker,
            args=(app, interval_seconds),
            daemon=True,
            name="DailyJobSyncWorker"
        )
        _scheduler_thread.start()
        _scheduler_started = True
