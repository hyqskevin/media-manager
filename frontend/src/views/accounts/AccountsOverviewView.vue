<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { api } from '@/api/client'

interface Account {
  id: number
  name: string
  platform: string
  enabled: boolean
  login_status: string
}

const accounts = ref<Account[]>([])
const loading = ref(false)

const total = computed(() => accounts.value.length)
const enabledCount = computed(() => accounts.value.filter(a => a.enabled).length)
const disabledCount = computed(() => total.value - enabledCount.value)
const abnormalCount = computed(() =>
  accounts.value.filter(a => a.login_status === 'expired' || a.login_status === 'logged_out').length,
)
const platformCount = computed(() => new Set(accounts.value.map(a => a.platform)).size)

async function load() {
  loading.value = true
  try {
    const res = await api.platformAccounts()
    accounts.value = res.data as Account[]
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>

<template>
  <div class="overview-page">
    <h2 class="md-typescale-headline-medium">账号总览</h2>

    <div class="kpi-grid" v-loading="loading">
      <ElCard shadow="never" class="kpi-card">
        <span class="kpi-value">{{ total }}</span><span class="kpi-label">账号总数</span>
      </ElCard>
      <ElCard shadow="never" class="kpi-card">
        <span class="kpi-value">{{ enabledCount }}</span><span class="kpi-label">启用账号</span>
      </ElCard>
      <ElCard shadow="never" class="kpi-card">
        <span class="kpi-value">{{ disabledCount }}</span><span class="kpi-label">禁用账号</span>
      </ElCard>
      <ElCard shadow="never" class="kpi-card">
        <span class="kpi-value kpi-abnormal">{{ abnormalCount }}</span><span class="kpi-label">异常账号</span>
      </ElCard>
    </div>

    <ElCard shadow="never" class="section-card">
      <template #header><span class="md-typescale-title-medium">平台分布({{ platformCount }} 平台)</span></template>
      <div class="platform-dist">
        <div v-for="p in new Set(accounts.map(a => a.platform))" :key="String(p)" class="dist-row">
          <span class="dist-name">{{ p }}</span>
          <ElProgress :percentage="total ? Math.round((accounts.filter(a => a.platform === p).length / total) * 100) : 0" />
        </div>
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
.overview-page { padding: var(--md-sys-spacing-6); }
.overview-page h2 { margin: 0 0 var(--md-sys-spacing-4); }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: var(--md-sys-spacing-4);
  margin-bottom: var(--md-sys-spacing-4);
}
.kpi-card { display: flex; flex-direction: column; gap: var(--md-sys-spacing-1); }
.kpi-value { font: var(--md-sys-typescale-headline-small); color: var(--md-sys-color-primary); }
.kpi-abnormal { color: var(--md-sys-color-error); }
.kpi-label { font: var(--md-sys-typescale-label-medium); color: var(--md-sys-color-on-surface-variant); }
.section-card { margin-bottom: var(--md-sys-spacing-4); }
.platform-dist { display: flex; flex-direction: column; gap: var(--md-sys-spacing-3); }
.dist-row { display: grid; grid-template-columns: 120px 1fr; align-items: center; gap: var(--md-sys-spacing-3); }
.dist-name { font: var(--md-sys-typescale-label-medium); }
</style>