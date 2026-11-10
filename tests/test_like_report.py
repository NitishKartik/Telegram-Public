import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from src.core import like_history, like_report


def sample(likes, day):
    return {"likes": likes, "observed_at": f"{day}T03:35:00+05:30"}


class LikeReportTests(unittest.TestCase):
    def test_baseline_is_not_zero_growth(self):
        report = like_report.build_report({"uids": {"123": {
            "daily": {"2026-11-09": sample(100, "2026-11-09")}
        }}}, "2026-11-09")
        self.assertEqual(report["uids"]["123"]["status"], "baseline")
        self.assertIsNone(report["uids"]["123"]["daily_increase"])

    def test_latest_same_day_value_is_compared_per_uid(self):
        history = {"uids": {
            "123": {"daily": {
                "2026-11-08": sample(100, "2026-11-08"),
                "2026-11-09": sample(110, "2026-11-09"),
            }},
            "456": {"daily": {
                "2026-11-08": sample(50, "2026-11-08"),
                "2026-11-09": sample(48, "2026-11-09"),
            }},
        }}
        history["uids"]["123"]["daily"]["2026-11-09"] = sample(125, "2026-11-09")
        rows = like_report.build_report(history, "2026-11-09")["uids"]
        self.assertEqual(rows["123"]["daily_increase"], 25)
        self.assertEqual(rows["456"]["daily_increase"], -2)

    def test_gap_is_not_reported_as_single_day_growth(self):
        report = like_report.build_report({"uids": {"123": {"daily": {
            "2026-11-06": sample(100, "2026-11-06"),
            "2026-11-09": sample(130, "2026-11-09"),
        }}}}, "2026-11-09")
        row = report["uids"]["123"]
        self.assertEqual(row["status"], "gap")
        self.assertEqual(row["comparison_days"], 3)
        self.assertEqual(row["increase_since_previous_record"], 30)
        self.assertIsNone(row["daily_increase"])
        self.assertIn("+30 over 3 days", like_report.render_markdown(report))

    def test_uid_without_current_observation_remains_in_report(self):
        row = like_report.build_report({"uids": {"123": {"daily": {
            "2026-11-08": sample(100, "2026-11-08"),
        }}}}, "2026-11-09")["uids"]["123"]
        self.assertEqual(row["status"], "missing_today")
        self.assertIsNone(row["likes"])
        self.assertEqual(row["previous_likes"], 100)
        self.assertIsNone(row["increase_since_previous_record"])

    def test_generation_preserves_history_and_writes_summary(self):
        test_root = Path(__file__).resolve().parent
        with tempfile.TemporaryDirectory(dir=test_root) as temp:
            work = Path(temp).resolve()
            self.assertTrue(work.is_relative_to(test_root))
            history_path = work / "history.json"
            contents = json.dumps({"uids": {"123": {"daily": {
                "2026-11-09": sample(100, "2026-11-09"),
            }}}})
            history_path.write_text(contents, encoding="utf-8")
            summary_path = work / "summary.md"
            with patch.object(like_history, "HISTORY_PATH", history_path), \
                    patch.dict("os.environ", {"GITHUB_STEP_SUMMARY": str(summary_path)}), \
                    contextlib.redirect_stdout(io.StringIO()):
                like_report.generate_report({"output_dir": str(work)}, "2026-11-09")
            self.assertEqual(history_path.read_text(encoding="utf-8"), contents)
            self.assertTrue((work / "like_report_2026-11-09.json").is_file())
            self.assertTrue((work / "like_report_2026-11-09.md").is_file())
            summary_content = summary_path.read_text(encoding="utf-8")
            self.assertIn("| 123 |", summary_content)
            self.assertIn("100", summary_content)

    def test_render_telegram_message_card_view(self):
        report = like_report.build_report({
            "uids": {
                "1852353345": {
                    "player_name": "Ƙᴀɪᴅɪ⁷⁸⁶",
                    "telegram_username": "@nitish1201",
                    "daily": {
                        "2026-11-08": sample(126066, "2026-11-08"),
                        "2026-11-09": sample(126181, "2026-11-09"),
                    }
                }
            }
        }, "2026-11-09")
        msg = like_report.render_telegram_message(report)
        self.assertIn("LIKE INFORMATION REPORT • 2026-11-09 • ", msg)
        self.assertIn("┌ Like Info", msg)
        self.assertIn("├─ UID: 1852353345", msg)
        self.assertIn("├─ Nickname: Ƙᴀɪᴅɪ⁷⁸⁶", msg)
        self.assertIn("├─ Last Fetched Likes: 126,066", msg)
        self.assertIn("├─ Latest Fetched Likes: 126,181", msg)
        self.assertIn("├─ Added Likes Today: +115", msg)
        self.assertIn("├─ Current Total Likes: 126,181", msg)
        self.assertIn("└─ @nitish1201", msg)


if __name__ == "__main__":
    unittest.main()
