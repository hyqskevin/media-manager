<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh } from '@element-plus/icons-vue'
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

const items = ref<NurtureTask[]>([])
const loading = ref(false)
const drawerVisible = ref(false)
const detail = ref<NurtureTask | null>(null)
const logs = ref<NurtureLog[]>([])
let timer: ReturnType<typeof setInterval> | null = null

async function load() {
  loading.value = true
  try {
    const res = await api.nurtureRunning()
    items.value = (res.data as { items: NurtureTask[] }).items ?? []
  } finally {
    loading.value = false
  }
}

async function cancelTask(t: NurtureTask) {
  await ElMessageBox.confirm(`确认取消任务 #${t.id}？`, '取消确认', { type: 'warning' })
  await api.cancelNurtureTask(t.id)
  ElMessage.success('已取消')
  load()
}

async function openDetail(t: NurtureTask) {
  detail.value = t
  drawerVisible.value = true
  const [taskRes, logRes] = await Promise.all([api.nurtureTask(t.id), api.nurtureTaskLogs(t.id)])
  detail.value = taskRes.data as NurtureTask
  logs.value = (logRes.data as { items: NurtureLog[] })?.items ?? (logRes.data as NurtureLog[])
}

onMounted(() => {
  load()
  timer = setInterval(load, 5000)
})
onBeforeUnmount(() => {
  if (timer) clearInterval(timer)
})
</script>

<template>
  <div class="running-page">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">执行中</h2>
      <ElButton type="primary" plain :icon="Refresh" @click="load">刷新</ElButton>
    </div>

    <div v-loading="loading">
      <ElTable :data="items" empty-text="暂无执行中的养号任务">
        <ElTableColumn prop="id" label="ID" width="70" />
        <ElTableColumn prop="platform" label="平台" width="110" />
        <ElTableColumn prop="account_id" label="账号ID" width="100" />
        <ElTableColumn label="当前动作" width="140">
          <template #default="{ row }">{{ row.current_action || '—' }}</template>
        </ElTableColumn>
        <ElTableColumn label="进度" min-width="180">
          <template #default="{ row }">
            <ElProgress :percentage="row.progress_pct" :stroke-width="10" />
          </template>
        </ElTableColumn>
        <ElTableColumn prop="items_collected" label="已采集" width="90" />
        <ElTableColumn label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <ElButton size="small" plain @click="openDetail(row)" data-test="detail">详情</ElButton>
            <ElButton size="small" type="danger" plain @click="cancelTask(row)" data-test="cancel">取消</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </div>

    <ElDrawer v-model="drawerVisible" title="任务详情" size="480px">
      <ElDescriptions v-if="detail" :column="1" border>
        <ElDescriptionsItem label="任务ID">#{{ detail.id }}</ElDescriptionsItem>
        <ElDescriptionsItem label="平台">{{ detail.platform }}</ElDescriptionsItem>
        <ElDescriptionsItem label="账号ID">{{ detail.account_id }}</ElDescriptionsItem>
        <ElDescriptionsItem label="动作">{{ (detail.actions || []).join('、') }}</ElDescriptionsItem>
        <ElDescriptionsItem label="进度">{{ detail.progress_pct }}%</ElDescriptionsItem>
        <ElDescriptionsItem label="已采集">{{ detail.items_collected }}</ElDescriptionsItem>
        <ElDescriptionsItem label="错误">{{ detail.error || '—' }}</ElDescriptionsItem>
      </ElDescriptions>
      <h4 class="md-typescale-title-medium">动作日志</h4>
      <ElTimeline v-if="logs.length">
        <ElTimelineItem v-for="l in logs" :key="l.id" :type="l.status === 'failed' ? 'danger' : 'primary'">
          <div class="log-item">
            <b>{{ l.action }}</b>
            <span v-if="l.status">（{{ l.status }}）</span>
            <p v-if="l.error" class="log-error">{{ l.error }}</p>
          </div>
        </ElTimelineItem>
      </ElTimeline>
      <ElEmpty v-else description="暂无动作日志" />
    </ElDrawer>
  </div>
</template>

<style scoped>
.running-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.log-item p { margin: var(--md-sys-spacing-1) 0 0; }
.log-error { color: var(--md-sys-color-error); }
</style>