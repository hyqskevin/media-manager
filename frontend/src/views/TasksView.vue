<script setup lang="ts">
import { Delete, Refresh, View } from '@element-plus/icons-vue'
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import { formatUtcAsShanghai } from '@/utils/datetime'

const rows = ref<any[]>([])
const selected = ref<any[]>([])
const logs = ref<any[]>([])
const drawer = ref(false)
const batchDeleting = ref(false)
const restartingId = ref<number | null>(null)
const resumableStatuses = ['FAILED', 'STOPPED', 'STOP_REQUESTED', 'PAUSED']
const statusLabels: Record<string, string> = { PENDING: '等待中', RUNNING: '抓取中', STOP_REQUESTED: '正在停止', STOPPED: '已停止', DOWNLOADING: '下载中', COMPLETED: '已完成', COMPLETED_WITH_ERRORS: '完成但有错误', FAILED: '失败', PAUSED: '等待登录' }
const stageLabels: Record<string, string> = { SEARCHING: '搜索笔记', DOWNLOADING: '下载笔记', OCR: 'OCR 识别', EXTRACTING: '提取活动', ARCHIVING: '归档结果' }
// 进度按"已处理笔记"算（已下载 + 失败 + 跳过），反映真实推进度；
// 旧公式只看 extracted，导致 OCR 阶段进度条长期卡在 ~2%
function progress(row: any) {
  return row.total_notes
    ? Math.round(
        ((row.downloaded_notes || 0) + (row.failed_notes || 0) + (row.skipped_notes || 0)) * 100 / row.total_notes,
      )
    : 0
}

async function load() { rows.value = (await api.tasks()).data.data.items }
async function show(id: number) { logs.value = (await api.logs(id)).data.data; drawer.value = true }

async function restart(row: any) {
  restartingId.value = row.id
  try {
    await api.restartTask(row.id)
    ElMessage.success(row.status === 'PAUSED' ? '登录状态正常，任务已继续抓取' : '任务已继续抓取')
    await load()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message === 'AUTH_REQUIRED' ? '尚未检测到小红书登录状态，请登录后重试' : error.response?.data?.message || error.response?.data?.detail || '任务续跑失败')
  } finally {
    restartingId.value = null
  }
}

async function batchDelete() {
  if (!selected.value.length) return
  await ElMessageBox.confirm(
    `确认批量删除选中的 ${selected.value.length} 条任务？已抓取的推文会保留，仅清理任务历史。`,
    '批量删除确认',
    { type: 'warning' },
  )
  batchDeleting.value = true
  try {
    const ids = selected.value.map((row: any) => row.id)
    const response = await api.batchDeleteTasks(ids)
    const deletedCount = response.data.data.deleted_count
    ElMessage.success(`已删除 ${deletedCount} 条任务`)
    selected.value = []
    await load()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '批量删除失败')
  } finally {
    batchDeleting.value = false
  }
}

onMounted(load)
</script>

<template>
  <ElCard shadow="never">
    <template #header><div class="toolbar"><strong>抓取日志</strong><ElButton type="danger" :icon="Delete" :disabled="!selected.length" :loading="batchDeleting" @click="batchDelete">批量删除 ({{ selected.length }})</ElButton></div></template>
    <ElAlert title="此页面仅用于监控抓取任务；请在仪表盘发起新的抓取" type="info" show-icon :closable="false" />
    <ElTable :data="rows" @selection-change="(rows: any[]) => (selected = rows)">
      <ElTableColumn type="selection" width="48" />
      <ElTableColumn prop="id" label="任务 ID" width="100" />
      <ElTableColumn label="状态" width="130"><template #default="scope"><ElTag>{{ statusLabels[scope.row.status] || scope.row.status }}</ElTag></template></ElTableColumn>
      <ElTableColumn prop="current_stage" label="当前阶段" width="120"><template #default="scope">{{ stageLabels[scope.row.current_stage] || '-' }}</template></ElTableColumn>
      <ElTableColumn prop="total_notes" label="发现" width="80" />
      <ElTableColumn prop="downloaded_notes" label="已下载" width="90" />
      <ElTableColumn prop="ocr_notes" label="OCR 完成" width="100" />
      <ElTableColumn prop="extracted_notes" label="提取完成" width="100" />
      <ElTableColumn prop="failed_notes" label="失败" width="90" />
      <ElTableColumn prop="skipped_notes" label="已跳过" width="90" />
      <ElTableColumn label="进度" width="160"><template #default="scope"><ElProgress :percentage="progress(scope.row)" /></template></ElTableColumn>
      <ElTableColumn label="创建时间" min-width="180"><template #default="scope">{{ formatUtcAsShanghai(scope.row.created_at) }}</template></ElTableColumn>
      <ElTableColumn prop="error_message" label="错误" min-width="220" show-overflow-tooltip />
      <ElTableColumn label="操作" min-width="190" class-name="action-column"><template #default="scope"><ElButton v-if="resumableStatuses.includes(scope.row.status)" text :icon="Refresh" :loading="restartingId === scope.row.id" @click="restart(scope.row)">{{ scope.row.status === 'PAUSED' ? '登录并继续' : '继续抓取' }}</ElButton><ElButton text :icon="View" @click="show(scope.row.id)">日志</ElButton></template></ElTableColumn>
    </ElTable>
  </ElCard>
  <ElDrawer v-model="drawer" title="任务日志"><ElTimeline><ElTimelineItem v-for="item in logs" :key="item.id" :timestamp="formatUtcAsShanghai(item.created_at)">{{ item.level }} - {{ item.message }}</ElTimelineItem></ElTimeline></ElDrawer>
</template>

<style scoped>
.toolbar { display: flex; align-items: center; justify-content: space-between; gap: 12px; }
</style>
