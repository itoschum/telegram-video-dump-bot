import os
import logging
import asyncio
import re
import shutil
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    MessageHandler,
    CommandHandler,
    filters,
    ContextTypes,
)
from functools import wraps
from downloader import download_video, DownloadError

load_dotenv()

class SensitiveFilter(logging.Filter):
    def __init__(self) -> None:
        super().__init__()
        self._token = os.getenv("TELEGRAM_BOT_TOKEN", "")

    def filter(self, record: logging.LogRecord) -> bool:
        if self._token:
            full_msg = record.getMessage()
            if self._token in full_msg:
                record.msg = record.getMessage().replace(self._token, "********")
                record.args = None  # prevent double formatting
        return True
    
class SuppressGetUpdates(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        full_msg = record.getMessage()  # formats msg + args together
        return "getUpdates" not in full_msg


def setup_logging():
    logging.basicConfig(
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        level=logging.INFO,
    )
    logging.getLogger("httpx").addFilter(SensitiveFilter())
    logging.getLogger("httpx").addFilter(SuppressGetUpdates())

    return logging.getLogger(__name__)

logger = setup_logging()

TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    raise RuntimeError("TELEGRAM_BOT_TOKEN is not set in .env")

ALLOWED_USER_IDS = {
    int(uid.strip())
    for uid in os.getenv("ALLOWED_USER_IDS", "").split(",")
    if uid.strip()
}

def restricted(func):
    @wraps(func)
    async def user_id_filter(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        if update.effective_user.id not in ALLOWED_USER_IDS:
            await update.message.reply_text("⚠️ You are not authorized to use this bot.")
            return
        return await func(update, context, *args, **kwargs)
    return user_id_filter

@restricted
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    await update.message.reply_text(
        "Send me a video URL and I'll download it for you!\n\n"
        "Supported sites: YouTube, Twitter/X, Instagram, TikTok, and "
        "<a href='https://github.com/yt-dlp/yt-dlp/blob/master/supportedsites.md'>many more</a>.\n\n"
        "⚠️ Max file size: 50 MB (Telegram limit).",
        parse_mode="HTML",
    )

@restricted
async def handle_url(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    
    url_match = re.search(r'https?://\S+', update.message.text.strip())
    if not url_match:
        await update.message.reply_text("❌ Please send a valid URL starting with http:// or https://")
        return
    
    url = url_match.group(0)
    
    status_msg = await update.message.reply_text("⏳ Fetching video info…")
    filepath = None

    try:
        await status_msg.edit_text("⏬ Downloading…")
        filepath, title, has_inline, metadata = await asyncio.to_thread(download_video, url)

        await status_msg.edit_text("⏫ Uploading to Telegram…")
        with open(filepath, "rb") as video_file:
            caption = f"Title: {title}"
            if spec := metadata.get("spec"):
                caption += f"\n\n{spec}"
            
            if has_inline:
                await update.message.reply_video(
                    video=video_file,
                    caption=caption,
                    supports_streaming=True,
                    width=metadata.get("width"),
                    height=metadata.get("height"),
                    duration=metadata.get("duration"),
                    read_timeout=120,
                    write_timeout=120,
                )
            else:
                # VP9 / AV1 — Telegram won't show an inline player, send as file
                await update.message.reply_document(
                    document=video_file,
                    caption=(
                        f"Title: {caption}\n\n"
                        "⚠️ No H.264/H.265 stream was available under 50 MB — "
                        "sent as a file (no inline preview)."
                    ),
                    read_timeout=120,
                    write_timeout=120,
                )
        
        # shutil.copy(filepath, os.path.basename(filepath))  # save copy to pwd DEBUGGING ONLY
        await status_msg.delete()

    except DownloadError as e:
        logger.warning("Download failed for %s: %s", url, e)
        await status_msg.edit_text(f"❌ Download failed:\n<code>{e}</code>", parse_mode="HTML")

    except Exception as e:
        logger.exception("Unexpected error for %s", url)
        await status_msg.edit_text("⚠️ An unexpected error occurred. Please try again later.")

    finally:
        # Always clean up the temp file
        if filepath and os.path.exists(filepath):
            try:
                print("\n[file path]", filepath)
                os.remove(filepath)
            except OSError as e:
                logger.warning("Could not delete temp file %s: %s", filepath, e)


def main() -> None:
    app = ApplicationBuilder().token(TELEGRAM_BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_url))

    logger.info("Bot is running…")
    app.run_polling()


if __name__ == "__main__":
    main()
