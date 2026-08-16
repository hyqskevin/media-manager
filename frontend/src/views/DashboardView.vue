<script setup lang="ts">
import { Connection, Link, RefreshRight, TrendCharts, VideoPlay } from '@element-plus/icons-vue'
import { computed, onMounted, onUnmounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getHealth } from '@/api/health'
import { api } from '@/api/client'
import { formatUtcAsShanghai } from '@/utils/datetime'
import CrawlTrendChart from '@/components/CrawlTrendChart.vue'
import CrawlSuccessPie from '@/components/CrawlSuccessPie.vue'

const status = ref<'loading' | 'ok' | 'error'>('loading')
const database = ref('SQLite')
const cities = ref<any[]>([])
const bloggers = ref<any[]>([])
const xhsAccounts = ref<any[]>([])
const submitting = ref(false)
const restarting = ref(false)
const openingLogin = ref(false)
const stopping = ref(false)
const lastTask = ref<any>(null)
const resumableTask = ref<any>(null)
const summary = ref<any>({ weekly_notes_count: 0, weekly_activities_count: 0, pending_duplicates: 0, recent_logs: [] })
const analytics = ref<any>({ recent_tasks: [], status_counts: {}, schedules: [] })
const diagnostics = ref<any>({
  opencli: { ok: null, bin: 'opencli', resolved: null, reason: null, version: null },
  xhs_login: { logged_in: null, username: null, user_id: null, reason: null },
  xhs_pool: { mode: 'unknown', version: null, version_tuple: null, daemon_running: null, extension_connected: null, profiles: [], daemon_port: null, cdp_endpoint: '', cdp_reachable: null, sessions: [], reason: null },
  checked_at: null,
})
const diagLoading = ref<Record<string, boolean>>({ opencli: false, xhs_login: false, xhs_pool: false })
const reasonText = (key: string | null | undefined) => {
  switch (key) {
    case 'auth_required': return '小红书未登录，请在 Chrome 完成扫码后重试'
    case 'timeout': return '检测超时：可能未登录或浏览器等待扫码'
    case 'other': return '检测失败，详见服务器日志'
    default: return key || ''
  }
}
const xhsLoginTag = computed(() => {
  const v = diagnostics.value.xhs_login
  if (v.logged_in === true) return { type: 'success' as const, text: `已登录: ${v.username || v.user_id || '未知账号'}` }
  if (v.logged_in === false) {
    if (v.reason === 'timeout') return { type: 'warning' as const, text: '登录检测超时' }
    return { type: 'danger' as const, text: '未登录' }
  }
  return { type: 'info' as const, text: '未检测' }
})
const xhsPoolTag = computed(() => {
  const v = diagnostics.value.xhs_pool
  if (v.mode === 'daemon') {
    if (v.daemon_running && v.extension_connected) return { type: 'success' as const, text: `Daemon 已连接 · ${(v.profiles || []).length} profiles` }
    return { type: 'danger' as const, text: 'Daemon 未就绪' }
  }
  if (v.mode === 'cdp') {
    if (v.cdp_reachable === true) return { type: 'success' as const, text: `CDP 可达 · ${(v.sessions || []).length} sessions` }
    if (v.cdp_reachable === false) return { type: 'danger' as const, text: 'CDP 不可达' }
  }
  if (v.mode === 'unknown') return { type: 'danger' as const, text: '未就绪' }
  return { type: 'info' as const, text: '未检测' }
})
const scheduleStatusMeta: Record<string, { type: string; label: string }> = {
  COMPLETED: { type: 'success', label: '成功' },
  COMPLETED_WITH_ERRORS: { type: 'warning', label: '部分成功' },
  FAILED: { type: 'danger', label: '失败' },
  RUNNING: { type: 'primary', label: '运行中' },
  PENDING: { type: 'info', label: '等待中' },
  PAUSED: { type: 'warning', label: '已暂停' },
  STOPPED: { type: 'info', label: '已停止' },
}
const weekdayLabels: Record<number, string> = { 1: '一', 2: '二', 3: '三', 4: '四', 5: '五', 6: '六', 7: '日' }
const pad2 = (n: number) => String(n).padStart(2, '0')
const scheduleStatusOf = (task: any) => scheduleStatusMeta[task?.status] || { type: 'info', label: task?.status || '' }
let pollLastTaskTimer: ReturnType<typeof setInterval> | undefined
let pollStatsTimer: ReturnType<typeof setInterval> | undefined
const form = reactive({
  city: '',
  keyword_source: 'custom' as 'custom' | 'groups',
  keyword_group_ids: [] as number[],
  custom_keywords: [] as string[],
  blogger_source: 'list' as 'list' | 'groups',
  blogger_ids: [] as number[],
  blogger_group_ids: [] as number[],
  recent_filter: '一周内',
  xhs_account_id: null as number | null,
})
const newCustomKeyword = ref('')
const recentFilters = ['不限', '一天内', '一周内', '半年内']
const cityKeywordGroups = ref<any[]>([])
const allEnabledKeywordGroups = ref<any[]>([])
const allEnabledBloggerGroups = ref<any[]>([])
const selectedCity = computed(() => cities.value.find((city) => city.code === form.city))
const cityBloggers = computed(() => {
  if (!form.city) return bloggers.value.filter((b: any) => b.enabled)
  return bloggers.value.filter((b: any) => (b.city_codes || []).includes(form.city) && b.enabled)
})
const incompleteBloggers = computed(() => form.blogger_ids.filter((id: number) => {
  const b = bloggers.value.find((x: any) => x.id === id)
  return b && !b.profile_url
}))
const statusLabels: Record<string, string> = { PENDING: '等待中', RUNNING: '抓取中', STOP_REQUESTED: '正在停止', STOPPED: '已停止', COMPLETED: '已完成', COMPLETED_WITH_ERRORS: '完成但有错误', FAILED: '失败', PAUSED: '等待登录' }
const stageLabels: Record<string, string> = { SEARCHING: '搜索笔记', DOWNLOADING: '下载笔记', OCR: 'OCR 识别', EXTRACTING: '提取活动', ARCHIVING: '归档结果' }
const errorVisibleStatuses = ['RUNNING', 'STOP_REQUESTED', 'FAILED', 'PAUSED', 'STOPPED']
const shouldShowLastTaskError = computed(() =>
  !!lastTask.value?.error_message && errorVisibleStatuses.includes(lastTask.value.status)
)

