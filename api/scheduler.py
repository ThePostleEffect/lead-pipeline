"""Background scheduler — checks for due schedules and submits runs.

Runs as a daemon thread started on server boot. Checks every 60 seconds
for enabled schedules whose next_run_at has passed, then triggers a pipeline
run via the same submit_collect path the API uses.
"""

from __future__ import annotations

import logging
import threading
import time

from api.models import CollectRequest
from api.run_store import create_run
from api.schedule_store import get_due_schedules, mark_schedule_ran
from api.tasks import submit_collect

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 60  # seconds between checks
_thread: threading.Thread | None = None


def _scheduler_loop() -> None:
    """Main loop — runs forever in a daemon thread."""
    logger.info("Scheduler started (checking every %ds)", CHECK_INTERVAL)

    while True:
        try:
            due = get_due_schedules()
            if due:
                logger.info("Scheduler: %d schedule(s) due", len(due))

            for schedule in due:
                _fire_schedule(schedule)

        except Exception:
            logger.exception("Scheduler: error in check loop")

        time.sleep(CHECK_INTERVAL)


def _fire_schedule(schedule: dict) -> None:
    """Trigger a single scheduled run."""
    sid = schedule["schedule_id"]
    lane = schedule["lane"]
    params = schedule.get("params", {})

    logger.info(
        "Scheduler: firing %s (%s) — lane=%s",
        sid, schedule["name"], lane,
    )

    try:
        # Build a CollectRequest from the stored params
        request = CollectRequest(
            lane=lane,
            limit=params.get("limit"),
            min_quality=params.get("min_quality"),
            source_type=params.get("source_type", "web"),
            save_discards=params.get("save_discards", True),
            export_xlsx=params.get("export_xlsx", False),
            chapters=params.get("chapters"),
            lookback_days=params.get("lookback_days"),
            include_individuals=params.get("include_individuals"),
        )

        run_id = create_run(lane=lane)
        submit_collect(run_id, request, source_path=None)

        # Advance the schedule
        mark_schedule_ran(sid)

        logger.info("Scheduler: submitted run %s for schedule %s", run_id, sid)

    except Exception:
        logger.exception("Scheduler: failed to fire schedule %s", sid)


def start_scheduler() -> None:
    """Start the background scheduler thread (idempotent)."""
    global _thread
    if _thread is not None and _thread.is_alive():
        return

    _thread = threading.Thread(target=_scheduler_loop, daemon=True, name="scheduler")
    _thread.start()
