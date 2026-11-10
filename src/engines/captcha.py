import re
import asyncio
import random
from typing import Set, List, Optional
from telethon.tl.custom.message import Message
from src.utils.terminal_ui import log_captcha_solved

CAPTCHA_KEYWORDS = [
    "math", "robot", "captcha", "verify", "confirm",
    "ʀᴏʙᴏᴛ", "ᴄᴏɴғɪʀᴍ", "ᴄᴀᴘᴛᴄʜᴀ", "ᴠᴇʀɪғʏ", "ᴍᴀᴛʜ"
]

async def process_captcha(
    msg_obj: Message,
    extracted_uids: List[str],
    solved_captchas: Set[int],
    account_name: str,
    group_name: str = "Group",
    source: str = "Instant",
    captcha_type: str = "all"
) -> bool:
    """
    Evaluates Telegram bot messages for challenges according to `captcha_type`:
      - "none": Skip solving.
      - "math": Only solve inline math equations (e.g. 5 + 3 = ?).
      - "button": Only click universal verification buttons.
      - "all" (default): Solves math equations first, falls back to button clicking.
    """
    captcha_type_norm = str(captcha_type or "all").strip().lower()
    if captcha_type_norm in ("none", "false", "disabled"):
        return False

    text = msg_obj.raw_text or ""
    text_lower = text.lower()
    
    if not any(kw in text_lower or kw in text for kw in CAPTCHA_KEYWORDS):
        return False
        
    if msg_obj.id in solved_captchas:
        return False

    found_nums = re.findall(r'\d+', text)
    if not any(uid in found_nums for uid in extracted_uids):
        return False
        
    await asyncio.sleep(random.uniform(0.7, 1.3))
    
    if msg_obj.id in solved_captchas:
        return False
        
    match = re.search(r'(\d+)\s*([\+\-\*\/])\s*(\d+)\s*=\s*\?', text)
    
    # 1. Math Captcha Solving
    if match and captcha_type_norm in ("all", "math"):
        num1 = int(match.group(1))
        operator = match.group(2)
        num2 = int(match.group(3))
        
        result = 0
        if operator == '+': result = num1 + num2
        elif operator == '-': result = num1 - num2
        elif operator == '*': result = num1 * num2
        elif operator == '/': result = num1 // num2
        
        buttons = await msg_obj.get_buttons()
        if buttons:
            clicked = False
            for row in buttons:
                for button in row:
                    clean_btn = re.sub(r'[^\d\-]', '', button.text or "")
                    if clean_btn == str(result):
                        try:
                            res = await button.click()
                            cb_msg = getattr(res, 'message', '') or ''
                            if getattr(res, 'alert', False) and ("expired" in cb_msg.lower() or "not for you" in cb_msg.lower()):
                                pass
                            else:
                                solved_captchas.add(msg_obj.id)
                                log_text = f"{num1} {operator} {num2} = {result}"
                                if cb_msg:
                                    log_text += f" [{cb_msg}]"
                                log_captcha_solved(account_name, group_name, log_text, source)
                                clicked = True
                        except Exception:
                            pass
                        break
                if clicked: 
                    break
            
            return clicked

    # 2. Universal / Verification Button Solving
    elif msg_obj.buttons and captcha_type_norm in ("all", "button"):
        try:
            res = await msg_obj.click(0)
            cb_msg = getattr(res, 'message', '') or ''
            if getattr(res, 'alert', False) and ("expired" in cb_msg.lower() or "not for you" in cb_msg.lower()):
                return False
            solved_captchas.add(msg_obj.id)
            log_captcha_solved(account_name, group_name, f"Universal Verification Button [{cb_msg}]" if cb_msg else "Universal Verification Button", source)
            return True
        except Exception:
            pass
            
    return False
