"""
Telegram Bot Fleet Master Execution Engine
Cross-platform support: Android (Termux), Linux / GitHub Actions, and Windows.
"""
import asyncio
import json
import os
import sys
import argparse
import random
import re
from datetime import datetime
from pathlib import Path

# Guarantee root directory is in sys.path
PROJECT_ROOT = Path(__file__).resolve().parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Ensure UTF-8 output on Windows consoles to prevent UnicodeEncodeError
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from src.config import (
    API_ID,
    API_HASH,
    get_config_path,
    get_sessions_dir,
    load_json_config
)
from src.core.stats import BotStats
from src.core.like_history import IST, daily_uid_summary, load_history
from src.engines.runner import send_from_account
from src.utils.terminal_ui import log_header, log_job_info, log_like_daily_summary

async def main():
    parser = argparse.ArgumentParser(description="🚀 Run the Telegram Bot Fleet")
    parser.add_argument("--time", type=str, required=False, help="Target Job (e.g., 4am, 8am, info_bot, like_report)")
    parser.add_argument("--config", type=str, default="master_config.json", help="Path to config file")
    parser.add_argument("--summary", nargs="?", const="today", help="Show daily likes summary table (e.g., --summary or --summary 2026-11-09)")
    parser.add_argument("--show", type=str, help="Show stored history for a UID (e.g., --show 1852353345)")
    parser.add_argument("--send", type=str, help="Send guarded /level query using nitish1 session (e.g., --send 1852353345)")
    parser.add_argument("--report", nargs="?", const="today", help="Generate likes report markdown & JSON files (e.g., --report)")
    parser.add_argument("--telegram", action="store_true", help="Send generated report directly into Telegram group")
    parser.add_argument("--force", action="store_true", help="Bypass cron schedule safety checks for local manual testing")
    args = parser.parse_args()

    # Handle direct utility flags first
    if args.summary is not None:
        selected_day = datetime.now(IST).date().isoformat() if args.summary == "today" else args.summary
        daily = daily_uid_summary(load_history(), selected_day)
        log_like_daily_summary(selected_day, daily)
        return

    if args.show:
        if not re.fullmatch(r"\d+", args.show):
            print("❌ Error: UID must contain digits only")
            sys.exit(1)
        data = load_history()
        uid_data = data.get("uids", {}).get(args.show)
        if uid_data is None:
            print(f"⚠️ UID {args.show} not found in history.")
        else:
            print(json.dumps(uid_data, indent=2))
        return

    if args.report is not None:
        from src.core.like_report import generate_report, send_report_telegram
        selected_day = None if args.report == "today" else args.report
        report = generate_report({"output_dir": "data/reports"}, day=selected_day)
        if getattr(args, "telegram", False):
            try:
                cfg = load_json_config(get_config_path(args.config))
                job_cfg = cfg.get("jobs", {}).get("like_report", {})
            except Exception:
                job_cfg = {}
            try:
                await send_report_telegram(report, job_cfg, force=args.force)
            except RuntimeError as e:
                print(f"\n🛡️ Safety check prevented Telegram send: {e}")
                print(f"   (Use --force to bypass safety checks if you are certain no remote fleet runs are active)\n")
                sys.exit(1)
        return

    if args.send:
        if not re.fullmatch(r"\d+", args.send):
            print("❌ Error: UID must contain digits only")
            sys.exit(1)
        from src.engines.level_query import send_level
        from src.core.like_history import extract_likes, extract_player_name, record_likes, HISTORY_PATH
        from src.utils.terminal_ui import log_like_result
        try:
            reply, message_id = await send_level(args.send, force=args.force)
            likes = extract_likes(reply)
            player_name = extract_player_name(reply)
            entry = record_likes(args.send, likes, player_name=player_name)
            log_like_result(
                "Nitish1",
                args.send,
                likes,
                entry.get("change_from_previous_recorded_day"),
                player_name=entry.get("player_name"),
                added_since_prev=entry.get("change_from_previous_observation"),
            )
            print(f"Saved {HISTORY_PATH}")
        except Exception as e:
            print(f"❌ Error sending /level {args.send}: {e}")
            sys.exit(1)
        return

    if not args.time:
        parser.print_help()
        sys.exit(1)

    time_slot = args.time
    config_file = get_config_path(args.config)
    sessions_dir = get_sessions_dir()

    try:
        full_data = load_json_config(config_file)
    except FileNotFoundError as e:
        print(f"❌ Error: {e}")
        sys.exit(1)

    if "jobs" not in full_data or time_slot not in full_data["jobs"]:
        print(f"❌ Error: Job '{time_slot}' not found inside {config_file.name}")
        available_jobs = list(full_data.get("jobs", {}).keys())
        print(f"   Available: {', '.join(available_jobs)}")
        sys.exit(1)

    data = full_data["jobs"][time_slot]

    if time_slot == "like_report" or data.get("type") == "report":
        from src.core.like_report import generate_report, send_report_telegram
        report = generate_report(data)
        if data.get("send_telegram") or data.get("groups"):
            try:
                await send_report_telegram(report, data, force=getattr(args, "force", False))
            except RuntimeError as e:
                print(f"\n🛡️ Safety check prevented Telegram send: {e}")
                print(f"   (Use --force to bypass safety checks if you are certain no remote fleet runs are active)\n")
                sys.exit(1)
        return

    log_header("TELEGRAM BOT FLEET ENGINE", "Multi-Device • Anti-Ban • Captcha Solver")

    if not API_ID or not API_HASH:
        print("❌ Error: Missing Telegram credentials!")
        print("   Add them to `credentials/telegram_creds.json` or export TELEGRAM_API_ID / TELEGRAM_API_HASH.")
        sys.exit(1)

    raw_groups = data.get("groups", [])
    target_groups = []

    for g in raw_groups:
        if isinstance(g, dict):
            if g.get("active", True):
                target_groups.append(g)
        else:
            target_groups.append({"id": g, "solve_captcha": True, "ghost_mode": False})

    accounts_data = data.get("accounts", [])
    repeat_count = data.get("repeat_count", 1)
    hz_data = data.get("humanization_settings", {})

    hz_config = {
        "show_typing_status": hz_data.get("show_typing_status", True),
        "wait_between_messages_sec_min": hz_data.get("wait_between_messages_sec_min", 15),
        "wait_between_messages_sec_max": hz_data.get("wait_between_messages_sec_max", 30),
        "wait_between_rounds_sec_min": hz_data.get("wait_between_rounds_sec_min", 30),
        "wait_between_rounds_sec_max": hz_data.get("wait_between_rounds_sec_max", 50),
        "take_long_break_after_x_messages": hz_data.get("take_long_break_after_x_messages", 50),
        "long_break_duration_sec_min": hz_data.get("long_break_duration_sec_min", 180),
        "long_break_duration_sec_max": hz_data.get("long_break_duration_sec_max", 300),
        "account_startup_delay_sec_min": hz_data.get("account_startup_delay_sec_min", 2),
        "account_startup_delay_sec_max": hz_data.get("account_startup_delay_sec_max", 5)
    }

    active_accounts = [acc for acc in accounts_data if acc.get("active", True)]

    if not target_groups or not active_accounts:
        print("⚠️ No active targets or accounts found for this job!")
        sys.exit(1)

    if os.environ.get("GITHUB_ACTIONS") != "true" and not getattr(args, "force", False):
        from src.utils.schedule_guard import check_cron_window, check_public_workflows
        try:
            check_cron_window()
            check_public_workflows()
        except Exception as guard_error:
            print(f"❌ Local session safety check failed: {guard_error}")
            print(f"   (Use --force to bypass safety checks if you are certain no remote fleet runs are active)\n")
            sys.exit(1)

    delay_info = f"{hz_config['wait_between_messages_sec_min']}s - {hz_config['wait_between_messages_sec_max']}s"
    log_job_info(time_slot, len(active_accounts), len(target_groups), repeat_count, delay_info)

    stats_tracker = BotStats()
    tasks = []
    current_stagger = 0.0

    for idx, acc in enumerate(active_accounts):
        session_name = acc["session"]
        if not session_name.endswith(".session"):
            session_name += ".session"

        session_path = sessions_dir / session_name
        if not session_path.exists():
            legacy_path = PROJECT_ROOT / "Session" / session_name
            if legacy_path.exists():
                session_path = legacy_path

        if idx > 0:
            current_stagger += random.uniform(
                hz_config["account_startup_delay_sec_min"],
                hz_config["account_startup_delay_sec_max"]
            )

        raw_msg = acc.get("messages", acc.get("message", ""))
        msg_list = raw_msg if isinstance(raw_msg, list) else [raw_msg]

        tasks.append(send_from_account(
            account_name=acc["name"],
            session_path=session_path,
            msg_list=msg_list,
            target_groups=target_groups,
            repeat_count=repeat_count,
            hz_config=hz_config,
            stats_tracker=stats_tracker,
            api_id=API_ID,
            api_hash=API_HASH,
            initial_delay=current_stagger,
            track_level_replies=(time_slot == "info_bot"),
        ))

    tracked_results = await asyncio.gather(*tasks)
    stats_tracker.print_stats()
    if time_slot == "info_bot":
        expected = 0
        for acc in active_accounts:
            raw = acc.get("messages", acc.get("message", ""))
            messages = raw if isinstance(raw, list) else [raw]
            expected += sum(
                bool(re.fullmatch(r"/level\s+\d+", str(message).strip()))
                for message in messages
            )
        expected *= len(target_groups) * repeat_count
        tracked = sum(result or 0 for result in tracked_results)
        today = datetime.now(IST).date().isoformat()
        daily = daily_uid_summary(load_history(), today)
        log_like_daily_summary(today, daily, captured=tracked, expected=expected)

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
