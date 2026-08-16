<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { api } from '@/api/client'

interface PermissionOut {
  id: number
  code: string
  description: string | null
  is_builtin: boolean
}

const permissions = ref<PermissionOut[]>([])

onMounted(async () => {
  // 后端 list_permissions 返回裸数组，从 axios 响应里取 .data
  const r = await api.listPermissions()
  permissions.value = (r as any).data as PermissionOut[]
})
</script>

<template>
  <ElTable :data="permissions" stripe>
    <ElTableColumn prop="code" label="权限码" width="220" />
    <ElTableColumn prop="description" label="说明" />
    <ElTableColumn label="内置" width="100">
      <template #default="{ row }">
        <ElTag v-if="row.is_builtin" type="info" size="small">内置</ElTag>
        <span v-else>—</span>
      </template>
    </ElTableColumn>
  </ElTable>
</template>