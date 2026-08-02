"""网易云账号登录（官方扫码接口）+ 我的歌单。

与上游中转（MUSIC_API）无关，直连 music.163.com：
- 扫码登录：/api/login/qrcode/unikey 取 key → 前端渲染二维码 →
  轮询 /api/login/qrcode/client/login（800 过期 / 801 等待 / 802 已扫码 / 803 确认）
- 多会话：每次登录会话相互独立（浏览器持有 tunebox_session Cookie 标识），
  持久化到本地文件（NETEASE_COOKIE_FILE），重启不丢
- 我的歌单：/api/user/playlist；私有歌单兜底：/api/v6/playlist/detail
"""

import json
import logging
import threading
import time
from pathlib import Path
from uuid import uuid4

import requests

logger = logging.getLogger("tunebox.netease")

from . import client
from .config import BACKEND_DIR, NCM_REAL_IP, NETEASE_COOKIE_FILE

NCM_HOST = "https://music.163.com"

# 扫码确认对服务器（机房）IP 风控严格：未配置时默认伪装大陆 IP，
# 否则会返回「请切换其他登录方式或升级新版本再试」
DEFAULT_REAL_IP = "112.17.8.18"

# 官方接口的语义码
QR_EXPIRED = 800
QR_WAITING = 801
QR_SCANNED = 802
QR_CONFIRMED = 803

# 登录确认后 Cookie 会在随后的请求里短暂失效，立即拉取账号信息（官方行为）
_PROFILE_RETRIES = 3

# 无数据库：登录态以「会话 id → 网易云 Cookie」映射存 JSON 文件
SESSION_COOKIE = "tunebox_session"
SESSION_TTL_DAYS = 30
_SESSION_MAX = 10

# RLock：持锁期间会调用 _obj()（内部也要加锁），可重入锁避免同线程死锁
_lock = threading.RLock()
# sid -> {"cookies": {...}, "profile": {...} | None, "created_at": iso}
_sessions: dict[str, dict] = {}
# sid -> requests.Session（内存态，含未登录阶段的匿名 Cookie，登录后含 MUSIC_U）
_sess_objs: dict[str, requests.Session] = {}


def _headers() -> dict:
    h = client.headers_for(NCM_HOST)
    h["Accept"] = "application/json, text/plain, */*"
    h["X-Real-IP"] = NCM_REAL_IP or DEFAULT_REAL_IP
    return h


def cookie_file() -> Path:
    return Path(NETEASE_COOKIE_FILE or BACKEND_DIR / "netease_cookie.json")


