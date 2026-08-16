<script setup lang="ts">
import type { StatusResponse, ServiceState } from '@/api/client'

interface Props {
  status: StatusResponse
}

const props = defineProps<Props>()
const emit = defineEmits<{
  restart: [name: string]
  'stop-all': []
}>()

const services: { key: keyof StatusResponse; label: string }[] = [
  { key: 'api', label: 'API' },
  { key: 'worker', label: 'Worker' },
  { key: 'beat', label: 'Beat' },
]

function stateText(state: ServiceState): string {
  if (state.state === 'running') return `运行中${state.pid ? ' (PID ' + state.pid + ')' : ''}`
  if (state.state === 'crashed') return '异常退出'
  return '已停止'
}
</script>

<template>
  <el-card class="service-status-card" data-test="service-status-card">
    <template #header>
      <div class="card-header">
        <span class="card-title">服务状态</span>
        <el-button size="small" data-test="stop-all-btn" @click="emit('stop-all')">
          停止全部
        </el-button>
      </div>
    </template>

    <div
      v-for="svc in services"
      :key="svc.key"
      class="service-row"
      data-test="service-row"
    >
      <span
        class="dot"
        :class="`dot--${props.status[svc.key].state}`"
        :data-test="`dot-${svc.key}`"
      />
      <span class="service-name">{{ svc.label }}</span>
      <span class="service-state">{{ stateText(props.status[svc.key]) }}</span>
      <el-button
        size="small"
        :data-test="`restart-btn`"
        @click="emit('restart', svc.key)"
      >
        重启
      </el-button>
    </div>
  </el-card>
</template>

<style scoped>
.service-status-card {
  background: var(--md-sys-color-surface);
  color: var(--md-sys-color-on-surface);
  border: none;
  box-shadow: var(--md-sys-elevation-1);
  border-radius: var(--md-sys-shape-corner-medium);
  margin-bottom: var(--md-sys-spacing-4);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font: var(--md-sys-typescale-title-large);
}

.service-row {
  display: flex;
  align-items: center;
  gap: var(--md-sys-spacing-3);
  padding: var(--md-sys-spacing-2) 0;
  font: var(--md-sys-typescale-body-large);
}

.service-name {
  min-width: 80px;
  font: var(--md-sys-typescale-label-large);
}

.service-state {
  flex: 1;
  color: var(--md-sys-color-on-surface-variant);
  font: var(--md-sys-typescale-body-medium);
}

.dot {
  width: 10px;
  height: 10px;
  border-radius: var(--md-sys-shape-corner-full);
  display: inline-block;
}

.dot--running {
  background: var(--md-sys-color-success);
}

.dot--stopped {
  background: var(--md-sys-color-on-surface-variant);
}

.dot--crashed {
  background: var(--md-sys-color-error);
}
</style>
