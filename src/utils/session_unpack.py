"""
Automated Telegram Sessions Unpacker for GitHub Actions.
Restores lightweight StringSession files (Session/<name>.txt) from TELEGRAM_SESSIONS,
with fallback support for legacy tar.gz SESSIONS_PART_1 / SESSIONS_PART_2.
"""

import base64
import io
import json
import os
import tarfile
from pathlib import Path


def unpack_sessions() -> bool:
    target_dir = Path("Session")
    target_dir.mkdir(parents=True, exist_ok=True)

    raw_json = os.environ.get("TELEGRAM_SESSIONS", "").strip()
    if raw_json:
        sessions = json.loads(raw_json)
        for name, session_str in sessions.items():
            clean_name = name[:-8] if name.endswith(".session") else name
            (target_dir / f"{clean_name}.txt").write_text(session_str.strip(), encoding="utf-8")
        print(f"[session_unpack] Restored {len(sessions)} StringSession(s) into Session/")
        return True

    part1 = os.environ.get("SESSIONS_PART_1", "").strip()
    part2 = os.environ.get("SESSIONS_PART_2", "").strip()
    if not part1 and not part2:
        print("[session_unpack] Notice: No session secrets found in environment.")
        return False

    compressed_bytes = base64.b64decode((part1 + part2).strip())
    with tarfile.open(fileobj=io.BytesIO(compressed_bytes), mode="r:gz") as tar:
        tar.extractall(path=target_dir)

    restored = list(target_dir.glob("*.session"))
    print(f"[session_unpack] Unpacked {len(restored)} legacy .session file(s) into Session/")
    return True


if __name__ == "__main__":
    unpack_sessions()
