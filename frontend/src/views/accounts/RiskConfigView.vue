<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, SetUp } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface RiskConfig {
  nurture_global_enabled: boolean
  silent_hour_start: number
  silent_hour_end: number
  max_daily_seconds: number
  min_action_interval_s: number
  max_likes_per_hour: number
  max_likes_per_day: number
}

const form = reactive<RiskConfig>({
  nurture_global_enabled: false,
  silent_hour_start: 0,
  silent_hour_end: 6,
  max_daily_seconds: 14400,
  min_action_interval_s: 30,
  max_likes_per_hour: 20,
  max_likes_per_day: 100,
})
const loading = ref(false)

async function load() {
  loading.value = true
  try {
    const res = await api.riskConfig()
    Object.assign(form, res.data as RiskConfig)
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
  form.nurture_global_enabled = value
}

async function save() {
  try {
    await api.saveRiskConfig({ ...form })
    ElMessage.success('风控配置已保存')
  } catch {
    ElMessage.error('保存失败')
  }
}

async function reload() {
  try {
    await api.reloadRiskConfig()
    ElMessage.success('风控配置已重新加载')
    load()
  } catch {
    ElMessage.error('重载失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="risk-page" v-loading="loading">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">风控配置</h2>
      <div class="header-actions">
        <ElButton plain @click="reload">重新加载</ElButton>
        <ElButton type="primary" @click="save" data-test="save">保存</ElButton>
      </div>
    </div>

    <ElCard shadow="never" class="config-card">
      <ElForm label-width="220px" class="config-form">
        <ElFormItem label="全局养号开关">
          <div class="switch-row">
            <ElSwitch v-model="form.nurture_global_enabled" @change="toggleGlobal" data-test="global-switch" />
            <span class="hint">关闭后所有养号任务会立即进入 skipped 状态</span>
          </div>
        </ElFormItem>
        <ElFormItem label="静默时段开始(小时)">
          <ElInputNumber v-model="form.silent_hour_start" :min="0" :max="23" />
        </ElFormItem>
        <ElFormItem label="静默时段结束(小时)">
          <ElInputNumber v-model="form.silent_hour_end" :min="0" :max="23" />
        </ElFormItem>
        <ElFormItem label="单日最大时长(秒)">
          <ElInputNumber v-model="form.max_daily_seconds" :min="600" :max="86400" :step="600" />
        </ElFormItem>
        <ElFormItem label="最小动作间隔(秒)">
          <ElInputNumber v-model="form.min_action_interval_s" :min="1" :max="3600" />
        </ElFormItem>
        <ElFormItem label="每小时点赞上限">
          <ElInputNumber v-model="form.max_likes_per_hour" :min="0" />
        </ElFormItem>
        <ElFormItem label="每天点赞上限">
          <ElInputNumber v-model="form.max_likes_per_day" :min="0" />
        </ElFormItem>
      </ElForm>
    </ElCard>
  </div>
</template>

<style scoped>
.risk-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.header-actions { display: flex; gap: var(--md-sys-spacing-3); }
.config-card { max-width: 720px; }
.switch-row { display: flex; align-items: center; gap: var(--md-sys-spacing-3); }
.hint { color: var(--md-sys-color-on-surface-variant); }
</style>