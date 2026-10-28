import os
import json
from pathlib import Path
from typing import Dict, Any, Optional, Tuple

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

# Determine Project Root dynamically
PROJECT_ROOT = Path(__file__).resolve().parent.parent

def resolve_credentials() -> Tuple[int, str]:
    """
    Resolves Telegram API credentials in priority order:
    1. Local device file: `credentials/telegram_creds.json`
    2. Environment variables: `TELEGRAM_API_ID` & `TELEGRAM_API_HASH` (Used on GitHub Actions)
    3. Return (0, "") if none found
    """
    creds_file = PROJECT_ROOT / "credentials" / "telegram_creds.json"
    
    # Priority 1: Check device-specific file
    if creds_file.exists():
        try:
            with open(creds_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                file_id = int(data.get("api_id", 0))
                file_hash = str(data.get("api_hash", "")).strip()
                if file_id and file_hash:
                    return file_id, file_hash
        except Exception:
            pass

    # Priority 2: Check environment variables (GitHub Secrets / System env)
    raw_id = os.environ.get("TELEGRAM_API_ID", "").strip()
    api_id = int(raw_id) if raw_id.isdigit() else 0
    api_hash = os.environ.get("TELEGRAM_API_HASH", "").strip()

    return api_id, api_hash

API_ID, API_HASH = resolve_credentials()

def get_config_path(filename: str = "master_config.json") -> Path:
    nested = PROJECT_ROOT / "config" / filename
    if nested.exists():
        return nested
    root = PROJECT_ROOT / filename
    if root.exists():
        return root
    return nested

def get_sessions_dir() -> Path:
    nested = PROJECT_ROOT / "data" / "sessions"
    if nested.exists():
        return nested
    legacy = PROJECT_ROOT / "Session"
    if legacy.exists():
        return legacy
    return nested

def load_json_config(file_path: Optional[Path] = None) -> Dict[str, Any]:
    target = file_path or get_config_path("master_config.json")
    if not target.exists():
        raise FileNotFoundError(f"Configuration file not found: {target}")
    with open(target, "r", encoding="utf-8") as f:
        return json.load(f)
