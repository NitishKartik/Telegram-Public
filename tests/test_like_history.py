import asyncio
import sys
import unittest
from datetime import datetime
from pathlib import Path
from unittest.mock import patch

from src.core import like_history
from src.engines.level_query import wait_for_level_reply

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())


class FakeMessage:
    out = False
    reply_to_msg_id = 42

    def __init__(self, text):
        self.raw_text = text

    async def get_sender(self):
        return type("Bot", (), {"bot": True})()


class FakeClient:
    def __init__(self):
        self.calls = 0

    async def iter_messages(self, group_id, min_id, limit):
        self.calls += 1
        if self.calls == 1:
            yield FakeMessage("Fetching Level Information For 1852353345...")
        else:
            yield FakeMessage("├─ UID: 1852353345\n├─ Likes: 126,067")


class LikeHistoryTests(unittest.IsolatedAsyncioTestCase):
    async def test_waits_for_edited_reply(self):
        client = FakeClient()
        likes, _ = await wait_for_level_reply(
            client, -1003451378152, 42, "1852353345", timeout_seconds=5
        )
        self.assertEqual(likes, 126067)
        self.assertEqual(client.calls, 2)

    def test_extract_player_name(self):
        sample_reply = "Level Information\n┌ Level Information\n├─ UID: 1852353345\n├─ Username: Ƙᴀɪᴅɪ⁷⁸⁶\n├─ Likes: 126,066"
        self.assertEqual(like_history.extract_player_name(sample_reply), "Ƙᴀɪᴅɪ⁷⁸⁶")
        self.assertEqual(like_history.extract_likes(sample_reply), 126066)
        self.assertEqual(like_history.extract_uid(sample_reply), "1852353345")

    def test_per_uid_daily_change_and_repeat_query(self):
        history_path = Path(__file__).with_name("_like_history_test.json")
        try:
            with patch.object(like_history, "HISTORY_PATH", history_path):
                for uid, likes, date, name in [
                    ("1", 100, "2026-11-08T10:00:00+05:30", "PlayerOne"),
                    ("2", 50, "2026-11-08T10:00:00+05:30", "PlayerTwo"),
                    ("1", 107, "2026-11-09T10:00:00+05:30", "PlayerOne"),
                    ("2", 54, "2026-11-09T10:00:00+05:30", "PlayerTwo"),
                    ("1", 115, "2026-11-09T12:00:00+05:30", "PlayerOne"),
                ]:
                    entry = like_history.record_likes(uid, likes, datetime.fromisoformat(date), player_name=name)
                # The last update for UID 1 increased from 107 to 115 (+8 added)
                self.assertEqual(entry["change_from_previous_observation"], 8)
                self.assertEqual(entry["player_name"], "PlayerOne")

                data = like_history.load_history()
                day = like_history.daily_uid_summary(data, "2026-11-09")
                self.assertEqual(day["1"]["likes"], 115)
                self.assertEqual(day["1"]["player_name"], "PlayerOne")
                self.assertEqual(day["1"]["increase_from_previous_recorded_day"], 15)
                self.assertEqual(day["1"]["change_from_previous_observation"], 8)
                self.assertEqual(day["2"]["likes"], 54)
                self.assertEqual(day["2"]["increase_from_previous_recorded_day"], 4)
                self.assertNotIn("daily_totals", data)
        finally:
            history_path.unlink(missing_ok=True)


if __name__ == "__main__":
    unittest.main()
