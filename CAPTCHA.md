# 🧩 Telegram Bot Captcha Engine & Configuration Guide

This guide provides a universal reference for the **Captcha Engine** parameters in `master_config.json`. Anyone can use this document to understand, configure, or fine-tune automated captcha handling and fleet behavior across different Telegram groups and channels.

---

## 1. Captcha Parameters Reference

Under each group in your job definitions (`jobs.<job_name>.groups[]`), the following parameters control captcha behavior:

```json
{
  "id": -1003739609039,
  "solve_captcha": true,
  "captcha_type": "all",
  "ghost_mode": false,
  "active": true
}
```

### Parameter Breakdown

| Parameter | Type | Allowed Values | Default | Description |
| :--- | :---: | :--- | :---: | :--- |
| **`solve_captcha`** | `boolean` | `true`, `false` | `false` | Master toggle. If `false`, the bot will completely ignore any captcha challenge messages in this group. |
| **`captcha_type`** | `string` | `"none"`, `"all"`, `"math"`, `"button"` | `"all"` | Tells the engine precisely what kind of challenge to look for and solve in this specific group. |
| **`ghost_mode`** | `boolean` | `true`, `false` | `false` | When `true`, automatically deletes the sent message after 120 seconds to keep chats clean and prevent history spam. |
| **`active`** | `boolean` | `true`, `false` | `true` | If `false`, the bot fleet skips this group during the execution cycle. |

---

## 2. Supported `captcha_type` Values

### 1. `"all"` *(Recommended Default)*
- **Behavior**: Dual-engine solver.
- First looks for inline math arithmetic expressions (`num1 +/-/*// num2 = ?`) and clicks the matching numbered button.
- If no math is found or if parsing fails, it safely falls back to clicking the first interactive confirmation button (universal verify button).
- **When to use**: When a group may rotate between math questions and verification buttons, or when the exact challenge style is unknown.

### 2. `"math"`
- **Behavior**: Strictly solves arithmetic equations.
- Regular expression parses the bot's challenge text (e.g. `12 + 7 = ?`, `45 - 9 = ?`, `6 * 3 = ?`).
- Calculates the answer and clicks the exact button containing that numerical value.
- **When to use**: FreeFire bot groups that present `15 + 4 = ?` style verification prompts.

### 3. `"button"`
- **Behavior**: Universal button clicker.
- Solves prompts by clicking the bot's inline confirmation button (e.g. `[ Click here to verify ]`, `[ I am human ]`, `[ Confirm ]`).
- **When to use**: Groups that require a simple button tap without an arithmetic equation.

### 4. `"none"`
- **Behavior**: Captcha detection is deactivated for this group.
- Useful if a group does not use a verification bot or if you want to bypass captcha processing.

---

## 3. Complete JSON Job Blueprint

Below is a complete, copy-pasteable example of how to configure jobs in `config/master_config.json`:

```json
{
  "jobs": {
    "myCustomJob": {
      "groups": [
        {
          "id": -1003739609039,
          "solve_captcha": true,
          "captcha_type": "math",
          "ghost_mode": false,
          "active": true
        },
        {
          "id": -1002700686902,
          "solve_captcha": true,
          "captcha_type": "button",
          "ghost_mode": false,
          "active": true
        },
        {
          "id": "@ExampleGroupWithoutCaptcha",
          "solve_captcha": false,
          "captcha_type": "none",
          "ghost_mode": true,
          "active": true
        }
      ],
      "repeat_count": 1,
      "humanization_settings": {
        "show_typing_status": true,
        "wait_between_messages_sec_min": 10,
        "wait_between_messages_sec_max": 20,
        "wait_between_rounds_sec_min": 15,
        "wait_between_rounds_sec_max": 25,
        "take_long_break_after_x_messages": 20,
        "long_break_duration_sec_min": 90,
        "long_break_duration_sec_max": 120,
        "account_startup_delay_sec_min": 2,
        "account_startup_delay_sec_max": 5
      },
      "accounts": [
        {
          "name": "Nitish1",
          "session": "nitish1",
          "message": "/like 10053791024",
          "active": true
        },
        {
          "name": "Yogesh",
          "session": "yogeshAnytime",
          "message": "/like 16241701976",
          "active": true
        }
      ]
    }
  }
}
```

---

## 4. Humanization Settings Reference

These parameters prevent Telegram spam limits and account bans:

| Parameter | Type | Recommended Value | Condition / Purpose |
| :--- | :---: | :---: | :--- |
| **`show_typing_status`** | `bool` | `true` | Simulates real user keystroke typing indicator before sending. |
| **`wait_between_messages_sec_min`** | `int` | `10` – `30` | Minimum sleep time between successive messages from an account. |
| **`wait_between_messages_sec_max`** | `int` | `20` – `45` | Maximum sleep time between successive messages (jittered randomly). |
| **`wait_between_rounds_sec_min`** | `int` | `15` – `30` | Pause duration between iterations when `repeat_count > 1`. |
| **`wait_between_rounds_sec_max`** | `int` | `30` – `60` | Maximum pause duration between rounds. |
| **`take_long_break_after_x_messages`** | `int` | `10` – `30` | Triggers a resting break after this many messages. Set to `9999` for rapid tests. |
| **`long_break_duration_sec_min`** | `int` | `90` – `180` | Minimum duration of resting break. |
| **`long_break_duration_sec_max`** | `int` | `120` – `300` | Maximum duration of resting break. |
| **`account_startup_delay_sec_min`** | `int` | `2` – `10` | Staggers when account 2, 3, etc. begin execution so accounts do not fire simultaneously. |
| **`account_startup_delay_sec_max`** | `int` | `5` – `20` | Maximum stagger delay for account fleet initialization. |

---

## 5. Account Parameters Reference

Under `accounts[]`:

| Field | Type | Description |
| :--- | :---: | :--- |
| **`name`** | `string` | Display label for console logs and telemetry breakdown. |
| **`session`** | `string` | Base filename of `.session` in `data/sessions/` (e.g. `"nitish1"` or `"nitish1.session"`). |
| **`message`** or **`messages`** | `str` or `list[str]` | A single command string (e.g. `"/like 10053791024"`) or list of multiple messages to dispatch sequentially. |
| **`active`** | `bool` | If `false`, the engine skips this account. |
