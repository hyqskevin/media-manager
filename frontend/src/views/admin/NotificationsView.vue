<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Check, Finished, Refresh } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface Notification {
  id: number
  severity: string
  title: string
  body: string
  related_entity_type: string
  related_entity_id: number | null
  created_at: string
  read_at: string | null
  is_read: boolean
}

const SEVERITY_META: Record<string, string> = {
  critical: 'danger',
  warning: 'warning',
  info: 'info',
  success: 'success',
  error: 'danger',
}

const items = ref<Notification[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const unreadCount = ref(0)
const activeTab = ref('all')

const tabs = [
  { name: 'all', label: '全部' },
  { name: 'unread', label: '未读' },
  { name: 'critical', label: '严重' },
  { name: 'warning', label: '警告' },
]

async function loadUnread() {
  const res = await api.notificationsUnreadCount()
  unreadCount.value = res.data as number
}

async function load() {
  loading.value = true
  try {
    const params: Record<string, unknown> = { page: page.value, page_size: pageSize.value }
    if (activeTab.value === 'unread') params.is_read = false
    if (activeTab.value === 'critical') params.severity = 'critical'
    if (activeTab.value === 'warning') params.severity = 'warning'
    const res = await api.notifications(params)
    const data = res.data as { total: number; items: Notification[] }
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function switchTab() {
  page.value = 1
  load()
}

async function markRead(n: Notification) {
  await api.markNotificationRead(n.id)
  n.is_read = true
  loadUnread()
  load()
}

async function readAll() {
  await api.readAllNotifications()
  ElMessage.success('已全部标记为已读')
  loadUnread()
  load()
}

onMounted(() => {
  loadUnread()
  load()
})
</script>

<template>
  <div class="notifications-page">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">通知中心</h2>
      <div class="header-actions">
        <ElBadge :value="unreadCount" :hidden="unreadCount === 0">
          <ElButton type="primary" plain :icon="Finished" @click="readAll" data-test="read-all">全部已读</ElButton>
        </ElBadge>
        <ElButton :icon="Refresh" circle @click="load" />
      </div>
    </div>

    <ElTabs v-model="activeTab" @tab-change="switchTab">
      <ElTabPane v-for="t in tabs" :key="t.name" :label="t.label" :name="t.name" />
    </ElTabs>

    <ElTable :data="items" v-loading="loading">
      <ElTableColumn label="级别" width="100">
        <template #default="{ row }">
          <ElTag :type="SEVERITY_META[row.severity] || 'info'" effect="plain">{{ row.severity }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn label="标题" min-width="180">
        <template #default="{ row }">
          <span :class="{ 'is-read': row.is_read }">{{ row.title }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="body" label="内容" min-width="240" />
      <ElTableColumn prop="created_at" label="时间" width="170" />
      <ElTableColumn label="操作" width="130" fixed="right">
        <template #default="{ row }">
          <ElButton v-if="!row.is_read" size="small" :icon="Check" @click="markRead(row)" data-test="mark-read">标记已读</ElButton>
          <span v-else class="read-text">已读</span>
        </template>
      </ElTableColumn>
    </ElTable>

    <div class="pager">
      <ElPagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next"
        @current-change="load"
      />
    </div>
  </div>
</template>

<style scoped>
.notifications-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.header-actions { display: flex; align-items: center; gap: var(--md-sys-spacing-3); }
.pager { display: flex; justify-content: flex-end; margin-top: var(--md-sys-spacing-4); }
.is-read { color: var(--md-sys-color-on-surface-variant); }
.read-text { color: var(--md-sys-color-on-surface-variant); }
</style>