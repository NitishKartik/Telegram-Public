# Telegram Fleet Engine & Likes Tracker — Command Reference Guide

This document lists all available commands in the **Telegram-Public** project with their purpose, syntax, safety rules, and real terminal output examples.

---

## 🛡️ Safety Rule: Before Running Any Command Using `.session` Files

> [!IMPORTANT]
> **Telegram allows only one active Telethon session connection at a time per session string/file.**
> Before running any command that opens a Telegram `.session` file locally (such as `--send` or `--time info_bot`):
> 1. **Check GitHub Actions:** Ensure no scheduled or manual GitHub Actions workflow (`fleet-runner.yml`) is currently running.
> 2. **Check Cron Schedules:** Verify the `cron-job.org` timer (e.g. 3:44 AM IST) is not about to trigger dual-login collisions.
> 3. **Automatic Schedule Guard:** The engine automatically verifies both `check_cron_window()` and `check_public_workflows()` before accessing Telethon. If a remote workflow is active, local execution will safely halt.
> 4. **Credentials Security:** Session files (`*.session`) and credential files (`credentials/*.json`) are strictly excluded by `.gitignore` and must **never** be committed to GitHub.

---

## 📋 Quick Command Cheat Sheet

| Command | Needs Telegram Session? | Modifies History? | Purpose |
|---|:---:|:---:|---|
| `python main.py --summary` | ❌ No | ❌ No | View clean daily likes table with added counts |
| `python main.py --report` | ❌ No | ❌ No | Generate JSON & Markdown reports and view report table |
| `python main.py --report --telegram` | ✅ Yes | ❌ No | Generate reports and dispatch message to Telegram group |
| `python main.py --show <UID>` | ❌ No | ❌ No | Inspect raw JSON history for a specific UID |
| `python main.py --send <UID>` | ✅ Yes | ✅ Yes | Send single guarded `/level` query and record new likes |
| `python main.py --time like_report` | ✅ Yes | ❌ No | Daily 3:44 AM job: generates reports & sends card to group |
| `python main.py --time info_bot` | ✅ Yes | ✅ Yes | Run full fleet to query `/level` for all tracked UIDs |
| `python main.py --time 4am` | ✅ Yes | ❌ No | Run scheduled 4:00 AM broadcast job |
| `python main.py --time 8am` | ✅ Yes | ❌ No | Run scheduled 8:00 AM broadcast job |
| `python -m unittest discover -s tests -v` | ❌ No | ❌ No | Run all 13 automated test suites |

---

## 1. View Daily Summary Table (`--summary`)

Displays the daily status of all tracked UIDs for today (or a specific date). Fits cleanly within standard terminal windows on a single line per row.

### Syntax
```bash
python main.py --summary              # View today's summary (IST)
python main.py --summary 2026-11-09   # View summary for a specific date
```

### Example Terminal Output
```
============================================================================
  DAILY LIKES BY UID • 2026-11-09 IST
----------------------------------------------------------------------------
  UID         Player Name         Likes     Added   Daily Change
  ------------------------------------------------------------------------
  1714257555  ALWAYSﾠR6          32,418         -   first recorded day
  1852353345  Ƙᴀɪᴅɪ⁷⁸⁶          126,181      +115   first recorded day
  2512117368  ＦＣ✿Sʜᴀᴅoω࿐       34,619         -   first recorded day
  3037405463  MᴏᴍᴏsCʜᴏʀ          13,422         -   first recorded day
  4354244058  MissCrime271       23,849         -   first recorded day
  5799545097  ꕶꕶ┊Ꮪᴀᴅ-Ᏼᴏʏ™        14,263         -   first recorded day
  8495643303  ༱ㅤℓαꪜㅤ           33,346         -   first recorded day
  9692973675  ?★Sᗩᑭᑎᗩ★?          14,738         -   first recorded day
============================================================================
```

- **Player Name:** In-game name auto-aligned with full-width unicode monospace padding.
- **Likes:** Total likes recorded on this day.
- **Added:** Likes gained since the immediately preceding check on that day.
- **Daily Change:** Likes gained compared to the previous calendar day.

---

## 2. Generate Likes Report (`--report` or `--time like_report`)

Compares each UID's current likes against their previous recorded date based on the **04:00 AM IST operational day cycle**. Saves reports in `data/reports/like_report_YYYY-MM-DD.json` and `.md`, and prints a single-line terminal table.

When dispatched to Telegram (`--telegram`), it sends **separate formatted cards per user** with hyperlinked account handles (`<a href="https://t.me/username">Account Name</a> (@username)`), clean borders, execution telemetry, and link previews suppressed (`link_preview=False`).

### Syntax
```bash
python main.py --report               # Generate report for today (files + terminal table)
python main.py --report 2026-11-11    # Generate report for specific date
python main.py --report --telegram    # Generate report AND dispatch separate message cards to Telegram
python main.py --report --telegram --force # Send to Telegram bypassing cron schedule lock
python main.py --time like_report     # Runs via master_config.json job (files + Telegram group)
```

