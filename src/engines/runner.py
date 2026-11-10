import asyncio
import random
import re
from pathlib import Path
from typing import List, Dict, Any, Tuple
from telethon import TelegramClient, events
from telethon.tl.types import Channel, Chat, User
from telethon.errors import FloodWaitError, UserBannedInChannelError, ChatWriteForbiddenError

from src.engines.captcha import process_captcha
from src.core.stats import print_progress_bar, BotStats
from src.core.like_history import extract_player_name, record_likes
from src.engines.level_query import wait_for_level_reply
from src.utils.terminal_ui import (
    log_account_connect,
    log_send_success,
    log_send_error,
    log_flood_wait,
    log_human_break,
    log_like_result,
)

async def ghost_delete(client: TelegramClient, chat_id: Any, msg_id: int, delay: int = 120):
    """Deletes sent messages after a specified delay to keep chat clean."""
    await asyncio.sleep(delay)
    try:
        await client.delete_messages(chat_id, msg_id)
    except Exception:
        pass

async def resolve_entity_title(client: TelegramClient, chat_target: Any) -> str:
    """Fetches human-readable channel or group title, falls back to ID/username."""
    try:
        entity = await client.get_entity(chat_target)
        if isinstance(entity, (Channel, Chat)):
            return entity.title
        elif isinstance(entity, User):
            first = entity.first_name or ""
            last = entity.last_name or ""
            return f"@{entity.username}" if entity.username else f"{first} {last}".strip()
    except Exception:
        pass
    return str(chat_target)