watch(() => form.city, async () => {
  form.keyword_group_ids = []
  form.blogger_ids = []
  form.blogger_group_ids = []
  form.recent_filter = selectedCity.value?.recent_filter || '一周内'
  if (form.city) {
    try {
      const kgResp = await api.keywordGroups({ city_code: form.city })
      cityKeywordGroups.value = (kgResp.data.data.items || []).filter((g: any) => g.enabled)
    } catch {
      cityKeywordGroups.value = []
    }
  } else {
    // 不限城市：保留全部已启用关键词组供选择
    cityKeywordGroups.value = [...allEnabledKeywordGroups.value]
  }
})

function addCustomKeyword() {
  const w = newCustomKeyword.value.trim()
  if (!w) return
  if (!form.custom_keywords.includes(w)) form.custom_keywords.push(w)
  newCustomKeyword.value = ''
}

function removeCustomKeyword(word: string) {
  form.custom_keywords = form.custom_keywords.filter((w) => w !== word)
}

async function initialize() {
  try {
    const [cityResponse, bloggerResponse] = await Promise.all([api.settings('cities'), api.settings('bloggers')])
    cities.value = (cityResponse.data.data || []).filter((city: any) => city.enabled)
    bloggers.value = bloggerResponse.data.data || []
    // 城市默认空 = 不限城市
  } catch {
    cities.value = []
    bloggers.value = []
  }
  try {
    const [kgResp, bgResp] = await Promise.all([api.keywordGroups(), api.bloggerGroups()])
    allEnabledKeywordGroups.value = (kgResp.data.data?.items || []).filter((g: any) => g.enabled)
    allEnabledBloggerGroups.value = (bgResp.data.data?.items || []).filter((g: any) => g.enabled)
    // 城市默认空=不限城市，关键词组下拉显示全部启用组
    cityKeywordGroups.value = [...allEnabledKeywordGroups.value]
  } catch {
    allEnabledKeywordGroups.value = []
    allEnabledBloggerGroups.value = []
    cityKeywordGroups.value = []
  }
  try {
    const accountResponse = await api.xhsAccounts()
    xhsAccounts.value = (accountResponse.data.data || []).filter((account: any) => account.enabled)
  } catch {
    xhsAccounts.value = []
  }
  try {
    const result = await getHealth()
    database.value = result.database === 'sqlite' ? 'SQLite' : result.database
    status.value = result.status === 'ok' ? 'ok' : 'error'
  } catch {
    status.value = 'error'
  }
  loadDiagnosticsSnapshot()
  await Promise.all([loadLatestTask(), pollAnalytics()])
  pollLastTaskTimer = setInterval(pollLastTask, 3000)
  pollStatsTimer = setInterval(async () => {
    await pollSummaryStats()
    await pollAnalytics()
  }, 60_000)
}

