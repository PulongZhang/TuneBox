"""API 路由：/api/v1 全部端点。从旧版单文件播放器移植。"""

import re

from fastapi import APIRouter, HTTPException, Query, Request
from fastapi.responses import Response, StreamingResponse

from . import client, streaming

router = APIRouter(prefix="/api/v1")


@router.get("/health")
def health():
    return {"status": "ok"}


@router.get("/search")
def search(q: str = Query(..., min_length=1), limit: int = Query(30, ge=1, le=100)):
    try:
        r = client.api_get("/163_search", {"keyword": q, "limit": limit})
        body = r.json()
        if body.get("code") != 200:
            raise HTTPException(status_code=502, detail="上游搜索失败")
        raw = body.get("data", {})
        if isinstance(raw, dict):
            raw = raw.get("songs", [])
        songs = [client.normalize_song(s) for s in raw]
        return {"data": songs}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"搜索失败: {e}") from e


@router.get("/songs/{sid}")
def song(sid: str):
    raw = client.get_song_meta(sid)
    if not raw:
        raise HTTPException(status_code=404, detail="歌曲不存在或无法获取音源")
    return {"data": {
        "id": raw.get("id"),
        "url": raw.get("url", ""),
        "br": raw.get("br", 0),
        "size": raw.get("size", 0),
        "level": raw.get("level", ""),
        "md5": raw.get("md5", ""),
        "name": raw.get("name", ""),
        "artist": raw.get("artist", ""),
        "cover": client.try_https(raw.get("picUrl", "")),
    }}


@router.get("/songs/{sid}/lyric")
def lyric(sid: str):
    try:
        r = client.api_get("/163_lyric", {"id": sid}, timeout=8)
        body = r.json()
        d = (body.get("data") or {}) if body.get("code") == 200 else {}
    except Exception:
        d = {}
    return {"data": {
        "lrc": d.get("lrc", ""),
        "tlrc": d.get("tlyric", ""),
        "romalrc": d.get("romalrc", ""),
        "klyric": d.get("klyric", ""),
    }}


@router.get("/playlists/{pid}")
def playlist(pid: str):
    try:
        r = client.api_get("/163_playlist", {"id": pid})
        body = r.json()
        tracks: list = []
        data = body.get("data")
        if isinstance(data, dict):
            tracks = data.get("tracks", [])
        elif isinstance(data, list):
            tracks = data
        elif isinstance(body, dict) and "tracks" in body:
            tracks = body["tracks"]
        songs = [client.normalize_song(t) for t in tracks]
        return {"data": songs}
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"歌单加载失败: {e}") from e


@router.get("/cover-proxy")
def cover_proxy(url: str = Query(..., min_length=1)):
    data, ct = streaming.proxy_fetch(url)
    if data is None:
        raise HTTPException(status_code=404, detail="封面获取失败")
    return Response(content=data, media_type=ct or "image/jpeg")


def _stream_response(audio_url: str, range_header: str | None = None):
    gen, ct, _, total_size = streaming.stream_audio(audio_url, range_header)
    headers = {
        "Accept-Ranges": "bytes",
        "Cache-Control": "no-cache",
        "Content-Disposition": "inline",
    }

    if range_header and total_size > 0:
        m = re.match(r"bytes=(\d+)-(\d*)", range_header)
        if m:
            start = int(m.group(1))
            end = int(m.group(2)) if m.group(2) else total_size - 1
            end = min(end, total_size - 1)
            headers["Content-Range"] = f"bytes {start}-{end}/{total_size}"
            headers["Content-Length"] = str(end - start + 1)
            gen, ct, _, _ = streaming.stream_audio(audio_url, f"bytes={start}-{end}")
            return StreamingResponse(gen, status_code=206, media_type=ct, headers=headers)

    if total_size > 0:
        headers["Content-Length"] = str(total_size)
    return StreamingResponse(gen, status_code=200, media_type=ct, headers=headers)


@router.get("/songs/{sid}/stream")
def stream(sid: str, request: Request):
    audio_url = client.get_audio_url(sid)
    if not audio_url:
        raise HTTPException(status_code=404, detail="无法获取音源")
    return _stream_response(audio_url, request.headers.get("Range"))


@router.get("/songs/{sid}/download")
def download(sid: str):
    raw = client.get_song_meta(sid)
    audio_url = raw.get("url", "")
    if not audio_url:
        raise HTTPException(status_code=404, detail="无法获取音源")
    name = raw.get("name", sid)
    artist = raw.get("artist", "")
    title = f"{artist} - {name}" if artist else name

    ext = streaming._guess_ext(audio_url)
    if ext not in streaming.AUDIO_EXTS:
        ext = "flac"

    filename = streaming.song_filename(title, ext, name, sid)
    gen, ct, _, total_size = streaming.stream_audio(audio_url)
    hdrs = streaming.make_download_headers(filename, fallback=f"{name}.{ext}")
    if total_size > 0:
        hdrs["Content-Length"] = str(total_size)
    return StreamingResponse(gen, status_code=200, media_type=ct, headers=hdrs)


@router.get("/songs/{sid}/lyric/download")
def download_lyric(sid: str):
    try:
        r = client.api_get("/163_lyric", {"id": sid}, timeout=8)
        body = r.json()
        d = (body.get("data") or {}) if body.get("code") == 200 else {}
    except Exception:
        d = {}
    raw = client.get_song_meta(sid)
    name = raw.get("name", sid)
    artist = raw.get("artist", "")
    title = f"{artist} - {name}" if artist else name
    filename = streaming.song_filename(title, "lrc", name, sid)
    content = streaming.make_lyric_text(d, name, artist)
    hdrs = streaming.make_download_headers(filename, fallback=f"{name}.lrc")
    return Response(
        content=content,
        status_code=200,
        media_type="text/plain; charset=utf-8",
        headers=hdrs,
    )
