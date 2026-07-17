# KAGE OS — Troubleshooting Guide

## Common Issues & Solutions

### 1. "Cannot connect to Obsidian REST API at http://localhost:27123"
* **Cause**: Obsidian app is not running or the Local REST API community plugin is disabled.
* **Fix**: Ensure Obsidian is open on your device and the Local REST API plugin is enabled in plugin settings.

### 2. "Gemini rate limit exceeded (429)"
* **Cause**: Free tier request rate limit reached on active model.
* **Fix**: Kage will automatically failover to `gemini-2.0-flash`. You can also switch providers dynamically:
  ```bash
  kage chat "/config set llm.provider groq"
  ```

### 3. "Daemon socket connection error"
* **Cause**: Daemon process is stopped or stale socket file exists.
* **Fix**: Restart supervisor daemon:
  ```bash
  kage daemon stop
  kage daemon start
  ```

### 4. "Telegram bot disconnected or not polling"
* **Cause**: Invalid bot token or missing PID file.
* **Fix**: Verify token and check status:
  ```bash
  kage telegram status
  kage telegram start
  ```
