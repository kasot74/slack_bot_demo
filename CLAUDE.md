# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A Traditional Chinese Slack bot (slack_bolt, Socket Mode) backed by MongoDB. Features include AI chat/image generation (Claude, OpenAI, Gemini, xAI, dzmm), a virtual coin economy with gambling games, stock/crypto price lookup, a shop, nginx access-log import, and server resource monitoring. User-facing strings and most code comments are in Traditional Chinese.

## Running

```
python -m src.bot_main
```

Must be run from the repo root: the code uses relative imports (`from .model...`) and reads `config/config.txt` via a relative path.

- `config/config.txt` holds all secrets/settings as `KEY=VALUE` lines (parsed by `src/utilities.py:read_config`, which splits on `=` — values cannot contain `=`). Required keys include `SLACK_BOT_TOKEN`, `SLACK_SIGNING_SECRET`, `SLACK_APP_TOKEN`, `MONGO_USER/PASSWORD/HOST/PORT`, and per-service AI API keys (e.g. `CLAUDE_API_KEY`). This file is gitignored.
- Dependencies: `pip install -r requirements.txt` (note: the file is UTF-16 encoded). Playwright is used for URL content fetching: `playwright install chromium`.
- There are no tests or lint configuration in this repo (pytest is in requirements but unused).

## Deployment

Pushing to `main` triggers `.github/workflows/deploytoecr.yml`: builds the Docker image, pushes to AWS ECR, then SSHes into an EC2 host and restarts via `docker compose`. A commit message containing `[更新說明]` additionally posts the commit message to Slack via webhook. The Dockerfile has no CMD — the run command lives in the EC2 host's compose file.

## Architecture

`src/bot_main.py` is the entry point. It reads config, connects to MongoDB (`src/database.py:con_db` — database is always `myDatabase`), creates the Bolt `App`, then wires in each feature module.

### Feature module pattern (src/model/)

Every feature module follows the same convention:

1. Exports `COMMANDS_HELP` — a list of `(command, description)` tuples appended to `ALL_COMMANDS` in `bot_main.py` to build the `!help` output.
2. Exports a `register_*_handlers(app, config, db)` function that defines `@app.message(re.compile(...))` handlers as closures over `app`, `config`, and `db`.

All bot commands are message-text triggers prefixed with `!` (e.g. `!簽到`, `!openai`, `!畫`), matched by regex. To add a feature: create a module following this pattern and register it in `bot_main.py`.

Modules: `handlers_model.py` (misc/base commands), `coin_model.py` (coin economy and gambling — daily transactions are merged per user/type/day with int64 caps), `shop_model.py`, `stock_model.py` (delegates to `src/stock.py`), `crypto_model.py` (delegates to `src/crypto.py`), `ai_model.py` (routes `!openai`/`!gemini`/`!ai`/`!畫`/`!dalle` etc. to AI_Service functions), `resource_monitor.py`, `member_monitor.py`.

### AI services (src/AI_Service/)

One module per provider (`claude.py`, `openai.py`, `gemini.py`, `xai.py`, `dzmm.py`), each exposing roughly the same surface: `generate_summary(user_input)` plus provider-specific extras (image/video generation, sentiment). Important caveats:

- Each AI_Service module independently re-reads `config/config.txt` and opens its own MongoDB connection at import time — importing them outside the repo root or without a reachable MongoDB fails.
- Conversation history is global (stored in shared Mongo collections like `ai_his`, not per-user/per-channel).
- Model names are runtime-configurable: stored in the `ai_model_config` collection, managed by `src/database.py` (`get_ai_model_config` etc.) and changeable from Slack via `!setmodel <service> <field> <value>` / `!listmodels`. **Note:** `init_ai_model_configs` runs at startup and overwrites the collection with `_DEFAULT_AI_MODEL_CONFIGS`, so runtime changes don't survive restarts unless the defaults are updated too.
- `ai_tool.py` holds shared tooling (e.g. Playwright-based `read_url_content`).

### Other

- `src/log_analyzer.py`: nginx access-log parser (目前為孤兒模組)。原 `!importlog` / `!匯入日誌` 指令已移除 —— nginx 日誌匯入改由主機 cron 處理(`~/log-importer/import_nginx_logs.py`,邏輯/unique_key 沿用本檔)。
- Generated images are written to an `images/` directory before upload to Slack.
