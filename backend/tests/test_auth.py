"""网易云登录路由测试：mock netease 模块，不触网。"""

from fastapi.testclient import TestClient

from app import app as fastapi_app
from app import netease


def _client():
    return TestClient(fastapi_app)


def test_auth_status(monkeypatch):
    monkeypatch.setattr(netease, "status", lambda sid: {"logged_in": True, "profile": {"userId": 1}})
    r = _client().get("/api/v1/auth/status")
    assert r.status_code == 200
    assert r.json()["data"]["logged_in"] is True


def test_auth_status_without_session():
    r = _client().get("/api/v1/auth/status")
    assert r.json()["data"] == {"logged_in": False, "profile": None}


def test_import_cookie_ok(monkeypatch):
    """首次导入 Cookie 创建会话并下发 tunebox_session。"""
    monkeypatch.setattr(
        netease,
        "import_cookie",
        lambda sid, cookie: (True, {"userId": 1, "nickname": "饼干", "avatarUrl": ""}),
    )
    r = _client().post("/api/v1/auth/cookie", json={"cookie": "MUSIC_U=abc; __csrf=123"})
    assert r.status_code == 200
    assert r.json()["data"]["profile"]["nickname"] == "饼干"
    assert "tunebox_session" in r.headers.get("set-cookie", "")


def test_import_cookie_invalid(monkeypatch):
    monkeypatch.setattr(netease, "import_cookie", lambda sid, cookie: (False, None))
    r = _client().post("/api/v1/auth/cookie", json={"cookie": "MUSIC_U=bad"})
    assert r.status_code == 400


def test_import_cookie_missing():
    r = _client().post("/api/v1/auth/cookie", json={})
    assert r.status_code == 400


def test_logout(monkeypatch):
    logged_out = []
    monkeypatch.setattr(netease, "logout", lambda sid: logged_out.append(sid))
    monkeypatch.setattr(
        netease,
        "import_cookie",
        lambda sid, cookie: (True, {"userId": 1, "nickname": "n", "avatarUrl": ""}),
    )
    c = _client()
    c.post("/api/v1/auth/cookie", json={"cookie": "MUSIC_U=abc"})
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
    monkeypatch.setattr(
        netease,
        "import_cookie",
        lambda sid, cookie: (True, {"userId": 1, "nickname": "n", "avatarUrl": ""}),
    )
    c = _client()
    c.post("/api/v1/auth/cookie", json={"cookie": "MUSIC_U=abc"})
    r = c.get("/api/v1/user/playlists")
    assert r.status_code == 200
    assert r.json()["data"][0]["name"] == "我的歌单"


def test_my_playlists_not_logged_in(monkeypatch):
    monkeypatch.setattr(netease, "user_playlists", lambda sid: None)
    monkeypatch.setattr(
        netease,
        "import_cookie",
        lambda sid, cookie: (True, {"userId": 1, "nickname": "n", "avatarUrl": ""}),
    )
    c = _client()
    c.post("/api/v1/auth/cookie", json={"cookie": "MUSIC_U=abc"})
    r = c.get("/api/v1/user/playlists")
    assert r.status_code == 401


def test_my_playlists_without_session():
    r = _client().get("/api/v1/user/playlists")
    assert r.status_code == 401