async def send_from_account(
    account_name: str,
    session_path: Path,
    msg_list: List[str],
    target_groups: List[Dict[str, Any]],
    repeat_count: int,
    hz_config: Dict[str, Any],
    stats_tracker: BotStats,
    api_id: int,
    api_hash: str,
    initial_delay: float = 0.0,
    track_level_replies: bool = False,
):
    """
    Fleet worker executing humanized message dispatches for a single account.
    Cross-platform safe with clean channel/group name resolution.
    """
    if initial_delay > 0:
        await asyncio.sleep(initial_delay)

    extracted_ff_uids = [
        re.search(r'\d+', str(msg)).group(0) 
        for msg in msg_list if re.search(r'\d+', str(msg))
    ]

    client = None
    solved_captchas = set()
    account_solved_event = asyncio.Event()
    chat_min_ids = {}
    ghost_tasks = []
    captcha_enabled_real_ids = set()
    chat_titles: Dict[int, str] = {}
    chat_captcha_types: Dict[int, str] = {}
    tracked_count = 0

    try:
        client = TelegramClient(str(session_path), api_id, api_hash)

        async def active_sleep(duration: float, stop_on_solve: bool = False):
            poll_interval = 2.0
            elapsed = 0.0
            while elapsed < duration:
                if stop_on_solve and account_solved_event.is_set():
                    await asyncio.sleep(8.0)
                    break
                step = min(poll_interval, duration - elapsed)
                await asyncio.sleep(step)
                elapsed += step

                if not captcha_enabled_real_ids:
                    continue

                for real_chat_id in list(captcha_enabled_real_ids):
                    min_id = chat_min_ids.get(real_chat_id, 0)
                    if min_id == 0:
                        continue
                    try:
                        g_name = chat_titles.get(real_chat_id, str(real_chat_id))
                        c_type = chat_captcha_types.get(real_chat_id, "all")
                        async for msg_obj in client.iter_messages(real_chat_id, limit=3, min_id=min_id):
                            solved = await process_captcha(
                                msg_obj, extracted_ff_uids, solved_captchas,
                                account_name, group_name=g_name, source="Poller",
                                captcha_type=c_type
                            )
                            if solved:
                                account_solved_event.set()
                    except Exception:
                        pass

        @client.on(events.NewMessage)
        @client.on(events.MessageEdited)
        async def catch_captcha(event):
            if event.chat_id not in captcha_enabled_real_ids:
                return
            try:
                g_name = chat_titles.get(event.chat_id, str(event.chat_id))
                c_type = chat_captcha_types.get(event.chat_id, "all")
                solved = await process_captcha(
                    event, extracted_ff_uids, solved_captchas,
                    account_name, group_name=g_name, source="Instant",
                    captcha_type=c_type
                )
                if solved:
                    account_solved_event.set()
            except Exception as e:
                err_str = str(e)
                if "Message ID is invalid" not in err_str and "GetBotCallbackAnswerRequest" not in err_str:
                    pass

        await client.connect()

        if not await client.is_user_authorized():
            log_send_error(account_name, "Session", f"Authorization failed: '{session_path.name}' is expired")
            return

        # Pre-resolve titles of target groups for clean visual logging
        for tg in target_groups:
            raw_id = tg["id"]
            title = await resolve_entity_title(client, raw_id)
            chat_label = f"{title} [{raw_id}]" if title != str(raw_id) else str(raw_id)
            chat_titles[raw_id] = chat_label

        me = await client.get_me()
        user_info = me.first_name if me else ""
        log_account_connect(account_name, user_info)

        total_iterations = repeat_count * len(target_groups) * len(msg_list)
        current_iteration = 0

        if target_groups:
            for i in range(repeat_count):
                for tg in target_groups:
                    raw_id = tg["id"]
                    group_label = chat_titles.get(raw_id, str(raw_id))
                    is_ghost = tg.get("ghost_mode", False)
                    solve_captcha = tg.get("solve_captcha", True)
                    captcha_type = tg.get("captcha_type", "all" if solve_captcha else "none")

                    for msg in msg_list:
                        try:
                            if hz_config.get("show_typing_status", True):
                                try:
                                    async with client.action(raw_id, 'typing'):
                                        await asyncio.sleep(random.uniform(1.0, 2.5))
                                except Exception:
                                    pass

                            sent_msg = await client.send_message(raw_id, msg)
                            real_chat_id = sent_msg.chat_id
                            chat_titles[real_chat_id] = group_label
                            chat_captcha_types[real_chat_id] = captcha_type

                            if real_chat_id not in chat_min_ids:
                                chat_min_ids[real_chat_id] = sent_msg.id
                            if solve_captcha and captcha_type != "none":
                                captcha_enabled_real_ids.add(real_chat_id)

                            stats_tracker.add_success(account_name)
                            log_send_success(account_name, group_label, msg)

                            if track_level_replies:
                                level_match = re.fullmatch(r"/level\s+(\d+)", str(msg).strip())
                                if level_match:
                                    uid = level_match.group(1)
                                    try:
                                        likes, reply = await wait_for_level_reply(
                                            client, real_chat_id, sent_msg.id, uid
                                        )
                                        observed_at = reply.edit_date or reply.date
                                        player_name = extract_player_name(reply.raw_text)
                                        entry = record_likes(uid, likes, observed_at, player_name=player_name)
                                        tracked_count += 1
                                        daily_change = entry.get("change_from_previous_recorded_day")
                                        added_since_prev = entry.get("change_from_previous_observation")
                                        log_like_result(
                                            account_name,
                                            uid,
                                            likes,
                                            daily_change,
                                            player_name=entry.get("player_name"),
                                            added_since_prev=added_since_prev,
                                        )
                                    except Exception as track_error:
                                        print(
                                            f"\n  ⚠️ [{account_name}] UID {uid} likes not recorded: "
                                            f"{track_error}"
                                        )

                            if is_ghost:
                                t = asyncio.create_task(ghost_delete(client, real_chat_id, sent_msg.id, delay=120))
                                ghost_tasks.append(t)

                        except FloodWaitError as flood:
                            stats_tracker.add_failure(account_name)
                            log_flood_wait(account_name, flood.seconds)
                            await asyncio.sleep(flood.seconds)
                        except (UserBannedInChannelError, ChatWriteForbiddenError) as perm_err:
                            stats_tracker.add_failure(account_name)
                            log_send_error(account_name, group_label, f"Permission Denied: {perm_err}")
                        except Exception as group_err:
                            stats_tracker.add_failure(account_name)
                            log_send_error(account_name, group_label, str(group_err)[:50])

                        current_iteration += 1
                        print_progress_bar(current_iteration, total_iterations, f"[{account_name}]")

                        # Humanized delay logic
                        long_break_trigger = hz_config.get("take_long_break_after_x_messages", 0)
                        if long_break_trigger > 0 and current_iteration % long_break_trigger == 0:
                            break_time = random.uniform(
                                hz_config.get("long_break_duration_sec_min", 90),
                                hz_config.get("long_break_duration_sec_max", 120)
                            )
                            log_human_break(account_name, break_time)
                            await active_sleep(break_time)
                        else:
                            is_end_of_round = (current_iteration % (len(target_groups) * len(msg_list)) == 0)
                            if is_end_of_round and i < repeat_count - 1:
                                round_gap = random.uniform(
                                    hz_config.get("wait_between_rounds_sec_min", 15),
                                    hz_config.get("wait_between_rounds_sec_max", 30)
                                )
                                await active_sleep(round_gap)
                            elif current_iteration < total_iterations:
                                msg_delay = random.uniform(
                                    hz_config.get("wait_between_messages_sec_min", 5),
                                    hz_config.get("wait_between_messages_sec_max", 10)
                                )
                                await active_sleep(msg_delay)

            if captcha_enabled_real_ids:
                captcha_wait = float(hz_config.get("captcha_wait_seconds", 15))
                await active_sleep(captcha_wait, stop_on_solve=True)

                # Final Sweep: If not solved, perform a sweep over recent messages to catch delayed bot challenges
                if not account_solved_event.is_set():
                    for real_chat_id in list(captcha_enabled_real_ids):
                        try:
                            g_name = chat_titles.get(real_chat_id, str(real_chat_id))
                            c_type = chat_captcha_types.get(real_chat_id, "all")
                            async for msg_obj in client.iter_messages(real_chat_id, limit=10):
                                solved = await process_captcha(
                                    msg_obj, extracted_ff_uids, solved_captchas,
                                    account_name, group_name=g_name, source="Sweep",
                                    captcha_type=c_type
                                )
                                if solved:
                                    account_solved_event.set()
                                    await asyncio.sleep(2.0)
                                    break
                        except Exception:
                            pass

            if ghost_tasks:
                await asyncio.gather(*ghost_tasks)

    except Exception as e:
        log_send_error(account_name, "Network", str(e)[:70])
    finally:
        if client:
            await client.disconnect()
    return tracked_count
