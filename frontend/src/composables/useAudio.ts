import { ElMessage } from 'element-plus'
import { watch } from 'vue'
import { streamUrl } from '../api'
import { usePlayerStore } from '../stores/player'
import { usePlaylistStore } from '../stores/playlist'
import type { Song } from '../types'

/** 全局唯一的 audio 元素 */
const audio = new Audio()
audio.preload = 'auto'

export function useAudio() {
  const player = usePlayerStore()
  const playlist = usePlaylistStore()

  // audio 事件 → store 状态
  audio.ontimeupdate = () => {
    player.currentTime = audio.currentTime
  }
  audio.ondurationchange = () => {
    player.duration = audio.duration || 0
  }
  audio.onplay = () => {
    player.playing = true
  }
  audio.onpause = () => {
    player.playing = false
  }
  audio.onerror = () => {
    ElMessage.warning('⚠ 播放失败')
  }

  // 播放结束：单曲循环重播，否则按模式切下一曲
  audio.onended = () => {
    if (player.mode === 'repeat-one' || playlist.list.length === 1) {
      reloadCurrent()
    } else if (playlist.list.length > 1) {
      next()
    }
  }

  // 卡顿恢复：3 秒未起播则重试
  audio.onstalled = () => {
    setTimeout(() => {
      if (!audio.paused && audio.currentTime === 0) {
        audio.play().catch(() => {})
      }
    }, 3000)
  }

  // store 音量/静音 → audio
  watch(
    () => player.volume,
    (v) => {
      audio.volume = v / 100
    },
    { immediate: true },
  )
  watch(
    () => player.muted,
    (m) => {
      audio.muted = m
    },
    { immediate: true },
  )

  function loadAndPlay(song: Song) {
    const idx = playlist.indexOf(song)
    if (idx >= 0) playlist.playAt(idx)
    audio.src = streamUrl(song.id, player.quality)
    audio.load()
    audio.play().catch((e) => {
      if ((e as DOMException)?.name === 'NotAllowedError') {
        ElMessage.info('浏览器阻止了自动播放，请点击播放按钮')
      } else {
        ElMessage.warning('❌ 获取链接失败')
      }
    })
  }

  function reloadCurrent() {
    const song = playlist.currentSong
    if (!song) return
    audio.src = streamUrl(song.id, player.quality)
    audio.load()
    audio.play().catch(() => {})
  }

  function toggle() {
    if (audio.paused) {
      if (!audio.src && playlist.list.length) {
        playlist.playAt(0)
        loadAndPlay(playlist.list[0])
      } else {
        audio.play().catch(() => {})
      }
    } else {
      audio.pause()
    }
  }

  function next() {
    const n = playlist.list.length
    if (!n) return
    let idx: number
    if (player.mode === 'shuffle') {
      idx = Math.floor(Math.random() * n)
    } else {
      idx = (playlist.currentIndex + 1) % n
    }
    playlist.playAt(idx)
    loadAndPlay(playlist.list[idx])
  }

  function prev() {
    const n = playlist.list.length
    if (!n) return
    const idx = (playlist.currentIndex - 1 + n) % n
    playlist.playAt(idx)
    loadAndPlay(playlist.list[idx])
  }

  function seek(t: number) {
    audio.currentTime = t
  }

  return { audio, loadAndPlay, reloadCurrent, toggle, next, prev, seek }
}
