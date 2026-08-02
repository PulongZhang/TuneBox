"""网易云登录路由测试：mock netease 模块，不触网。"""

from fastapi.testclient import TestClient

from app import app as fastapi_app
from app import netease

KEY = "709a5c15-fb8b-41c0-9093-c8ab5edf642e"


def _client():
    return TestClient(fastapi_app)


def test_qr_key_creates_session(monkeypatch):
    """首次请求创建会话并下发 tunebox_session Cookie。"""
    monkeypatch.setattr(netease, "create_session", lambda: "sid-1")
    monkeypatch.setattr(netease, "get_session", lambda sid: {"cookies": {}} if sid == "sid-1" else None)
    monkeypatch.setattr(netease, "qr_key", lambda sid: KEY)
    r = _client().get("/api/v1/auth/qr/key")
    assert r.status_code == 200
    assert r.json()["data"]["key"] == KEY
    assert "tunebox_session" in r.headers.get("set-cookie", "")


def test_qr_key_reuses_session(monkeypatch):
    """已有会话时复用，不再新建。"""
    created = []
    monkeypatch.setattr(netease, "get_session", lambda sid: {"cookies": {}} if sid == "sid-1" else None)
    monkeypatch.setattr(netease, "qr_key", lambda sid: KEY)
    monkeypatch.setattr(netease, "create_session", lambda: created.append(1) or "sid-1")
    c = _client()
    c.get("/api/v1/auth/qr/key")
    r = c.get("/api/v1/auth/qr/key")
    assert r.status_code == 200
    assert created == [1]  # 仅首次新建会话，第二次复用


def test_qr_key_failure(monkeypatch):
    monkeypatch.setattr(netease, "qr_key", lambda sid: "")
    r = _client().get("/api/v1/auth/qr/key")
    assert r.status_code == 502


def test_qr_check_waiting(monkeypatch):
    monkeypatch.setattr(netease, "qr_check", lambda sid, key: {"code": 801, "message": "等待扫码"})
    c = _client()
    c.get("/api/v1/auth/qr/key")  # 拿到会话 Cookie
    r = c.get("/api/v1/auth/qr/check", params={"key": KEY})
    assert r.status_code == 200
    assert r.json()["data"]["code"] == 801


def test_qr_check_confirmed(monkeypatch):
    monkeypatch.setattr(
        netease,
        "qr_check",
        lambda sid, key: {
            "code": 803,
            "message": "授权登录成功",
            "profile": {"userId": 1, "nickname": "测试用户", "avatarUrl": "https://a.png"},
        },
    )
    c = _client()
    c.get("/api/v1/auth/qr/key")
    r = c.get("/api/v1/auth/qr/check", params={"key": KEY})
    assert r.status_code == 200
    assert r.json()["data"]["profile"]["nickname"] == "测试用户"


def test_qr_check_without_session():
    r = _client().get("/api/v1/auth/qr/check", params={"key": KEY})
    assert r.status_code == 400


def test_qr_check_requires_key():
    c = _client()
    c.get("/api/v1/auth/qr/key")
    r = c.get("/api/v1/auth/qr/check")
    assert r.status_code == 422


def test_auth_status(monkeypatch):
    monkeypatch.setattr(netease, "status", lambda sid: {"logged_in": True, "profile": {"userId": 1}})
    c = _client()
    c.get("/api/v1/auth/qr/key")
    r = c.get("/api/v1/auth/status")
    assert r.status_code == 200
    assert r.json()["data"]["logged_in"] is True


def test_auth_status_without_session():
    r = _client().get("/api/v1/auth/status")
    assert r.json()["data"] == {"logged_in": False, "profile": None}


def test_logout(monkeypatch):
    logged_out = []
    monkeypatch.setattr(netease, "logout", lambda sid: logged_out.append(sid))
    c = _client()
    c.get("/api/v1/auth/qr/key")
    r = c.post("/api/v1/auth/logout")
    assert r.status_code == 200
    assert logged_out
    assert "tunebox_session" in r.headers.get("set-cookie", "")


def test_my_playlists(monkeypatch):
    monkeypatch.setattr(
        netease,
        "user_playlists",
        lambda sid: [{"id": 1, "name": "我的歌单", "cover": "", "trackCount": 10}],
    )
    c = _client()
    c.get("/api/v1/auth/qr/key")
    r = c.get("/api/v1/user/playlists")
    assert r.status_code == 200
    assert r.json()["data"][0]["name"] == "我的歌单"


def test_my_playlists_not_logged_in(monkeypatch):
    monkeypatch.setattr(netease, "user_playlists", lambda sid: None)
    c = _client()
    c.get("/api/v1/auth/qr/key")
    r = c.get("/api/v1/user/playlists")
    assert r.status_code == 401


def test_my_playlists_without_session():
    r = _client().get("/api/v1/user/playlists")
    assert r.status_code == 401
