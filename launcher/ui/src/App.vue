<script setup lang="ts">
import { onMounted, onUnmounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import ServiceStatus from './components/ServiceStatus.vue'
import OpenCLIPanel from './components/OpenCLIPanel.vue'
import OcrPanel from './components/OcrPanel.vue'
import LogViewer from './components/LogViewer.vue'
import {
  fetchStatus,
  restartService,
  stopAll,
  testOpencli,
  getOpencliDownloadUrl,
  getOcrStatus,
  installOcr,
  getOcrInstallProgress,
  testOcr,
  getLogsTail,
  initBaseUrlFromLocation,
  getBaseUrl,
  type StatusResponse,
  type OpencliTestResult,
  type OcrStatus,
  type OcrInstallProgress,
  type OcrTestResult,
} from './api/client'

const APP_VERSION = '0.1.0'
const STATUS_POLL_MS = 3000
const LOGS_POLL_MS = 5000
const PROGRESS_POLL_MS = 2000

const status = ref<StatusResponse>({
  api: { state: 'stopped', pid: null },
  worker: { state: 'stopped', pid: null },
  beat: { state: 'stopped', pid: null },
})
const opencliResult = ref<OpencliTestResult | null>(null)
const opencliLoading = ref(false)
const ocrStatus = ref<OcrStatus>({ status: 'not_installed', version: '' })
const ocrProgress = ref<OcrInstallProgress>({ active: false, percent: 0, message: '' })
const ocrTestResult = ref<OcrTestResult | null>(null)
const ocrInstalling = ref(false)
const ocrTesting = ref(false)
const logLines = ref<string[]>([])

let statusTimer: ReturnType<typeof setInterval> | null = null
let logsTimer: ReturnType<typeof setInterval> | null = null
let progressTimer: ReturnType<typeof setInterval> | null = null

async function refreshStatus() {
  try {
    status.value = await fetchStatus()
  } catch (e) {
    // 静默失败,下次轮询重试
  }
}

async function refreshLogs() {
  try {
    const resp = await getLogsTail(50)
    logLines.value = resp.lines
  } catch (e) {
    // 静默失败
  }
}

async function refreshOcrStatus() {
  try {
    ocrStatus.value = await getOcrStatus()
  } catch (e) {
    // 静默失败
  }
}

async function refreshOcrProgress() {
  try {
    ocrProgress.value = await getOcrInstallProgress()
    if (!ocrProgress.value.active && ocrInstalling.value) {
      ocrInstalling.value = false
      if (progressTimer) {
        clearInterval(progressTimer)
        progressTimer = null
      }
      await refreshOcrStatus()
      if (ocrProgress.value.ok) {
        ElMessage.success('OCR 安装完成')
      } else {
        ElMessage.error(`OCR 安装失败: ${ocrProgress.value.message}`)
      }
    }
  } catch (e) {
    // 静默失败
  }
}

async function handleRestart(name: string) {
  try {
    await restartService(name)
    ElMessage.success(`${name} 已重启`)
    await refreshStatus()
  } catch (e) {
    ElMessage.error(`重启 ${name} 失败`)
  }
}

async function handleStopAll() {
  try {
    await stopAll()
    ElMessage.success('已停止全部服务')
    await refreshStatus()
  } catch (e) {
    ElMessage.error('停止服务失败')
  }
}

async function handleOpencliTest() {
  opencliLoading.value = true
  try {
    opencliResult.value = await testOpencli()
  } catch (e) {
    opencliResult.value = { ok: false, version: '', reason: 'api_error', message: '测试失败' }
  } finally {
    opencliLoading.value = false
  }
}

async function handleOpencliDownload() {
  try {
    const { url } = await getOpencliDownloadUrl()
    window.open(url, '_blank')
  } catch (e) {
    ElMessage.error('获取下载链接失败')
  }
}

async function handleOcrInstall() {
  ocrInstalling.value = true
  ocrTestResult.value = null
  try {
    await installOcr()
    progressTimer = setInterval(refreshOcrProgress, PROGRESS_POLL_MS)
  } catch (e) {
    ocrInstalling.value = false
    ElMessage.error('启动安装失败')
  }
}

async function handleOcrTest() {
  ocrTesting.value = true
  try {
    ocrTestResult.value = await testOcr()
  } catch (e) {
    ocrTestResult.value = { ok: false, reason: 'api_error', message: '测试失败' }
  } finally {
    ocrTesting.value = false
  }
}

async function handleOpenWeb() {
  // 优先读 URL query (?apiPort=xxx),
  // 否则调状态服务 /api-port 拿真实端口(避开 hardcode 8000)
  const queryPort = new URLSearchParams(window.location.search).get('apiPort')
  let port = queryPort
  if (!port) {
    try {
      const resp = await fetch(`${getBaseUrl()}/api-port`)
      const data = await resp.json()
      port = String(data.port || 8000)
    } catch (e) {
      port = '8000'
    }
  }
  const url = `http://127.0.0.1:${port}`
  // 用 PyWebView 注入的 API 在系统默认浏览器打开,
  // 避免 PyWebView 窗口跳转后无法返回
  const pywebview = (window as unknown as { pywebview?: { api?: { open_url: (u: string) => void } } }).pywebview
  if (pywebview?.api?.open_url) {
    pywebview.api.open_url(url)
  } else {
    window.open(url, '_blank')
  }
}

function handleExit() {
  // PyWebView 注入的 API:window.pywebview.api.exit()
  const pywebview = (window as unknown as { pywebview?: { api?: { exit: () => void } } }).pywebview
  if (pywebview?.api?.exit) {
    pywebview.api.exit()
  } else {
    // 无 PyWebView 时(开发模式)只停止服务
    handleStopAll()
  }
}

function handleOpenLogDir() {
  // 通过 PyWebView 注入的 API 在 Finder/Explorer 打开日志目录
  const pywebview = (window as unknown as { pywebview?: { api?: { open_dir: (p: string) => Promise<string> } } }).pywebview
  if (pywebview?.api?.open_dir) {
    pywebview.api.open_dir('data/logs').catch((err: unknown) => {
      ElMessage.error(`打开日志目录失败: ${err}`)
    })
  } else {
    ElMessage.warning('该功能仅在桌面启动器中可用')
  }
}

onMounted(async () => {
  initBaseUrlFromLocation()
  await Promise.all([refreshStatus(), refreshLogs(), refreshOcrStatus()])
  statusTimer = setInterval(refreshStatus, STATUS_POLL_MS)
  logsTimer = setInterval(refreshLogs, LOGS_POLL_MS)
})

onUnmounted(() => {
  if (statusTimer) clearInterval(statusTimer)
  if (logsTimer) clearInterval(logsTimer)
  if (progressTimer) clearInterval(progressTimer)
})
</script>

<template>
  <div class="launcher-app" data-test="launcher-app">
    <header class="top-app-bar" data-test="top-app-bar">
      <h1 class="app-title" data-test="app-title">小红书活动信息抓取系统</h1>
      <span class="app-version">v{{ APP_VERSION }}</span>
    </header>

    <main class="main-content">
      <ServiceStatus
        :status="status"
        @restart="handleRestart"
        @stop-all="handleStopAll"
      />

      <OpenCLIPanel
        :result="opencliResult"
        :loading="opencliLoading"
        @test="handleOpencliTest"
        @download="handleOpencliDownload"
      />

      <OcrPanel
        :status="ocrStatus"
        :progress="ocrProgress"
        :test-result="ocrTestResult"
        :installing="ocrInstalling"
        :testing="ocrTesting"
        @install="handleOcrInstall"
        @test="handleOcrTest"
      />

      <LogViewer :lines="logLines" @refresh="refreshLogs" @open-dir="handleOpenLogDir" />
    </main>

    <footer class="bottom-action-bar" data-test="bottom-action-bar">
      <el-button type="primary" data-test="open-web-btn" @click="handleOpenWeb">
        打开网页
      </el-button>
      <el-button data-test="app-stop-all-btn" @click="handleStopAll">
        停止全部
      </el-button>
      <el-button text data-test="exit-btn" @click="handleExit">
        退出
      </el-button>
    </footer>
  </div>
</template>

<style scoped>
.launcher-app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--md-sys-color-background);
  color: var(--md-sys-color-on-surface);
}

.top-app-bar {
  background: var(--md-sys-color-surface);
  box-shadow: var(--md-sys-elevation-2);
  padding: var(--md-sys-spacing-4) var(--md-sys-spacing-6);
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.app-title {
  font: var(--md-sys-typescale-headline-medium);
  margin: 0;
}

.app-version {
  font: var(--md-sys-typescale-label-medium);
  color: var(--md-sys-color-on-surface-variant);
}

.main-content {
  flex: 1;
  padding: var(--md-sys-spacing-4) var(--md-sys-spacing-6);
  overflow-y: auto;
}

.bottom-action-bar {
  background: var(--md-sys-color-surface-container-high);
  padding: var(--md-sys-spacing-3) var(--md-sys-spacing-6);
  display: flex;
  justify-content: flex-end;
  gap: var(--md-sys-spacing-2);
}
</style>
