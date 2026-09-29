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
cp .env.example .env   # Fill in your TELEGRAM_BOT_TOKEN and ALLOWED_USER_IDS, while cookies is optional

uv run python src/bot.py
```

## Configurations

### Telegram Bot Token

Acquire your bot token from [BotFather](https://t.me/BotFather) on Telegram.

Example:

```ini
TELEGRAM_BOT_TOKEN=123456789:ABCdefGHIj
```

### Access Control (Whitelist)

Add the authorized user ids to `ALLOWED_USER_IDS` in `.env`.
Only the users in this list have access to the bot.

Example:

```ini
ALLOWED_USER_IDS=123456789,987654321
```

### Cookies

To bypass the bot detection, you can attach your cookies to the bot.  
Put your cookies files into the repo root directory and set the cookies variable in `.env` accordingly.  
CurrentlyYouTube and Bilibili cookies are supported.

Example:

```ini
YOUTUBE_COOKIES_FILE=youtube_cookies.txt
BILIBILI_COOKIES_FILE=bilibili_cookies.txt
```

> More details about fetching cookies can be found in <https://github.com/yt-dlp/yt-dlp/wiki/Extractors#exporting-youtube-cookies>
