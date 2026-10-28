# 🔑 Credentials Directory

This folder is designed for **device-specific credentials** (Windows, Android Termux, local machine).

### How it works:
1. **Local Device Run**:
   Keep a file named `telegram_creds.json` in this folder:
   ```json
   {
     "api_id": 1234567,
     "api_hash": "abcdef0123456789abcdef0123456789"
   }
   ```
2. **Cloud / GitHub Actions / Clean Run**:
   Whenever you **delete** `telegram_creds.json` (or on GitHub Actions where the file doesn't exist), the engine **automatically falls back** to reading credentials from:
   - Environment variables: `TELEGRAM_API_ID` and `TELEGRAM_API_HASH`
   - GitHub Actions Repository Secrets

All `*.json` files in this directory are listed in `.gitignore` so your local credentials won't accidentally be committed or pushed to GitHub.
