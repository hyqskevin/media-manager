<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Download, Refresh, Search } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface NurtureTask {
  id: number
  celery_task_id: string
  account_id: number
  platform: string
  actions: string[]
  duration_minutes: number
  status: string
  current_action: string | null
  progress_pct: number
  started_at: string | null
  finished_at: string | null
  error: string | null
  items_collected: number
  created_at: string
}
interface NurtureLog {
  id: number
  task_id: number
  action: string
  status: string
  sequence: number
  started_at: string | null
  finished_at: string | null
  result: object
  error: string | null
}

const STATUS_META: Record<string, { text: string; cls: string }> = {
  completed: { text: '已完成', cls: 'md-badge--success' },
  running: { text: '执行中', cls: 'md-badge--primary' },
  failed: { text: '失败', cls: 'md-badge--error' },
  cancelled: { text: '已取消', cls: 'md-badge--info' },
  pending: { text: '排队中', cls: 'md-badge--warning' },
  skipped: { text: '已跳过', cls: 'md-badge--info' },
}

const items = ref<NurtureTask[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const filters = reactive({ status: '', platform: '', account_id: '', q: '' })
const logDrawerVisible = ref(false)
const logTask = ref<NurtureTask | null>(null)
const logs = ref<NurtureLog[]>([])

async function load() {
  loading.value = true
  try {
    const params = {
      status: filters.status || undefined,
      platform: filters.platform || undefined,
      account_id: filters.account_id || undefined,
      q: filters.q || undefined,
      page: page.value,
      page_size: pageSize.value,
    }
    const res = await api.nurtureHistory(params)
    const data = res.data as { total: number; page: number; page_size: number; items: NurtureTask[] }
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function search() {
  page.value = 1
  load()
}

async function rerun(t: NurtureTask) {
  await api.rerunNurtureTask(t.id)
  ElMessage.success('已重新入队')
  load()
}

async function remove(t: NurtureTask) {
  await ElMessageBox.confirm(`确认删除历史任务 #${t.id}？`, '删除确认', { type: 'warning' })
  await api.deleteNurtureTask(t.id)
  ElMessage.success('已删除')
  load()
}

async function openLogs(t: NurtureTask) {
  logTask.value = t
  logDrawerVisible.value = true
  const res = await api.nurtureTaskLogs(t.id)
  logs.value = (res.data as { items: NurtureLog[] })?.items ?? (res.data as NurtureLog[])
}

async function exportCsv() {
  const params = {
    status: filters.status || undefined,
    platform: filters.platform || undefined,
    account_id: filters.account_id || undefined,
    q: filters.q || undefined,
  }
  const res = await api.exportNurtureHistory(params)
  const blob = res.data as Blob
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `nurture-history-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<template>
  <div class="history-page">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">养号历史</h2>
      <div class="header-actions">
        <ElButton :icon="Download" @click="exportCsv" data-test="export">导出 CSV</ElButton>
        <ElButton type="primary" plain :icon="Refresh" @click="load">刷新</ElButton>
      </div>
    </div>

    <div class="filter-bar">
      <ElInput v-model="filters.q" placeholder="搜索" clearable style="width: 200px" data-test="q" />
      <ElSelect v-model="filters.status" placeholder="状态" clearable style="width: 140px">
        <ElOption label="已完成" value="completed" />
        <ElOption label="执行中" value="running" />
        <ElOption label="失败" value="failed" />
        <ElOption label="已取消" value="cancelled" />
        <ElOption label="排队中" value="pending" />
        <ElOption label="已跳过" value="skipped" />
      </ElSelect>
      <ElSelect v-model="filters.platform" placeholder="平台" clearable style="width: 140px">
        <ElOption label="小红书" value="xhs" />
        <ElOption label="微博" value="weibo" />
        <ElOption label="抖音" value="douyin" />
      </ElSelect>
      <ElSelect v-model="filters.account_id" placeholder="账号ID" clearable filterable style="width: 140px">
        <ElOption v-for="t in items" :key="t.account_id" :label="`#${t.account_id}`" :value="String(t.account_id)" />
      </ElSelect>
      <ElButton :icon="Search" @click="search" data-test="search">查询</ElButton>
    </div>

    <ElTable :data="items" v-loading="loading">
      <ElTableColumn prop="id" label="ID" width="70" />
      <ElTableColumn prop="platform" label="平台" width="100" />
      <ElTableColumn prop="account_id" label="账号" width="90" />
      <ElTableColumn label="动作" min-width="160">
        <template #default="{ row }">{{ (row.actions || []).join('、') }}</template>
      </ElTableColumn>
      <ElTableColumn prop="duration_minutes" label="时长(分)" width="90" />
      <ElTableColumn label="状态" width="110">
        <template #default="{ row }">
          <span :class="['md-badge', STATUS_META[row.status]?.cls || 'md-badge--info']">
            {{ (STATUS_META[row.status]?.text) || row.status }}
          </span>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="items_collected" label="已采集" width="90" />
      <ElTableColumn prop="created_at" label="创建时间" min-width="170" />
      <ElTableColumn label="操作" width="220" fixed="right">
        <template #default="{ row }">
          <ElButton size="small" plain @click="openLogs(row)" data-test="logs">日志</ElButton>
          <ElButton size="small" type="primary" plain @click="rerun(row)" data-test="rerun">重跑</ElButton>
          <ElButton size="small" type="danger" plain @click="remove(row)" data-test="delete-row">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <div class="pager">
      <ElPagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @current-change="load"
        @size-change="search"
      />
    </div>

    <ElDrawer v-model="logDrawerVisible" :title="`任务 #${logTask?.id} 日志`" size="480px">
      <ElTimeline v-if="logs.length">
        <ElTimelineItem v-for="l in logs" :key="l.id" :type="l.status === 'failed' ? 'danger' : 'primary'">
          <div>
            <b>{{ l.action }}</b>
            <span v-if="l.status">（{{ l.status }}）</span>
            <p v-if="l.error">{{ l.error }}</p>
          </div>
        </ElTimelineItem>
      </ElTimeline>
      <ElEmpty v-else description="暂无日志" />
    </ElDrawer>
  </div>
</template>

<style scoped>
.history-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.header-actions { display: flex; gap: var(--md-sys-spacing-3); }
.filter-bar {
  display: flex;
  gap: var(--md-sys-spacing-3);
  margin-bottom: var(--md-sys-spacing-4);
}
.pager { display: flex; justify-content: flex-end; margin-top: var(--md-sys-spacing-4); }
</style>