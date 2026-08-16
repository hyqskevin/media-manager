<script setup lang="ts">
import type { ECharts } from 'echarts'
import { onBeforeUnmount, onMounted, ref, watch } from 'vue'

const props = defineProps<{ counts: Record<string, number> }>()
const container = ref<HTMLDivElement | null>(null)
let chart: ECharts | null = null

const statusLabels: Record<string, string> = {
  COMPLETED: '成功',
  COMPLETED_WITH_ERRORS: '部分成功',
  FAILED: '失败',
  STOPPED: '已停止',
  OTHER: '其他',
}
const order = ['COMPLETED', 'COMPLETED_WITH_ERRORS', 'FAILED', 'STOPPED', 'OTHER']

function buildOption() {
  const counts = props.counts || {}
  const data = order
    .filter((key) => counts[key])
    .map((key) => ({ name: statusLabels[key] || key, value: counts[key] }))
  return {
    tooltip: { trigger: 'item', formatter: '{b}: {c} ({d}%)' },
    legend: { bottom: 0 },
    series: [
      {
        type: 'pie',
        radius: ['38%', '65%'],
        center: ['50%', '44%'],
        label: { formatter: '{b}\n{d}%' },
        data,
      },
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
watch(() => props.counts, render, { deep: true })
onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  chart?.dispose()
  chart = null
})
</script>

<template>
  <div ref="container" class="chart-container" aria-label="抓取成功率图" />
</template>

<style scoped>
.chart-container { width: 100%; height: 320px; }
</style>
