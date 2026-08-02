<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { computed, ref, watch } from 'vue'
import { coverUrl, downloadLyricUrl, downloadUrl, getLyric, getSong } from './api'
import { useAudio } from './composables/useAudio'
import { useHotkeys } from './composables/useHotkeys'
import { parseLyric } from './composables/useLyric'
import { usePlayerStore } from './stores/player'
import { usePlaylistStore } from './stores/playlist'
import { downloadFile } from './utils/download'
import LyricView from './views/LyricView.vue'
import PlaylistView from './views/PlaylistView.vue'
import SearchView from './views/SearchView.vue'

const player = usePlayerStore()
const playlist = usePlaylistStore()
const { reloadCurrent, toggle, next, prev, seek } = useAudio()

const activeTab = ref('search')
const keyword = ref('')
const searchRef = ref<InstanceType<typeof SearchView>>()
const playlistRef = ref<InstanceType<typeof PlaylistView>>()

const QUALITY_MAP: Record<string, { label: string; type: 'primary' | 'success' | 'warning' | 'info' | 'danger' }> = {
  jymaster: { label: '💎 臻品母带', type: 'primary' },
  lossless: { label: '🔵 无损FLAC', type: 'success' },
  hires: { label: '🟣 Hi-Res', type: 'warning' },
  exhigh: { label: '🟢 极高320kbps', type: 'info' },
  higher: { label: '🟡 较高192kbps', type: 'info' },
  standard: { label: '⚪ 标准128kbps', type: 'info' },
}

const modeMeta: Record<string, { icon: string; label: string }> = {
  loop: { icon: '🔁', label: '列表循环' },
  shuffle: { icon: '🔀', label: '随机播放' },
  'repeat-one': { icon: '🔂', label: '单曲循环' },
}
const modeIcon = computed(() => modeMeta[player.mode].icon)
const modeLabel = computed(() => modeMeta[player.mode].label)

const qualityOptions = Object.entries(QUALITY_MAP).map(([value, meta]) => ({
  value,
  label: meta.label,
}))

useHotkeys(() => activeTab.value)

// 切换音质：重载当前曲目并刷新音质详情
watch(
  () => player.quality,
  async (q) => {
    const song = playlist.currentSong
    if (!song) return
    reloadCurrent()
    try {
      const detail = await getSong(song.id, q)
      player.setDetail(detail)
    } catch {
      // 详情拉取失败不影响播放
    }
    ElMessage.success(`已切换为 ${QUALITY_MAP[q]?.label}`)
  },
)

// 切换当前曲目：拉取音质详情与歌词
watch(
  () => playlist.currentSong,
  async (song) => {
    if (!song) {
      player.setDetail(null)
      player.setLyricLines([])
      return
    }
    player.setDetail(null)
    player.setLyricLines([])
    try {
      const [detail, lyric] = await Promise.all([getSong(song.id, player.quality), getLyric(song.id)])
      player.setDetail(detail)
      player.setLyricLines(parseLyric(lyric.lrc, lyric.tlrc))
    } catch {
      ElMessage.warning('❌ 获取链接失败')
    }
  },
  { immediate: true },
)

function doSearch() {
  searchRef.value?.doSearch(keyword.value)
}

function formatTime(s: number): string {
  if (!Number.isFinite(s) || s < 0) return '0:00'
  return `${Math.floor(s / 60)}:${String(Math.floor(s % 60)).padStart(2, '0')}`
}

function triggerDownload(kind: 'audio' | 'lyric') {
  const song = playlist.currentSong
  if (!song) return
  const url = kind === 'audio' ? downloadUrl(song.id, player.quality) : downloadLyricUrl(song.id)
  downloadFile(url, `${song.artist} - ${song.name}`)
  ElMessage.success(`下载: ${song.artist} - ${song.name}`)
}
</script>

