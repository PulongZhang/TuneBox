import { defineStore } from 'pinia'
import type { Song } from '../types'

const LS_KEY = 'music.playlist'

function loadPersisted(): { list: Song[]; currentIndex: number } {
  try {
    const raw = localStorage.getItem(LS_KEY)
    if (raw) {
      const parsed = JSON.parse(raw)
      if (Array.isArray(parsed.list)) {
        const idx = typeof parsed.currentIndex === 'number' ? parsed.currentIndex : -1
        return { list: parsed.list, currentIndex: idx }
      }
    }
  } catch {
    // 本地数据损坏时从头开始
  }
  return { list: [], currentIndex: -1 }
}

export const usePlaylistStore = defineStore('playlist', {
  state: () => {
    const persisted = loadPersisted()
    return {
      list: persisted.list as Song[],
      currentIndex: persisted.currentIndex,
    }
  },
  getters: {
    currentSong: (state): Song | null =>
      state.currentIndex >= 0 && state.currentIndex < state.list.length
        ? state.list[state.currentIndex]
        : null,
  },
  actions: {
    persist() {
      localStorage.setItem(LS_KEY, JSON.stringify({ list: this.list, currentIndex: this.currentIndex }))
    },
    add(song: Song) {
      if (!this.list.some((s) => String(s.id) === String(song.id))) {
        this.list.push(song)
        this.persist()
      }
    },
    removeAt(idx: number) {
      this.list.splice(idx, 1)
      if (this.currentIndex === idx) {
        this.currentIndex = -1
      } else if (this.currentIndex > idx) {
        this.currentIndex -= 1
      }
      this.persist()
    },
    clear() {
      this.list = []
      this.currentIndex = -1
      this.persist()
    },
    setList(songs: Song[]) {
      this.list = songs
      this.currentIndex = -1
      this.persist()
    },
    indexOf(song: Song): number {
      return this.list.findIndex((s) => String(s.id) === String(song.id))
    },
    playAt(idx: number) {
      if (idx >= 0 && idx < this.list.length) {
        this.currentIndex = idx
        this.persist()
      }
    },
  },
})
