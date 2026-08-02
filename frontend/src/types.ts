/** 与后端 /api/v1 对齐的数据类型 */

export interface Song {
  id: number | string
  name: string
  artist: string
  album: string
  cover: string
  duration: number
}

export interface SongDetail {
  id: number | string
  url: string
  br: number
  size: number
  level: string
  md5: string
  name: string
  artist: string
  cover: string
}

export interface LyricData {
  lrc: string
  tlrc: string
  romalrc: string
  klyric: string
}

export interface LyricLine {
  ms: number
  orig: string
  tran: string
}

export type PlayMode = 'loop' | 'shuffle' | 'repeat-one'

export interface NetEaseProfile {
  userId: number | string
  nickname: string
  avatarUrl: string
}

export interface UserPlaylist {
  id: number | string
  name: string
  cover: string
  trackCount: number
}
