"""
Telegram Bot Fleet Master Execution Engine
Cross-platform support: Android (Termux), Linux / GitHub Actions, and Windows.
"""
import asyncio
import os
import sys
import argparse
import random
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
from src.engines.runner import send_from_account
from src.utils.terminal_ui import log_header, log_job_info

async def main():
    parser = argparse.ArgumentParser(description="🚀 Run the Telegram Bot Fleet")
    parser.add_argument("--time", type=str, required=True, help="Target Job (e.g., 4am, 8am, testCaptcha_no_ind)")
    parser.add_argument("--config", type=str, default="master_config.json", help="Path to config file")
    args = parser.parse_args()

    time_slot = args.time
    config_file = get_config_path(args.config)
    sessions_dir = get_sessions_dir()

    log_header("TELEGRAM BOT FLEET ENGINE", "Multi-Device • Anti-Ban • Captcha Solver")

    if not API_ID or not API_HASH:
        print("❌ Error: Missing Telegram credentials!")
        print("   Add them to `credentials/telegram_creds.json` or export TELEGRAM_API_ID / TELEGRAM_API_HASH.")
        sys.exit(1)

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
            initial_delay=current_stagger
        ))

    await asyncio.gather(*tasks)
    stats_tracker.print_stats()

if __name__ == "__main__":
    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
    asyncio.run(main())
