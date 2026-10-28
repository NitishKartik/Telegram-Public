# 📖 The Telegram Bot Fleet Handbook: From Basics to Production Engineering

> **A Complete Universal Field Guide, Architectural Manual, and Configuration Reference for Distributed Multi-Account Telegram Automation.**
>
> *Author:* Nitish Kartik  
> *Target Platforms:* Windows, Android (Termux), Linux / macOS, and GitHub Actions (Cloud CI/CD)  
> *Compatible Runtimes:* Python 3.10+  

---

## 📑 Table of Contents

1. [Chapter 1: Architectural Philosophy & System Overview](#chapter-1-architectural-philosophy--system-overview)
2. [Chapter 2: Project Layout & Directory Blueprint](#chapter-2-project-layout--directory-blueprint)
3. [Chapter 3: Credential Architecture & The Fallback Engine](#chapter-3-credential-architecture--the-fallback-engine)
4. [Chapter 4: The Master Configuration Manual (`master_config.json`)](#chapter-4-the-master-configuration-manual-master_configjson)
   - [4.1 Root & Job Envelope](#41-root--job-envelope)
   - [4.2 Group Configuration Parameters](#42-group-configuration-parameters)
   - [4.3 Humanization & Anti-Ban Timing Controls](#43-humanization--anti-ban-timing-controls)
   - [4.4 Account Fleet Definitions](#44-account-fleet-definitions)
5. [Chapter 5: The Captcha Engine Manual](#chapter-5-the-captcha-engine-manual)
   - [5.1 Solving Modes & Parameters](#51-solving-modes--parameters)
   - [5.2 Dual-Engine Strategy (Listener vs. Poller)](#52-dual-engine-strategy-listener-vs-poller)
6. [Chapter 6: Cross-Platform Execution Guide](#chapter-6-cross-platform-execution-guide)
   - [6.1 Running on Windows](#61-running-on-windows)
   - [6.2 Running on Android via Termux](#62-running-on-android-via-termux)
   - [6.3 Running in GitHub Actions (Cloud Serverless)](#63-running-in-github-actions-cloud-serverless)
7. [Chapter 7: Practical Field Recipes & Use Case Blueprints](#chapter-7-practical-field-recipes--use-case-blueprints)
   - [Recipe A: Ultra-Fast Captcha Benchmark](#recipe-a-ultra-fast-captcha-benchmark)
   - [Recipe B: Multi-UID Like Campaign (Sequential Routing)](#recipe-b-multi-uid-like-campaign-sequential-routing)
   - [Recipe C: Stealth Ghost Mode Campaign](#recipe-c-stealth-ghost-mode-campaign)
   - [Recipe D: 24/7 Daily Bonus Harvester](#recipe-d-247-daily-bonus-harvester)
8. [Chapter 8: Diagnostics, FloodWait Recovery, & Troubleshooting](#chapter-8-diagnostics-floodwait-recovery--troubleshooting)

---

## Chapter 1: Architectural Philosophy & System Overview

Automating interactions on the Telegram protocol across multiple accounts presents three core engineering challenges:
1. **Telegram Anti-Spam (SpamBot & FloodWait):** Simultaneous automated messages trigger immediate IP or peer flood penalties (`FloodWaitError`).
2. **Interactive Verification Barriers:** Groups deploy bot gatekeepers requiring inline arithmetic equations or confirmation buttons to be solved within seconds.
3. **Cross-Platform Disparity:** Path resolution, process models, and character encodings differ dramatically between Windows (PowerShell/CP1252), Linux (UTF-8 POSIX), and mobile Android environments (Termux bionic libc).

This framework solves these challenges through:
- **Decoupled Architecture:** Configuration (`config/`), credentials (`credentials/`), and business logic (`src/`) are strictly separated.
- **Asynchronous Concurrency:** Built on Python's `asyncio` and `telethon` (MTProto), managing dozens of Telegram sessions concurrently in a non-blocking event loop.
- **Dynamic Entity Resolution:** Group numeric IDs are automatically converted to human-readable group titles at runtime (`GroupName [-100xxxxxxx]`).
- **Resilient Fallback Pipelines:** Credentials flow smoothly from local JSON $\rightarrow$ system environment $\rightarrow$ GitHub Secrets with zero code modifications.

---

## Chapter 2: Project Layout & Directory Blueprint

Below is the production-grade directory layout:

```text
Telegram/
├── .github/
│   └── workflows/
│       └── fleet-runner.yml          # Cloud CI/CD automation workflow
├── config/
│   ├── master_config.json            # Central fleet configuration & scheduled jobs
│   ├── permissions.json              # Access control & privileges
│   └── target_groups.json            # Target group list for quick scripts
├── credentials/
│   ├── README.md                     # Security & usage guidelines
│   └── telegram_creds.json           # [IGNORED IN GIT] Local device credentials
├── data/
│   ├── sessions/                     # [IGNORED IN GIT] Active .session files
│   └── dead_sessions/                # Quarantined / expired session files
├── scripts/
│   └── auto_referral.py              # Interactive terminal referral dispatcher
├── src/
│   ├── __init__.py
│   ├── config.py                     # Path-independent config & credential resolver
│   ├── core/
│   │   ├── __init__.py
│   │   └── stats.py                  # Fleet telemetry, metrics, and progress bars
│   ├── engines/
│   │   ├── __init__.py
│   │   ├── captcha.py                # Math & button challenge solver
│   │   └── runner.py                 # Core asynchronous fleet execution worker
│   └── utils/
│       ├── __init__.py
│       ├── logger.py                 # Structured file & stream logging
│       └── terminal_ui.py            # Visual, mobile-compatible terminal cards
├── .env.example                      # Template for environment variables
├── .gitignore                        # Security filter preventing credential leaks
├── CAPTCHA.md                        # Quick reference for captcha parameters
├── HANDBOOK.md                       # This comprehensive manual
├── main.py                           # Primary CLI entry point
└── requirements.txt                  # Python dependencies
```

---

## Chapter 3: Credential Architecture & The Fallback Engine

The system employs a **3-tier hierarchical credential resolver** in [`src/config.py`](file:///d:/Projects/GitHub%20Projects/Telegram/src/config.py):

```
+-------------------------------------------------------------+
| Tier 1: Local Device File                                   |
| Path: credentials/telegram_creds.json                       |
| Priority: HIGHEST (Overwrites all environment settings)    |
+------------------------------+------------------------------+
                               | (If file missing or empty)
                               v
+-------------------------------------------------------------+
| Tier 2: Environment Variables / .env                         |
| Keys: TELEGRAM_API_ID, TELEGRAM_API_HASH                    |
| Priority: MEDIUM (Used by Termux exports & GitHub Secrets)   |
+------------------------------+------------------------------+
                               | (If environment unset)
                               v
+-------------------------------------------------------------+
| Tier 3: Safe Halt & Informative Prompt                      |
| Return: (0, "") -> Logs clear setup guidance and exits cleanly|
+-------------------------------------------------------------+
```

### The Security Guarantee
The file [`.gitignore`](file:///d:/Projects/GitHub%20Projects/Telegram/.gitignore) contains:
```gitignore
credentials/*.json
credentials/telegram_creds.json
telegram_creds.json
!credentials/README.md
```
Even if you push commits or publish your repository publicly, **your local credentials cannot accidentally leak into Git.** When deploying to GitHub Actions, you delete or omit `telegram_creds.json`, and the script automatically sources secrets from your GitHub repository settings.

---

## Chapter 4: The Master Configuration Manual (`master_config.json`)

The entire operational fleet is configured inside [`config/master_config.json`](file:///d:/Projects/GitHub%20Projects/Telegram/config/master_config.json).

### 4.1 Root & Job Envelope

```json
{
  "_meta_": "MASTER FLEET CONFIGURATION",
  "jobs": {
    "<job_name>": {
      "groups": [ ... ],
      "repeat_count": 1,
      "humanization_settings": { ... },
      "accounts": [ ... ]
    }
  }
}
```

- **`jobs.<job_name>`**: Unique identifier used at the command line (e.g. `py main.py --time 4am`).
- **`repeat_count`**: Integer $\ge 1$. Specifies how many full cycles over all target groups each account should execute.

---

### 4.2 Group Configuration Parameters

Inside `groups[]`, target destinations are defined as structured objects:

```json
{
  "id": -1003739609039,
  "solve_captcha": true,
  "captcha_type": "all",
  "ghost_mode": false,
  "active": true
}
```

| Field | Type | Required | Allowed Values | Description & Best Practice |
| :--- | :---: | :---: | :--- | :--- |
| **`id`** | `int` or `str` | **Yes** | `-100xxxxxxxxx`, `"@username"` | Telegram peer ID or public channel username. Supergroups typically begin with `-100`. |
| **`solve_captcha`** | `bool` | **Yes** | `true`, `false` | Master switch. If `false`, incoming messages in this group are not monitored for challenges. |
| **`captcha_type`** | `str` | **Yes** | `"all"`, `"math"`, `"button"`, `"none"` | Must immediately follow `solve_captcha`. Dictates the algorithm used to evaluate and solve challenges. |
| **`ghost_mode`** | `bool` | No (Default: `false`) | `true`, `false` | If `true`, the bot schedules a background deletion task to wipe the sent message after 120 seconds. |
| **`active`** | `bool` | No (Default: `true`) | `true`, `false` | If `false`, the runner skips this group entirely without needing to delete the configuration block. |

---

### 4.3 Humanization & Anti-Ban Timing Controls

Inside `humanization_settings`:

```json
{
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
}
```

| Parameter | Recommended Default | Functional Description |
| :--- | :---: | :--- |
| **`show_typing_status`** | `true` | Sends a Telegram `typing` action for 1.0 to 2.5 seconds before dispatching the message, mimicking human keystrokes. |
| **`wait_between_messages_sec_min`** | `10` | The lower bound (in seconds) of random sleep between consecutive messages sent by the same account. |
| **`wait_between_messages_sec_max`** | `20` | The upper bound (in seconds) of random sleep between messages. Prevents fixed-frequency detection. |
| **`wait_between_rounds_sec_min`** | `15` | Resting period between complete group rounds when `repeat_count > 1`. |
| **`wait_between_rounds_sec_max`** | `25` | Upper limit for round pauses. |
| **`take_long_break_after_x_messages`** | `20` | Threshold of messages before the account pauses for an extended rest. Set to `9999` for quick testing. |
| **`long_break_duration_sec_min`** | `90` | Minimum duration of the extended break (in seconds). |
| **`long_break_duration_sec_max`** | `120` | Maximum duration of the extended break (in seconds). |
| **`account_startup_delay_sec_min`** | `2` | Stagger offset so Account 2 starts slightly after Account 1, preventing burst spikes. |
| **`account_startup_delay_sec_max`** | `5` | Maximum stagger delay applied cumulatively across the fleet. |

---

### 4.4 Account Fleet Definitions

Inside `accounts[]`:

```json
{
  "name": "Nitish1",
  "session": "nitish1",
  "message": "/like 10053791024",
  "active": true
}
```

- **`name`**: Display label used in console cards and final telemetry reports.
- **`session`**: Filename prefix located in `data/sessions/` (e.g., `"nitish1"` maps to `data/sessions/nitish1.session`).
- **`message`** (or **`messages`**): A single string or an array of strings. If an array is provided, the account dispatches each message sequentially across the targets.
- **`active`**: Toggles whether this account participates in the run.

---

## Chapter 5: The Captcha Engine Manual

### 5.1 Solving Modes & Parameters

The engine evaluates incoming challenges matching trigger keywords (`math`, `robot`, `captcha`, `verify`, `confirm`, `ʀᴏʙᴏᴛ`, `ᴍᴀᴛʜ`) and applies one of the following strategies:

```
                          [ Incoming Event ]
                                  |
                   Is Sender Bot or Group Mention?
                                  |
               +------------------+------------------+
               |                                     |
    [ Matches Math Equation? ]              [ Contains Inline Buttons? ]
               |                                     |
     (captcha_type == "math"               (captcha_type == "button"
       or "all")                             or "all")
               |                                     |
      Evaluate num1 +/-/* num2                Click Button Index 0
               |                                     |
    Click matching button                           Done!
               |
             Done!
```

1. **`"math"`**:
   - Parses regex `(\d+)\s*([\+\-\*\/])\s*(\d+)\s*=\s*\?`.
   - Computes integer arithmetic ($+$, $-$, $\times$, $/$) and clicks the inline button with matching text.
2. **`"button"`**:
   - Skips arithmetic parsing and clicks the first active callback button (universal human verification).
3. **`"all"`**:
   - Dual mode. Attempts math parsing first; if buttons are present but do not match equations, clicks the fallback button.
4. **`"none"`**:
   - Complete bypass. No CPU cycles or listeners spent on messages in this group.

### 5.2 Dual-Engine Strategy (Listener vs. Poller)

Telegram bots often deliver captchas via two different delivery mechanisms:
1. **Push Notifications (`events.NewMessage` & `events.MessageEdited`):** Handled instantly by the event listener with $\le 1.0\text{s}$ response latency.
2. **Silent Message Edits / Delayed Delivery:** Certain server-side bots fail to trigger client event listeners on edited messages. To guarantee a 100% solve rate, the runner includes an **active poller loop** during idle sleep windows that queries `client.iter_messages(limit=3, min_id=...)` to intercept any challenges that bypassed the push listener.

---

## Chapter 6: Cross-Platform Execution Guide

### 6.1 Running on Windows

Open PowerShell or Antigravity Terminal:

```powershell
# 1. Navigate to repository
cd "d:\Projects\GitHub Projects\Telegram"

# 2. Run your target job
py main.py --time testCaptcha_no_ind
```

*Note: Windows automatically loads UTF-8 output modes and ASCII card framing to prevent `cp1252` encoding exceptions.*

---

### 6.2 Running on Android via Termux

1. **Install Prerequisites:**
   ```bash
   pkg update -y && pkg install -y python git libjpeg-turbo
   ```
2. **Clone & Setup:**
   ```bash
   git clone https://github.com/NitishKartik/Telegram.git
   cd Telegram
   pip install -r requirements.txt
   ```
3. **Configure Local Credentials:**
   ```bash
   cat <<EOF > credentials/telegram_creds.json
   {
     "api_id": 1234567,
     "api_hash": "abcdef0123456789abcdef0123456789"
   }
   EOF
   ```
4. **Copy Sessions:**
   Place your `.session` files into `data/sessions/`.
5. **Execute:**
   ```bash
   python main.py --time testCaptcha_no_ind
   ```

---

### 6.3 Running in GitHub Actions (Cloud Serverless)

1. Open your GitHub Repository in your web browser.
2. Navigate to: **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**.
3. Add Repository Secrets:
   - `TELEGRAM_API_ID`: `1234567`
   - `TELEGRAM_API_HASH`: `abcdef0123456789abcdef0123456789`
4. Under the **Actions** tab, select **Telegram Fleet Runner**.
5. Click **Run workflow**, choose your target job from the dropdown menu (e.g. `testCaptcha_no_ind` or `8am`), and click **Run workflow**.

---

## Chapter 7: Practical Field Recipes & Use Case Blueprints

### Recipe A: Ultra-Fast Captcha Benchmark

**Objective:** Test whether a new group's captcha bot is working and responsive in under 30 seconds.

```json
{
  "groups": [
    {
      "id": -1003739609039,
      "solve_captcha": true,
      "captcha_type": "all",
      "active": true
    }
  ],
  "repeat_count": 1,
  "humanization_settings": {
    "show_typing_status": true,
    "wait_between_messages_sec_min": 3,
    "wait_between_messages_sec_max": 5,
    "wait_between_rounds_sec_min": 5,
    "wait_between_rounds_sec_max": 10,
    "take_long_break_after_x_messages": 9999,
    "long_break_duration_sec_min": 0,
    "long_break_duration_sec_max": 0,
    "account_startup_delay_sec_min": 1,
    "account_startup_delay_sec_max": 2
  },
  "accounts": [
    {
      "name": "Tester",
      "session": "nitish1",
      "message": "/like 10053791024",
      "active": true
    }
  ]
}
```

---

### Recipe B: Multi-UID Like Campaign (Sequential Routing)

**Objective:** Dispatch multiple player profile IDs sequentially through each account with healthy delays.

```json
{
  "accounts": [
    {
      "name": "Nitish1",
      "session": "nitish1",
      "messages": [
        "/like 10053791024",
        "/like 16241701976",
        "/like 2512117368"
      ],
      "active": true
    }
  ]
}
```

---

### Recipe C: Stealth Ghost Mode Campaign

**Objective:** Send promotional or command messages that automatically vanish after 2 minutes to keep chat logs clean.

```json
{
  "groups": [
    {
      "id": -1002700686902,
      "solve_captcha": true,
      "captcha_type": "all",
      "ghost_mode": true,
      "active": true
    }
  ]
}
```

---

### Recipe D: 24/7 Daily Bonus Harvester

**Objective:** Claim daily bot bonuses across multiple accounts at high speed without typing indicators.

```json
{
  "groups": [
    {
      "id": "@PRINCE_REFER_BOT",
      "solve_captcha": false,
      "captcha_type": "none",
      "active": true
    }
  ],
  "humanization_settings": {
    "show_typing_status": false,
    "wait_between_messages_sec_min": 3,
    "wait_between_messages_sec_max": 6
  },
  "accounts": [
    {
      "name": "Aman",
      "session": "aman",
      "messages": ["/bonus", "DAILY BONUS"],
      "active": true
    }
  ]
}
```

---

## Chapter 8: Diagnostics, FloodWait Recovery, & Troubleshooting

### 1. `FloodWaitError: A wait of X seconds is required`
- **Root Cause:** Telegram's server-side rate limits have been triggered by excessive request volume.
- **System Behavior:** The fleet engine catches this exception directly, logs:
  ```text
  [12:11:48] ⏳ [Nitish1] Rate limited (FloodWait): Pausing 42s...
  ```
  and suspends execution for that specific session until the penalty expires, after which it safely resumes.
- **Remedy:** Increase `wait_between_messages_sec_min` and `wait_between_messages_sec_max` in your configuration.

### 2. `Session missing or invalid`
- **Root Cause:** The `.session` file is absent in `data/sessions/` or the account was logged out on another device.
- **Remedy:** Verify that `data/sessions/<session_name>.session` exists and is a valid SQLite file.

### 3. `Permission Denied (ChatWriteForbiddenError / UserBannedInChannelError)`
- **Root Cause:** The account is muted or banned in the destination group.
- **System Behavior:** The engine logs the error, marks a failure on the telemetry board, and moves to the next target group without crashing the remaining fleet.

---

### 4. Live Visual Terminal Output Reference

When running cleanly, your terminal renders real-time device-optimized cards:

```text
====================================================
             TELEGRAM BOT FLEET ENGINE              
      Multi-Device • Anti-Ban • Captcha Solver      
====================================================

🎯 JOB: testCaptcha_no_ind
   ├─ 👥 Accounts : 2 active
   ├─ 📢 Targets  : 3 group(s)
   ├─ 🔁 Repeats  : 1 round(s)
   └─ ⏱️  Pacing   : 30s - 30s

[12:11:46] 🔑 [Nitish1] (Nitish) Connected & Ready
[12:11:46] 🔑 [Yogesh] (Yogesh) Connected & Ready
[12:11:48] ✅ [Nitish1] -> FreeFire Group [-1003739609039] : "/like 10053791024"
[12:11:49] 🧩 [Nitish1] -> FreeFire Group [-1003739609039] Solved Captcha [Instant]: 14 + 5 = 19
  [Nitish1] ╸[━━━━━━━━━━]╸ 100% (1/1)

====================================================
                 EXECUTION SUMMARY                  
----------------------------------------------------
 ⏱️  Runtime      : 34.2s
 ✅ Delivered    : 2
 ❌ Errors       : 0
 📈 Success Rate : 100.0%
----------------------------------------------------
 Account Breakdown:
  • Nitish1      : ✅ 1   | ❌ 0  | 100%
  • Yogesh       : ✅ 1   | ❌ 0  | 100%
====================================================
```
