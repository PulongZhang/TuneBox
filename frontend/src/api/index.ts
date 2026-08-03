import axios from 'axios'
import type { LyricData, Song, SongDetail } from '../types'

const http = axios.create({ baseURL: '/api/v1', timeout: 15000 })

export async function searchSongs(q: string, limit = 30): Promise<Song[]> {
  const { data } = await http.get<{ data: Song[] }>('/search', { params: { q, limit } })
  return data.data
}

export async function getSong(sid: number | string, level = 'jymaster'): Promise<SongDetail> {
  const { data } = await http.get<{ data: SongDetail }>(`/songs/${sid}`, { params: { level } })
  return data.data
}

export async function getLyric(sid: number | string): Promise<LyricData> {
  const { data } = await http.get<{ data: LyricData }>(`/songs/${sid}/lyric`)
  return data.data
}

export async function getPlaylist(pid: number | string): Promise<Song[]> {
  const { data } = await http.get<{ data: Song[] }>(`/playlists/${pid}`)
  return data.data
}

export function streamUrl(sid: number | string, level = 'jymaster'): string {
  return `/api/v1/songs/${sid}/stream?level=${level}`
}

export function downloadUrl(sid: number | string, level = 'jymaster'): string {
  return `/api/v1/songs/${sid}/download?level=${level}`
}

export function downloadLyricUrl(sid: number | string): string {
  return `/api/v1/songs/${sid}/lyric/download`
}

export function coverUrl(url: string): string {
  return `/api/v1/cover-proxy?url=${encodeURIComponent(url)}`
}
