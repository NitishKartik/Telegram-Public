# 🤖 Telegram Auto-Bot Fleet Engine (Production Grade)

A cross-platform, enterprise-grade multi-account Telegram automation fleet engine built with Python and Telethon. Designed to run identically across **Android (Termux)**, **Windows**, and **GitHub Actions**.

Maintained by **Nitish Kartik**.

> 📚 **Complete Documentation Book:** Read [`HANDBOOK.md`](HANDBOOK.md) for an in-depth reference guide, architectural manual, parameter breakdowns, and field recipes.  
> 🧩 **Captcha Reference:** Read [`CAPTCHA.md`](CAPTCHA.md) for dedicated captcha engine parameters.

---

## 🏗️ Production Architecture

```text
Telegram-Public/
├── .github/workflows/
│   └── fleet-runner.yml          <- Cloud execution via GitHub Actions
├── config/
│   └── master_config.json        <- Multi-job scheduled targets & humanization
├── credentials/
│   └── README.md                 <- Device credentials & security guide
├── data/
│   ├── sessions/                 <- Store .session files (Protected by .gitignore)
│   └── dead_sessions/            <- Quarantined banned or expired sessions
├── src/
│   ├── config.py                 <- Path-independent configuration & env loader
│   ├── core/
│   │   └── stats.py              <- Live delivery rate & per-account metrics
│   ├── engines/
│   │   ├── captcha.py            <- Math & inline button captcha solver
│   │   └── runner.py             <- Fleet runner with FloodWait recovery
│   └── utils/
│       ├── logger.py             <- Cross-platform logging utility
│       ├── session_unpack.py     <- Decodes session bundles from GitHub Secrets
│       └── terminal_ui.py        <- Terminal cards & progress UI
├── .env.example                  <- Credentials template
├── .gitignore                    <- Security barrier
├── requirements.txt              <- Dependencies
└── main.py                       <- CLI entry point
```

---

## ⚙️ How It Works

The engine is engineered as an enterprise-grade automation framework designed to handle distributed multi-account Telegram workloads without triggering anti-spam defenses:

1. **Asynchronous MTProto Concurrency**:
   - Built on Telethon and Python `asyncio`, managing multiple active sessions simultaneously in a non-blocking event loop.
   - Each account operates independently with isolated task queues, message dispatchers, and state tracking.

2. **Automated Captcha Engine**:
   - **Push Listener + Idle Poller**: Listens in real-time to bot replies via `events.NewMessage` and `events.MessageEdited`, combined with an active poller loop during idle sleep windows to catch silent message updates.
   - **Math Parsing**: Parses inline arithmetic equations (e.g. `14 + 5 = ?`) via regex and automatically clicks the inline button matching the calculated answer.
   - **Button Solver**: Clicks interactive verification/confirmation buttons (e.g. `[ Click to Verify ]`) when no math equation is present.

3. **FloodWait & Anti-Ban Protection**:
   - **Auto-Recovery**: Catches MTProto `FloodWaitError` exceptions on a per-account basis, pausing only the affected session for the exact penalty duration before safely resuming.
   - **Human Typing Mimicry**: Emulates realistic typing status (`SendMessageUploadDocumentAction` / `SendMessageRecordAudioAction` / `typing`) prior to message transmission.
   - **Pacing & Break Schedules**: Injects randomized sleep intervals between messages, resting periods between complete rounds, and extended breaks after message quotas.
   - **Fleet Staggering**: Delays individual account startup times to eliminate simultaneous connection spikes.

4. **Ghost Mode**:
   - Automatically schedules background message deletion after a specified retention period (e.g. 120 seconds) to maintain chat cleanliness.

5. **Hierarchical Credential Architecture**:
   - Evaluates credentials using a 3-tier fallback order: local credentials file $\rightarrow$ system environment variables $\rightarrow$ CI/CD repository secrets.

---

## 📋 How It Is Configured

All fleet behavior is defined inside `config/master_config.json`:

```json
{
  "_meta_": "MASTER FLEET CONFIGURATION",
  "jobs": {
    "<job_name>": {
      "groups": [
        {
          "id": -1001234567890,
          "solve_captcha": true,
          "captcha_type": "all",
          "ghost_mode": false,
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
          "name": "Account1",
          "session": "session1",
          "message": "/command <args>",
          "active": true
        }
      ]
    }
  }
}
```

### Configuration Sections:
- **`jobs.<job_name>`**: Named execution profiles passed at runtime (e.g., `4am`, `8am`, `info_bot`).
- **`groups[]`**: Target chats/supergroups with per-group captcha solver settings (`all`, `math`, `button`, `none`) and ghost mode toggles.
- **`humanization_settings`**: Anti-ban pacing rules controlling keystroke delays, inter-message pauses, round intervals, resting breaks, and account startup staggering.
- **`accounts[]`**: Accounts assigned to the job, linking `.session` files to dispatch messages (single command string or sequential message arrays).

---

## 🛡️ Anti-Ban & Resiliency Features

- **FloodWait Auto-Recovery**: Intercepts Telegram flood restrictions and pauses the account safely instead of terminating the process.
- **Human Typing Mimicry**: Configurable typing indicator durations before dispatching messages.
- **Automated Math & Button Captcha Solver**: Listens to bot replies in real-time and solves inline math challenges.
- **Ghost Mode**: Scheduled automatic message deletion after broadcast.
- **Path Independence**: Resolves directories dynamically without relying on fixed operating system paths.
