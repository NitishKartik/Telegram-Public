import io
import json
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import MagicMock

from src.utils import history_artifacts


class HistoryArtifactsTests(unittest.TestCase):
    def test_validate_history_valid(self):
        valid = {
            "timezone": "Asia/Kolkata",
            "uids": {
                "123": {
                    "daily": {
                        "2026-11-09": {"likes": 100, "observed_at": "2026-11-09T05:35:00+05:30"}
                    }
                }
            }
        }
        self.assertEqual(history_artifacts.validate_history(valid), valid)

    def test_validate_history_operational_day_before_4am(self):
        # 03:15 AM on Nov 10 belongs to operational day Nov 09
        valid = {
            "timezone": "Asia/Kolkata",
            "uids": {
                "123": {
                    "daily": {
                        "2026-11-09": {"likes": 105, "observed_at": "2026-11-10T03:15:00+05:30"}
                    }
                }
            }
        }
        self.assertEqual(history_artifacts.validate_history(valid), valid)

    def test_validate_history_invalid(self):
        invalid_tz = {"timezone": "UTC", "uids": {}}
        with self.assertRaises(ValueError):
            history_artifacts.validate_history(invalid_tz)

        invalid_uid = {"timezone": "Asia/Kolkata", "uids": {"abc": {"daily": {}}}}
        with self.assertRaises(ValueError):
            history_artifacts.validate_history(invalid_uid)

    def test_merge_history(self):
        restored = {
            "timezone": "Asia/Kolkata",
            "uids": {
                "123": {
                    "daily": {
                        "2026-11-08": {"likes": 100, "observed_at": "2026-11-08T05:35:00+05:30"},
                        "2026-11-09": {"likes": 110, "observed_at": "2026-11-09T05:35:00+05:30"}
                    }
                }
            }
        }
        seed = {
            "timezone": "Asia/Kolkata",
            "uids": {
                "456": {
                    "daily": {
                        "2026-11-09": {"likes": 50, "observed_at": "2026-11-09T05:35:00+05:30"}
                    }
                }
            }
        }
        merged = history_artifacts.merge_history(restored, seed)
        self.assertIn("123", merged["uids"])
        self.assertIn("456", merged["uids"])
        self.assertEqual(merged["uids"]["123"]["daily"]["2026-11-09"]["likes"], 110)
        self.assertEqual(merged["uids"]["456"]["daily"]["2026-11-09"]["likes"], 50)

    def test_history_from_archive(self):
        payload = {
            "timezone": "Asia/Kolkata",
            "uids": {
                "123": {
                    "daily": {
                        "2026-11-09": {"likes": 100, "observed_at": "2026-11-09T05:35:00+05:30"}
                    }
                }
            }
        }
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w") as z:
            z.writestr("like_history.json", json.dumps(payload))
        archive_bytes = buf.getvalue()

        extracted = history_artifacts.history_from_archive(archive_bytes)
        self.assertEqual(extracted["uids"]["123"]["daily"]["2026-11-09"]["likes"], 100)

    def test_restore_history_seed_fallback(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp) / "like_history.json"
            seed = {
                "timezone": "Asia/Kolkata",
                "uids": {
                    "123": {
                        "daily": {
                            "2026-11-09": {"likes": 100, "observed_at": "2026-11-09T05:35:00+05:30"}
                        }
                    }
                }
            }
            tmp_path.write_text(json.dumps(seed), encoding="utf-8")

            client = MagicMock()
            client.latest_artifact.return_value = None

            result = history_artifacts.restore_history(client, tmp_path)
            self.assertEqual(result, "seed")


if __name__ == "__main__":
    unittest.main()
