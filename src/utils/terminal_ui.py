import sys
import unicodedata
from datetime import datetime

# Guarantee safe UTF-8 terminal encoding on Windows / Termux / Linux
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Enable ANSI colors in classic Windows Command Prompt when possible.
def _enable_windows_ansi():
    if sys.platform != "win32":
        return True
    try:
        import ctypes
        kernel = ctypes.windll.kernel32
        handle = kernel.GetStdHandle(-11)
        mode = ctypes.c_ulong()
        if not kernel.GetConsoleMode(handle, ctypes.byref(mode)):
            return False
        return bool(kernel.SetConsoleMode(handle, mode.value | 0x0004))
    except Exception:
        return False


# Check if terminal supports color
def _use_color():
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty() and _enable_windows_ansi()

# ANSI Color Codes
CYAN = "\033[36m" if _use_color() else ""
GREEN = "\033[32m" if _use_color() else ""
YELLOW = "\033[33m" if _use_color() else ""
RED = "\033[31m" if _use_color() else ""
BOLD = "\033[1m" if _use_color() else ""
DIM = "\033[2m" if _use_color() else ""
RESET = "\033[0m" if _use_color() else ""

def display_width(s: str) -> int:
    """Calculates visual monospace column width accounting for full-width Unicode characters."""
    return sum(2 if unicodedata.east_asian_width(c) in ("W", "F") else 1 for c in s)

def pad_display(s: str, width: int, align="<") -> str:
    """Pads a string according to its visual display width rather than raw character length."""
    dw = display_width(s)
    pad = max(0, width - dw)
    if align == ">":
        return " " * pad + s
    return s + " " * pad

def _timestamp() -> str:
    return datetime.now().strftime("%H:%M:%S")

def log_header(title: str, subtitle: str = ""):
    """Renders a clean card header that looks great on mobile Termux and desktop terminals."""
    width = 52
    border = "=" * width
    print(f"\n{CYAN}{border}{RESET}")
    print(f"{BOLD}{title.center(width)}{RESET}")
    if subtitle:
        print(f"{DIM}{subtitle.center(width)}{RESET}")
    print(f"{CYAN}{border}{RESET}\n")

def log_job_info(job_name: str, accounts_count: int, groups_count: int, repeat: int, delays: str):
    """Outputs compact card of job metadata."""
    print(f"{BOLD}🎯 JOB:{RESET} {GREEN}{job_name}{RESET}")
    print(f"   ├─ 👥 Accounts : {BOLD}{accounts_count}{RESET} active")
    print(f"   ├─ 📢 Targets  : {BOLD}{groups_count}{RESET} group(s)")
    print(f"   ├─ 🔁 Repeats  : {BOLD}{repeat}{RESET} round(s)")
    print(f"   └─ ⏱️  Pacing   : {DIM}{delays}{RESET}\n")

def log_account_connect(account_name: str, phone_or_name: str = ""):
    extra = f" ({phone_or_name})" if phone_or_name else ""
    print(f"{DIM}[{_timestamp()}]{RESET} 🔑 {BOLD}[{account_name}]{RESET}{extra} Connected & Ready")

def log_send_success(account_name: str, group_name: str, message: str):
    print(f"{DIM}[{_timestamp()}]{RESET} ✅ {BOLD}[{account_name}]{RESET} -> {CYAN}{group_name}{RESET} : {GREEN}\"{message}\"{RESET}")

def log_send_error(account_name: str, group_name: str, error_msg: str):
    print(f"{DIM}[{_timestamp()}]{RESET} ❌ {BOLD}[{account_name}]{RESET} -> {RED}{group_name}{RESET} : {error_msg}")

def log_captcha_solved(account_name: str, group_name: str, detail: str, source: str = "Instant"):
    print(f"{DIM}[{_timestamp()}]{RESET} 🧩 {BOLD}[{account_name}]{RESET} -> {YELLOW}{group_name}{RESET} Solved Captcha [{source}]: {BOLD}{detail}{RESET}")


def _like_change(delta):
    if delta is None:
        return f"{YELLOW}first recorded day{RESET}"
    color = GREEN if delta > 0 else RED if delta < 0 else CYAN
    return f"{color}{delta:+,}{RESET}"


def log_like_result(account_name: str, uid: str, likes: int, delta, player_name=None, added_since_prev=None):
    name_str = f" ({CYAN}{player_name}{RESET})" if player_name else ""
    added_str = f" • added {GREEN}{added_since_prev:+,}{RESET}" if added_since_prev is not None and added_since_prev != 0 else ""
    print(
        f"{DIM}[{_timestamp()}]{RESET} 📈 {BOLD}[{account_name}]{RESET} "
        f"UID {CYAN}{uid}{RESET}{name_str} • likes {GREEN}{likes:,}{RESET}{added_str} "
        f"• daily change {_like_change(delta)}"
    )