def _load() -> dict:
    """从文件加载会话映射（过期会话剔除），线程安全。"""
    global _sessions
    with _lock:
        if _sessions:
            return _sessions
        try:
            data = json.loads(cookie_file().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            data = {}
        now = time.time()
        sessions = {}
        for sid, s in (data.get("sessions") or {}).items():
            try:
                age = now - time.mktime(time.strptime(s.get("created_at", ""), "%Y-%m-%dT%H:%M:%S"))
            except (ValueError, TypeError):
                age = 0
            if 0 <= age <= SESSION_TTL_DAYS * 86400:
                sessions[sid] = s
        _sessions = sessions
        return sessions


def _save() -> None:
    with _lock:
        payload = {"sessions": _sessions}
        cookie_file().write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def _obj(sid: str) -> requests.Session:
    """取会话对应的 requests.Session（含持久化 Cookie），不存在则新建匿名会话。"""
    with _lock:
        s = _sess_objs.get(sid)
        if s is None:
            s = requests.Session()
            data = _load().get(sid)
            if data:
                s.cookies.update(requests.utils.cookiejar_from_dict(data.get("cookies", {})))
            _sess_objs[sid] = s
        return s


def create_session() -> str:
    """创建新会话；会话数超限时淘汰最旧的（含文件清理）。"""
    sessions = _load()
    with _lock:
        sid = str(uuid4())
        sessions[sid] = {"cookies": {}, "profile": None, "created_at": time.strftime("%Y-%m-%dT%H:%M:%S")}
        _obj(sid)
        if len(sessions) > _SESSION_MAX:
            oldest = min(sessions, key=lambda k: sessions[k].get("created_at", ""))
            sessions.pop(oldest, None)
            _sess_objs.pop(oldest, None)
        _save()
        return sid


def get_session(sid: str) -> dict | None:
    """取会话元数据（cookies/profile/created_at）；不存在返回 None。"""
    return _load().get(sid)


def qr_key(sid: str) -> str:
    """获取扫码 key（官方 unikey），返回空串表示失败。

    unikey 请求下发的匿名 Cookie 落在该会话对象上，扫码确认必须复用同一会话。
    """
    try:
        s = _obj(sid)
        r = s.get(f"{NCM_HOST}/api/login/qrcode/unikey", params={"type": 1}, headers=_headers(), timeout=10)
        body = r.json()
        key = body.get("unikey", "")
        if not key or body.get("code") != 200:
            return ""
        return key
    except (requests.RequestException, ValueError):
        return ""


def qr_check(sid: str, key: str) -> dict:
    """轮询扫码结果。803 确认时保存 Cookie 并拉取账号资料。

    返回 {"code", "message", "profile"?}，语义码与官方一致（800/801/802/803）。
    """
    try:
        r = _obj(sid).get(
            f"{NCM_HOST}/api/login/qrcode/client/login",
            params={"key": key, "type": 1},
            headers=_headers(),
            timeout=10,
        )
        body = r.json()
        code = int(body.get("code", -1))
        message = body.get("message") or body.get("msg") or ""
    except (requests.RequestException, ValueError):
        return {"code": -1, "message": "轮询失败，请重试"}

    if code not in (QR_WAITING, QR_SCANNED):
        logger.warning("扫码登录异常: code=%s message=%s", code, message)
    if code == QR_CONFIRMED:
        sessions = _load()
        with _lock:
            data = sessions.get(sid)
            if data is None:
                return {"code": -1, "message": "会话不存在，请重新扫码"}
            data["cookies"] = requests.utils.dict_from_cookiejar(_obj(sid).cookies)
            _save()
        profile = fetch_profile(sid)
        if not profile:
            return {"code": -1, "message": "登录确认成功，但获取账号信息失败，请重试"}
        return {"code": code, "message": message, "profile": profile}
    return {"code": code, "message": message}


def fetch_profile(sid: str) -> dict | None:
    """用会话登录态拉取账号资料（/api/nuser/account/get）。"""
    sessions = _load()
    with _lock:
        data = sessions.get(sid)
        if data is None:
            return None
        for _ in range(_PROFILE_RETRIES):
            try:
                r = _obj(sid).get(f"{NCM_HOST}/api/nuser/account/get", headers=_headers(), timeout=10)
                body = r.json()
                if body.get("code") == 200:
                    p = body.get("data", {}).get("profile")
                    if p:
                        data["profile"] = {
                            "userId": p.get("userId"),
                            "nickname": p.get("nickname", ""),
                            "avatarUrl": client.try_https(p.get("avatarUrl", "")),
                        }
                        _save()
                        return data["profile"]
                time.sleep(0.5)
            except (requests.RequestException, ValueError):
                time.sleep(0.5)
        return None


def status(sid: str | None) -> dict:
    """会话登录态：是否有网易云 Cookie 与缓存资料；无会话视为未登录。"""
    if not sid:
        return {"logged_in": False, "profile": None}
    data = get_session(sid)
    if not data:
        return {"logged_in": False, "profile": None}
    return {"logged_in": bool(data.get("cookies", {}).get("MUSIC_U")), "profile": data.get("profile")}


def logout(sid: str) -> None:
    """删除会话（内存 + 文件），其他会话不受影响。"""
    with _lock:
        _load().pop(sid, None)
        _sess_objs.pop(sid, None)
        _save()


def user_playlists(sid: str) -> list[dict] | None:
    """会话账号的歌单列表；未登录/过期返回 None。"""
    data = get_session(sid)
    if not data or "MUSIC_U" not in (data.get("cookies") or {}):
        return None
    uid = (data.get("profile") or {}).get("userId")
    try:
        r = _obj(sid).get(
            f"{NCM_HOST}/api/user/playlist",
            params={"uid": uid, "limit": 1000},
            headers=_headers(),
            timeout=10,
        )
        body = r.json()
        if body.get("code") != 200:
            return None
        pls = []
        for p in body.get("playlist") or []:
            pls.append({
                "id": p.get("id"),
                "name": p.get("name", ""),
                "cover": client.try_https(p.get("coverImgUrl", "")),
                "trackCount": p.get("trackCount", 0),
            })
        return pls
    except (requests.RequestException, ValueError):
        return None


def playlist_songs(pid: str, sid: str | None = None) -> list[dict]:
    """直连官方接口取歌单歌曲；私有歌单需该会话已登录，失败返回空列表。"""
    s = _obj(sid) if sid else requests.Session()
    try:
        r = s.get(
            f"{NCM_HOST}/api/v6/playlist/detail",
            params={"id": pid},
            headers=_headers(),
            timeout=10,
        )
        body = r.json()
        if body.get("code") != 200:
            return []
        tracks = (body.get("playlist") or {}).get("tracks") or []
        return [client.normalize_song(t) for t in tracks]
    except (requests.RequestException, ValueError):
        return []
