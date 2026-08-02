import { defineStore } from 'pinia'
import type { LyricLine, PlayMode, SongDetail } from '../types'

const LS_KEY = 'music.player'

export const QUALITY_LEVELS = ['jymaster', 'lossless', 'hires', 'exhigh', 'higher', 'standard']

function loadPersisted(): { volume: number; mode: PlayMode; quality: string } {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      return {
        volume: Number.isFinite(parsed.volume) ? parsed.volume : 70,
        mode: ['loop', 'shuffle', 'repeat-one'].includes(parsed.mode) ? parsed.mode : 'loop',
        quality: QUALITY_LEVELS.includes(parsed.quality) ? parsed.quality : 'standard',
      }
    }
  } catch {
    // 忽略损坏数据
  }
  return { volume: 70, mode: 'loop', quality: 'standard' }
}

export const usePlayerStore = defineStore('player', {
  state: () => {
    const persisted = loadPersisted()
    return {
      playing: false,
      volume: persisted.volume,
      muted: false,
      mode: persisted.mode as PlayMode,
      quality: persisted.quality,
      currentTime: 0,
      duration: 0,
      detail: null as SongDetail | null,
      lyricLines: [] as LyricLine[],
    }
  },
  actions: {
    persist() {
      localStorage.setItem(
        LS_KEY,
        JSON.stringify({ volume: this.volume, mode: this.mode, quality: this.quality }),
      )
    },
    setQuality(q: string) {
      if (QUALITY_LEVELS.includes(q)) {
        this.quality = q
        this.persist()
      }
    },
    setDetail(detail: SongDetail | null) {
      this.detail = detail
    },
    setLyricLines(lines: LyricLine[]) {
      this.lyricLines = lines
    },
    setVolume(v: number) {
      this.volume = v
      this.persist()
    },
    toggleMuted() {
      this.muted = !this.muted
    },
    cycleMode() {
      const order: PlayMode[] = ['loop', 'shuffle', 'repeat-one']
      this.mode = order[(order.indexOf(this.mode) + 1) % order.length]
      this.persist()
    },
  },
})
