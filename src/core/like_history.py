"""Parse /level bot replies and maintain per-UID daily likes history."""

import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
HISTORY_PATH = ROOT / "data" / "like_history.json"
IST = timezone(timedelta(hours=5, minutes=30))
UID_PATTERN = re.compile(r"(?im)\bUID\s*:\s*(\d+)\b")
LIKES_PATTERN = re.compile(
    r"(?im)^\s*(?:[^\w\n]*\s*)?(?:total\s+|current\s+)?likes?\s*(?:count)?\s*[:=\-]\s*([\d][\d,]*)\b"
)
PLAYER_NAME_PATTERN = re.compile(
    r"(?im)^\s*(?:[^\w\n]*\s*)?(?:Username|Player Name|Player|Name|IGN|Nick(?:name)?)\s*[:=\-]\s*(.+?)\s*$"
)


def extract_uid(reply: str) -> str | None:
    match = UID_PATTERN.search(reply)
    return match.group(1) if match else None


def extract_player_name(reply: str) -> str | None:
    match = PLAYER_NAME_PATTERN.search(reply)
    if match:
        name = match.group(1).strip()
        return name if name else None
    return None


def extract_likes(reply: str) -> int:
    """Require exactly one labeled likes field, ignoring UID and level values."""
    matches = [int(value.replace(",", "")) for value in LIKES_PATTERN.findall(reply)]
    if len(matches) != 1:
        raise ValueError(f"Expected one labeled likes value; found {len(matches)}")
    return matches[0]


def load_history() -> dict:
    if HISTORY_PATH.exists():
        data = json.loads(HISTORY_PATH.read_text(encoding="utf-8"))
    else:
        data = {"timezone": "Asia/Kolkata", "uids": {}}
    rebuild_daily_changes(data)
    return data


def rebuild_daily_changes(data: dict) -> None:
    data.pop("daily_totals", None)
    for entry in data.get("uids", {}).values():
        daily = entry.get("daily", {})
        previous_day = None
        player_name = entry.get("player_name")
        for day in sorted(daily):
            sample = daily[day]
            if player_name and "player_name" not in sample:
                sample["player_name"] = player_name
            sample["previous_recorded_day"] = previous_day
            sample["increase_from_previous_recorded_day"] = (
                sample["likes"] - daily[previous_day]["likes"]
                if previous_day else None
            )
            previous_day = day
        if daily:
            latest_day = max(daily, key=lambda d: daily[d]["observed_at"])
            latest = daily[latest_day]
            entry["latest"] = {
                "likes": latest["likes"],
                "observed_at": latest["observed_at"],
            }
            if player_name or latest.get("player_name"):
                entry["player_name"] = player_name or latest.get("player_name")
                entry["latest"]["player_name"] = entry["player_name"]
            entry["previous_recorded_day"] = latest["previous_recorded_day"]
            entry["change_from_previous_recorded_day"] = (
                latest["increase_from_previous_recorded_day"]
            )


def daily_uid_summary(data: dict, day: str) -> dict:
    summary = {}
    for uid, entry in sorted(data.get("uids", {}).items()):
        if day in entry.get("daily", {}):
            sample = dict(entry["daily"][day])
            if "player_name" not in sample and entry.get("player_name"):
                sample["player_name"] = entry["player_name"]
            if "telegram_username" not in sample and entry.get("telegram_username"):
                sample["telegram_username"] = entry["telegram_username"]
            sample["change_from_previous_observation"] = entry.get("change_from_previous_observation")
            summary[uid] = sample
    return summary


def save_history(data: dict) -> None:
    rebuild_daily_changes(data)
    HISTORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    temp_path = HISTORY_PATH.with_suffix(".json.tmp")
    temp_path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    os.replace(temp_path, HISTORY_PATH)


def record_likes(
    uid: str,
    likes: int,
    observed_at: datetime | None = None,
    player_name: str | None = None,
    telegram_username: str | None = None,
) -> dict:
    if not re.fullmatch(r"\d+", uid):
        raise ValueError("UID must contain digits only")
    if likes < 0:
        raise ValueError("Likes cannot be negative")
    now = (observed_at or datetime.now(IST)).astimezone(IST)
    day = now.date().isoformat()
    data = load_history()
    entry = data.setdefault("uids", {}).setdefault(uid, {"daily": {}})
    daily = entry.setdefault("daily", {})
    if player_name:
        entry["player_name"] = player_name
    if telegram_username:
        entry["telegram_username"] = telegram_username

    existing = daily.get(day)
    if existing and datetime.fromisoformat(existing["observed_at"]) >= now and existing.get("likes") == likes:
        changed = False
        if player_name and not existing.get("player_name"):
            existing["player_name"] = player_name
            changed = True
        if telegram_username and not existing.get("telegram_username"):
            existing["telegram_username"] = telegram_username
            changed = True
        if changed:
            save_history(data)
        return entry

    prior_observation = entry.get("latest")
    added_since_prev = (likes - prior_observation["likes"]) if prior_observation else None

    sample = {
        "likes": likes,
        "observed_at": now.isoformat(),
    }
    if entry.get("player_name"):
        sample["player_name"] = entry["player_name"]
    if entry.get("telegram_username"):
        sample["telegram_username"] = entry["telegram_username"]
    if added_since_prev is not None:
        sample["added_since_previous_observation"] = added_since_prev

    daily[day] = sample
    if not prior_observation or datetime.fromisoformat(prior_observation["observed_at"]) <= now:
        entry["latest"] = sample
        entry["change_from_previous_observation"] = added_since_prev
        if prior_observation:
            entry["previous_likes"] = prior_observation["likes"]

    save_history(data)
    return entry
