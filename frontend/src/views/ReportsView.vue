<script setup lang="ts">
import { Delete, Download, Plus, View } from '@element-plus/icons-vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import DOMPurify from 'dompurify'
import { api } from '@/api/client'

const rows = ref<any[]>([])
const cities = ref<any[]>([])
const preview = ref('')
const previewHtml = ref('')
async function renderPreview() {
  if (!preview.value) { previewHtml.value = ''; return }
  const { marked } = await import('marked')
  previewHtml.value = DOMPurify.sanitize(marked.parse(preview.value, { async: false }) as string)
}
watch(preview, renderPreview)
const dialog = ref(false)
const generating = ref(false)
const form = reactive<{
  weekDate: Date | null
  cities: string[]
  keyword_group_ids: number[]
  keywords: string[]
  blogger_group_ids: number[]
  blogger_ids: number[]
}>({
  weekDate: new Date(),
  cities: [],
  keyword_group_ids: [],
  keywords: [],
  blogger_group_ids: [],
  blogger_ids: [],
})
const cityNames = computed(() => Object.fromEntries(cities.value.map((city) => [city.code, city.name])))
const allKeywordGroups = ref<any[]>([])
const allBloggerGroups = ref<any[]>([])
const allBloggers = ref<any[]>([])
const kgNames = computed(() => Object.fromEntries(allKeywordGroups.value.map((g) => [g.id, g.name])))
const bgNames = computed(() => Object.fromEntries(allBloggerGroups.value.map((g) => [g.id, g.name])))
const bloggerNames = computed(() => Object.fromEntries(allBloggers.value.map((b) => [b.id, b.username])))

function formatFilters(row: any): string {
  const parts: string[] = []
  if (row.keyword_group_ids?.length) parts.push(`关键词组：${row.keyword_group_ids.map((id: number) => kgNames.value[id] ?? id).join('、')}`)
  if (row.keywords?.length) parts.push(`关键词：${row.keywords.join('、')}`)
  if (row.blogger_group_ids?.length) parts.push(`博主组：${row.blogger_group_ids.map((id: number) => bgNames.value[id] ?? id).join('、')}`)
  if (row.blogger_ids?.length) parts.push(`博主：${row.blogger_ids.map((id: number) => bloggerNames.value[id] ?? id).join('、')}`)
  return parts.join(' · ')
}

function toIsoWeek(value: Date): string {
  const date = new Date(Date.UTC(value.getFullYear(), value.getMonth(), value.getDate()))
  const day = date.getUTCDay() || 7
  date.setUTCDate(date.getUTCDate() + 4 - day)
  const year = date.getUTCFullYear()
  const yearStart = new Date(Date.UTC(year, 0, 1))
  const week = Math.ceil((((date.getTime() - yearStart.getTime()) / 86400000) + 1) / 7)
  return `${year}-W${String(week).padStart(2, '0')}`
}

async function load() {
  const [reportResponse, cityResponse, kgResp, bgResp, bloggerResp] = await Promise.all([
    api.reports(),
    api.settings('cities'),
    api.keywordGroups(),
    api.bloggerGroups(),
    api.settings('bloggers'),
  ])
  rows.value = reportResponse.data.data
  cities.value = cityResponse.data.data.filter((city: any) => city.enabled)
  allKeywordGroups.value = (kgResp.data.data?.items || []).filter((g: any) => g.enabled)
  allBloggerGroups.value = (bgResp.data.data?.items || []).filter((g: any) => g.enabled)
  allBloggers.value = bloggerResp.data.data || []
  if (!form.cities.length && cities.value.length) form.cities = [cities.value[0].code]
}

async function generate() {
  if (!form.weekDate) { ElMessage.warning('请选择周次'); return }
  if (!form.cities.length && !form.keyword_group_ids.length && !form.keywords.length && !form.blogger_group_ids.length && !form.blogger_ids.length) { ElMessage.warning('请至少选择城市或关键词/博主等筛选条件'); return }
  generating.value = true
  try {
    await api.generateReport({
      week: toIsoWeek(form.weekDate),
      cities: form.cities,
      keyword_group_ids: form.keyword_group_ids,
      keywords: form.keywords,
      blogger_group_ids: form.blogger_group_ids,
      blogger_ids: form.blogger_ids,
    })
    ElMessage.success('周报生成成功')
    await load()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || error.response?.data?.detail || '周报生成失败')
  } finally {
    generating.value = false
  }
}

