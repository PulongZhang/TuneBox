"""音频流式转发、下载响应头、LRC 组装。从旧版单文件播放器移植。"""

import re
from collections.abc import Iterator
from urllib.parse import quote, urlparse

from .client import SESSION, headers_for

MIME_MAP = {
    "flac": "audio/flac", "mp3": "audio/mpeg",
    "m4a": "audio/mp4", "aac": "audio/aac",
    "ogg": "audio/ogg", "wav": "audio/wav", "wma": "audio/x-ms-wma",
}

AUDIO_EXTS = ["flac", "mp3", "m4a", "aac", "ogg", "wav"]


def _guess_ext(audio_url: str) -> str:
    parsed = urlparse(audio_url)
    if "." in parsed.path:
        return parsed.path.rsplit(".", 1)[-1]
    return "flac"


def stream_audio(
    audio_url: str, range_header: str | None = None
) -> tuple[Iterator[bytes], str, str, int]:
    """以生成器方式转发上游音频流；支持 Range 透传。"""
    ext = _guess_ext(audio_url)
    content_type = MIME_MAP.get(ext.lower(), "audio/flac")

    # 获取文件大小（供 206/Content-Length 使用）
    try:
        head_resp = SESSION.head(audio_url, headers=headers_for(audio_url), timeout=10)
        total_size = int(head_resp.headers.get("content-length", 0))
    except Exception:
        total_size = 0

    extra = {"Accept": "*/*"}
    if range_header:
        extra["Range"] = range_header

    def generate() -> Iterator[bytes]:
        try:
            resp = SESSION.get(
                audio_url, headers=headers_for(audio_url, extra),
                stream=True, timeout=30,
            )
            resp.raise_for_status()
            for chunk in resp.iter_content(256 * 1024):
                if chunk:
                    yield chunk
        except Exception:
            return

    return generate(), content_type, ext, total_size


def proxy_fetch(url: str) -> tuple[bytes | None, str | None]:
    """通用资源代理（封面图等），失败返回 (None, None)。"""
    try:
        r = SESSION.get(url, headers=headers_for(url), timeout=12)
        if r.status_code == 200:
            ct = r.headers.get("content-type", "application/octet-stream")
            return r.content, ct
    except Exception:
        pass
    return None, None


def make_download_headers(filename: str, fallback: str = "download") -> dict:
    """附件下载头：ASCII 兜底 + RFC 5987 UTF-8 文件名。"""
    ascii_name = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)
    if len(ascii_name) > 80:
        ascii_name = fallback
    encoded = quote(filename.encode("utf-8"), safe="")
    return {
        "Content-Disposition": (
            f'attachment; filename="{ascii_name}"; '
            f"filename*=UTF-8''{encoded}"
        ),
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache",
    }


def make_lyric_text(raw: dict, name: str, artist: str) -> str:
    """组装 LRC 文本：[ti]/[ar] 头 + 原文 + 翻译段落。"""
    title_line = f"[ti:{name}]" if name else ""
    artist_line = f"[ar:{artist}]" if artist else ""
    lrc = raw.get("lrc", "")
    tlrc = raw.get("tlyric", "")
    parts = [title_line, artist_line]
    if lrc:
        parts.append(lrc.strip())
    if tlrc:
        parts.append("\n\n[翻译歌词]\n" + tlrc.strip())
    return "\n".join(p for p in parts if p) + "\n"


def song_filename(title: str, ext: str, name: str, sid: str) -> str:
    """下载文件名：`艺术家 - 歌名.ext`，非法字符替换。"""
    clean = re.sub(r'[<>:"/\\|?*]', "_", title) if title else name
    return f"{clean}.{ext}"
