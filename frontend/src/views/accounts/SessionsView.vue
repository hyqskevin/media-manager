<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'

interface Account {
  id: number
  name: string
  platform: string
  login_status: string
  last_login_check_at: string | null
}

const LOGIN_META: Record<string, { text: string; cls: string }> = {
  logged_in: { text: '已登录', cls: 'md-badge--success' },
  logged_out: { text: '未登录', cls: 'md-badge--error' },
  expired: { text: '已过期', cls: 'md-badge--warning' },
  unknown: { text: '未知', cls: 'md-badge--info' },
}

const accounts = ref<Account[]>([])
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await api.platformAccounts()
    accounts.value = res.data as Account[]
  } finally {
    loading.value = false
  }
}
async function check(a: Account) {
  try {
    const r = await api.checkPlatformAccountLogin(a.id)
    ElMessage.success((r.data as { logged_in: boolean }).logged_in ? '登录有效' : '未登录')
    load()
  } catch {
    ElMessage.error('检查失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="sessions-page">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">登录态管理</h2>
      <ElButton type="primary" plain @click="load">刷新</ElButton>
    </div>

    <ElTable :data="accounts" v-loading="loading" data-test="sessions-table">
      <ElTableColumn prop="id" label="ID" width="70" />
      <ElTableColumn prop="name" label="名称" min-width="140" />
      <ElTableColumn prop="platform" label="平台" width="120" />
      <ElTableColumn label="状态" width="140">
        <template #default="{ row }">
          <span :class="['md-badge', LOGIN_META[row.login_status]?.cls || 'md-badge--info']">
            {{ LOGIN_META[row.login_status]?.text || row.login_status }}
          </span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="上次检查" min-width="140">
        <template #default="{ row }">
          <span class="md-typescale-body-small">{{ row.last_login_check_at || '—' }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="140" fixed="right">
        <template #default="{ row }">
          <ElButton size="small" @click="check(row)">重新登录</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
  </div>
</template>

<style scoped>
.sessions-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
</style>