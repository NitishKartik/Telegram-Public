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
│   ├── like_history.json         <- Per-UID daily likes and changes
│   ├── reports/                  <- Daily JSON and Markdown like reports
│   │   ├── like_report_YYYY-MM-DD.json
│   │   └── like_report_YYYY-MM-DD.md
│   ├── sessions/                 <- Store .session files (Protected by .gitignore)
│   └── dead_sessions/            <- Quarantined banned or expired sessions
├── src/
│   ├── config.py                 <- Path-independent configuration & env loader
│   ├── cli/
│   │   └── like_tracker.py       <- Single-UID query and history commands
│   ├── core/
│   │   ├── like_history.py       <- Bot reply parsing and per-UID daily storage (04:00 AM IST)
│   │   ├── like_report.py        <- Report generation & per-user Telegram card dispatcher
│   │   └── stats.py              <- Live delivery rate & per-account metrics
│   ├── engines/
│   │   ├── captcha.py            <- Math & inline button captcha solver
│   │   ├── level_query.py        <- Guarded single /level Telegram query
│   │   └── runner.py             <- Fleet runner with FloodWait recovery
│   └── utils/
│       ├── history_artifacts.py  <- GitHub Actions history artifact sync & restore
│       ├── logger.py             <- Cross-platform logging utility
│       ├── schedule_guard.py     <- Session collision guard (cron & GHA active checks)
│       ├── session_unpack.py     <- Decodes session bundles from GitHub Secrets
│       └── terminal_ui.py        <- Terminal cards & progress UI
├── tests/                        <- 13 automated test suites
├── .env.example                  <- Credentials template
├── .gitignore                    <- Security barrier
├── COMMANDS.md                   <- Complete CLI command cheat sheet & manual
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

---

## 📈 Daily Likes Tracking & Reporting Engine

The fleet automatically monitors Free Fire player profile growth by dispatching `/level <UID>` queries to game info bots and tracking likes over time.

### Key Capabilities:
- **04:00 AM IST Operational Day Cycle**: Standardized against Free Fire server resets (UTC+05:30) rather than midnight, ensuring accurate 24-hour gain metrics.
- **Intra-Day & Day-over-Day Metrics**: Tracks both immediate changes within the same day (`added_since_previous_observation`) and daily growth (`increase_from_previous_recorded_day`).
- **Dynamic Profile Metadata**: Captures player names and Telegram account usernames directly from bot replies.
- **Automated Report Generation**: Builds JSON and Markdown daily report cards stored in `data/reports/like_report_YYYY-MM-DD.md` and `.json`.
- **Per-User Telegram Card Dispatch**: Dispatches clean, separate Telegram message cards per user with `User: <a href="https://t.me/username">Name</a> (@username)` hyperlinked tags, visual dividers, execution time telemetry (`⚡ Execution Time: X.Xs`), and `link_preview=False`.
- **Pre-Flight Schedule Collision Guard**: Verifies live `cron-job.org` upcoming timers and GitHub Actions runner status before local execution to prevent dual-login session revocation.
- **Automated CI/CD Persistence**: GitHub Actions automatically restores history artifacts (`history_artifacts.py restore`), executes jobs, saves 90-day artifacts (`like-history` and `like-reports`), and commits updated data back to `main` with `[skip ci]`.

### Quick CLI Commands:
```powershell
# View clean single-line daily summary table
python main.py --summary
python main.py --summary 2026-11-11

# Generate daily Markdown/JSON reports and show summary
python main.py --report
python main.py --report 2026-11-11

# Generate reports and dispatch formatted message cards to Telegram
python main.py --report --telegram
python main.py --report --telegram --force   # Bypass schedule guard if needed

# Inspect stored historical JSON for a specific UID
python main.py --show 1852353345

# Guarded single /level query using local session
python main.py --send 1852353345

# Run scheduled cron fleet jobs
python main.py --time info_bot
python main.py --time like_report
```

> 📖 **Full Command Reference:** See [`COMMANDS.md`](COMMANDS.md) for detailed parameter explanations, schedule guard details, and terminal output examples.
