<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { Download, Refresh, Search } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface AuditLog {
  id: number
  created_at: string
  operator: string
  action: string
  entity_type: string
  entity_id: number | null
  changes: object
  ip: string
  user_agent: string
}

const items = ref<AuditLog[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const filters = reactive({ operator: '', action: '' })
const drawerVisible = ref(false)
const detail = ref<AuditLog | null>(null)

async function load() {
  loading.value = true
  try {
    const params = {
      operator: filters.operator || undefined,
      action: filters.action || undefined,
      page: page.value,
      page_size: pageSize.value,
    }
    const res = await api.auditLogs(params)
    const data = res.data as { total: number; page: number; page_size: number; items: AuditLog[] }
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

async function openDetail(row: AuditLog) {
  const res = await api.auditLog(row.id)
  detail.value = res.data as AuditLog
  drawerVisible.value = true
}

function formatChanges(changes: object): string {
  try {
    return JSON.stringify(changes, null, 2)
  } catch {
    return String(changes)
  }
}

async function exportCsv() {
  const params = {
    operator: filters.operator || undefined,
    action: filters.action || undefined,
  }
  const res = await api.exportAuditLogs(params)
  const blob = res.data as Blob
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `audit-logs-${new Date().toISOString().slice(0, 10)}.csv`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(load)
</script>

<template>
  <div class="audit-page">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">操作日志</h2>
      <div class="header-actions">
        <ElButton :icon="Download" @click="exportCsv" data-test="export">导出 CSV</ElButton>
        <ElButton type="primary" plain :icon="Refresh" @click="load">刷新</ElButton>
      </div>
    </div>

    <div class="filter-bar">
      <ElInput v-model="filters.operator" placeholder="操作者" clearable style="width: 180px" data-test="operator" />
      <ElInput v-model="filters.action" placeholder="动作" clearable style="width: 180px" data-test="action" />
      <ElButton :icon="Search" @click="search" data-test="search">查询</ElButton>
    </div>

    <ElTable :data="items" v-loading="loading">
      <ElTableColumn prop="id" label="ID" width="70" />
      <ElTableColumn prop="created_at" label="时间" width="170" />
      <ElTableColumn prop="operator" label="操作者" width="120" />
      <ElTableColumn prop="action" label="动作" width="120" />
      <ElTableColumn prop="entity_type" label="实体" width="120" />
      <ElTableColumn prop="entity_id" label="实体ID" width="90" />
      <ElTableColumn prop="ip" label="IP" width="130" />
      <ElTableColumn label="操作" width="100" fixed="right">
        <template #default="{ row }">
          <ElButton size="small" plain @click="openDetail(row)" data-test="detail">详情</ElButton>
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

    <ElDrawer v-model="drawerVisible" title="变更详情" size="560px">
      <template v-if="detail">
        <ElDescriptions :column="1" border class="detail-desc">
          <ElDescriptionsItem label="ID">#{{ detail.id }}</ElDescriptionsItem>
          <ElDescriptionsItem label="操作者">{{ detail.operator }}</ElDescriptionsItem>
          <ElDescriptionsItem label="动作">{{ detail.action }}</ElDescriptionsItem>
          <ElDescriptionsItem label="实体">{{ detail.entity_type }} #{{ detail.entity_id }}</ElDescriptionsItem>
          <ElDescriptionsItem label="IP">{{ detail.ip }}</ElDescriptionsItem>
          <ElDescriptionsItem label="User-Agent">{{ detail.user_agent }}</ElDescriptionsItem>
        </ElDescriptions>
        <h4 class="md-typescale-title-medium">变更字段</h4>
        <pre class="changes">{{ formatChanges(detail.changes) }}</pre>
      </template>
    </ElDrawer>
  </div>
</template>

<style scoped>
.audit-page { padding: var(--md-sys-spacing-6); }
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
.detail-desc { margin-bottom: var(--md-sys-spacing-4); }
.changes {
  background: var(--md-sys-color-surface-variant);
  padding: var(--md-sys-spacing-4);
  border-radius: var(--md-sys-spacing-2);
  overflow: auto;
  white-space: pre-wrap;
}
</style>