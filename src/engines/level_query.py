"""Send one guarded /level query through the configured Telegram session."""

import asyncio

from src.config import API_HASH, API_ID, get_sessions_dir, load_json_config
from src.core.like_history import extract_likes, extract_uid
from src.utils.schedule_guard import check_cron_window, check_public_workflows


def info_bot_group_id() -> int:
    job = load_json_config()["jobs"]["info_bot"]
    active_groups = [
        group["id"] if isinstance(group, dict) else group
        for group in job["groups"]
        if not isinstance(group, dict) or group.get("active", True)
    ]
    if len(active_groups) != 1:
        raise RuntimeError("Expected exactly one active info_bot group")
    return int(active_groups[0])


async def wait_for_level_reply(client, group_id: int, sent_id: int,
                               uid: str, timeout_seconds: int = 120):
    """Poll until a matching bot reply is complete, including edited placeholders."""
    deadline = asyncio.get_running_loop().time() + timeout_seconds
    while asyncio.get_running_loop().time() < deadline:
        async for message in client.iter_messages(group_id, min_id=sent_id, limit=30):
            if message.out or not message.raw_text or extract_uid(message.raw_text) != uid:
                continue
            reply_to = getattr(message, "reply_to_msg_id", None)
            if reply_to is not None and reply_to != sent_id:
                continue
            sender = await message.get_sender()
            if not getattr(sender, "bot", False):
                continue
            try:
                likes = extract_likes(message.raw_text)
            except ValueError:
                continue
            return likes, message
        await asyncio.sleep(2)
    raise TimeoutError(f"No completed /level reply for UID {uid} within {timeout_seconds}s")


async def send_level(uid: str, timeout_seconds: int = 120, force: bool = False) -> tuple[str, int]:
    from telethon import TelegramClient

    if not API_ID or not API_HASH:
        raise RuntimeError("Telegram API credentials are missing")
    if not force:
        check_cron_window()
        check_public_workflows()
    session = get_sessions_dir() / "nitish1.session"
    if not session.is_file():
        raise FileNotFoundError(session)
    group_id = info_bot_group_id()

    async with TelegramClient(str(session), API_ID, API_HASH) as client:
        if not await client.is_user_authorized():
            raise RuntimeError("nitish1 session is no longer authorized")
        sent = await client.send_message(group_id, f"/level {uid}")
        print(f"Sent /level {uid} to {group_id}; message ID {sent.id}")
        _, message = await wait_for_level_reply(
            client, group_id, sent.id, uid, timeout_seconds=timeout_seconds
        )
        return message.raw_text, message.id
