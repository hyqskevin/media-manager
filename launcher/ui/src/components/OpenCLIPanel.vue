<script setup lang="ts">
import type { OpencliTestResult } from '@/api/client'

interface Props {
  result: OpencliTestResult | null
  loading: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  test: []
  download: []
}>()

function chipType(): 'success' | 'danger' | 'info' {
  if (!props.result) return 'info'
  return props.result.ok ? 'success' : 'danger'
}

function chipText(): string {
  if (props.loading) return '测试中'
  if (!props.result) return '未检测'
  return props.result.ok ? '已连接' : '未连接'
}
</script>

<template>
  <el-card class="opencli-card" data-test="opencli-card">
    <template #header>
      <div class="card-header">
        <span class="card-title">OpenCLI 连接</span>
        <el-tag :type="chipType()" data-test="opencli-chip">{{ chipText() }}</el-tag>
      </div>
    </template>

    <div v-if="result" class="result-area" data-test="opencli-result">
      <p v-if="result.ok" class="result-success">
        ✓ 连接正常<span v-if="result.version"> · 版本 {{ result.version }}</span>
      </p>
      <p v-else class="result-error">
        ✗ {{ result.message }}
      </p>
    </div>

    <div class="actions">
      <el-button
        :disabled="loading"
        data-test="test-opencli-btn"
        @click="emit('test')"
      >
        {{ loading ? '测试中...' : '测试连接' }}
      </el-button>
      <el-button type="primary" data-test="download-opencli-btn" @click="emit('download')">
        下载 OpenCLI
      </el-button>
    </div>
  </el-card>
</template>

<style scoped>
.opencli-card {
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

.result-area {
  margin-bottom: var(--md-sys-spacing-3);
}

.result-success {
  color: var(--md-sys-color-success);
  font: var(--md-sys-typescale-body-medium);
  margin: 0;
}

.result-error {
  color: var(--md-sys-color-error);
  font: var(--md-sys-typescale-body-medium);
  margin: 0;
}

.actions {
  display: flex;
  gap: var(--md-sys-spacing-2);
}
</style>
