import os
import tempfile
from typing import Any, cast

import yt_dlp
from yt_dlp.utils import DownloadError as YtDlpDownloadError

MAX_FILE_SIZE = 45 * 1024 * 1024  # 50 MB — Telegram bot upload limit, reserved 5 MB for audio and metadata

# Use _LIMIT / _APPROX_LIMIT to avoid double quoting in yt-dlp's -f option
_LIMIT = f"[filesize<{MAX_FILE_SIZE}]"
_APPROX_LIMIT = f"[filesize_approx<{MAX_FILE_SIZE}]"

# ---------------------------------------------------------------------------
# Format selection
#
# _INLINE_FORMAT — AVC / HEVC only (Telegram shows inline player)
#   Priority: HEVC > AVC, AAC audio preferred but falls back to any audio
#
# _FALLBACK_FORMAT — any codec (VP9, AV1…, no inline preview on Telegram)
#   Same audio preference: AAC first, then anything
#
# _SORT — within each -f candidate, -S picks the best resolution tier,
#         then prefers h265 over h264, and mp4a (AAC) over opus.
#         Note: -S reorders but never excludes — exclusion is done in -f.
# ---------------------------------------------------------------------------

_INLINE_VCODECS = ["hvc", "hev", "avc", "av01"]
_AAC = "[acodec*=mp4a]"

_SORT = ["res", "vcodec:h265:h264:av01:vp9", "acodec:mp4a:opus"]

def _build_inline_format() -> str:
    candidates = []
    for size_filter in (_LIMIT, _APPROX_LIMIT):
        for audio in (_AAC, ""):
            for vcodec in _INLINE_VCODECS:
                candidates.append(f"bestvideo{size_filter}[vcodec*={vcodec}]+bestaudio{audio}")
    return "/".join(candidates)

def _build_fallback_format() -> str:
    candidates = []
    for size_filter in (_LIMIT, _APPROX_LIMIT):
        for audio in (_AAC, ""):
            candidates.append(f"bestvideo{size_filter}+bestaudio{audio}")
    candidates.append("best")
    return "/".join(candidates)

_INLINE_FORMAT = _build_inline_format()
_FALLBACK_FORMAT = _build_fallback_format()

class DownloadError(Exception):
    """Raised when yt-dlp fails or the file is over the size limit."""


def _make_opts(fmt: str, tmp_dir: str, url: str) -> dict[str, Any]:
    opts = {
        "format": fmt,
        "format_sort": _SORT,
        "outtmpl": os.path.join(tmp_dir, "%(title).100B.%(ext)s"),
        "merge_output_format": "mp4/mkv",
        "max_filesize": MAX_FILE_SIZE,
        "quiet": True,
        "no_warnings": False,
        "retries": 3,
        "fragment_retries": 3,
        "remote_components": ['ejs:github'],
        "verbose": False,
    }
    
    cookies_file = None
    if "youtube.com" in url:
        cookies_file = os.getenv("YOUTUBE_COOKIES_FILE")
    if "bilibili.com" in url:
        cookies_file = os.getenv("BILIBILI_COOKIES_FILE")
        
    if cookies_file:
        opts["cookiefile"] = cookies_file
        print("\n== Cookies Loaded ==")
    return opts


def download_video(url: str) -> tuple[str, str, bool, dict[str, Any]]:
    """
    Download the best video from *url*.

    Returns:
        (filepath, title, has_inline_preview)
        has_inline_preview=False means VP9/AV1 — no Telegram inline player.

    Raises:
        DownloadError on failure or file > 50 MB.
    """
    filepath, title, metadata = _attempt(url, _INLINE_FORMAT)
    has_inline = filepath is not None

    if not has_inline:
        filepath, title, metadata = _attempt(url, _FALLBACK_FORMAT)
        if filepath is None:
            raise DownloadError("Could not find a stream under 50 MB for this URL.")

    title = title or "video"

    size = os.path.getsize(filepath)
    if size > MAX_FILE_SIZE:
        os.remove(filepath)
        raise DownloadError(
            f"File is {size / 1024 / 1024:.1f} MB — exceeds Telegram's 50 MB limit."
        )

    return filepath, title, has_inline, metadata


def _attempt(url: str, fmt: str) -> tuple[str | None, str | None, dict[str, Any]]:
    """Run one download attempt. Returns (filepath, title) or (None, '') on failure."""
    tmp_dir = tempfile.mkdtemp()
    try:
        ydl_instance = yt_dlp.YoutubeDL(cast(Any, _make_opts(fmt, tmp_dir, url)))
        with ydl_instance as ydl:
            info = ydl.extract_info(url, download=True)
            if "entries" in info:
                info = info["entries"][0]
            filepath = ydl.prepare_filename(info)
            if not os.path.exists(filepath):
                filepath = _find_output_file(tmp_dir)    
            
            spec = _format_selected_info(info)
            return filepath, info.get("title", "video"), {
                "width": info.get("width"),
                "height": info.get("height"),
                "duration": int(info.get("duration") or 0),
                "spec": spec,
            }
    except YtDlpDownloadError:
        return None, "", {}

def _format_selected_info(info: dict[str, Any]) -> None:
    lines = []
    for fmt in (info.get("requested_formats") or [info]):
        vcodec    = fmt.get("vcodec", "none")
        acodec    = fmt.get("acodec", "none")
        width    = fmt.get("width", "?")
        height    = fmt.get("height", "?")
        format_id = fmt.get("format_id", "?")
        size      = fmt.get("filesize") or fmt.get("filesize_approx") or 0
        tbr       = fmt.get("tbr") or 0
        
        if vcodec != "none":
            lines.append(f"Video: [{format_id}] {f"{width}x{height}":<9} | {vcodec} | {tbr:.0f}kbps | {size/1024/1024:.1f}MB")
            
        if acodec != "none":
            lines.append(f"Audio: [{format_id}] {f"audio-only":<10} | {acodec} | {tbr:.0f}kbps | {size/1024/1024:.1f}MB")
    return "\n".join(lines)

def _find_output_file(directory: str) -> str:
    """Fallback for when yt-dlp changes the extension after merging."""
    files = [os.path.join(directory, f) for f in os.listdir(directory)
             if os.path.isfile(os.path.join(directory, f))]
    if not files:
        raise DownloadError("Download succeeded but no output file was found.")
    for ext in (".mp4", ".mkv", ".webm"):
        for f in files:
            if f.endswith(ext):
                return f
    return files[0]