"""路由测试：mock 上游，覆盖参数校验、错误路径与响应头。"""

from fastapi.testclient import TestClient

from app import app as fastapi_app
from app import client


def _client():
    return TestClient(fastapi_app)


def test_health():
    r = _client().get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}


def test_search_requires_q():
    r = _client().get("/api/v1/search")
    assert r.status_code == 422


def test_search_normalizes_songs(monkeypatch):
    def fake_api_get(path, params=None, timeout=12):
        class R:
            def json(self):
                return {"code": 200, "data": {"songs": [
                    {"id": 1, "name": "A", "ar": [{"name": "X"}],
                     "al": {"name": "Al", "picUrl": "https://c/a.jpg"}, "duration": 1000},
                ]}}
        return R()

    monkeypatch.setattr(client, "api_get", fake_api_get)
    r = _client().get("/api/v1/search", params={"q": "test"})
    assert r.status_code == 200
    song = r.json()["data"][0]
    assert song["artist"] == "X"
    assert song["cover"].startswith("https://")


def test_search_upstream_error(monkeypatch):
    def fake_api_get(path, params=None, timeout=12):
        class R:
            def json(self):
                return {"code": 500}
        return R()

    monkeypatch.setattr(client, "api_get", fake_api_get)
    r = _client().get("/api/v1/search", params={"q": "test"})
    assert r.status_code == 502


def test_song_not_found(monkeypatch):
    monkeypatch.setattr(client, "get_song_meta", lambda sid: {})
    r = _client().get("/api/v1/songs/999")
    assert r.status_code == 404


def test_song_ok(monkeypatch):
    monkeypatch.setattr(client, "get_song_meta", lambda sid: {
        "id": sid, "url": "https://cdn/a.flac", "br": 5532261,
        "size": 1000, "level": "jymaster", "md5": "m", "name": "N", "artist": "A",
    })
    r = _client().get("/api/v1/songs/1")
    assert r.status_code == 200
    assert r.json()["data"]["level"] == "jymaster"


def test_stream_missing_url_404(monkeypatch):
    monkeypatch.setattr(client, "get_audio_url", lambda sid: "")
    r = _client().get("/api/v1/songs/1/stream")
    assert r.status_code == 404


def test_stream_206_with_range(monkeypatch):
    monkeypatch.setattr(client, "get_audio_url", lambda sid: "https://cdn/a.flac")
    monkeypatch.setattr(
        client, "api_get",
        lambda path, params=None, timeout=12: None,
    )

    # stream_audio 依赖真实 HEAD 请求，这里只验证 Range 头解析路径
    from fastapi.testclient import TestClient

    from app import streaming

    def fake_stream(url, range_header=None):
        class Gen:
            def __iter__(self):
                return iter([b"x" * 10])
        return Gen(), "audio/flac", "flac", 1000

    monkeypatch.setattr(streaming, "stream_audio", fake_stream)
    r = TestClient(fastapi_app).get(
        "/api/v1/songs/1/stream", headers={"Range": "bytes=0-99"}
    )
    assert r.status_code == 206
    assert r.headers["Content-Range"] == "bytes 0-99/1000"


def test_download_headers(monkeypatch):
    monkeypatch.setattr(client, "get_song_meta", lambda sid: {
        "url": "https://cdn/a.flac", "name": "歌", "artist": "歌手",
    })
    from app import streaming

    def fake_stream(url, range_header=None):
        return iter([b"x"]), "audio/flac", "flac", 100

    monkeypatch.setattr(streaming, "stream_audio", fake_stream)
    r = _client().get("/api/v1/songs/1/download")
    assert r.status_code == 200
    assert "attachment" in r.headers["content-disposition"]
    assert "filename*=UTF-8''" in r.headers["content-disposition"]


def test_lyric_empty_fallback(monkeypatch):
    def fake_api_get(path, params=None, timeout=12):
        class R:
            def json(self):
                return {"code": 500}
        return R()

    monkeypatch.setattr(client, "api_get", fake_api_get)
    monkeypatch.setattr(client, "get_song_meta", lambda sid: {})
    r = _client().get("/api/v1/songs/1/lyric")
    assert r.status_code == 200
    assert r.json()["data"]["lrc"] == ""


def test_cover_proxy_requires_url():
    r = _client().get("/api/v1/cover-proxy")
    assert r.status_code == 422


def test_playlist_upstream_error(monkeypatch):
    """上游抛异常（网络失败）→ 502。"""

    def fake_api_get(path, params=None, timeout=12):
        raise ConnectionError("upstream down")

    monkeypatch.setattr(client, "api_get", fake_api_get)
    r = _client().get("/api/v1/playlists/1")
    assert r.status_code == 502


def test_playlist_ok(monkeypatch):
    """上游歌单响应无 code 字段，直接返回 {"data": {tracks}}。"""

    def fake_api_get(path, params=None, timeout=12):
        class R:
            def json(self):
                return {"data": {"name": "热歌榜", "tracks": [
                    {"id": 1, "name": "A", "ar": [{"name": "X"}],
                     "al": {"name": "Al", "picUrl": "https://c/a.jpg"}, "duration": 1000},
                ]}}
        return R()

    monkeypatch.setattr(client, "api_get", fake_api_get)
    r = _client().get("/api/v1/playlists/1")
    assert r.status_code == 200
    assert r.json()["data"][0]["artist"] == "X"
