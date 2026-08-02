<script setup lang="ts">
import { ElMessage } from 'element-plus'
import { ref } from 'vue'
import { coverUrl, downloadUrl, searchSongs } from '../api'
import { useAudio } from '../composables/useAudio'
import { usePlaylistStore } from '../stores/playlist'
import type { Song } from '../types'
import { downloadFile } from '../utils/download'

const playlist = usePlaylistStore()
const { loadAndPlay } = useAudio()

const results = ref<Song[]>([])
const loading = ref(false)

function formatDuration(ms: number): string {
  if (!ms) return '--:--'
  return `${Math.floor(ms / 60000)}:${String(Math.floor(ms / 1000) % 60).padStart(2, '0')}`
}

async function doSearch(q: string) {
  if (!q.trim()) return
  loading.value = true
  try {
    results.value = await searchSongs(q.trim())
  } catch {
    ElMessage.error('搜索失败，请检查上游服务')
    results.value = []
  } finally {
    loading.value = false
  }
}

function play(song: Song) {
  playlist.add(song)
  loadAndPlay(song)
}

function addToList(song: Song) {
  playlist.add(song)
  ElMessage.success(`+ ${song.name}`)
}

function download(song: Song) {
  downloadFile(downloadUrl(song.id), `${song.artist} - ${song.name}`)
}

defineExpose({ doSearch })
</script>

<template>
  <div class="search-view" v-loading="loading">
    <el-empty v-if="!results.length" description="输入关键词搜索歌曲" :image-size="120">
      <template #image>
        <div style="font-size: 56px">🎵</div>
      </template>
      <template #description>
        <div>
          <div>输入关键词搜索歌曲</div>
          <div style="font-size: 12px; color: var(--el-text-color-secondary)">
            双击播放 · 单击加号加入列表 · 悬停可下载
          </div>
        </div>
      </template>
    </el-empty>

    <el-table v-else :data="results" highlight-current-row style="width: 100%" @row-dblclick="play">
      <el-table-column label="" width="52">
        <template #default="{ row }">
          <el-image
            :src="row.cover ? coverUrl(row.cover) : ''"
            fit="cover"
            style="width: 36px; height: 36px; border-radius: 4px"
          >
            <template #error>
              <div style="font-size: 18px; text-align: center">🎵</div>
            </template>
          </el-image>
        </template>
      </el-table-column>
      <el-table-column prop="name" label="歌曲" min-width="180" show-overflow-tooltip />
      <el-table-column prop="artist" label="歌手" min-width="120" show-overflow-tooltip />
      <el-table-column prop="album" label="专辑" min-width="140" show-overflow-tooltip />
      <el-table-column label="时长" width="80" align="center">
        <template #default="{ row }">{{ formatDuration(row.duration) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="150" align="center">
        <template #default="{ row }">
          <el-button size="small" type="primary" plain @click="play(row)">播放</el-button>
          <el-button size="small" @click="addToList(row)">加入</el-button>
          <el-button size="small" circle title="下载音频" @click="download(row)">⬇</el-button>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<style scoped>
.search-view {
  height: 100%;
  overflow-y: auto;
  padding: 12px;
}
</style>
