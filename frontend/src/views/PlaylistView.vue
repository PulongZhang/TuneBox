<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { reactive } from 'vue'
import { getPlaylist } from '../api'
import { useAudio } from '../composables/useAudio'
import { usePlaylistStore } from '../stores/playlist'
import type { Song } from '../types'
import { downloadFile } from '../utils/download'

const playlist = usePlaylistStore()
const { loadAndPlay } = useAudio()

const contextMenu = reactive({ visible: false, x: 0, y: 0, index: -1 })

function playAt(idx: number) {
  playlist.playAt(idx)
  loadAndPlay(playlist.list[idx])
}

async function loadPlaylist() {
  let input = ''
  try {
    const { value } = await ElMessageBox.prompt(
      '输入歌单 ID 或链接（数字 ID 即可，如 3778678）',
      '加载歌单',
      {
        confirmButtonText: '加载',
        cancelButtonText: '取消',
        inputPattern: /\d+/,
        inputErrorMessage: '未识别到歌单 ID',
      },
    )
    input = value ?? ''
  } catch {
    return
  }
  const m = input.match(/[?&]id=(\d+)/)
  const pid = m ? m[1] : input.trim()
  try {
    const songs = await getPlaylist(pid)
    playlist.setList(songs)
    ElMessage.success(`加载了 ${songs.length} 首歌曲`)
  } catch {
    ElMessage.error('❌ 歌单加载失败')
  }
}

function removeAt(idx: number) {
  ElMessage.info(`已移除: ${playlist.list[idx].name}`)
  playlist.removeAt(idx)
}

function clearAll() {
  playlist.clear()
  ElMessage.info('已清空播放列表')
}

function triggerDownload(song: Song, kind: 'audio' | 'lyric') {
  const path = kind === 'audio' ? 'download' : 'lyric/download'
  downloadFile(`/api/v1/songs/${song.id}/${path}`, `${song.artist} - ${song.name}`)
}

function onRowContextMenu(row: Song, _col: unknown, event: MouseEvent) {
  event.preventDefault()
  contextMenu.index = playlist.list.indexOf(row)
  contextMenu.x = event.clientX
  contextMenu.y = event.clientY
  contextMenu.visible = true
}

function onMenu(action: string) {
  contextMenu.visible = false
  const song = playlist.list[contextMenu.index]
  if (!song) return
  if (action === 'play') playAt(contextMenu.index)
  else if (action === 'download') triggerDownload(song, 'audio')
  else if (action === 'lyric') triggerDownload(song, 'lyric')
  else if (action === 'remove') removeAt(contextMenu.index)
}

defineExpose({ loadPlaylist, clearAll })
</script>

<template>
  <div class="playlist-view" @click="contextMenu.visible = false">
    <el-empty v-if="!playlist.list.length" description="播放列表为空" :image-size="120">
      <template #image>
        <div style="font-size: 56px">📋</div>
      </template>
      <template #description>
        <div>
          <div>播放列表为空</div>
          <div style="font-size: 12px; color: var(--el-text-color-secondary)">
            在搜索结果中双击歌曲，或点击上方「加载歌单」导入整张歌单
          </div>
        </div>
      </template>
    </el-empty>

    <el-table
      v-else
      :data="playlist.list"
      highlight-current-row
      :row-class-name="({ row }: any) => (playlist.currentIndex === playlist.list.indexOf(row) ? 'playing-row' : '')"
      style="width: 100%"
      @row-dblclick="(row: Song) => playAt(playlist.list.indexOf(row))"
      @row-contextmenu="onRowContextMenu"
    >
      <el-table-column label="#" width="48" align="center">
        <template #default="{ $index }">{{ $index + 1 }}</template>
      </el-table-column>
      <el-table-column label="歌曲" min-width="220" show-overflow-tooltip>
        <template #default="{ row }">
          <span style="font-weight: 600">{{ row.name }}</span>
          <span style="color: var(--el-text-color-secondary); margin-left: 8px">— {{ row.artist }}</span>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140" align="center">
        <template #default="{ $index }">
          <el-button size="small" type="primary" plain @click="playAt($index)">播放</el-button>
          <el-button size="small" circle title="下载音频" @click="triggerDownload(playlist.list[$index], 'audio')">⬇</el-button>
          <el-button size="small" circle type="danger" plain title="移除" @click="removeAt($index)">✕</el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- 右键菜单 -->
    <ul
      v-show="contextMenu.visible"
      class="context-menu"
      :style="{ left: contextMenu.x + 'px', top: contextMenu.y + 'px' }"
    >
      <li @click="onMenu('play')">▶ 播放</li>
      <li @click="onMenu('download')">⬇ 下载音频</li>
      <li @click="onMenu('lyric')">📃 下载歌词</li>
      <li @click="onMenu('remove')">✕ 移除</li>
      <li class="danger" @click="clearAll">🗑 清空全部</li>
    </ul>
  </div>
</template>

<style scoped>
.playlist-view {
  position: relative;
  height: 100%;
  overflow-y: auto;
  padding: 12px;
}
.context-menu {
  position: fixed;
  z-index: 3000;
  margin: 0;
  padding: 4px 0;
  list-style: none;
  background: #fff;
  border: 1px solid var(--el-border-color);
  border-radius: 6px;
  box-shadow: var(--el-box-shadow-light);
  min-width: 140px;
}
.context-menu li {
  padding: 8px 16px;
  font-size: 13px;
  cursor: pointer;
}
.context-menu li:hover {
  background: var(--el-fill-color-light);
}
.context-menu li.danger {
  color: var(--el-color-danger);
}
</style>
