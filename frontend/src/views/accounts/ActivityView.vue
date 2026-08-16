<script setup lang="ts">
import { onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import * as echarts from 'echarts'
import { Refresh } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface ActivityKpi {
  login_count: number
  nurture_seconds: number
  like_count: number
  favorite_count: number
  nurture_task_count: number
}
interface HeatmapCell {
  account_id: number
  date: string
  intensity: number
}

const kpi = ref<ActivityKpi | null>(null)
const loading = ref(false)
const range = ref<[string, string] | []>([])
const heatmapRef = ref<HTMLElement | null>(null)
const actionChartRef = ref<HTMLElement | null>(null)
const platformChartRef = ref<HTMLElement | null>(null)
let heatmapChart: ReturnType<typeof echarts.init> | null = null
let actionChart: ReturnType<typeof echarts.init> | null = null
let platformChart: ReturnType<typeof echarts.init> | null = null

function params() {
  const [start, end] = range.value ?? []
  const p: Record<string, unknown> = {}
  if (start) p.start_date = start
  if (end) p.end_date = end
  return p
}

async function loadKpi() {
  const res = await api.activityKpi(params())
  kpi.value = res.data as ActivityKpi
}

async function loadHeatmap() {
  const res = await api.activityHeatmap(params())
  const cells = res.data as HeatmapCell[]
  if (!heatmapRef.value) return
  if (!heatmapChart) heatmapChart = echarts.init(heatmapRef.value)
  const dates = Array.from(new Set(cells.map(c => c.date))).sort()
  const accounts = Array.from(new Set(cells.map(c => c.account_id))).sort()
  const data = cells.map(c => [dates.indexOf(c.date), accounts.indexOf(c.account_id), c.intensity])
  heatmapChart.setOption({
    tooltip: { position: 'top' },
    grid: { left: 80, top: 20, bottom: 40 },
    xAxis: { type: 'category', data: dates, splitArea: { show: true } },
    yAxis: { type: 'category', data: accounts.map(a => `#${a}`), splitArea: { show: true } },
    visualMap: { min: 0, max: Math.max(1, ...cells.map(c => c.intensity)), calculable: true, orient: 'horizontal', left: 'center' },
    series: [{ type: 'heatmap', data, label: { show: false }, emphasis: { itemStyle: { shadowBlur: 10 } } }],
  })
}

async function loadActionChart() {
  const res = await api.activityActionCounts(params())
  const rows = res.data as Array<{ action: string; count: number }>
  if (!actionChartRef.value) return
  if (!actionChart) actionChart = echarts.init(actionChartRef.value)
  actionChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: ['40%', '70%'], data: rows.map(r => ({ name: r.action, value: r.count })) }],
  })
}

async function loadPlatformChart() {
  const res = await api.activityPlatformCounts(params())
  const rows = res.data as Array<{ platform: string; count: number }>
  if (!platformChartRef.value) return
  if (!platformChart) platformChart = echarts.init(platformChartRef.value)
  platformChart.setOption({
    tooltip: { trigger: 'item' },
    series: [{ type: 'pie', radius: ['40%', '70%'], data: rows.map(r => ({ name: r.platform, value: r.count })) }],
  })
}

async function load() {
  loading.value = true
  try {
    await Promise.all([loadKpi(), loadHeatmap(), loadActionChart(), loadPlatformChart()])
  } finally {
    loading.value = false
  }
}

function handleResize() {
  heatmapChart?.resize()
  actionChart?.resize()
  platformChart?.resize()
}

onMounted(() => {
  load()
  window.addEventListener('resize', handleResize)
})
onBeforeUnmount(() => {
  window.removeEventListener('resize', handleResize)
  heatmapChart?.dispose()
  actionChart?.dispose()
  platformChart?.dispose()
})
</script>

<template>
  <div class="activity-page" v-loading="loading">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">账号活跃度</h2>
      <div class="header-actions">
        <ElDatePicker v-model="range" type="daterange" value-format="YYYY-MM-DD"
          start-placeholder="开始日期" end-placeholder="结束日期" />
        <ElButton :icon="Refresh" circle @click="load" data-test="refresh" />
      </div>
    </div>

    <div class="kpi-grid">
      <ElCard shadow="never" class="kpi-card">
        <p class="kpi-label">登录次数</p>
        <p class="kpi-value">{{ kpi?.login_count ?? 0 }}</p>
      </ElCard>
      <ElCard shadow="never" class="kpi-card">
        <p class="kpi-label">养号时长(秒)</p>
        <p class="kpi-value">{{ kpi?.nurture_seconds ?? 0 }}</p>
      </ElCard>
      <ElCard shadow="never" class="kpi-card">
        <p class="kpi-label">点赞数</p>
        <p class="kpi-value">{{ kpi?.like_count ?? 0 }}</p>
      </ElCard>
      <ElCard shadow="never" class="kpi-card">
        <p class="kpi-label">收藏数</p>
        <p class="kpi-value">{{ kpi?.favorite_count ?? 0 }}</p>
      </ElCard>
    </div>

    <ElCard shadow="never" class="chart-card">
      <template #header><span class="md-typescale-title-medium">活跃热力图</span></template>
      <div ref="heatmapRef" class="chart-box" data-test="heatmap" />
    </ElCard>

    <div class="chart-row">
      <ElCard shadow="never" class="chart-card">
        <template #header><span class="md-typescale-title-medium">动作分布</span></template>
        <div ref="actionChartRef" class="chart-box" />
      </ElCard>
      <ElCard shadow="never" class="chart-card">
        <template #header><span class="md-typescale-title-medium">平台占比</span></template>
        <div ref="platformChartRef" class="chart-box" />
      </ElCard>
    </div>
  </div>
</template>

<style scoped>
.activity-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.header-actions { display: flex; align-items: center; gap: var(--md-sys-spacing-3); }
.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
  gap: var(--md-sys-spacing-4);
  margin-bottom: var(--md-sys-spacing-4);
}
.kpi-card { text-align: center; }
.kpi-label { margin: 0; color: var(--md-sys-color-on-surface-variant); }
.kpi-value { margin: var(--md-sys-spacing-2) 0 0; font-size: 28px; font-weight: 600; }
.chart-card { margin-bottom: var(--md-sys-spacing-4); }
.chart-row { display: grid; grid-template-columns: 1fr 1fr; gap: var(--md-sys-spacing-4); }
.chart-box { height: 320px; width: 100%; }
</style>