def log_like_daily_summary(day: str, daily: dict, captured=None, expected=None):
    border = "=" * 76
    print(f"\n{CYAN}{border}{RESET}")
    print(f"{BOLD}  DAILY LIKES BY UID • {day} IST{RESET}")
    if captured is not None and expected is not None:
        capture_color = GREEN if captured == expected else YELLOW
        print(f"  Replies captured: {capture_color}{captured}/{expected}{RESET}")
    print(f"{CYAN}{'-' * 76}{RESET}")
    if not daily:
        print(f"  {YELLOW}No likes recorded for this date.{RESET}")
    else:
        print(f"  {BOLD}{'UID':<10}  {pad_display('Player Name', 14)}  {'Likes':>9}   {'Added':>7}   {'Daily Change'}{RESET}")
        print(f"  {'-' * 72}")
        for uid, sample in daily.items():
            name = sample.get("player_name") or "-"
            added = sample.get("change_from_previous_observation")
            likes = sample.get("likes")
            likes_str = f"{likes:,}" if likes is not None else "-"
            if added is not None and added != 0:
                ac = GREEN if added > 0 else RED
                added_str = f"{ac}{added:>+7,}{RESET}"
            else:
                added_str = f"{DIM}{'-':>7}{RESET}"
            padded_name = pad_display(name[:13], 14)
            print(
                f"  {CYAN}{uid:<10}{RESET}  "
                f"{BOLD}{padded_name}{RESET}  "
                f"{GREEN}{likes_str:>9}{RESET}   "
                f"{added_str}   "
                f"{_like_change(sample.get('increase_from_previous_recorded_day'))}"
            )
    print(f"{CYAN}{border}{RESET}\n")


def log_like_report_table(report: dict, json_path=None, markdown_path=None):
    day = report.get("date", "")
    border = "=" * 76
    sep = "-" * 76
    print(f"\n{CYAN}{border}{RESET}")
    print(f"{BOLD}DAILY LIKES REPORT • {day} (IST){RESET}".center(84))
    print(f"{CYAN}{sep}{RESET}")
    print(f"  {BOLD}{'UID':<10}  {pad_display('Player Name', 14)}  {'Likes':>9}   {'Prev Day':>10}  {'Change':>8}   {'Status'}{RESET}")
    print(f"{CYAN}{sep}{RESET}")

    uids = report.get("uids", {})
    if not uids:
        print(f"  {YELLOW}No UIDs found in history.{RESET}")

    for uid, row in uids.items():
        name = row.get("player_name") or "-"
        likes = row.get("likes")
        likes_str = f"{likes:,}" if likes is not None else "-"
        prev_day = row.get("previous_recorded_day") or "-"
        delta = row.get("increase_since_previous_record")

        if delta is not None:
            change_color = GREEN if delta > 0 else RED if delta < 0 else CYAN
            change_str = f"{change_color}{delta:>+8,}{RESET}"
        else:
            change_str = f"{DIM}{'-':>8}{RESET}"

        status_type = row.get("status")
        if status_type == "baseline":
            status_desc = f"{YELLOW}First day{RESET}"
        elif status_type == "gap":
            status_desc = f"{YELLOW}Gap ({row.get('comparison_days')}d){RESET}"
        elif status_type == "missing_today":
            status_desc = f"{RED}Missing{RESET}"
        else:
            status_desc = f"{GREEN}Daily {delta:+,}{RESET}"

        padded_name = pad_display(name[:13], 14)
        print(
            f"  {CYAN}{uid:<10}{RESET}  "
            f"{BOLD}{padded_name}{RESET}  "
            f"{GREEN}{likes_str:>9}{RESET}   "
            f"{DIM}{prev_day:>10}{RESET}  "
            f"{change_str}   "
            f"{status_desc}"
        )

    print(f"{CYAN}{sep}{RESET}")
    if json_path or markdown_path:
        parts = []
        if json_path:
            parts.append(str(json_path).replace("\\", "/").split("data/")[-1])
        if markdown_path:
            parts.append(str(markdown_path).replace("\\", "/").split("data/")[-1])
        print(f"  {DIM}Report files: data/{' & data/'.join(parts)}{RESET}")
    print(f"{CYAN}{border}{RESET}\n")

def log_flood_wait(account_name: str, wait_seconds: int):
    print(f"{DIM}[{_timestamp()}]{RESET} ⏳ {YELLOW}[{account_name}]{RESET} Rate limited (FloodWait): Pausing {wait_seconds}s...")

def log_human_break(account_name: str, break_seconds: int):
    print(f"{DIM}[{_timestamp()}]{RESET} ☕ {DIM}[{account_name}] Humanization pause for {int(break_seconds)}s...{RESET}")

def log_summary_box(elapsed_sec: float, total_sent: int, total_failed: int, account_stats: dict):
    """Prints a beautiful summary card suited for Android, Windows, and CI consoles."""
    width = 52
    border = "=" * width
    total = total_sent + total_failed
    rate = (total_sent / total * 100) if total > 0 else 0.0

    print(f"\n{CYAN}{border}{RESET}")
    print(f"{BOLD}{'EXECUTION SUMMARY'.center(width)}{RESET}")
    print(f"{CYAN}{'-' * width}{RESET}")
    print(f" ⏱️  Runtime      : {elapsed_sec:.1f}s")
    print(f" ✅ Delivered    : {GREEN}{total_sent}{RESET}")
    print(f" ❌ Errors       : {RED if total_failed > 0 else DIM}{total_failed}{RESET}")
    print(f" 📈 Success Rate : {BOLD}{rate:.1f}%{RESET}")

    if account_stats:
        print(f"{CYAN}{'-' * width}{RESET}")
        print(f" {DIM}Account Breakdown:{RESET}")
        for acc, s in account_stats.items():
            tot = s['sent'] + s['failed']
            acc_rate = (s['sent'] / tot * 100) if tot > 0 else 0.0
            print(f"  • {acc:<12} : ✅ {s['sent']:<3} | ❌ {s['failed']:<2} | {acc_rate:.0f}%")

    print(f"{CYAN}{border}{RESET}\n")
