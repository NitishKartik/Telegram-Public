"""
Automated Telegram Sessions Unpacker for GitHub Actions.
Safely decodes compressed session bundles passed via GitHub Secrets
(SESSIONS_PART_1 and SESSIONS_PART_2) and restores them to Session/.
"""

import os
import io
import base64
import tarfile
from pathlib import Path


def unpack_sessions() -> bool:
    part1 = os.environ.get("SESSIONS_PART_1", "").strip()
    part2 = os.environ.get("SESSIONS_PART_2", "").strip()

    if not part1 and not part2:
        print("[session_unpack] Notice: No SESSIONS_PART secrets found in environment.")
        return False

    try:
        combined = (part1 + part2).strip()
        compressed_bytes = base64.b64decode(combined)

        target_dir = Path("Session")
        target_dir.mkdir(parents=True, exist_ok=True)

        with tarfile.open(fileobj=io.BytesIO(compressed_bytes), mode="r:gz") as tar:
            tar.extractall(path=target_dir)

        restored = list(target_dir.glob("*.session"))
        print(f"[session_unpack] Successfully unpacked {len(restored)} Telegram session(s) into Session/")
        return True
    except Exception as e:
        print(f"[session_unpack] ERROR: Failed to unpack sessions from secrets: {e}")
        raise


if __name__ == "__main__":
    unpack_sessions()