async function loadDiagnosticsSnapshot() {
  try {
    const res = await api.diagnosticsSnapshot()
    diagnostics.value = { ...diagnostics.value, ...res.data.data }
  } catch (error: any) {
    // 单点失败不应影响仪表盘其他卡片
    diagnostics.value.checked_at = new Date().toISOString()
  }
}

async function probe(section: 'opencli' | 'xhs_login' | 'xhs_pool') {
  diagLoading.value[section] = true
  try {
    const fn = section === 'opencli' ? api.diagnosticsOpencli : section === 'xhs_login' ? api.diagnosticsXhsLogin : api.diagnosticsXhsPool
    const res = await fn()
    diagnostics.value = { ...diagnostics.value, [section]: res.data.data, checked_at: new Date().toISOString() }
  } catch (error: any) {
    const reason = error.response?.data?.message || error.response?.data?.detail || '检测失败'
    diagnostics.value = { ...diagnostics.value, [section]: { ...diagnostics.value[section], ok: section === 'opencli' ? false : diagnostics.value[section].ok, logged_in: section === 'xhs_login' ? false : diagnostics.value[section].logged_in, mode: section === 'xhs_pool' ? 'unknown' : diagnostics.value[section].mode, cdp_reachable: section === 'xhs_pool' ? false : diagnostics.value[section].cdp_reachable, reason }, checked_at: new Date().toISOString() }
    ElMessage.error(reason)
  } finally {
    diagLoading.value[section] = false
  }
}

async function loadLatestTask() {
  try {
    const data = (await api.dashboard()).data.data
    lastTask.value = data.last_task
    resumableTask.value = data.resumable_task || null
    summary.value = { weekly_notes_count: 0, weekly_activities_count: 0, pending_duplicates: 0, recent_logs: [], ...data }
  } catch { /* health card reports service errors */ }
}

/** 仅刷新最近抓取任务进度（高频，3 秒一次）。*/
async function pollLastTask() {
  try {
    const data = (await api.dashboard()).data.data
    lastTask.value = data.last_task
    resumableTask.value = data.resumable_task || null
  } catch { /* health card reports service errors */ }
}

/** 仅刷新 last_task 之外的 summary 字段（顶部 3 个卡片 + 最近日志）。*/
async function pollSummaryStats() {
  try {
    const data = (await api.dashboard()).data.data
    summary.value = { weekly_notes_count: 0, weekly_activities_count: 0, pending_duplicates: 0, recent_logs: [], ...data }
  } catch { /* health card reports service errors */ }
}

/** 刷新 analytics（趋势图/成功率饼/定时任务表）。*/
async function pollAnalytics() {
  try {
    analytics.value = (await api.dashboardAnalytics()).data.data
  } catch { /* 图表数据加载失败不阻塞主流程 */ }
}

async function start() {
  // 校验：自定义关键词 / 关键词组 / 博主列表 / 博主组 至少选其一
  const hasKeyword = form.keyword_source === 'custom'
    ? form.custom_keywords.length > 0
    : form.keyword_group_ids.length > 0
  const hasBlogger = form.blogger_source === 'list'
    ? form.blogger_ids.length > 0
    : form.blogger_group_ids.length > 0
  if (!hasKeyword && !hasBlogger) {
    ElMessage.warning('请至少输入关键词或选择一个关键词组/博主组/博主')
    return
  }
  if (incompleteBloggers.value.length) {
    ElMessage.warning(`所选博主信息不完整（${incompleteBloggers.value.length} 个），请到配置中心点"补充博主信息"后再发起抓取`)
    return
  }
  submitting.value = true
  try {
    const payload: Record<string, any> = {
      type: 'mixed',
      city: form.city,  // 空字符串 = 不限城市
      recent_filter: form.recent_filter,
    }
    if (form.keyword_source === 'custom') {
      payload.keywords = [...form.custom_keywords]
    } else {
      payload.keyword_group_ids = [...form.keyword_group_ids]
    }
    if (form.blogger_source === 'list') {
      payload.blogger_ids = [...form.blogger_ids]
    } else {
      payload.blogger_group_ids = [...form.blogger_group_ids]
    }
    if (form.xhs_account_id != null) payload.xhs_account_id = form.xhs_account_id
    await api.createTask(payload)
    ElMessage.success('抓取任务已提交，可到任务日志查看进度')
    await loadLatestTask()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || error.response?.data?.detail || '提交失败')
  } finally {
    submitting.value = false
  }
}

