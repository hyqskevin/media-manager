<script setup lang="ts">
import type { ECharts } from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{ tasks: any[] }>()
const container = ref<HTMLDivElement | null>(null)
let chart: ECharts | null = null

// 后端 started_at 为 UTC naive（无 Z 后缀）：按 UTC 解析再转东八区，
// 避免 JS 默认把 UTC 数字当本地时间导致 x 轴时间慢 8h
function formatTime(value: string | null) {
  if (!value) return '-'
  const normalized = /(?:Z|[+-]\d{2}:?\d{2})$/i.test(value) ? value : `${value}Z`
  const date = new Date(normalized)
  if (Number.isNaN(date.getTime())) return '-'
  const parts = new Intl.DateTimeFormat('zh-CN', {
    timeZone: 'Asia/Shanghai',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
    hourCycle: 'h23',
  }).formatToParts(date)
  if (!parts.length) return '-'
  const get = (type: string) => parts.find((p) => p.type === type)?.value ?? ''
  return `${get('month')}-${get('day')} ${get('hour')}:${get('minute')}`
}

function buildOption() {
  const tasks = props.tasks || []
  return {
    tooltip: { trigger: 'axis' },
    legend: { data: ['发现', '成功', '失败'] },
    grid: { left: 44, right: 16, top: 36, bottom: 28 },
    xAxis: { type: 'category', data: tasks.map((t: any) => formatTime(t.started_at)) },
    yAxis: { type: 'value', minInterval: 1 },
    series: [
      { name: '发现', type: 'line', smooth: true, data: tasks.map((t: any) => t.total_notes) },
      { name: '成功', type: 'line', smooth: true, data: tasks.map((t: any) => t.success_notes) },
      { name: '失败', type: 'line', smooth: true, data: tasks.map((t: any) => t.failed_notes) },
    ],
  }
}

function render() {
  chart?.setOption(buildOption())
}

function resize() {
  chart?.resize()
}

onMounted(async () => {
  const echarts = await import('echarts')
  chart = echarts.init(container.value!)
  render()
  window.addEventListener('resize', resize)
})
watch(() => props.tasks, render, { deep: true })
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="container" class="chart-container" aria-label="抓取趋势图" />
</template>

<style scoped>
.chart-container { width: 100%; height: 320px; }
</style>
