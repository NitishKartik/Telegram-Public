"""Command-line entry point for per-UID daily likes tracking.

Run from the project root with ``python -m src.cli.like_tracker summary``.
"""

import argparse
import asyncio
import json
import re
import sys
from datetime import datetime
from pathlib import Path

from src.core.like_history import (
    HISTORY_PATH, IST, daily_uid_summary, extract_likes, get_operational_date, load_history, record_likes,
)
from src.engines.level_query import send_level
from src.utils.terminal_ui import log_like_daily_summary, log_like_result


def main() -> None:
    if sys.platform == "win32":
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description="Track daily likes for Free Fire UIDs")
    sub = parser.add_subparsers(dest="action", required=True)
    send = sub.add_parser("send", help="Send /level UID using nitish1")
    send.add_argument("uid")
    record = sub.add_parser("record", help="Record a previously captured bot reply")
    record.add_argument("uid")
    record.add_argument("--reply-file", required=True, type=Path)
    show = sub.add_parser("show", help="Show stored history for a UID")
    show.add_argument("uid")
    summary = sub.add_parser("summary", help="Show daily likes and increases by UID")
    summary.add_argument("--date", default=None, help="Operational date YYYY-MM-DD (defaults to current 4am cycle)")
    args = parser.parse_args()

    if args.action == "summary":
        target_date = args.date or get_operational_date()
        daily = daily_uid_summary(load_history(), target_date)
        log_like_daily_summary(target_date, daily)
        return
    if not re.fullmatch(r"\d+", args.uid):
        parser.error("UID must contain digits only")

    if args.action == "show":
        data = load_history()
        print(json.dumps(data.get("uids", {}).get(args.uid), indent=2))
        return
    if args.action == "send":
        reply, message_id = asyncio.run(send_level(args.uid))
        print(f"Bot reply (message ID {message_id}):\n{reply}")
    else:
        reply = args.reply_file.read_text(encoding="utf-8")

    likes = extract_likes(reply)
    entry = record_likes(args.uid, likes)
    log_like_result("Nitish1", args.uid, likes, entry["change_from_previous_recorded_day"])
    print(f"Saved {HISTORY_PATH}")


if __name__ == "__main__":
    main()