async function restart(taskOverride?: any) {
  const target = taskOverride || lastTask.value
  if (!target) return
  restarting.value = true
  try {
    await api.restartTask(target.id)
    ElMessage.success(target.status === 'PAUSED' ? '登录状态正常，任务已继续抓取' : '任务已继续抓取')
    await loadLatestTask()
  } catch (error:any) {
    ElMessage.error(error.response?.data?.message === 'AUTH_REQUIRED' ? '尚未检测到小红书登录状态，请登录后重试' : error.response?.data?.message || error.response?.data?.detail || '任务续跑失败')
  } finally { restarting.value = false }
}

async function openLogin() {
  openingLogin.value = true
  try {
    await api.openXhsLogin()
    ElMessage.success('已打开 Chrome 小红书登录页')
  } catch (error:any) {
    ElMessage.error(error.response?.data?.message || '无法打开 Chrome 小红书登录页')
  } finally { openingLogin.value = false }
}

async function stop() {
  if (!lastTask.value) return
  await ElMessageBox.confirm('当前笔记完成后停止，已处理数据会保留。确认停止抓取？', '安全停止', { type: 'warning' })
  stopping.value = true
  try {
    await api.stopTask(lastTask.value.id)
    ElMessage.success('已请求安全停止')
    await loadLatestTask()
  } catch (error:any) {
    ElMessage.error(error.response?.data?.detail || '停止任务失败')
  } finally { stopping.value = false }
}

async function finish(taskOverride?: any) {
  const target = taskOverride || lastTask.value
  if (!target) return
  await ElMessageBox.confirm(`此任务（#${target.id}）已失败。结束抓取将强制清理残留状态并关闭 Browser 标签，已抓取数据会保留。确认结束？`, '结束抓取', { type: 'warning' })
  stopping.value = true
  try {
    await api.stopTask(target.id)
    ElMessage.success('抓取已结束')
    await loadLatestTask()
  } catch (error:any) {
    ElMessage.error(error.response?.data?.detail || '结束抓取失败')
  } finally { stopping.value = false }
}

onMounted(initialize)
onUnmounted(() => {
  if (pollLastTaskTimer) clearInterval(pollLastTaskTimer)
  if (pollStatsTimer) clearInterval(pollStatsTimer)
})
</script>

