<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import { onMounted, ref } from 'vue'
import { coverUrl, getAuthStatus, getMyPlaylists, getPlaylist, importCookie, postLogout } from '../api'
import { usePlaylistStore } from '../stores/playlist'
import type { NetEaseProfile, UserPlaylist } from '../types'

const emit = defineEmits<{ imported: [] }>()

const playlist = usePlaylistStore()

const loggedIn = ref(false)
const profile = ref<NetEaseProfile | null>(null)
const playlists = ref<UserPlaylist[]>([])
const loadingPlaylists = ref(false)

// Cookie 登录（网易云网页版登录后复制 Cookie 粘贴导入）
const cookieText = ref('')
const importingCookie = ref(false)

onMounted(refreshStatus)

async function refreshStatus() {
  try {
    const s = await getAuthStatus()
    loggedIn.value = s.loggedIn
    profile.value = s.profile
    if (s.loggedIn) loadPlaylists()
  } catch {
    // 后端不可用时保持未登录态
  }
}

async function submitCookie() {
  if (!cookieText.value.trim()) {
    ElMessage.warning('请先复制粘贴网易云 Cookie')
    return
  }
  importingCookie.value = true
  try {
    const p = await importCookie(cookieText.value.trim())
    cookieText.value = ''
    loggedIn.value = true
    profile.value = p
    ElMessage.success(`欢迎，${p.nickname}`)
    loadPlaylists()
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(detail ?? '登录失败，请检查 Cookie')
  } finally {
    importingCookie.value = false
  }
}

async function loadPlaylists() {
  loadingPlaylists.value = true
  try {
    playlists.value = await getMyPlaylists()
  } catch {
    playlists.value = []
  } finally {
    loadingPlaylists.value = false
  }
}

async function importPlaylist(p: UserPlaylist) {
  try {
    const songs = await getPlaylist(p.id)
    playlist.setList(songs)
    ElMessage.success(`已导入「${p.name}」${songs.length} 首`)
    emit('imported')
  } catch (e: unknown) {
    const detail = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
    ElMessage.error(`导入失败: ${detail ?? '请检查歌单是否私密'}`)
  }
}

async function doLogout() {
  try {
    await ElMessageBox.confirm('确定退出登录吗？', '退出登录', {
      confirmButtonText: '退出',
      cancelButtonText: '取消',
      type: 'warning',
    })
  } catch {
    return
  }
  try {
    await postLogout()
  } catch {
    // 即使后端失败也清除本地状态
  }
  loggedIn.value = false
  profile.value = null
  playlists.value = []
  ElMessage.info('已退出登录')
}
</script>

<template>
  <div class="my-view" v-loading="loadingPlaylists">
    <!-- 未登录：导入网易云 Cookie -->
    <div v-if="!loggedIn" class="login-card">
      <div class="login-title">🎵 登录网易云账号</div>
      <div class="login-desc">登录后可导入「我的歌单」与私有歌单</div>

      <div class="cookie-desc">
        获取方法：<br />
        ① 用浏览器打开 <b>music.163.com</b> 并登录你的账号<br />
        ② 按 F12 打开开发者工具 → 切换到「网络」标签 → 刷新页面<br />
        ③ 任选一个请求，在「请求头」里找到 <b>Cookie</b> 一整行，全选复制<br />
        ④ 粘贴到下面的输入框
      </div>
      <el-input
        v-model="cookieText"
        type="textarea"
        :rows="5"
        placeholder="MUSIC_U=xxxx; __csrf=xxxx; ..."
      />
      <el-button type="primary" :loading="importingCookie" class="cookie-btn" @click="submitCookie">
        登录并导入歌单
      </el-button>
    </div>

    <!-- 已登录：账号信息 + 我的歌单 -->
    <template v-else>
      <div class="user-card">
        <el-avatar :size="48" :src="profile?.avatarUrl ? coverUrl(profile.avatarUrl) : ''">
          {{ profile?.nickname?.[0] ?? '🎵' }}
        </el-avatar>
        <div class="user-meta">
          <div class="user-name">{{ profile?.nickname }}</div>
          <div class="user-sub">网易云账号已登录</div>
        </div>
        <el-button size="small" @click="doLogout">退出登录</el-button>
      </div>

      <div class="playlist-section">
        <div class="section-title">📋 我的歌单</div>
        <el-empty v-if="!playlists.length && !loadingPlaylists" description="暂无歌单" :image-size="100" />
        <div v-else class="playlist-grid">
          <div
            v-for="p in playlists"
            :key="p.id"
            class="playlist-card"
            @click="importPlaylist(p)"
          >
            <el-image :src="p.cover ? coverUrl(p.cover) : ''" fit="cover" class="playlist-cover">
              <template #error>
                <div class="cover-fallback">🎵</div>
              </template>
            </el-image>
            <div class="playlist-name" :title="p.name">{{ p.name }}</div>
            <div class="playlist-count">{{ p.trackCount }} 首 · 点击导入</div>
          </div>
        </div>
      </div>
    </template>
  </div>
</template>

<style scoped>
.my-view {
  height: 100%;
  overflow-y: auto;
  padding: 12px;
}
.login-card {
  max-width: 420px;
  margin: 40px auto;
  text-align: center;
  padding: 32px 24px;
  border: 1px dashed var(--el-border-color);
  border-radius: 12px;
  background: var(--el-bg-color);
}
.login-title {
  font-size: 18px;
  font-weight: 700;
}
.login-desc {
  margin: 8px 0 20px;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.cookie-desc {
  text-align: left;
  font-size: 12px;
  line-height: 1.8;
  color: var(--el-text-color-secondary);
  margin-bottom: 12px;
}
.cookie-btn {
  width: 100%;
  margin-top: 12px;
}
.user-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px;
  border-radius: 10px;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
}
.user-meta {
  flex: 1;
  min-width: 0;
}
.user-name {
  font-size: 16px;
  font-weight: 700;
}
.user-sub {
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
.section-title {
  margin: 20px 4px 12px;
  font-size: 15px;
  font-weight: 700;
}
.playlist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}
.playlist-card {
  cursor: pointer;
  border-radius: 8px;
  overflow: hidden;
  background: var(--el-bg-color);
  border: 1px solid var(--el-border-color-light);
  transition: transform 0.15s, box-shadow 0.15s;
}
.playlist-card:hover {
  transform: translateY(-2px);
  box-shadow: var(--el-box-shadow-light);
}
.playlist-cover {
  width: 100%;
  aspect-ratio: 1;
  display: block;
}
.cover-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 40px;
  background: var(--el-fill-color-light);
}
.playlist-name {
  padding: 8px 10px 0;
  font-size: 13px;
  font-weight: 600;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.playlist-count {
  padding: 2px 10px 10px;
  font-size: 12px;
  color: var(--el-text-color-secondary);
}
</style>
