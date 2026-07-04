"""Background scheduler that polls IQAir every few minutes (Guideline 3.2.4).

Uses APScheduler with django-apscheduler's DjangoJobStore so job runs are
recorded in the database. Started from DataApiConfig.ready() when the dev
server runs, so `python manage.py runserver` is all that's needed for the
dashboard to keep refreshing.
"""

import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger
from django.conf import settings
from django.utils import timezone
from django_apscheduler.jobstores import DjangoJobStore
from django_apscheduler.models import DjangoJobExecution
from django_apscheduler import util

logger = logging.getLogger(__name__)

_scheduler = None


def _fetch_job():
    """Job body: pull all locations, store them, then log a fresh prediction each.

    Generating a prediction on every new reading satisfies Guideline 3.4.10
    ("generate a fresh prediction each time new data arrives") and logs it with
    a timestamp.
    """
    from data_api.services import fetch_and_store_all

    summary = fetch_and_store_all()

    predicted = 0
    try:
        from predictor.services import predict_from_reading, ModelNotTrained

        for reading in summary["created"]:
            try:
                predicted += len(predict_from_reading(reading, save=True))
            except ModelNotTrained:
                break  # models not trained yet — skip quietly
    except Exception as exc:  # noqa: BLE001
        logger.warning("Prediction step failed: %s", exc)

    logger.info(
        "Scheduled fetch complete: %d stored, %d errors, %d predictions logged",
        len(summary["created"]),
        len(summary["errors"]),
        predicted,
    )


@util.close_old_connections
def _delete_old_job_executions(max_age=7 * 24 * 3600):
    """Housekeeping: drop APScheduler execution logs older than a week."""
    DjangoJobExecution.objects.delete_old_job_executions(max_age)


def start():
    """Start the background scheduler once."""
    global _scheduler
    if _scheduler is not None and _scheduler.running:
        return

    interval = max(1, settings.FETCH_INTERVAL_MINUTES)
    scheduler = BackgroundScheduler(timezone=str(settings.TIME_ZONE))
    scheduler.add_jobstore(DjangoJobStore(), "default")

    scheduler.add_job(
        _fetch_job,
        trigger=IntervalTrigger(minutes=interval),
        id="fetch_air_quality",
        max_instances=1,
        replace_existing=True,
        next_run_time=timezone.now(),  # also fetch immediately on startup
    )
    scheduler.add_job(
        _delete_old_job_executions,
        trigger=IntervalTrigger(days=1),
        id="delete_old_job_executions",
        max_instances=1,
        replace_existing=True,
    )

    scheduler.start()
    _scheduler = scheduler
    logger.info("APScheduler started — fetching air quality every %d minute(s).", interval)