### Example Terminal Output
```
============================================================================
                       DAILY LIKES REPORT • 2026-11-11 (IST)                        
----------------------------------------------------------------------------
  UID         Player Name         Likes     Prev Day    Change   Status
----------------------------------------------------------------------------
  1714257555  ALWAYSﾠR6          32,593   2026-11-10      +113   Daily +113
  1852353345  Ƙᴀɪᴅɪ⁷⁸⁶          126,454   2026-11-10      +127   Daily +127
  2512117368  ＦＣ✿Sʜᴀᴅoω࿐       34,795   2026-11-10      +115   Daily +115
  3037405463  MᴏᴍᴏsCʜᴏʀ          13,609   2026-11-10      +123   Daily +123
  4354244058  MissCrime271       24,026   2026-11-10      +100   Daily +100
  5799545097  ꕶꕶ┊Ꮪᴀᴅ-Ᏼᴏʏ™        14,403   2026-11-10       +97   Daily +97
  8495643303  ༱ㅤℓαꪜㅤ           33,490   2026-11-10       +86   Daily +86
  9692973675  ?★Sᗩᑭᑎᗩ★?          14,923   2026-11-10      +110   Daily +110
----------------------------------------------------------------------------
  Report files: data/reports/like_report_2026-11-11.json & data/reports/like_report_2026-11-11.md
============================================================================
```

### Example Telegram Message Card (Dispatched per User)
```text
LIKE INFORMATION REPORT • 2026-11-11 • 09:25 AM
──────────────────────────────
┌ Like Info
├─ UID: 1852353345
├─ Nickname: Ƙᴀɪᴅɪ⁷⁸⁶
├─ Last Fetched Likes: 126,185
├─ Latest Fetched Likes: 126,454
├─ Added Likes Today: +127
├─ Current Total Likes: 126,454
└─ User: <a href="https://t.me/Kaidi786">Kaidi</a> (@Kaidi786)
──────────────────────────────
```

---

## 3. View Stored History for a UID (`--show`)

Prints the raw structured JSON record for a single UID from `data/like_history.json`.

### Syntax
```bash
python main.py --show <UID>
```

### Example
```bash
python main.py --show 1852353345
```

### Example Terminal Output
```json
{
  "daily": {
    "2026-11-09": {
      "likes": 126181,
      "observed_at": "2026-11-09T17:19:00.787386+05:30",
      "player_name": "Ƙᴀɪᴅɪ⁷⁸⁶",
      "added_since_previous_observation": 115,
      "previous_recorded_day": null,
      "increase_from_previous_recorded_day": null
    }
  },
  "latest": {
    "likes": 126181,
    "observed_at": "2026-11-09T17:19:00.787386+05:30",
    "player_name": "Ƙᴀɪᴅɪ⁷⁸⁶"
  },
  "change_from_previous_observation": 115,
  "previous_recorded_day": null,
  "change_from_previous_recorded_day": null,
  "player_name": "Ƙᴀɪᴅɪ⁷⁸⁶",
  "previous_likes": 126066
}
```

---

## 4. Guarded Single `/level` Query (`--send`)

Sends `/level <UID>` to the Telegram bot group using the local `nitish1.session`, waits for the bot reply (handling edits and typing state), extracts the latest likes and player name, updates `data/like_history.json`, and prints the result card.

> [!NOTE]
> This command automatically runs local safety checks (`check_cron_window` and `check_public_workflows`) before opening the Telethon session.

### Syntax
```bash
python main.py --send <UID>
```

### Example
```bash
python main.py --send 1852353345
```

### Example Terminal Output
```
[17:18:56] 🛡️ Verifying GitHub Actions and Cron status...
[17:18:57] ✅ Session safety check passed. No remote runners active.
[17:19:00] 📬 [Nitish1] UID 1852353345 (Ƙᴀɪᴅɪ⁷⁸⁶) -> Likes: 126,181 (+115) [Day: First recorded day]
Saved D:\Projects\Antigravity\Telegram-Automation\Telegram-Public\data\like_history.json
```

---

## 5. Full Fleet Info Bot Run (`--time info_bot`)

Runs the fleet across multiple accounts in `config/master_config.json`, dispatching `/level <UID>` for every configured UID, waiting for responses, parsing player names and likes, and logging the final summary table.

### Syntax
```bash
python main.py --time info_bot
```

---

## 6. Scheduled Broadcast Jobs (`--time 4am`, `--time 8am`)

Runs broadcast message routines defined in `config/master_config.json` with humanized delays, anti-ban protection, and captcha detection.

### Syntax
```bash
python main.py --time 4am
python main.py --time 8am
```

---

## 7. Automated Test Suite

Runs the automated test suite verifying history persistence, regex matching, unicode table padding, report rendering, and schedule guard logic.

### Syntax
```bash
python -m unittest discover -s tests -v
```

---

## 💡 How "Added Likes" Works: Intra-Day vs Next-Day

### Case A: Adding Likes on the SAME Day
If UID `1852353345` had `126,066` likes, and you add 115 likes on the same day (`2026-11-09`):
- **Today Likes:** `126,181`
- **Added:** `+115` (tracked via `change_from_previous_observation`)
- **Daily Change:** `first recorded day` (because this UID has no earlier calendar day recorded yet)

### Case B: Adding 100 Likes on the NEXT Day (`2026-11-10`)
If you add 100 likes on the next day, bringing the total to `126,281`:
- **`--summary` table:**
  - `Likes`: `126,281`
  - `Added`: `+100`
  - `Daily Change`: `+100` (bright green)
- **`--report` table:**
  - `Today Likes`: `126,281`
  - `Prev Day`: `2026-11-09`
  - `Change`: `+100` (bright green)
  - `Status`: `Daily +100` (bright green)
- **Report Markdown / JSON:**
  - `| 1852353345 | Ƙᴀɪᴅɪ⁷⁸⁶ | 126,281 | 2026-11-09 | 126,181 | +100 | Change from previous day |`
