"""上游音乐 API 客户端：请求头伪装、搜索/歌曲/歌词/歌单、数据规范化。

从旧版单文件播放器移植，接口路径/参数保持不变。
"""

import random
from urllib.parse import urlparse

import requests

from .config import MUSIC_API

CHROME_VERSIONS = [
    "128.0.6613.137", "128.0.6613.138", "129.0.6668.58", "129.0.6668.59",
    "129.0.6668.70", "130.0.6723.58", "130.0.6723.59", "130.0.6723.69",
    "131.0.6778.85", "131.0.6778.108", "132.0.6834.83", "132.0.6834.110",
]

PLATFORMS = [
    "Windows NT 10.0; Win64; x64",
    "Windows NT 10.0; Win64; x64",
    "Windows NT 10.0; Win64; x64",
    "Macintosh; Intel Mac OS X 14_6_1",
    "Macintosh; Intel Mac OS X 14_5",
    "X11; Linux x86_64",
]

# 上游可能通过这些头探测真实客户端，一律剥离
FORWARDED_HEADERS = [
    "X-Forwarded-For", "X-Real-IP", "X-Forwarded-Proto",
    "X-Forwarded-Host", "Via", "Forwarded",
    "x-forwarded-for", "x-real-ip", "x-forwarded-proto",
    "x-forwarded-host", "via", "forwarded",
]

SESSION = requests.Session()


def random_ua(chrome: str | None = None) -> str:
    chrome = chrome or random.choice(CHROME_VERSIONS)
    plat = random.choice(PLATFORMS)
    return (
        f"Mozilla/5.0 ({plat}) AppleWebKit/537.36 "
        f"(KHTML, like Gecko) Chrome/{chrome} Safari/537.36"
    )


def headers_for(url: str, extra: dict | None = None) -> dict:
    """构造伪装浏览器请求头；浏览器不可能带转发头，全部剥离。"""
    parsed = urlparse(url)
    host = parsed.hostname or ""
    origin = f"{parsed.scheme}://{parsed.hostname}"
    # UA 与 Sec-Ch-Ua 必须来自同一 Chrome 版本（真实浏览器行为）
    chrome_ver = random.choice(CHROME_VERSIONS)
    h = {
        "User-Agent": random_ua(chrome_ver),
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Accept-Encoding": "identity",
        "Host": host,
        "Origin": origin,
        "Referer": origin + "/",
        "Connection": "keep-alive",
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Ch-Ua": f'"Chromium";v="{chrome_ver.split(".")[0]}", "Not/A)Brand";v="99"',
        "Sec-Ch-Ua-Mobile": "?0",
        "Sec-Ch-Ua-Platform": random.choice(['"Windows"', '"macOS"', '"Linux"']),
    }
    if extra:
        h.update(extra)
    for bad in FORWARDED_HEADERS:
        h.pop(bad, None)
    return h


def try_https(url: str) -> str:
    """http:// 封面/资源链接优先尝试升级为 https（上游 CDN 通常双协议）。"""
    if not url or not url.startswith("http://"):
        return url
    https = url.replace("http://", "https://", 1)
    try:
        r = SESSION.head(https, headers=headers_for(https), timeout=4, allow_redirects=True)
        if r.status_code < 500:
            return https
    except Exception:
        pass
    return url


def api_get(path: str, params: dict | None = None, timeout: int = 12) -> requests.Response:
    h = headers_for(MUSIC_API)
    h["Accept"] = "application/json"
    return SESSION.get(f"{MUSIC_API}{path}", params=params, headers=h, timeout=timeout)


def _extract_artists(track: dict) -> str:
    raw = track.get("ar") or track.get("artists") or track.get("artist", "")
    if isinstance(raw, list):
        return " / ".join(
            a["name"] if isinstance(a, dict) else str(a)
            for a in raw
        )
    return str(raw) if raw else ""


def _extract_album(track: dict) -> str:
    raw = track.get("al") or track.get("album", "")
    if isinstance(raw, dict):
        return raw.get("name", "")
    return str(raw) if raw else ""


def _extract_cover(track: dict) -> str:
    al = track.get("al")
    if isinstance(al, dict) and al.get("picUrl"):
        return al["picUrl"]
    if track.get("picUrl"):
        return track["picUrl"]
    album = track.get("album")
    if isinstance(album, dict) and album.get("picUrl"):
        return album["picUrl"]
    return ""


def normalize_song(s: dict) -> dict:
    return {
        "id": s["id"],
        "name": s.get("name", ""),
        "artist": _extract_artists(s),
        "album": _extract_album(s),
        "cover": try_https(_extract_cover(s)),
        "duration": s.get("duration", 0),
    }


def get_audio_url(sid: str, level: str = "jymaster") -> str:
    """获取歌曲直链（指定音质，默认臻品母带），失败返回空串。"""
    try:
        r = api_get("/163_music", {"id": sid, "level": level})
        body = r.json()
        if body.get("code") != 200:
            return ""
        raw = body["data"]
        if isinstance(raw, list):
            raw = raw[0] or {}
        return raw.get("url", "")
    except Exception:
        return ""


def get_song_meta(sid: str, level: str = "jymaster") -> dict:
    """获取歌曲完整元数据（含音质/大小/直链）。"""
    try:
        r = api_get("/163_music", {"id": sid, "level": level})
        body = r.json()
        if body.get("code") != 200:
            return {}
        raw = body["data"]
        if isinstance(raw, list):
            raw = raw[0] or {}
        return raw
    except Exception:
        return {}