async function show(id: number) {
  preview.value = (await api.report(id)).data.data.content
  dialog.value = true
}

async function download(row: any, format: 'md' | 'xlsx') {
  try {
    const response = await api.downloadReport(row.id, format)
    const disposition = response.headers?.['content-disposition'] || ''
    const star = disposition.match(/filename\*=(?:UTF-8'')?([^;]+)/i)
    const plain = disposition.match(/filename="?([^";]+)"?/i)
    const filename = star ? decodeURIComponent(star[1])
      : plain?.[1] || `${row.week}.${format}`
    const url = URL.createObjectURL(response.data)
    const link = document.createElement('a')
    link.href = url
    link.download = filename
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    ElMessage.success('下载已开始')
  } catch {
    ElMessage.error('周报下载失败')
  }
}

async function remove(row: any) {
  await ElMessageBox.confirm(`确认删除周报「${row.week}」？删除后不可恢复。`, '删除周报', { type: 'warning' })
  try {
    await api.deleteReport(row.id)
    ElMessage.success('周报已删除')
    await load()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || '周报删除失败')
  }
}

onMounted(load)
</script>

<template>
  <ElCard shadow="never">
    <div class="toolbar">
      <ElDatePicker v-model="form.weekDate" type="week" format="YYYY 第 ww 周" placeholder="选择周次" aria-label="周次" />
      <ElSelect v-model="form.cities" multiple placeholder="选择城市（可多选）" filterable collapse-tags collapse-tags-tooltip aria-label="城市">
        <ElOption v-for="city in cities" :key="city.code" :label="city.name" :value="city.code" />
      </ElSelect>
      <ElSelect v-model="form.keyword_group_ids" multiple placeholder="关键词组（可选）" filterable collapse-tags collapse-tags-tooltip aria-label="关键词组">
        <ElOption v-for="g in allKeywordGroups" :key="g.id" :label="g.name" :value="g.id" />
      </ElSelect>
      <ElSelect v-model="form.blogger_group_ids" multiple placeholder="博主组（可选）" filterable collapse-tags collapse-tags-tooltip aria-label="博主组">
        <ElOption v-for="g in allBloggerGroups" :key="g.id" :label="g.name" :value="g.id" />
      </ElSelect>
      <ElButton type="primary" :icon="Plus" :loading="generating" @click="generate">生成周报</ElButton>
    </div>
    <ElTable :data="rows">
      <ElTableColumn prop="week" label="周次" width="110" />
      <ElTableColumn prop="name" label="名称" min-width="180" show-overflow-tooltip />
      <ElTableColumn label="筛选条件" min-width="180"><template #default="scope">{{ formatFilters(scope.row) }}</template></ElTableColumn>
      <ElTableColumn label="城市"><template #default="scope">{{ (scope.row.cities || []).map((code: string) => cityNames[code] || code).join('、') }}</template></ElTableColumn>
      <ElTableColumn prop="note_count" label="推文数" />
      <ElTableColumn prop="activity_count" label="活动数" />
      <ElTableColumn prop="status" label="状态" />
      <ElTableColumn label="操作" min-width="300" class-name="action-column"><template #default="scope"><ElButton text :icon="View" @click="show(scope.row.id)">预览</ElButton><ElButton text :icon="Download" @click="download(scope.row,'md')">Markdown</ElButton><ElButton text :icon="Download" @click="download(scope.row,'xlsx')">Excel</ElButton><ElButton text type="danger" :icon="Delete" @click="remove(scope.row)">删除</ElButton></template></ElTableColumn>
    </ElTable>
  </ElCard>
  <ElDialog v-model="dialog" title="周报预览" width="760"><div class="report-preview" v-html="previewHtml"></div></ElDialog>
</template>

<style scoped>
.report-preview :deep(h1) { font-size: 22px; margin: 0 0 12px; }
.report-preview :deep(h2) { font-size: 18px; margin: 16px 0 8px; }
.report-preview :deep(p) { margin: 6px 0; line-height: 1.7; }
.report-preview :deep(ul) { padding-left: 20px; }
</style>
