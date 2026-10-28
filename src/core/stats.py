import time
from collections import defaultdict
from typing import Optional
from src.utils.terminal_ui import log_summary_box

class BotStats:
    """Thread-safe statistics tracker for message fleet delivery."""
    def __init__(self):
        self.total_sent = 0
        self.total_failed = 0
        self.account_stats = defaultdict(lambda: {"sent": 0, "failed": 0})
        self.start_time = time.time()
    
    def add_success(self, account_name: str):
        self.total_sent += 1
        self.account_stats[account_name]["sent"] += 1
    
    def add_failure(self, account_name: str):
        self.total_failed += 1
        self.account_stats[account_name]["failed"] += 1
    
    def get_elapsed_time(self) -> float:
        return time.time() - self.start_time
    
    def print_stats(self, milestone: Optional[int] = None):
        elapsed = self.get_elapsed_time()
        log_summary_box(elapsed, self.total_sent, self.total_failed, dict(self.account_stats))

def print_progress_bar(current: int, total: int, prefix: str = "Progress", length: int = 25):
    if total == 0:
        percent = 1.0
    else:
        percent = current / total
    filled = int(length * percent)
    bar = "━" * filled + "─" * (length - filled)
    print(f"\r  {prefix} ╸[{bar}]╸ {percent * 100:.0f}% ({current}/{total})", end="", flush=True)
