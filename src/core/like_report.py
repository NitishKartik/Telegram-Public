"""Read saved likes history and produce a separate daily report for every UID."""

import json
import os
from datetime import date, datetime
from pathlib import Path

from src.core import like_history


def build_report(history: dict, day: str) -> dict:
    """Compare each UID's observation with its latest earlier recorded date."""
    report_date = date.fromisoformat(day)
    rows = {}
    for uid, entry in sorted(history.get("uids", {}).items()):
        daily = entry.get("daily", {})
        current = daily.get(day)
        prior_dates = [candidate for candidate in daily if candidate < day]
        prior_day = max(prior_dates) if prior_dates else None
        prior = daily[prior_day] if prior_day else None
        interval = (report_date - date.fromisoformat(prior_day)).days if prior_day else None
        increase = current["likes"] - prior["likes"] if current and prior else None
        if current is None:
            status = "missing_today"
        elif prior is None:
            status = "baseline"
        elif interval == 1:
            status = "compared"
        else:
            status = "gap"
        rows[uid] = {
            "player_name": entry.get("player_name") or (current.get("player_name") if current else None) or "—",
            "likes": current["likes"] if current else None,
            "observed_at": current.get("observed_at") if current else None,
            "previous_recorded_day": prior_day,
            "previous_likes": prior["likes"] if prior else None,
            "increase_since_previous_record": increase,
            "comparison_days": interval,
            "daily_increase": increase if current and interval == 1 else None,
            "status": status,
        }
    return {
        "date": report_date.isoformat(),
        "timezone": "Asia/Kolkata",
        "generated_at": datetime.now(like_history.IST).isoformat(),
        "uids": rows,
    }


def render_markdown(report: dict) -> str:
    lines = [
        f"# Likes report — {report['date']} (IST)",
        "",
        "Each row compares one UID with its own previous recorded value.",
        "",
        "| UID | Player Name | Likes on report date | Previous date | Previous likes | Change | Result |",
        "| --- | --- | ---: | --- | ---: | --- | --- |",
    ]
    for uid, row in report["uids"].items():
        player = row.get("player_name") or "—"
        likes = f"{row['likes']:,}" if row["likes"] is not None else "—"
        previous_likes = f"{row['previous_likes']:,}" if row["previous_likes"] is not None else "—"
        previous_day = row["previous_recorded_day"] or "—"
        delta = row["increase_since_previous_record"]
        change = f"{delta:+,}" if delta is not None else "—"
        if row["status"] == "gap":
            change += f" over {row['comparison_days']} days"
            result = "Gap in observations"
        elif row["status"] == "missing_today":
            result = "No observation on report date"
        elif row["status"] == "baseline":
            result = "First recorded day"
        else:
            result = "Change from previous day"
        lines.append(f"| {uid} | {player} | {likes} | {previous_day} | {previous_likes} | {change} | {result} |")
    if not report["uids"]:
        lines.extend(["", "No UIDs are present in the saved history."])
    lines.extend([
        "",
        "Changes are measured between saved observations. Missing dates are shown explicitly; "
        "a change across several days is not a single-day increase.",
        "",
    ])
    return "\n".join(lines)


def generate_report(settings: dict, day: str | None = None) -> dict:
    """Write JSON/Markdown without opening Telegram sessions or changing history."""
    if not like_history.HISTORY_PATH.is_file():
        raise FileNotFoundError(f"Likes history not found: {like_history.HISTORY_PATH}")
    selected_day = day or datetime.now(like_history.IST).date().isoformat()
    report = build_report(like_history.load_history(), selected_day)
    output_dir = Path(settings.get("output_dir", "data/reports"))
    if not output_dir.is_absolute():
        output_dir = like_history.ROOT / output_dir
    output_dir.mkdir(parents=True, exist_ok=True)
    json_path = output_dir / f"like_report_{report['date']}.json"
    markdown_path = output_dir / f"like_report_{report['date']}.md"
    markdown = render_markdown(report)
    json_path.write_text(json.dumps(report, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    markdown_path.write_text(markdown, encoding="utf-8")
    if os.environ.get("GITHUB_STEP_SUMMARY"):
        with Path(os.environ["GITHUB_STEP_SUMMARY"]).open("a", encoding="utf-8") as summary:
            summary.write(markdown + "\n")
    from src.utils.terminal_ui import log_like_report_table
    log_like_report_table(report, json_path=json_path, markdown_path=markdown_path)
    return report


def render_telegram_message(report: dict) -> str:
    """Render mobile-friendly card-view Telegram Markdown message."""
    day = report.get("date", "")
    lines = [
        f"📊 **DAILY LIKES REPORT • {day} (IST)**",
        "─────────────────────────────",
    ]
    uids = report.get("uids", {})
    if not uids:
        lines.append("⚠️ No UIDs tracked in history.")
    for uid, row in uids.items():
        name = row.get("player_name") or "—"
        likes = row.get("likes")
        likes_str = f"{likes:,}" if likes is not None else "—"
        status_type = row.get("status")
        delta = row.get("increase_since_previous_record")

        if status_type == "baseline":
            status_text = "First recorded day"
        elif status_type == "missing_today":
            status_text = "❌ Missing today"
        elif status_type == "gap":
            status_text = f"📈 {delta:+,} (over {row.get('comparison_days')}d)"
        else:
            status_text = f"📈 Daily {delta:+,}"

        lines.append(f"👤 **{name}** (`{uid}`)")
        lines.append(f"   • **Likes**: `{likes_str}` | {status_text}")
        lines.append("")

    lines.append("─────────────────────────────")
    lines.append("📁 _Generated & archived automatically._")
    return "\n".join(lines).strip()


async def send_report_telegram(report: dict, settings: dict, force: bool = False) -> list[int]:
    """Send formatted like report card into configured Telegram groups."""
    from telethon import TelegramClient
    from src.config import API_ID, API_HASH, get_sessions_dir

    if not API_ID or not API_HASH:
        raise RuntimeError("Telegram API credentials missing")

    if os.environ.get("GITHUB_ACTIONS") != "true" and not force:
        from src.utils.schedule_guard import check_cron_window, check_public_workflows
        check_cron_window()
        check_public_workflows()

    groups = settings.get("groups", [])
    target_group_ids = [
        group["id"] if isinstance(group, dict) else group
        for group in groups
        if not isinstance(group, dict) or group.get("active", True)
    ]
    if not target_group_ids:
        target_group_ids = [-1003451378152]

    sender_name = settings.get("sender_account", "nitish1").lower()
    if not sender_name.endswith(".session"):
        sender_name += ".session"

    session_path = get_sessions_dir() / sender_name
    if not session_path.exists():
        legacy_path = like_history.ROOT / "Session" / sender_name
        if legacy_path.exists():
            session_path = legacy_path
        else:
            raise FileNotFoundError(f"Session file not found: {session_path}")

    text = render_telegram_message(report)
    sent_ids = []

    async with TelegramClient(str(session_path), API_ID, API_HASH) as client:
        if not await client.is_user_authorized():
            raise RuntimeError(f"Session {session_path.name} is no longer authorized")
        for gid in target_group_ids:
            sent = await client.send_message(int(gid), text, parse_mode="md")
            print(f"📬 [Like Report] Dispatched report to group {gid} (Message ID: {sent.id})")
            sent_ids.append(sent.id)

    return sent_ids

