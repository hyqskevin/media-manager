<script setup lang="ts">
import { ref, watch, nextTick } from 'vue'

interface Props {
  lines: string[]
}

const props = defineProps<Props>()
const emit = defineEmits<{
  refresh: []
  'open-dir': []
}>()

const container = ref<HTMLElement | null>(null)

watch(
  () => props.lines,
  async () => {
    await nextTick()
    if (container.value) {
      container.value.scrollTop = container.value.scrollHeight
    }
  },
)
</script>

<template>
  <el-card class="log-card" data-test="log-card">
    <template #header>
      <div class="card-header">
        <span class="card-title">日志</span>
        <div class="header-actions">
          <el-button size="small" data-test="refresh-logs-btn" @click="emit('refresh')">
            刷新
          </el-button>
          <el-button size="small" data-test="open-log-dir-btn" @click="emit('open-dir')">
            打开日志目录
          </el-button>
        </div>
      </div>
    </template>

    <div v-if="lines.length === 0" class="empty-state" data-test="empty-state">
      暂无日志
    </div>
    <div v-else ref="container" class="log-container" data-test="log-container">
      <div
        v-for="(line, idx) in lines"
        :key="idx"
        class="log-line"
        data-test="log-line"
      >
        {{ line }}
      </div>
    </div>
  </el-card>
</template>

<style scoped>
.log-card {
  background: var(--md-sys-color-surface-variant);
  color: var(--md-sys-color-on-surface);
  border: none;
  box-shadow: none;
  border-radius: var(--md-sys-shape-corner-medium);
  margin-bottom: var(--md-sys-spacing-4);
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-title {
  font: var(--md-sys-typescale-title-medium);
}

.header-actions {
  display: flex;
  gap: var(--md-sys-spacing-2);
}

.empty-state {
  color: var(--md-sys-color-on-surface-variant);
  font: var(--md-sys-typescale-body-medium);
  padding: var(--md-sys-spacing-4);
  text-align: center;
}

.log-container {
  max-height: 240px;
  overflow-y: auto;
  font-family: 'Menlo', 'Consolas', 'Courier New', monospace;
  font-size: 12px;
  line-height: 1.6;
}

.log-line {
  color: var(--md-sys-color-on-surface-variant);
  padding: var(--md-sys-spacing-1) var(--md-sys-spacing-2);
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
