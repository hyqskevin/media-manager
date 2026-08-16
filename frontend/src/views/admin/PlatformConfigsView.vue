<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'

interface PlatformMeta {
  id: string
  display_name: string
  icon: string
  status: string
}

const platforms = ref<PlatformMeta[]>([])
const nurtureGlobalEnabled = ref(false)
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await api.platforms()
    platforms.value = res.data as PlatformMeta[]
  } finally {
    loading.value = false
  }
}

async function toggleGlobal(value: boolean) {
  await ElMessageBox.confirm(
    value ? '开启后养号任务将正常执行。' : '关闭后所有养号任务会立即进入 skipped 状态。确认切换？',
    '全局养号开关',
    { type: 'warning' },
  )
  // v0.2 后端未实现持久化，前端本地态 + 提示
  nurtureGlobalEnabled.value = value
  ElMessage.success(`全局养号已${value ? '开启' : '关闭'}(本地态，后端 v0.3 持久化)`)
}

onMounted(load)
</script>

<template>
  <div class="platform-configs-page">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">平台配置</h2>
      <ElButton type="primary" plain @click="load">刷新</ElButton>
    </div>

    <ElCard class="global-card" shadow="never">
      <div class="global-row">
        <div>
          <span class="md-typescale-title-medium">全局养号开关</span>
          <p class="md-typescale-body-small">关闭后所有养号任务会立即进入 skipped 状态</p>
        </div>
        <ElSwitch v-model="nurtureGlobalEnabled" @change="toggleGlobal" data-test="global-switch" />
      </div>
    </ElCard>

    <ElTable :data="platforms" v-loading="loading" type="expand" data-test="platforms-table">
      <ElTableColumn type="expand">
        <template #default="{ row }">
          <div class="expand-detail">
            <p>适配器状态：<ElTag :type="row.status === 'implemented' ? 'success' : 'info'" effect="plain">
              {{ row.status === 'implemented' ? '已实现' : '规划中' }}
            </ElTag></p>
          </div>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="id" label="平台" width="140" />
      <ElTableColumn label="显示名" min-width="140">
        <template #default="{ row }">{{ row.icon }} {{ row.display_name }}</template>
      </ElTableColumn>
      <ElTableColumn label="状态" width="120">
        <template #default="{ row }">
          <span :class="['md-badge', row.status === 'implemented' ? 'md-badge--success' : 'md-badge--info']">
            {{ row.status === 'implemented' ? '已实现' : '规划中' }}
          </span>
        </template>
      </ElTableColumn>
    </ElTable>
  </div>
</template>

<style scoped>
.platform-configs-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.global-card { margin-bottom: var(--md-sys-spacing-4); }
.global-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.global-row p { margin: var(--md-sys-spacing-1) 0 0; color: var(--md-sys-color-on-surface-variant); }
.expand-detail { padding: 0 var(--md-sys-spacing-4) var(--md-sys-spacing-4) 48px; }
</style>