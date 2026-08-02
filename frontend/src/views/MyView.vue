<script setup lang="ts">
import { ElMessage, ElMessageBox } from 'element-plus'
import QRCode from 'qrcode'
import { onMounted, onUnmounted, ref } from 'vue'
import { checkQr, coverUrl, getAuthStatus, getMyPlaylists, getPlaylist, getQrKey, postLogout } from '../api'
import { usePlaylistStore } from '../stores/playlist'
import type { NetEaseProfile, UserPlaylist } from '../types'

const emit = defineEmits<{ imported: [] }>()

const playlist = usePlaylistStore()

const loggedIn = ref(false)
const profile = ref<NetEaseProfile | null>(null)
const playlists = ref<UserPlaylist[]>([])
const loadingPlaylists = ref(false)

// 扫码登录状态
const qrPhase = ref<'idle' | 'loading' | 'scanning' | 'expired'>('idle')
const qrTip = ref('')
const qrKeyVal = ref('')
const qrCanvas = ref<HTMLCanvasElement | null>(null)
let pollTimer: number | undefined

const QR_PAYLOAD = (key: string) => `https://music.163.com/login?codekey=${key}`

onMounted(refreshStatus)
onUnmounted(stopPolling)

function stopPolling() {
  if (pollTimer) {
    clearTimeout(pollTimer)
    pollTimer = undefined
  }
}

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

async function startLogin() {
  qrPhase.value = 'loading'
  qrTip.value = '正在获取二维码...'
  try {
    const { key } = await getQrKey()
    qrKeyVal.value = key
    if (qrCanvas.value) {
      await QRCode.toCanvas(qrCanvas.value, QR_PAYLOAD(key), { width: 200, margin: 1 })
    }
    qrPhase.value = 'scanning'
    qrTip.value = '请使用网易云音乐 App 扫码'
    pollQr(key)
  } catch {
    qrPhase.value = 'idle'
    qrTip.value = ''
    ElMessage.error('获取登录二维码失败')
  }
}

function pollQr(key: string) {
  stopPolling()
  pollTimer = window.setTimeout(async () => {
    try {
      const r = await checkQr(key)
      if (r.code === 803 && r.profile) {
        // 登录成功
        qrPhase.value = 'idle'
        qrTip.value = ''
        qrKeyVal.value = ''
        loggedIn.value = true
        profile.value = r.profile
        ElMessage.success(`欢迎，${r.profile.nickname}`)
        loadPlaylists()
        return
      }
      if (r.code === 802) {
        qrTip.value = '已扫码，请在手机上确认登录'
      } else if (r.code === 800) {
        qrPhase.value = 'expired'
        qrTip.value = '二维码已过期，请重新获取'
        return
      } else if (r.code === 801) {
        qrTip.value = '请使用网易云音乐 App 扫码'
      } else if (r.code === 803) {
        // 后端在 803 但资料拉取失败时会转成 -1，这里兜底防止无限轮询
        qrPhase.value = 'expired'
        qrTip.value = r.message || '登录状态异常，请刷新二维码重试'
        return
      } else if (r.message) {
        // 风控/错误码（如 401/400）：停止轮询，提示重试
        qrPhase.value = 'expired'
        qrTip.value = `${r.message}，请刷新二维码重试`
        return
      } else {
        qrPhase.value = 'expired'
        qrTip.value = '登录异常，请刷新二维码重试'
        return
      }
      if (qrPhase.value === 'scanning') pollQr(key)
    } catch {
      qrTip.value = '轮询失败，正在重试...'
      if (qrPhase.value === 'scanning') pollQr(key)
    }
  }, 2000)
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
    <!-- 未登录：扫码登录 -->
    <div v-if="!loggedIn" class="login-card">
      <div class="login-title">🎵 登录网易云账号</div>
      <div class="login-desc">登录后可导入「我的歌单」与私有歌单</div>

      <div v-if="qrPhase === 'idle'" class="login-actions">
        <el-button type="primary" size="large" @click="startLogin">扫码登录</el-button>
      </div>

      <div v-else class="qr-area">
        <canvas v-show="qrPhase === 'scanning'" ref="qrCanvas" class="qr-canvas" />
        <div v-if="qrPhase === 'expired'" class="qr-expired">😵 二维码已过期</div>
        <div v-if="qrPhase === 'loading'" class="qr-loading">⏳ 获取中...</div>
        <div class="qr-tip">{{ qrTip }}</div>
        <div class="qr-actions">
          <el-button size="small" @click="startLogin">刷新二维码</el-button>
          <el-button size="small" @click="qrPhase = 'idle'; qrTip = ''; stopPolling()">取消</el-button>
        </div>
      </div>
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
  max-width: 380px;
  margin: 48px auto;
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
.qr-canvas {
  border: 1px solid var(--el-border-color-light);
  border-radius: 8px;
}
.qr-loading,
.qr-expired {
  font-size: 24px;
  padding: 40px 0;
}
.qr-tip {
  margin: 12px 0;
  font-size: 13px;
  color: var(--el-text-color-secondary);
}
.qr-actions {
  display: flex;
  gap: 8px;
  justify-content: center;
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
