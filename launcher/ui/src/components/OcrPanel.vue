<script setup lang="ts">
import type { OcrStatus, OcrInstallProgress, OcrTestResult } from '@/api/client'

interface Props {
  status: OcrStatus
  progress: OcrInstallProgress
  testResult: OcrTestResult | null
  installing: boolean
  testing: boolean
}

const props = defineProps<Props>()
const emit = defineEmits<{
  install: []
  test: []
}>()

function chipType(): 'success' | 'warning' | 'info' {
  if (props.status.status === 'installed') return 'success'
  if (props.status.status === 'installing') return 'warning'
  return 'info'
}

function chipText(): string {
  if (props.status.status === 'installed') return '已安装'
  if (props.status.status === 'installing') return '安装中'
  return '未安装'
}
</script>

<template>
  <el-card class="ocr-card" data-test="ocr-card">
    <template #header>
      <div class="card-header">
        <div>
          <div class="card-title">OCR 增强</div>
          <div class="card-subtitle">PaddleOCR 图片本地识别</div>
        </div>
        <el-tag :type="chipType()" data-test="ocr-chip">
          {{ chipText() }}<span v-if="status.version"> · {{ status.version }}</span>
        </el-tag>
      </div>
    </template>

    <div v-if="installing || progress.active" class="progress-area" data-test="install-progress">
      <el-progress :percentage="progress.percent" :stroke-width="8" />
      <p class="progress-message">{{ progress.message }} · {{ progress.percent }}%</p>
    </div>

    <div v-if="testResult && !testing" class="test-result" data-test="ocr-test-result">
      <p v-if="testResult.ok" class="test-success">
        ✓ 识别成功 · 耗时 {{ testResult.latency_ms }}ms
        <span v-if="testResult.text"> · {{ testResult.text }}</span>
      </p>
      <p v-else class="test-error">
        ✗ {{ testResult.message || testResult.reason || '测试失败' }}
      </p>
    </div>

    <div class="actions">
      <el-button
        type="primary"
        :disabled="installing"
        data-test="install-ocr-btn"
        @click="emit('install')"
      >
        {{ installing ? '安装中...' : '下载安装 OCR' }}
      </el-button>
      <el-button
        :disabled="testing || status.status !== 'installed'"
        data-test="test-ocr-btn"
        @click="emit('test')"
      >
        {{ testing ? '测试中...' : '测试 OCR' }}
      </el-button>
    </div>
  </el-card>
</template>

<style scoped>
.ocr-card {
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
  align-items: flex-start;
}

.card-title {
  font: var(--md-sys-typescale-title-large);
}

.card-subtitle {
  font: var(--md-sys-typescale-body-medium);
  color: var(--md-sys-color-on-surface-variant);
  margin-top: var(--md-sys-spacing-1);
}

.progress-area {
  margin-bottom: var(--md-sys-spacing-3);
}

.progress-message {
  font: var(--md-sys-typescale-body-medium);
  color: var(--md-sys-color-on-surface-variant);
  margin: var(--md-sys-spacing-2) 0 0;
}

.test-result {
  margin-bottom: var(--md-sys-spacing-3);
}

.test-success {
  color: var(--md-sys-color-success);
  font: var(--md-sys-typescale-body-medium);
  margin: 0;
}

.test-error {
  color: var(--md-sys-color-error);
  font: var(--md-sys-typescale-body-medium);
  margin: 0;
}

.actions {
  display: flex;
  gap: var(--md-sys-spacing-2);
}
</style>