<template>
  <el-container class="app">
    <el-header class="topbar">
      <div class="logo">🎵 TuneBox</div>
      <div class="search-box">
        <el-input v-model="keyword" placeholder="搜歌..." clearable size="large" @keyup.enter="doSearch" />
        <el-button type="primary" size="large" @click="doSearch">搜索</el-button>
      </div>
      <el-button size="large" @click="playlistRef?.loadPlaylist()">📋 加载歌单</el-button>
    </el-header>

    <el-container class="body">
      <!-- 左侧播放器 -->
      <el-aside width="340px" class="player-panel">
        <el-image
          :src="playlist.currentSong?.cover ? coverUrl(playlist.currentSong.cover) : ''"
          fit="cover"
          class="np-cover"
        >
          <template #error>
            <div class="np-cover-fallback">🎵</div>
          </template>
        </el-image>

        <div class="np-title">{{ playlist.currentSong?.name || '未在播放' }}</div>
        <div class="np-artist">{{ playlist.currentSong?.artist || '从搜索或歌单选择歌曲' }}</div>
        <div class="np-quality">
          <span class="q-label">音质</span>
          <el-select
            v-model="player.quality"
            size="small"
            style="width: 150px"
            @change="player.persist()"
          >
            <el-option v-for="opt in qualityOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
          <el-tag
            v-if="player.detail?.level && QUALITY_MAP[player.detail.level]"
            :type="QUALITY_MAP[player.detail.level].type"
            size="small"
          >
            {{ QUALITY_MAP[player.detail.level].label }}
          </el-tag>
        </div>

        <div class="np-progress">
          <span>{{ formatTime(player.currentTime) }}</span>
          <el-slider
            class="prog-slider"
            :model-value="player.currentTime"
            :max="Math.max(player.duration, 1)"
            :show-tooltip="false"
            :disabled="!player.duration"
            @change="(v: number | number[]) => seek(Array.isArray(v) ? v[0] : v)"
          />
          <span>{{ formatTime(player.duration) }}</span>
        </div>

        <div class="np-controls">
          <el-tooltip :content="modeLabel" placement="top">
            <el-button circle size="large" @click="player.cycleMode()">{{ modeIcon }}</el-button>
          </el-tooltip>
          <el-button circle size="large" @click="prev">⏮</el-button>
          <el-button circle size="large" type="primary" class="play-btn" @click="toggle">
            {{ player.playing ? '⏸' : '▶' }}
          </el-button>
          <el-button circle size="large" @click="next">⏭</el-button>
          <el-button circle size="large" @click="player.toggleMuted()">
            {{ player.muted || player.volume === 0 ? '🔇' : '🔊' }}
          </el-button>
        </div>

        <div class="np-volume">
          <el-slider v-model="player.volume" :show-tooltip="false" class="vol-slider" @change="player.persist()" />
        </div>

        <div class="np-actions">
          <el-button size="small" :disabled="!playlist.currentSong" @click="triggerDownload('audio')">
            ⬇ 下载音频
          </el-button>
          <el-button size="small" :disabled="!playlist.currentSong" @click="triggerDownload('lyric')">
            📃 下载歌词
          </el-button>
        </div>
      </el-aside>

      <!-- 右侧主区 -->
      <el-main class="right-panel">
        <el-tabs v-model="activeTab" class="view-tabs">
          <el-tab-pane label="🔍 搜索" name="search">
            <SearchView ref="searchRef" />
          </el-tab-pane>
          <el-tab-pane :label="`📋 播放列表 (${playlist.list.length})`" name="playlist">
            <PlaylistView ref="playlistRef" />
          </el-tab-pane>
          <el-tab-pane label="🎤 歌词" name="lyrics">
            <LyricView />
          </el-tab-pane>
        </el-tabs>
      </el-main>
    </el-container>
  </el-container>
</template>

<style>
html,
body,
#app {
  height: 100%;
  margin: 0;
  background: var(--el-bg-color-page);
}
</style>

<style scoped>
.app {
  height: 100%;
}
.topbar {
  display: flex;
  align-items: center;
  gap: 16px;
  border-bottom: 1px solid var(--el-border-color-light);
  background: #fff;
}
.logo {
  font-size: 18px;
  font-weight: 700;
  white-space: nowrap;
}
.search-box {
  flex: 1;
  max-width: 480px;
  display: flex;
  gap: 8px;
}
.body {
  height: calc(100% - 60px);
}
.player-panel {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 10px;
  padding: 24px 20px;
  border-right: 1px solid var(--el-border-color-light);
  background: #fff;
  overflow-y: auto;
}
.np-cover {
  width: 200px;
  height: 200px;
  border-radius: 12px;
  box-shadow: var(--el-box-shadow);
  flex-shrink: 0;
}
.np-cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 72px;
  background: var(--el-fill-color-light);
}
.np-title {
  font-size: 18px;
  font-weight: 700;
  text-align: center;
  word-break: break-all;
}
.np-quality {
  display: flex;
  align-items: center;
  gap: 8px;
}
.q-label {
  font-size: 12px;
  color: var(--el-text-color-secondary);
  white-space: nowrap;
}
.np-artist {
  font-size: 13px;
  color: var(--el-text-color-secondary);
  text-align: center;
}
.np-progress {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.prog-slider {
  flex: 1;
}
.np-controls {
  display: flex;
  gap: 8px;
  align-items: center;
}
.play-btn {
  width: 52px;
  height: 52px;
  font-size: 20px;
}
.np-volume {
  width: 100%;
  padding: 0 16px;
}
.np-actions {
  display: flex;
  gap: 8px;
}
.right-panel {
  padding: 0 16px;
  overflow: hidden;
}
.view-tabs {
  height: 100%;
  display: flex;
  flex-direction: column;
}
.view-tabs :deep(.el-tabs__header) {
  flex-shrink: 0;
}
.view-tabs :deep(.el-tabs__content) {
  flex: 1;
  min-height: 0;
  overflow: hidden;
}
.view-tabs :deep(.el-tab-pane) {
  height: 100%;
}
</style>
