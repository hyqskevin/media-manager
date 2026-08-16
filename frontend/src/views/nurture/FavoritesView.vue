<script setup lang="ts">
import { onMounted, ref, watch } from 'vue'
import { api } from '@/api/client'

interface Account {
  id: number
  name: string
  platform: string
}
interface Snapshot {
  id: number
  account_id: number
  platform: string
  captured_at: string | null
  item_count: number
  items: Array<Record<string, unknown>>
  error: string | null
}

const accounts = ref<Account[]>([])
const snapshots = ref<Snapshot[]>([])
const accountFilter = ref<number | undefined>()
const loading = ref(false)

async function loadAccounts() {
  const res = await api.platformAccounts()
  accounts.value = res.data as Account[]
}

async function loadSnapshots() {
  loading.value = true
  try {
    const all: Snapshot[] = []
    const source = accountFilter.value
      ? accounts.value.filter(a => a.id === accountFilter.value)
      : accounts.value
    for (const a of source) {
      try {
        const res = await api.favoriteSnapshots(a.id)
        all.push(res.data as Snapshot)
      } catch {
        /* 无快照则跳过 */
      }
    }
    snapshots.value = all
  } finally {
    loading.value = false
  }
}

watch(accountFilter, () => loadSnapshots())
onMounted(async () => {
  await loadAccounts()
  loadSnapshots()
})
</script>

<template>
  <div class="favorites-page">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">我的收藏夹</h2>
      <ElButton type="primary" plain @click="loadSnapshots">刷新</ElButton>
    </div>

    <div class="filter-bar">
      <ElSelect v-model="accountFilter" placeholder="选择账号" clearable style="width: 220px" data-test="account-filter">
        <ElOption v-for="a in accounts" :key="a.id" :label="`#${a.id} ${a.name} (${a.platform})`" :value="a.id" />
      </ElSelect>
    </div>

    <div v-loading="loading" class="snapshot-grid">
      <ElCard v-for="s in snapshots" :key="s.id" shadow="hover" class="snapshot-card" data-test="snapshot-card">
        <template #header>
          <span class="md-typescale-title-medium">#{{ s.id }} · {{ accounts.find(a => a.id === s.account_id)?.name || `账号#${s.account_id}` }}</span>
        </template>
        <p class="md-typescale-body-small">平台：{{ s.platform }}</p>
        <p class="md-typescale-body-small">捕获时间：{{ s.captured_at || '—' }}</p>
        <p class="md-typescale-title-medium">{{ s.item_count }} 条</p>
      </ElCard>
      <ElEmpty v-if="!loading && snapshots.length === 0" description="暂无收藏快照" />
    </div>
  </div>
</template>

<style scoped>
.favorites-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.filter-bar { margin-bottom: var(--md-sys-spacing-4); }
.snapshot-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--md-sys-spacing-4);
}
.snapshot-card p { margin: var(--md-sys-spacing-1) 0; }
</style>