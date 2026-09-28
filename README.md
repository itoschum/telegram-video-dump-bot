# Telegram Video Dump Bot

A Telegram bot that downloads videos from URLs using yt-dlp.

## Requirements

- Python 3.14+
- [uv](https://docs.astral.sh/uv/)
- ffmpeg

## QuickStart

```bash
git clone https://github.com/you/tg-video-bot

cd telegram_yt-dlp_bot
cp .env.example .env   # fill in your TELEGRAM_BOT_TOKEN and ALLOWED_USER_IDS

uv run python src/bot.py
```

## Supported Sites

Anything supported by [yt-dlp](https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md).
