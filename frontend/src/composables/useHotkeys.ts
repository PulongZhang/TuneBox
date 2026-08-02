import { onBeforeUnmount, onMounted } from 'vue'
import { downloadLyricUrl, downloadUrl } from '../api'
import { usePlayerStore } from '../stores/player'
import { usePlaylistStore } from '../stores/playlist'
import { downloadFile } from '../utils/download'
import { useAudio } from './useAudio'

/** 全局快捷键：空格/←→/↑↓/M/Delete/Ctrl+S/Ctrl+L */
export function useHotkeys(getViewMode: () => string) {
  const player = usePlayerStore()
  const playlist = usePlaylistStore()
  const { audio, toggle, next, prev } = useAudio()

  function onKeydown(e: KeyboardEvent) {
    const target = e.target as HTMLElement
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA') return

    switch (e.code) {
      case 'Space':
        e.preventDefault()
        toggle()
        break
      case 'ArrowRight':
        next()
        break
      case 'ArrowLeft':
        prev()
        break
      case 'ArrowUp':
        player.setVolume(Math.min(100, player.volume + 5))
        break
      case 'ArrowDown':
        player.setVolume(Math.max(0, player.volume - 5))
        break
      case 'KeyM':
        player.toggleMuted()
        break
      case 'Delete':
        if (getViewMode() === 'playlist' && playlist.currentIndex >= 0) {
          playlist.removeAt(playlist.currentIndex)
        }
        break
      case 'KeyS':
        if (e.ctrlKey && playlist.currentSong) {
          e.preventDefault()
          downloadFile(downloadUrl(playlist.currentSong.id), 'song')
        }
        break
      case 'KeyL':
        if (e.ctrlKey && playlist.currentSong) {
          e.preventDefault()
          downloadFile(downloadLyricUrl(playlist.currentSong.id), 'lyric')
        }
        break
      default:
        break
    }
  }

  onMounted(() => window.addEventListener('keydown', onKeydown))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKeydown))

  return { audio }
}
