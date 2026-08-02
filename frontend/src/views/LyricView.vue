<script setup lang="ts">
import { nextTick, ref, watch } from 'vue'
import { currentLyricIndex } from '../composables/useLyric'
import { useAudio } from '../composables/useAudio'
import { usePlayerStore } from '../stores/player'

const player = usePlayerStore()
const { audio } = useAudio()

const container = ref<HTMLElement | null>(null)
const activeIndex = ref(-1)

// 200ms 轮询播放位置，同步高亮当前歌词行
let timer: number | undefined
watch(
  () => player.playing,
  (playing) => {
    if (playing) {
      timer = window.setInterval(syncHighlight, 200)
    } else {
      window.clearInterval(timer)
    }
  },
  { immediate: true },
)

async function syncHighlight() {
  const idx = currentLyricIndex(player.lyricLines, audio.currentTime * 1000)
  if (idx === activeIndex.value) return
  activeIndex.value = idx
  if (idx >= 0) {
    await nextTick()
    const el = container.value?.querySelector(`[data-idx="${idx}"]`)
    el?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  }
}
</script>

<template>
  <div ref="container" class="lyric-view" :class="{ empty: !player.lyricLines.length }">
    <el-empty v-if="!player.lyricLines.length" description="暂无歌词，开始播放后显示" :image-size="120">
      <template #image>
        <div style="font-size: 56px">🎤</div>
      </template>
    </el-empty>
    <div v-else class="lyrics">
      <div
        v-for="(line, i) in player.lyricLines"
        :key="line.ms + '-' + i"
        :data-idx="i"
        class="lyric-line"
        :class="{ active: i === activeIndex }"
      >
        <div class="orig">{{ line.orig }}</div>
        <div v-if="line.tran" class="tran">{{ line.tran }}</div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.lyric-view {
  height: 100%;
  overflow-y: auto;
  padding: 24px 32px 60px;
}
.lyric-view.empty {
  display: flex;
  align-items: center;
  justify-content: center;
}
.lyric-line {
  padding: 10px 0;
  transition: all 0.3s;
}
.lyric-line .orig {
  font-size: 16px;
  color: var(--el-text-color-secondary);
}
.lyric-line .tran {
  font-size: 13px;
  color: var(--el-text-color-placeholder);
  margin-top: 4px;
}
.lyric-line.active .orig {
  font-size: 22px;
  font-weight: 700;
  color: var(--el-color-primary);
}
.lyric-line.active .tran {
  font-size: 16px;
  color: var(--el-text-color-regular);
}
</style>
