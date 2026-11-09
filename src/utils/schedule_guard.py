"""Prevent local Telegram sessions from overlapping scheduled cloud runs."""

import json
import urllib.request
from datetime import datetime, timedelta
from pathlib import Path

from src.core.like_history import IST


ROOT = Path(__file__).resolve().parents[2]


def check_cron_window(now: datetime | None = None) -> None:
    """Fail closed unless the live cron schedule leaves a clear session window."""
    creds_path = ROOT / "credentials" / "cronjob_creds.json"
    token = json.loads(creds_path.read_text(encoding="utf-8"))["api_token"]
    request = urllib.request.Request(
        "https://api.cron-job.org/jobs",
        headers={"Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        jobs = json.load(response)["jobs"]

    relevant = [
        job for job in jobs
        if job.get("enabled") and "NitishKartik/Telegram" in job.get("url", "")
    ]
    if not relevant:
        raise RuntimeError("Live cron response contained no enabled Telegram jobs")

    current = (now or datetime.now(IST)).astimezone(IST)
    conflicts = []
    for job in relevant:
        schedule = job.get("schedule", {})
        if schedule.get("timezone") not in ("Asia/Kolkata", "Asia/Calcutta"):
            raise RuntimeError(f"Unknown timezone for cron job {job.get('title')}")
        if any(schedule.get(key, [-1]) != [-1] for key in ("mdays", "months", "wdays")):
            raise RuntimeError(f"Complex cron schedule for {job.get('title')} needs review")
        for day_offset in (-1, 0, 1):
            date = (current + timedelta(days=day_offset)).date()
            for hour in schedule.get("hours", []):
                for minute in schedule.get("minutes", []):
                    start = datetime(date.year, date.month, date.day, hour, minute, tzinfo=IST)
                    after_minutes = 5 if "Telegram-Public" in job.get("url", "") else 60
                    if start - timedelta(minutes=15) <= current <= start + timedelta(minutes=after_minutes):
                        conflicts.append(f"{job.get('title')} at {start:%Y-%m-%d %H:%M} IST")
    if conflicts:
        raise RuntimeError("Session window overlaps scheduled jobs: " + "; ".join(conflicts))


def check_public_workflows() -> None:
    """Reject local use while any public fleet workflow is queued or running."""
    request = urllib.request.Request(
        "https://api.github.com/repos/NitishKartik/Telegram-Public/actions/"
        "workflows/fleet-runner.yml/runs?per_page=30",
        headers={"User-Agent": "telegram-like-tracker"},
    )
    with urllib.request.urlopen(request, timeout=15) as response:
        runs = json.load(response)["workflow_runs"]
    active = [run for run in runs if run.get("status") != "completed"]
    if active:
        raise RuntimeError(
            "Public fleet workflow still active: "
            + ", ".join(str(run.get("id")) for run in active)
        )
