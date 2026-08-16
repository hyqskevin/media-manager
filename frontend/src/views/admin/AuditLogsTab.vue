<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import { formatUtcAsShanghai } from '@/utils/datetime'

interface AuditLogOut {
  id: number
  actor_user_id: number | null
  actor_username: string
  action: string
  resource_type: string | null
  resource_id: number | null
  target_label: string | null
  method: string
  path: string
  status_code: number
  client_ip: string
  user_agent: string | null
  extra: string | null
  created_at: string
}

const items = ref<AuditLogOut[]>([])
const total = ref(0)
const page = ref(1)
const size = ref(20)
const filter = ref({
  actor_username: '',
  action: [] as string[],
  date_from: '',
  date_to: '',
})
const actions = [
  'login_success', 'login_failed', 'user_created', 'user_updated',
  'user_deleted', 'group_created', 'group_permission_changed', 'user_group_changed',
  'audit_logs_deleted',
]

// 多选
const selection = ref<AuditLogOut[]>([])

async function load() {
  const r = await api.listAuditLogs({
    actor_username: filter.value.actor_username || undefined,
    action: filter.value.action.length ? filter.value.action : undefined,
    date_from: filter.value.date_from || undefined,
    date_to: filter.value.date_to || undefined,
    page: page.value,
    size: size.value,
  })
  // 后端 list_audit_logs 返回 {total, items} 裸对象（response_model=AuditLogPage），从 axios 响应里取 .data
  const data = (r as any).data as { total: number; items: AuditLogOut[] }
  items.value = data.items
  total.value = data.total
  selection.value = []
}

function onSelectionChange(rows: AuditLogOut[]) {
  selection.value = rows
}

async function batchDelete() {
  if (selection.value.length === 0) return
  try {
    await ElMessageBox.confirm(
      `确认删除选中的 ${selection.value.length} 条操作日志？此操作不可撤销。`,
      '批量删除确认',
      { type: 'warning' },
    )
  } catch {
    return
  }
  const ids = selection.value.map((row) => row.id)
  const r = await api.deleteAuditLogs(ids)
  const deletedCount = ((r as any).data?.deleted_count ?? (r as any).deleted_count) as number
  ElMessage.success(`已删除 ${deletedCount} 条`)
  await load()
}

onMounted(load)
</script>

<template>
  <div>
    <div class="filter" style="margin-bottom: 12px; display: flex; align-items: center;">
      <ElInput v-model="filter.actor_username" placeholder="操作者用户名" clearable style="width: 200px;" @change="load" />
      <ElSelect v-model="filter.action" multiple collapse-tags collapse-tags-tooltip placeholder="动作" style="width: 240px; margin-left: 8px;" @change="load">
        <ElOption v-for="a in actions" :key="a" :value="a" :label="a" />
      </ElSelect>
      <ElButton style="margin-left: 8px;" @click="load">查询</ElButton>
      <ElButton
        type="danger"
        :disabled="selection.length === 0"
        style="margin-left: auto;"
        @click="batchDelete"
      >
        批量删除 ({{ selection.length }})
      </ElButton>
    </div>
    <ElTable
      :data="items"
      stripe
      @selection-change="onSelectionChange"
    >
      <ElTableColumn type="selection" width="48" />
      <ElTableColumn label="时间" width="180">
        <template #default="scope">
          {{ formatUtcAsShanghai(scope.row.created_at) }}
        </template>
      </ElTableColumn>
      <ElTableColumn prop="actor_username" label="操作者" width="140" />
      <ElTableColumn prop="action" label="动作" width="200" />
      <ElTableColumn prop="target_label" label="目标" />
      <ElTableColumn prop="method" label="方法" width="80" />
      <ElTableColumn prop="path" label="路径" />
      <ElTableColumn prop="status_code" label="状态" width="80" />
      <ElTableColumn prop="client_ip" label="来源 IP" width="140" />
    </ElTable>
    <ElPagination
      :total="total"
      :page-size="size"
      :current-page="page"
      :page-sizes="[20, 50, 100, 200]"
      layout="total, sizes, prev, pager, next, jumper"
      style="margin-top: 12px;"
      @current-change="(p: number) => { page = p; load() }"
      @size-change="(s: number) => { size = s; page = 1; load() }"
    />
  </div>
</template>