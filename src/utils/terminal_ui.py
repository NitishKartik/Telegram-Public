import sys
from datetime import datetime

# Guarantee safe UTF-8 terminal encoding on Windows / Termux / Linux
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Check if terminal supports color
def _use_color():
    return hasattr(sys.stdout, "isatty") and sys.stdout.isatty()

# ANSI Color Codes
CYAN = "\033[36m" if _use_color() else ""
GREEN = "\033[32m" if _use_color() else ""
YELLOW = "\033[33m" if _use_color() else ""
RED = "\033[31m" if _use_color() else ""
BOLD = "\033[1m" if _use_color() else ""
DIM = "\033[2m" if _use_color() else ""
RESET = "\033[0m" if _use_color() else ""

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