<template>
  <div class="dashboard">
    <div class="page-intro"><div><p class="eyebrow">PHASE ONE</p><h2>小红书本地活动信息抓取系统</h2><p>从已配置的城市、关键词组和博主中选择本次抓取范围。</p></div></div>

    <div class="stats-row">
      <ElCard shadow="never" class="stat-card"><div class="stat-card__content"><span>本周抓取笔记</span><strong>{{ summary.weekly_notes_count }}</strong></div></ElCard>
      <ElCard shadow="never" class="stat-card"><div class="stat-card__content"><span>本周生成活动</span><strong>{{ summary.weekly_activities_count }}</strong></div></ElCard>
      <ElCard shadow="never" class="stat-card"><div class="stat-card__content"><span>待审核去重</span><strong>{{ summary.pending_duplicates }}</strong></div></ElCard>
    </div>

    <ElCard shadow="never" class="system-status-card">
      <template #header><div class="card-title"><ElIcon><Connection /></ElIcon><strong>系统状态</strong></div></template>
      <div class="system-status-grid">
        <div class="system-item">
          <span class="system-label">后端服务</span>
          <ElTag :type="status === 'ok' ? 'success' : status === 'loading' ? 'info' : 'danger'">{{ status === 'ok' ? '运行正常' : status === 'loading' ? '检测中' : '不可用' }}</ElTag>
          <span class="system-detail">{{ database }}</span>
        </div>
        <div class="system-item">
          <span class="system-label">opencli</span>
          <ElTag :type="diagnostics.opencli.ok === true ? 'success' : diagnostics.opencli.ok === false ? 'danger' : 'info'">{{ diagnostics.opencli.ok === true ? `已就绪${diagnostics.opencli.version ? ' v' + diagnostics.opencli.version : ''}` : diagnostics.opencli.ok === false ? '缺失' : '未检测' }}</ElTag>
          <ElButton size="small" :loading="diagLoading.opencli" @click="probe('opencli')">检测</ElButton>
          <p v-if="diagnostics.opencli.ok === false && diagnostics.opencli.reason" class="system-reason">{{ diagnostics.opencli.reason }}</p>
        </div>
        <div class="system-item">
          <span class="system-label">小红书登录</span>
          <ElTag :type="xhsLoginTag.type">{{ xhsLoginTag.text }}</ElTag>
          <ElButton size="small" :loading="diagLoading.xhs_login" @click="probe('xhs_login')">检测</ElButton>
          <p v-if="diagnostics.xhs_login.logged_in === false && diagnostics.xhs_login.reason" class="system-reason">{{ reasonText(diagnostics.xhs_login.reason) }}</p>
        </div>
        <div class="system-item">
          <span class="system-label">浏览器连接</span>
          <ElTag :type="xhsPoolTag.type">{{ xhsPoolTag.text }}</ElTag>
          <ElButton size="small" :loading="diagLoading.xhs_pool" @click="probe('xhs_pool')">检测</ElButton>
          <p v-if="diagnostics.xhs_pool.reason" class="system-reason">{{ diagnostics.xhs_pool.reason }}</p>
        </div>
      </div>
    </ElCard>

    <ElCard shadow="never" class="crawl-card">
      <template #header><div class="card-title"><ElIcon><VideoPlay /></ElIcon><strong>发起抓取</strong></div></template>
      <ElForm label-position="top">
        <div class="crawl-grid">
          <!-- Row 1: 城市 + 时间范围 -->
          <ElFormItem label="城市" class="grid-row-1">
            <ElSelect v-model="form.city" clearable placeholder="不限城市">
              <ElOption v-for="city in cities" :key="city.code" :label="city.name" :value="city.code" />
            </ElSelect>
          </ElFormItem>
          <ElFormItem label="时间范围" class="grid-row-1">
            <ElSelect v-model="form.recent_filter">
              <ElOption v-for="item in recentFilters" :key="item" :label="item" :value="item" />
            </ElSelect>
          </ElFormItem>

          <!-- Row 2: 关键词模式 + 关键词/关键词组 -->
          <ElFormItem label="关键词模式" class="grid-row-2">
            <ElRadioGroup v-model="form.keyword_source">
              <ElRadioButton value="custom">自定义关键词</ElRadioButton>
              <ElRadioButton value="groups">关键词组</ElRadioButton>
            </ElRadioGroup>
          </ElFormItem>
          <ElFormItem v-if="form.keyword_source === 'custom'" label="关键词" class="grid-row-2">
            <div class="custom-keywords-row">
              <ElInput
                v-model="newCustomKeyword"
                placeholder="回车添加关键词"
                style="width: 220px"
                @keyup.enter="addCustomKeyword"
              />
              <div v-if="form.custom_keywords.length" class="custom-keywords-tags">
                <ElTag v-for="word in form.custom_keywords" :key="word" closable @close="removeCustomKeyword(word)">{{ word }}</ElTag>
              </div>
            </div>
          </ElFormItem>
          <ElFormItem v-else label="关键词组" class="grid-row-2">
            <ElSelect v-model="form.keyword_group_ids" multiple collapse-tags collapse-tags-tooltip placeholder="选择一个或多个关键词组">
              <ElOption v-for="group in cityKeywordGroups" :key="group.id" :label="group.name" :value="group.id" />
            </ElSelect>
          </ElFormItem>

          <!-- Row 3: 博主模式 + 博主/博主组 -->
          <ElFormItem label="博主模式" class="grid-row-3">
            <ElRadioGroup v-model="form.blogger_source">
              <ElRadioButton value="list">博主列表</ElRadioButton>
              <ElRadioButton value="groups">博主组</ElRadioButton>
            </ElRadioGroup>
          </ElFormItem>
          <ElFormItem v-if="form.blogger_source === 'list'" label="博主" class="grid-row-3">
            <ElSelect v-model="form.blogger_ids" multiple collapse-tags collapse-tags-tooltip placeholder="选择一个或多个博主">
              <ElOption v-for="blogger in cityBloggers" :key="blogger.id" :value="blogger.id">
                <span style="float:left">{{ blogger.username }}</span>
                <span v-if="!blogger.profile_url" style="float:right;color:var(--el-color-warning);font-size:12px">待补充</span>
              </ElOption>
            </ElSelect>
          </ElFormItem>
          <ElFormItem v-else label="博主组" class="grid-row-3">
            <ElSelect v-model="form.blogger_group_ids" multiple collapse-tags collapse-tags-tooltip placeholder="选择一个或多个博主组">
              <ElOption v-for="group in allEnabledBloggerGroups" :key="group.id" :label="group.name" :value="group.id" />
            </ElSelect>
          </ElFormItem>

          <!-- Row 4: 操作账号（占满整行） -->
          <ElFormItem label="操作账号" class="grid-row-4">
            <ElSelect v-model="form.xhs_account_id" clearable placeholder="不选则自动按优先级" class="account-select">
              <ElOption v-for="account in xhsAccounts" :key="account.id" :label="account.name" :value="account.id" />
            </ElSelect>
          </ElFormItem>
        </div>
        <div class="crawl-actions"><ElButton type="primary" :icon="VideoPlay" :loading="submitting" @click="start">开始抓取</ElButton><span>任务启动前会检查 Chrome 小红书登录状态</span></div>
      </ElForm>
    </ElCard>

    <ElCard v-if="lastTask" shadow="never" class="progress-card">
      <template #header><div class="card-title"><strong>最近抓取任务 #{{ lastTask.id }}</strong><ElTag>{{ statusLabels[lastTask.status] || lastTask.status }}</ElTag></div></template>
      <div class="progress-summary">
        <div><span>当前阶段</span><strong>{{ stageLabels[lastTask.current_stage] || '未执行' }}</strong></div>
        <div><span>当前笔记</span><strong>{{ lastTask.current_note || '-' }}</strong></div>
        <div><span>发现</span><strong>{{ lastTask.total_notes }}</strong></div>
        <div><span>已下载</span><strong>{{ lastTask.downloaded_notes }}</strong></div>
        <div><span>OCR 完成</span><strong>{{ lastTask.ocr_notes }}</strong></div>
        <div><span>提取完成</span><strong>{{ lastTask.extracted_notes }}</strong></div>
        <div><span>失败</span><strong>{{ lastTask.failed_notes }}</strong></div>
        <div><span>已跳过</span><strong>{{ lastTask.skipped_notes || 0 }}</strong></div>
        <div><span>活动已跳过</span><strong>{{ lastTask.skipped_activities || 0 }}</strong></div>
      </div>
      <ElProgress :percentage="lastTask.progress_percent || 0" :indeterminate="lastTask.progress_percent == null && ['PENDING','RUNNING'].includes(lastTask.status)" />
      <ElAlert v-if="shouldShowLastTaskError" :title="lastTask.error_message" type="error" :closable="false" />
      <!-- 继续抓取：后端允许 FAILED/STOPPED/STOP_REQUESTED/PAUSED；STOP_REQUESTED 是中间态，按钮 disabled 提示稍候 -->
      <ElButton
        v-if="['FAILED','STOPPED','STOP_REQUESTED','PAUSED'].includes(lastTask.status)"
        type="primary"
        :icon="RefreshRight"
        :loading="restarting"
        :disabled="lastTask.status === 'STOP_REQUESTED'"
        @click="restart()"
      >
        {{ lastTask.status === 'STOP_REQUESTED' ? '正在停止…' : lastTask.status === 'PAUSED' ? '检测登录并继续' : '继续抓取' }}
      </ElButton>
      <ElButton v-if="['FAILED','PAUSED'].includes(lastTask.status)" type="danger" :loading="stopping" @click="finish()">结束抓取</ElButton>
      <ElButton v-if="lastTask.status === 'PAUSED'" :icon="Link" :loading="openingLogin" @click="openLogin">打开小红书登录</ElButton>
      <ElButton v-if="['PENDING','RUNNING','STOP_REQUESTED'].includes(lastTask.status)" type="danger" :loading="stopping || lastTask.status === 'STOP_REQUESTED'" :disabled="lastTask.status === 'STOP_REQUESTED'" @click="stop">停止抓取</ElButton>
    </ElCard>

    <!-- 可继续抓取的任务：当 lastTask 本身正在运行时，单独展示最近一个 FAILED/STOPPED/PAUSED 任务，方便用户继续 -->
    <ElCard v-if="resumableTask && resumableTask.id !== lastTask?.id" shadow="never" class="progress-card resumable-card">
      <template #header>
        <div class="card-title">
          <strong>可继续抓取的任务 #{{ resumableTask.id }}</strong>
          <ElTag :type="resumableTask.status === 'FAILED' ? 'danger' : resumableTask.status === 'PAUSED' ? 'warning' : 'info'">{{ statusLabels[resumableTask.status] || resumableTask.status }}</ElTag>
          <span class="hint">（最近一次中止的任务，task #{{ resumableTask.id }}）</span>
        </div>
      </template>
      <div class="progress-summary">
        <div><span>当前阶段</span><strong>{{ stageLabels[resumableTask.current_stage] || '未执行' }}</strong></div>
        <div><span>已下载</span><strong>{{ resumableTask.downloaded_notes }}</strong></div>
        <div><span>OCR 完成</span><strong>{{ resumableTask.ocr_notes }}</strong></div>
        <div><span>提取完成</span><strong>{{ resumableTask.extracted_notes }}</strong></div>
        <div><span>失败</span><strong>{{ resumableTask.failed_notes }}</strong></div>
        <div><span>已跳过</span><strong>{{ resumableTask.skipped_notes || 0 }}</strong></div>
      </div>
      <ElProgress :percentage="resumableTask.progress_percent || 0" />
      <ElAlert v-if="resumableTask.error_message" :title="resumableTask.error_message" type="error" :closable="false" />
      <ElButton
        type="primary"
        :icon="RefreshRight"
        :loading="restarting"
        :disabled="resumableTask.status === 'STOP_REQUESTED'"
        @click="restart(resumableTask)"
      >
        {{ resumableTask.status === 'STOP_REQUESTED' ? '正在停止…' : resumableTask.status === 'PAUSED' ? '检测登录并继续' : '继续抓取' }}
      </ElButton>
      <ElButton v-if="['FAILED','PAUSED'].includes(resumableTask.status)" type="danger" :loading="stopping" @click="finish(resumableTask)">结束抓取</ElButton>
      <ElButton v-if="resumableTask.status === 'PAUSED'" :icon="Link" :loading="openingLogin" @click="openLogin">打开小红书登录</ElButton>
    </ElCard>

    <ElCard shadow="never" class="schedule-status-card">
      <template #header><div class="card-title"><ElIcon><TrendCharts /></ElIcon><strong>定时任务状态</strong></div></template>
      <ElTable v-if="analytics.schedules.length" :data="analytics.schedules">
        <ElTableColumn prop="name" label="名称" min-width="160" />
        <ElTableColumn label="周期" width="140">
          <template #default="scope">每周{{ weekdayLabels[scope.row.day_of_week] || scope.row.day_of_week }} {{ pad2(scope.row.hour) }}:{{ pad2(scope.row.minute) }}</template>
        </ElTableColumn>
        <ElTableColumn label="状态" width="100">
          <template #default="scope"><ElTag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? '启用' : '停用' }}</ElTag></template>
        </ElTableColumn>
        <ElTableColumn label="最近抓取" min-width="120">
          <template #default="scope">
            <ElTag v-if="scope.row.last_task" :type="scheduleStatusOf(scope.row.last_task).type as any">{{ scheduleStatusOf(scope.row.last_task).label }}</ElTag>
            <span v-else>未执行</span>
          </template>
        </ElTableColumn>
      </ElTable>
      <ElEmpty v-else description="暂无定时任务，请到「定时任务」页面创建" :image-size="60" />
    </ElCard>

    <div class="charts-row">
      <ElCard shadow="never" class="chart-card">
        <template #header><div class="card-title"><strong>抓取趋势（最近 20 次）</strong></div></template>
        <CrawlTrendChart :tasks="analytics.recent_tasks" />
      </ElCard>
      <ElCard shadow="never" class="chart-card">
        <template #header><div class="card-title"><strong>抓取成功率（最近 50 次）</strong></div></template>
        <CrawlSuccessPie :counts="analytics.status_counts" />
      </ElCard>
    </div>

    <ElCard shadow="never" class="logs-card">
      <template #header><div class="card-title"><strong>最近任务日志</strong></div></template>
      <div v-if="summary.recent_logs.length" class="logs-list">
        <div v-for="log in summary.recent_logs" :key="log.id" class="log-line" @click="$router.push('/tasks')">
          <ElTag size="small" :type="log.level === 'ERROR' ? 'danger' : log.level === 'WARNING' ? 'warning' : 'info'">{{ log.level }}</ElTag>
          <span class="log-message">#{{ log.task_id }} {{ log.message }}</span>
          <span class="log-time">{{ formatUtcAsShanghai(log.created_at) }}</span>
        </div>
      </div>
      <ElEmpty v-else description="暂无任务日志" :image-size="60" />
    </ElCard>
  </div>
