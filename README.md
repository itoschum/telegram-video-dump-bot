# Telegram Video Dump Bot

A Telegram bot that downloads videos from URLs using yt-dlp.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- ffmpeg

## QuickStart

```bash
git clone https://github.com/you/telegram-video-dump-bot

cd telegram-video-dump-bot
cp .env.example .env   # fill in your TELEGRAM_BOT_TOKEN and ALLOWED_USER_IDS

uv run python src/bot.py
```

## Configurations

### Access Control (Whitelist)

Add the authorized user ids to `ALLOWED_USER_IDS` in `.env`.
Only the users in this list have access to the bot.

### Cookies

To bypass the bot detection, you can attach your cookies to the bot.  
For example, YouTube may block the requests from VPS IP addresses.  
Copy your cookies file into the repo root directory and set the `COOKIES_FILE` in `.env` to the cookies file name.

> More details about fetching cookies can be found in <https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies>
