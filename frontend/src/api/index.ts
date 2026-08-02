import axios from 'axios'
import type { LyricData, NetEaseProfile, Song, SongDetail, UserPlaylist } from '../types'

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

// ---------- 网易云账号（官方扫码登录） ----------

export async function getQrKey(): Promise<{ key: string }> {
  const { data } = await http.get<{ data: { key: string } }>('/auth/qr/key')
  return data.data
}

export interface QrCheckResult {
  code: number
  message?: string
  profile?: NetEaseProfile
}

export async function checkQr(key: string): Promise<QrCheckResult> {
  const { data } = await http.get<{ data: QrCheckResult }>('/auth/qr/check', { params: { key } })
  return data.data
}

export async function getAuthStatus(): Promise<{ loggedIn: boolean; profile: NetEaseProfile | null }> {
  const { data } = await http.get<{ data: { logged_in: boolean; profile: NetEaseProfile | null } }>('/auth/status')
  return { loggedIn: data.data.logged_in, profile: data.data.profile }
}

export async function postLogout(): Promise<void> {
  await http.post('/auth/logout')
}

export async function getMyPlaylists(): Promise<UserPlaylist[]> {
  const { data } = await http.get<{ data: UserPlaylist[] }>('/user/playlists')
  return data.data
}
