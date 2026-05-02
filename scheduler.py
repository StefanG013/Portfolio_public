"""
scheduler.py — runs the trading agent automatically during US market hours.

Uses APScheduler to trigger the agent every 30 minutes from 9:30 AM to
4:00 PM ET on weekdays (Monday–Friday).  Runs outside those windows are
skipped automatically by the cron trigger.

Usage
-----
    python scheduler.py
"""

from __future__ import annotations

import logging
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from trading_agent.agent import TradingAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s — %(message)s",
)
log = logging.getLogger(__name__)

TIMEZONE = "America/New_York"

# Run every 30 minutes between 09:30 and 16:00 ET, Monday–Friday.
# APScheduler cron: minute=*/30 means :00 and :30 of each hour.
# We restrict hours to 9–15 so that the last run is at 15:30.
CRON_KWARGS = dict(
    day_of_week="mon-fri",
    hour="9-15",
    minute="30,0",     # :30 and :00
    timezone=TIMEZONE,
)

agent = TradingAgent()


def run_agent_job() -> None:
    """Job executed by the scheduler."""
    log.info("Scheduled agent run triggered.")
    try:
        results = agent.run()
        executed = [r for r in results if r.get("status") in ("EXECUTED", "DRY_RUN")]
        log.info(
            "Scheduled run complete: %d symbols analysed, %d trades executed.",
            len(results),
            len(executed),
        )
    except Exception as exc:
        log.error("Scheduled agent run failed: %s", exc, exc_info=True)


def main() -> None:
    scheduler = BlockingScheduler()
    scheduler.add_job(
        run_agent_job,
        trigger=CronTrigger(**CRON_KWARGS),
        id="trading_agent",
        name="AI Trading Agent",
        max_instances=1,  # prevent overlapping runs
        coalesce=True,
    )

    log.info(
        "Scheduler started. Agent will run %s (ET) on weekdays.",
        "every 30 min from 09:30 to 16:00",
    )

    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        log.info("Scheduler stopped.")


if __name__ == "__main__":
    main()
