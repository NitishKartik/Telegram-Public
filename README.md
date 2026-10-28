# 🤖 Telegram Auto-Bot Fleet Engine (Production Grade)

A cross-platform, enterprise-grade multi-account Telegram automation fleet engine built with Python and Telethon. Designed to run identically across **Android (Termux)**, **Windows**, and **GitHub Actions**.

Maintained by **Nitish Kartik**.

> 📚 **Complete Documentation Book:** Read [`HANDBOOK.md`](HANDBOOK.md) for an in-depth reference guide, architectural manual, parameter breakdowns, and field recipes.  
> 🧩 **Captcha Reference:** Read [`CAPTCHA.md`](CAPTCHA.md) for dedicated captcha engine parameters.

---

## 🏗️ Production Architecture

```text
Telegram/
├── .github/workflows/
│   └── fleet-runner.yml          <- Cloud execution via GitHub Actions
├── config/
│   ├── master_config.json        <- Multi-job scheduled targets & humanization
│   ├── permissions.json
│   └── target_groups.json
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
│       └── logger.py             <- Cross-platform logging utility
├── scripts/
│   └── auto_referral.py          <- Interactive CLI referral tool
├── .env.example                  <- Credentials template
├── .gitignore                    <- Security barrier
├── requirements.txt              <- Dependencies
└── main.py                       <- CLI entry point
```

---

## 🚀 Setup & Run

### 1. Requirements
Ensure Python 3.10+ is installed:
```bash
pip install -r requirements.txt
```

### 2. Environment Variables
Create a `.env` file in the project root (see `.env.example`):
```env
TELEGRAM_API_ID=1234567
TELEGRAM_API_HASH=abcdef0123456789abcdef0123456789
```

---

## 📱 Cross-Platform Execution

### A. Windows (PowerShell or Antigravity)
```powershell
python main.py --time 4am
python main.py --time 8am
```

### B. Android (Termux)
```bash
pkg update && pkg install python git
git clone https://github.com/NitishKartik/Telegram.git
cd Telegram
pip install -r requirements.txt
export TELEGRAM_API_ID="your_api_id"
export TELEGRAM_API_HASH="your_api_hash"
python main.py --time 4am
```

### C. GitHub Actions (Automated Cloud Execution)
1. In your GitHub repository settings, go to:
   **Settings $\rightarrow$ Secrets and variables $\rightarrow$ Actions**
2. Add repository secrets:
   - `TELEGRAM_API_ID`
   - `TELEGRAM_API_HASH`
3. Trigger via the **Actions** tab $\rightarrow$ **Telegram Fleet Runner** $\rightarrow$ select job target (`4am`, `8am`, etc.) and click **Run workflow**.

---

## 🛡️ Anti-Ban & Resiliency Features

- **FloodWait Auto-Recovery**: Intercepts Telegram flood restrictions and pauses the account safely instead of terminating the process.
- **Human Typing Mimicry**: Configurable typing indicator durations before dispatching messages.
- **Automated Math & Button Captcha Solver**: Listens to bot replies in real-time and solves inline math challenges.
- **Ghost Mode**: Scheduled automatic message deletion after broadcast.
- **Path Independence**: Resolves directories dynamically without relying on fixed operating system paths.