</template>

<style scoped>
.stats-row { display: grid; grid-template-columns: repeat(3, 1fr); gap: 20px; margin-bottom: 20px; }
@media (max-width: 800px) { .stats-row { grid-template-columns: 1fr; } }
.stat-card__content { display: flex; flex-direction: column; gap: 6px; }
.stat-card__content span { color: var(--el-text-color-secondary); }
.stat-card__content strong { font-size: 28px; }
.logs-card { margin-bottom: 20px; }
.logs-list { display: flex; flex-direction: column; gap: 8px; }
.log-line { display: flex; align-items: center; gap: 10px; cursor: pointer; }
.log-line:hover { background: var(--el-fill-color-light); }
.log-message { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.log-time { color: var(--el-text-color-secondary); font-size: 12px; }
.crawl-card { margin-bottom: 20px; }
.progress-card { margin-bottom: 20px; }
.schedule-status-card { margin-bottom: 20px; }
.charts-row { display: grid; grid-template-columns: 3fr 2fr; gap: 20px; margin-bottom: 20px; }
@media (max-width: 1000px) { .charts-row { grid-template-columns: 1fr; } }
.progress-card .card-title { justify-content: space-between; }
.progress-summary { display: grid; grid-template-columns: repeat(4,minmax(120px,1fr)); gap: 14px; margin-bottom: 16px; }
.progress-summary div { display: flex; flex-direction: column; gap: 4px; }
.progress-summary span { color: var(--el-text-color-secondary); }
.progress-card .el-alert,.progress-card .el-button { margin-top: 14px; }
.card-title { display: flex; align-items: center; gap: 8px; }
.crawl-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 0 20px; }
.crawl-grid :deep(.el-select) { width: 100%; }
.grid-row-1, .grid-row-2, .grid-row-3 { grid-column: span 1; }
.grid-row-4 { grid-column: 1 / -1; }
/* 操作账号下拉框固定宽度，不要撑满整行（.el-select.account-select 组合类特异性高于 .crawl-grid :deep(.el-select) 的 100%） */
.crawl-grid :deep(.el-select.account-select) { width: 280px; max-width: 100%; }
.crawl-actions { display: flex; align-items: center; gap: 16px; color: var(--el-text-color-secondary); }
@media (max-width: 800px) {
  .crawl-grid { grid-template-columns: 1fr; }
  .grid-row-1, .grid-row-2, .grid-row-3, .grid-row-4 { grid-column: 1; }
}
.system-status-card { margin-bottom: 20px; }
.system-status-grid { display: grid; grid-template-columns: repeat(4, minmax(180px, 1fr)); gap: 16px; }
@media (max-width: 1000px) { .system-status-grid { grid-template-columns: repeat(2, 1fr); } }
@media (max-width: 600px) { .system-status-grid { grid-template-columns: 1fr; } }
.system-item { display: flex; flex-direction: column; gap: 8px; padding: 12px; border: 1px solid var(--el-border-color-light); border-radius: 6px; }
.system-label { color: var(--el-text-color-secondary); font-size: 13px; }
.system-item .el-button { align-self: flex-start; }
.system-reason { color: var(--el-color-danger); font-size: 12px; margin: 4px 0 0; line-height: 1.4; word-break: break-word; }
.system-detail { color: var(--el-text-color-secondary); font-size: 12px; }
</style>
