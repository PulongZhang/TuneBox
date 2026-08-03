"""client/streaming 模块单元测试。"""

import re

from app import client, streaming


def test_ua_sec_ch_ua_version_consistent():
    """Sec-Ch-Ua 的主版本号必须与 User-Agent 中的 Chrome 版本一致。"""
    for _ in range(20):
        headers = client.headers_for("https://example.com/")
        chrome_major = re.search(r"Chrome/(\d+)\.", headers["User-Agent"]).group(1)
        assert f'"Chromium";v="{chrome_major}"' in headers["Sec-Ch-Ua"]


def test_api_get_includes_apikey(monkeypatch):
    """api_get 应对每个上游请求附加 apikey 且不覆盖原参数。"""
    captured = {}

    def fake_get(url, params=None, headers=None, timeout=12):
        captured["url"] = url
        captured["params"] = params
        return type("R", (), {"json": lambda self: {}, "status_code": 200})()

    monkeypatch.setattr(client.SESSION, "get", fake_get)
    client.api_get("/163_search", {"keyword": "晴天", "limit": 5})

    assert captured["url"] == "https://test-upstream.example.com/api/163_search"
    assert captured["params"]["apikey"] == "test-key"
    assert captured["params"]["keyword"] == "晴天"
    assert captured["params"]["limit"] == 5


def test_forwarded_headers_stripped():
    h = client.headers_for("https://example.com/", {
        "X-Forwarded-For": "1.2.3.4",
        "X-Real-IP": "1.2.3.4",
        "Via": "proxy",
    })
    assert "X-Forwarded-For" not in h
    assert "X-Real-IP" not in h
    assert "Via" not in h
    assert "x-forwarded-for" not in h


def test_headers_contain_origin_and_referer():
    h = client.headers_for("https://cdn.example.com/audio.flac")
    assert h["Origin"] == "https://cdn.example.com"
    assert h["Referer"] == "https://cdn.example.com/"
    assert h["Host"] == "cdn.example.com"


def test_normalize_song():
    song = client.normalize_song({
        "id": 42,
        "name": "歌名",
        "ar": [{"name": "艺术家A"}, {"name": "艺术家B"}],
        "al": {"name": "专辑名", "picUrl": "https://x/cover.jpg"},
        "duration": 123456,
    })
    assert song["artist"] == "艺术家A / 艺术家B"
    assert song["album"] == "专辑名"
    assert song["cover"] == "https://x/cover.jpg"
    assert song["duration"] == 123456


def test_make_lyric_text():
    raw = {"lrc": "[00:01.00]第一句", "tlyric": "[00:01.00]First line"}
    text = streaming.make_lyric_text(raw, "歌名", "歌手")
    assert text.startswith("[ti:歌名]\n[ar:歌手]\n")
    assert "[00:01.00]第一句" in text
    assert "[翻译歌词]" in text
    assert "First line" in text


def test_make_download_headers_utf8_filename():
    h = streaming.make_download_headers("歌手 - 歌名.flac")
    assert "filename*=UTF-8''" in h["Content-Disposition"]
    assert "attachment;" in h["Content-Disposition"]


def test_song_filename_sanitizes_windows_illegal_chars():
    name = streaming.song_filename('A/B:C*D?.flac', "flac", "fallback", "1")
    assert "/" not in name and ":" not in name and "*" not in name
    assert name.endswith(".flac")


def test_guess_ext():
    assert streaming._guess_ext("https://cdn/a/b/song.flac?x=1") == "flac"
    assert streaming._guess_ext("https://cdn/a/b/song") == "flac"
    assert streaming._guess_ext("https://cdn/a/b/song.mp3") == "mp3"
