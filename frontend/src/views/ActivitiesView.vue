<script setup lang="ts">
import { CircleCheck, CircleClose, Delete, Edit, Refresh, Search, View } from '@element-plus/icons-vue'
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import { formatUtcAsShanghai } from '@/utils/datetime'

const rows = ref<any[]>([])
const cities = ref<any[]>([])
const bloggers = ref<any[]>([])
const keywordGroups = ref<any[]>([])
const bloggerGroups = ref<any[]>([])
const total = ref(0)
const drawer = ref(false)
const editDialog = ref(false)
const noteEditDialog = ref(false)
const noteSaving = ref(false)
const noteEditFromDetail = ref(false)
const detail = ref<any>({ activities: [], images: [] })
const form = reactive<any>({})
const noteForm = reactive<any>({ title: '', content: '', city_code: '', published_at: null, source_url: '' })
const noteActivities = ref<any[]>([])
const reExtracting = ref(false)
const addActivityDialog = ref(false)
const addActivitySaving = ref(false)
const newActivityForm = reactive({ name: '', location: '', start_time: null as Date | null, end_time: null as Date | null, type: '其他', summary: '' })
const editingId = ref<number | null>(null)
const imageUrls = ref<string[]>([])
const imagesLoading = ref(false)
const selectedRows = ref<any[]>([])
const batchDeleting = ref(false)
const batchApproving = ref(false)
const filters = reactive({
  city: '',
  review_status: '',
  keyword_mode: 'custom' as 'custom' | 'groups',
  keyword: '',
  keyword_group_ids: [] as number[],
  blogger_mode: 'list' as 'list' | 'groups',
  blogger_id: null as number | null,
  blogger_group_ids: [] as number[],
  dates: [] as string[],
  page: 1,
  page_size: 20,
})
const statusLabels: Record<string, string> = { PENDING: '待审核', APPROVED: '已通过', REJECTED: '未通过', RAW: '待审核', NEEDS_REVIEW: '待完善' }
const statusTypes: Record<string, string> = { PENDING: 'primary', APPROVED: 'success', REJECTED: 'danger', RAW: 'primary', NEEDS_REVIEW: 'warning' }
const cityNames = computed(() => Object.fromEntries(cities.value.map((city) => [city.code, city.name])))
const bloggerFilteredByCity = computed(() => {
  if (!filters.city) return bloggers.value
  return bloggers.value.filter((blogger: any) => (blogger.city_codes || []).includes(filters.city))
})
const detailDrawerSize = computed(() => window.innerWidth < 768 ? '95%' : '70%')

function queryParams() {
  const params: any = { city: filters.city || undefined, review_status: filters.review_status || undefined, start_date: filters.dates?.[0] || undefined, end_date: filters.dates?.[1] || undefined, page: filters.page, page_size: filters.page_size }
  if (filters.keyword_mode === 'custom') {
    const kw = filters.keyword?.trim()
    if (kw) params.keyword = kw
  } else {
    if (filters.keyword_group_ids.length) {
      params.keyword_group_ids = [...filters.keyword_group_ids]
    }
  }
  if (filters.blogger_mode === 'list') {
    if (filters.blogger_id != null) params.blogger_id = filters.blogger_id
  } else {
    if (filters.blogger_group_ids.length) {
      params.blogger_group_ids = [...filters.blogger_group_ids]
    }
  }
  return params
}
function setKeywordMode(mode: 'custom' | 'groups') {
  filters.keyword_mode = mode
  if (mode === 'custom') filters.keyword_group_ids = []
  else filters.keyword = ''
}
function setBloggerMode(mode: 'list' | 'groups') {
  filters.blogger_mode = mode
  if (mode === 'list') filters.blogger_group_ids = []
  else filters.blogger_id = null
}
async function load() { const response = await api.notes(queryParams()); rows.value = response.data.data.items; total.value = response.data.pagination.total }
async function initialize() {
  try {
    const [cityResp, bloggerResp, kgResp, bgResp] = await Promise.all([
      api.settings('cities'),
      api.settings('bloggers'),
      api.keywordGroups(),
      api.bloggerGroups(),
    ])
    cities.value = cityResp.data.data || []
    bloggers.value = bloggerResp.data.data || []
    keywordGroups.value = (kgResp.data.data?.items || []).filter((g: any) => g.enabled)
    bloggerGroups.value = (bgResp.data.data?.items || []).filter((g: any) => g.enabled)
  } catch { cities.value = []; bloggers.value = []; keywordGroups.value = []; bloggerGroups.value = [] }
  await load()
}
function applyFilters() { filters.page = 1; load() }
function resetFilters() {
  Object.assign(filters, {
    city: '',
    review_status: '',
    keyword_mode: 'custom',
    keyword: '',
    keyword_group_ids: [],
    blogger_mode: 'list',
    blogger_id: null,
    blogger_group_ids: [],
    dates: [],
    page: 1,
    page_size: 20,
  })
  load()
}
function formatTime(value: string | null) { return value ? formatUtcAsShanghai(value) : '待确认' }
function formatDate(value: string | null) { return value ? formatUtcAsShanghai(value).slice(0, 10) : '待确认' }
/** 点赞/收藏/评论；任一字段缺失显示 "—"；全部缺失显示 "—" */
function formatEngagement(row: any) {
  const fmt = (v: any) => (v == null ? '—' : Number(v).toLocaleString())
  return [fmt(row.like_count), fmt(row.collect_count), fmt(row.comment_count)].join(' / ')
}

async function batchRemove() {
  if (!selectedRows.value.length) return
  await ElMessageBox.confirm(`确认删除选中的 ${selectedRows.value.length} 篇推文及其活动？`, '批量删除确认', { type: 'warning' })
  batchDeleting.value = true
  try { const response = await api.deleteNotes(selectedRows.value.map(row => row.id)); ElMessage.success(`已删除 ${response.data.data.deleted_count} 篇推文`); selectedRows.value = []; await load() }
  finally { batchDeleting.value = false }
}
async function batchApprove() {
  if (!selectedRows.value.length) return
  await ElMessageBox.confirm(`确认通过选中的 ${selectedRows.value.length} 篇推文？`, '批量审核确认', { type: 'warning' })
  batchApproving.value = true
  try { const response = await api.approveNotes(selectedRows.value.map(row => row.id)); ElMessage.success(`已通过 ${response.data.data.approved_count} 篇推文`); selectedRows.value = []; await load() }
  finally { batchApproving.value = false }
}
function releaseImages() { imageUrls.value.forEach(url => URL.revokeObjectURL(url)); imageUrls.value = [] }
async function show(id: number) {
  releaseImages(); detail.value = (await api.note(id)).data.data; drawer.value = true; imagesLoading.value = true
  try { const responses = await Promise.all((detail.value.images || []).map((image: any) => api.noteImage(id, image.id))); imageUrls.value = responses.map((response: any) => URL.createObjectURL(response.data)) }
  catch { ElMessage.error('部分来源图片加载失败') }
  finally { imagesLoading.value = false }
}
function openEdit(activity: any) { editingId.value = activity.id; Object.keys(form).forEach(key => delete form[key]); Object.assign(form, activity); editDialog.value = true }
async function saveActivity() { await api.updateActivity(editingId.value!, { ...form, start_time: form.start_time ? new Date(form.start_time).toISOString() : null, end_time: form.end_time ? new Date(form.end_time).toISOString() : null }); editDialog.value = false; await show(detail.value.id); await load(); ElMessage.success('活动已更新') }
async function removeActivity(activity: any) { await ElMessageBox.confirm('确认删除该识别活动？', '删除确认', { type: 'warning' }); await api.deleteActivity(activity.id); await show(detail.value.id); await load() }
async function reExtractNote() {
  reExtracting.value = true
  try {
    const response = await api.reExtractNote(noteForm.id)
    noteActivities.value = response.data.data.activities || []
    const count = response.data.data.extracted_count || 0
    ElMessage.success(count > 0 ? `已提取 ${count} 条活动` : '未提取到活动')
  } catch { ElMessage.error('活动提取失败，请重试') }
  finally { reExtracting.value = false }
}
function openAddActivity() {
  Object.assign(newActivityForm, { name: '', location: '', start_time: null, end_time: null, type: '其他', summary: '' })
  addActivityDialog.value = true
}
async function saveNewActivity() {
  if (!newActivityForm.name.trim() || !newActivityForm.type) { ElMessage.warning('请填写活动名称和类型'); return }
  addActivitySaving.value = true
  try {
    const response = await api.createNoteActivity(noteForm.id, {
      name: newActivityForm.name.trim(),
      location: newActivityForm.location,
      start_time: newActivityForm.start_time ? new Date(newActivityForm.start_time).toISOString() : null,
      end_time: newActivityForm.end_time ? new Date(newActivityForm.end_time).toISOString() : null,
      type: newActivityForm.type,
      summary: newActivityForm.summary,
    })
    noteActivities.value.push(response.data.data)
    addActivityDialog.value = false
    ElMessage.success('活动已添加')
  } catch { ElMessage.error('活动添加失败') }
  finally { addActivitySaving.value = false }
}
async function removeEditActivity(activity: any) {
  await ElMessageBox.confirm('确认删除该识别活动？', '删除确认', { type: 'warning' })
  await api.deleteActivity(activity.id)
  noteActivities.value = noteActivities.value.filter(a => a.id !== activity.id)
  await load()
}
async function openNoteEdit(note: any, fromDetail = false) {
  const value = fromDetail ? note : (await api.note(note.id)).data.data
  Object.assign(noteForm, {
    id: value.id,
    title: value.title || '',
    content: value.content || '',
    city_code: value.city_code || '',
    published_at: value.published_at ? new Date(value.published_at) : null,
    source_url: value.source_url || '',
  })
  noteActivities.value = value.activities || []
  noteEditFromDetail.value = fromDetail
  noteEditDialog.value = true
}
async function saveNote() {
  if (!noteForm.title.trim() || !noteForm.city_code) { ElMessage.warning('请填写推文标题并选择城市'); return }
  noteSaving.value = true
  try {
    await api.updateNote(noteForm.id, {
      title: noteForm.title.trim(),
      content: noteForm.content,
      city_code: noteForm.city_code,
      published_at: noteForm.published_at ? new Date(noteForm.published_at).toISOString() : null,
    })
    noteEditDialog.value = false
    await load()
    if (noteEditFromDetail.value) await show(noteForm.id)
    ElMessage.success('推文已更新')
  } catch { ElMessage.error('推文更新失败，请重试') }
  finally { noteSaving.value = false }
}
async function reviewNote(note: any, target: 'APPROVED' | 'REJECTED', fromDetail = false) {
  const action = target === 'APPROVED' ? '通过' : '驳回'
  try {
    await ElMessageBox.confirm(`确认${action}这篇推文？`, '单篇审核确认', { type: 'warning' })
    await api.reviewNote(note.id, target)
    await load()
    if (fromDetail) await show(note.id)
    ElMessage.success(`推文已${action}`)
  } catch (error) {
    if (error === 'cancel' || error === 'close') return
    ElMessage.error('审核失败，请重试')
  }
}
onMounted(initialize)
onUnmounted(releaseImages)
</script>

<template>
  <ElCard shadow="never" class="page-card">
    <div class="toolbar filters-toolbar">
      <ElSelect v-model="filters.city" placeholder="城市" clearable class="filter-item"><ElOption v-for="city in cities" :key="city.code" :label="city.name" :value="city.code" /></ElSelect>
      <ElRadioGroup :model-value="filters.keyword_mode" @change="(v: any) => setKeywordMode(v)" class="filter-mode">
        <ElRadioButton value="custom">自定义关键词</ElRadioButton>
        <ElRadioButton value="groups">关键词组</ElRadioButton>
      </ElRadioGroup>
      <ElInput v-if="filters.keyword_mode === 'custom'" v-model="filters.keyword" placeholder="搜索推文标题或正文" clearable class="filter-item" aria-label="关键字" @keyup.enter="applyFilters" />
      <ElSelect v-else v-model="filters.keyword_group_ids" multiple collapse-tags collapse-tags-tooltip placeholder="选择 1 个或多个关键词组" class="filter-item" @change="applyFilters"><ElOption v-for="g in keywordGroups" :key="g.id" :label="g.name" :value="g.id" /></ElSelect>
      <ElRadioGroup :model-value="filters.blogger_mode" @change="(v: any) => setBloggerMode(v)" class="filter-mode">
        <ElRadioButton value="list">博主列表</ElRadioButton>
        <ElRadioButton value="groups">博主组</ElRadioButton>
      </ElRadioGroup>
      <ElSelect v-if="filters.blogger_mode === 'list'" v-model="filters.blogger_id" placeholder="博主" clearable filterable class="filter-item" @change="applyFilters"><ElOption v-for="blogger in bloggerFilteredByCity" :key="blogger.id" :label="blogger.username" :value="blogger.id" /></ElSelect>
      <ElSelect v-else v-model="filters.blogger_group_ids" multiple collapse-tags collapse-tags-tooltip placeholder="选择 1 个或多个博主组" class="filter-item" @change="applyFilters"><ElOption v-for="g in bloggerGroups" :key="g.id" :label="g.name" :value="g.id" /></ElSelect>
      <ElDatePicker v-model="filters.dates" type="daterange" value-format="YYYY-MM-DD" range-separator="至" start-placeholder="推文开始日期" end-placeholder="推文结束日期" aria-label="发布时间" />
      <ElSelect v-model="filters.review_status" placeholder="审核状态" clearable class="filter-item"><ElOption label="待审核" value="PENDING" /><ElOption label="已通过" value="APPROVED" /><ElOption label="已驳回" value="REJECTED" /></ElSelect>
      <ElButton :icon="Search" @click="applyFilters">筛选</ElButton><ElButton :icon="Refresh" @click="resetFilters">重置</ElButton>
      <ElButton type="success" :icon="CircleCheck" :disabled="!selectedRows.length" :loading="batchApproving" @click="batchApprove">批量通过</ElButton>
      <ElButton type="danger" :icon="Delete" :disabled="!selectedRows.length" :loading="batchDeleting" @click="batchRemove">批量删除</ElButton>
    </div>
    <ElTable :data="rows" @selection-change="selectedRows = $event">
      <ElTableColumn type="selection" width="48" /><ElTableColumn prop="title" label="推文标题" min-width="260" show-overflow-tooltip />
      <ElTableColumn label="城市" width="110"><template #default="scope">{{ cityNames[scope.row.city_code] || scope.row.city_code }}</template></ElTableColumn>
      <ElTableColumn label="发布时间" width="190"><template #default="scope">{{ formatDate(scope.row.published_at) }}</template></ElTableColumn>
      <ElTableColumn prop="activity_count" label="识别活动" width="110" />
      <ElTableColumn label="点赞/收藏/评论" width="170"><template #default="scope">{{ formatEngagement(scope.row) }}</template></ElTableColumn>
      <ElTableColumn label="审核状态" width="110"><template #default="scope"><ElTag :type="statusTypes[scope.row.review_status] as any">{{ statusLabels[scope.row.review_status] || scope.row.review_status }}</ElTag></template></ElTableColumn>
      <ElTableColumn label="操作" min-width="330"><template #default="scope"><div class="row-actions"><ElButton text :icon="View" @click="show(scope.row.id)">详情</ElButton><ElButton text :icon="Edit" @click="openNoteEdit(scope.row)">编辑推文</ElButton><ElButton v-if="scope.row.review_status !== 'APPROVED'" text type="success" :icon="CircleCheck" @click="reviewNote(scope.row, 'APPROVED')">通过</ElButton><ElButton v-if="scope.row.review_status !== 'REJECTED'" text type="danger" :icon="CircleClose" @click="reviewNote(scope.row, 'REJECTED')">驳回</ElButton></div></template></ElTableColumn>
    </ElTable>
    <ElPagination v-model:current-page="filters.page" v-model:page-size="filters.page_size" :page-sizes="[10,20,50,100]" :total="total" layout="total, sizes, prev, pager, next, jumper" @current-change="load" @size-change="filters.page=1;load()" />
  </ElCard>
  <ElDrawer v-model="drawer" title="推文详情" :size="detailDrawerSize" @closed="releaseImages">
    <div class="detail-actions"><ElButton :icon="Edit" @click="openNoteEdit(detail, true)">编辑推文</ElButton><ElButton v-if="detail.review_status !== 'APPROVED'" type="success" :icon="CircleCheck" @click="reviewNote(detail, 'APPROVED', true)">通过</ElButton><ElButton v-if="detail.review_status !== 'REJECTED'" type="danger" :icon="CircleClose" @click="reviewNote(detail, 'REJECTED', true)">驳回</ElButton></div>
    <ElDescriptions :column="1" border><ElDescriptionsItem label="标题">{{ detail.title }}</ElDescriptionsItem><ElDescriptionsItem label="审核状态"><ElTag :type="statusTypes[detail.review_status] as any">{{ statusLabels[detail.review_status] || detail.review_status }}</ElTag></ElDescriptionsItem><ElDescriptionsItem label="正文">{{ detail.content || '-' }}</ElDescriptionsItem><ElDescriptionsItem label="原文"><ElLink :href="detail.source_url" target="_blank" type="primary">查看小红书原文</ElLink></ElDescriptionsItem></ElDescriptions>
    <h3>识别活动</h3>
    <ElTable :data="detail.activities || []">
      <ElTableColumn prop="name" label="名称" min-width="160" />
      <ElTableColumn prop="location" label="地点" min-width="140" />
      <ElTableColumn label="开始时间" min-width="160" show-overflow-tooltip><template #default="scope">{{ formatTime(scope.row.start_time) }}</template></ElTableColumn>
      <ElTableColumn label="结束时间" min-width="160" show-overflow-tooltip><template #default="scope">{{ scope.row.end_time ? formatTime(scope.row.end_time) : '-' }}</template></ElTableColumn>
      <ElTableColumn label="操作" width="150"><template #default="scope"><ElButton text :icon="Edit" @click="openEdit(scope.row)">编辑</ElButton><ElButton text type="danger" @click="removeActivity(scope.row)">删除</ElButton></template></ElTableColumn>
    </ElTable>
    <section class="source-images"><h3>来源页面图片</h3><ElSkeleton v-if="imagesLoading" :rows="4" animated /><div v-else-if="imageUrls.length" class="source-image-grid"><ElImage v-for="(url,index) in imageUrls" :key="url" :src="url" :preview-src-list="imageUrls" :initial-index="index" fit="cover" lazy /></div><ElEmpty v-else description="暂无来源图片" /></section>
  </ElDrawer>
  <ElDialog v-model="noteEditDialog" title="编辑推文" width="680px">
    <ElForm label-width="90px">
      <ElFormItem label="推文标题" required><ElInput v-model="noteForm.title" aria-label="推文标题" maxlength="512" /></ElFormItem>
      <ElFormItem label="推文正文"><ElInput v-model="noteForm.content" aria-label="推文正文" type="textarea" :rows="6" /></ElFormItem>
      <ElFormItem label="城市" required><ElSelect v-model="noteForm.city_code" aria-label="城市"><ElOption v-for="city in cities" :key="city.code" :label="city.name" :value="city.code" /></ElSelect></ElFormItem>
      <ElFormItem label="发布时间"><ElDatePicker v-model="noteForm.published_at" aria-label="发布时间" type="datetime" placeholder="待确认" /></ElFormItem>
      <ElFormItem label="原文链接"><ElInput v-model="noteForm.source_url" aria-label="原文链接" disabled /></ElFormItem>
    </ElForm>
    <ElDivider />
    <h4 style="margin: 0 0 12px">识别活动</h4>
    <ElTable v-if="noteActivities.length" :data="noteActivities" size="small">
      <ElTableColumn prop="name" label="名称" min-width="140" />
      <ElTableColumn prop="location" label="地点" min-width="120" />
      <ElTableColumn label="开始时间" min-width="150"><template #default="scope">{{ formatTime(scope.row.start_time) }}</template></ElTableColumn>
      <ElTableColumn label="结束时间" min-width="150"><template #default="scope">{{ scope.row.end_time ? formatTime(scope.row.end_time) : '-' }}</template></ElTableColumn>
      <ElTableColumn label="操作" width="150"><template #default="scope"><ElButton text :icon="Edit" @click="openEdit(scope.row)">编辑</ElButton><ElButton text type="danger" @click="removeEditActivity(scope.row)">删除</ElButton></template></ElTableColumn>
    </ElTable>
    <ElEmpty v-else description="暂无识别活动">
      <ElButton :loading="reExtracting" @click="reExtractNote">重新提取</ElButton>
    </ElEmpty>
    <ElButton type="primary" style="margin-top: 12px" @click="openAddActivity">+ 手动添加活动</ElButton>
    <template #footer><ElButton @click="noteEditDialog=false">取消</ElButton><ElButton type="primary" :loading="noteSaving" @click="saveNote">保存推文</ElButton></template>
  </ElDialog>
  <ElDialog v-model="editDialog" title="编辑识别活动" width="680"><ElForm label-width="90px"><ElFormItem label="名称"><ElInput v-model="form.name" aria-label="活动名称" /></ElFormItem><ElFormItem label="地点"><ElInput v-model="form.location" aria-label="活动地点" /></ElFormItem><ElFormItem label="摘要"><ElInput v-model="form.summary" aria-label="活动摘要" type="textarea" /></ElFormItem></ElForm><template #footer><ElButton @click="editDialog=false">取消</ElButton><ElButton type="primary" @click="saveActivity">保存</ElButton></template></ElDialog>
  <ElDialog v-model="addActivityDialog" title="手动添加活动" width="520px">
    <ElForm label-width="90px">
      <ElFormItem label="活动名称" required><ElInput v-model="newActivityForm.name" aria-label="新活动名称" maxlength="256" /></ElFormItem>
      <ElFormItem label="地点"><ElInput v-model="newActivityForm.location" aria-label="新活动地点" maxlength="256" /></ElFormItem>
      <ElFormItem label="开始时间"><ElDatePicker v-model="newActivityForm.start_time" aria-label="新活动开始时间" type="datetime" placeholder="待确认" /></ElFormItem>
      <ElFormItem label="结束时间"><ElDatePicker v-model="newActivityForm.end_time" aria-label="新活动结束时间" type="datetime" placeholder="待确认" /></ElFormItem>
      <ElFormItem label="类型" required><ElSelect v-model="newActivityForm.type" aria-label="新活动类型"><ElOption label="展览" value="展览" /><ElOption label="市集" value="市集" /><ElOption label="演出" value="演出" /><ElOption label="赛事" value="赛事" /><ElOption label="讲座" value="讲座" /><ElOption label="工作坊" value="工作坊" /><ElOption label="亲子" value="亲子" /><ElOption label="户外" value="户外" /><ElOption label="美食" value="美食" /><ElOption label="其他" value="其他" /></ElSelect></ElFormItem>
      <ElFormItem label="简介"><ElInput v-model="newActivityForm.summary" aria-label="新活动简介" type="textarea" :rows="3" maxlength="2000" /></ElFormItem>
    </ElForm>
    <template #footer><ElButton @click="addActivityDialog=false">取消</ElButton><ElButton type="primary" :loading="addActivitySaving" @click="saveNewActivity">保存</ElButton></template>
  </ElDialog>
</template>

<style scoped>
.filters-toolbar{flex-wrap:wrap}.filter-item{width:180px}.filter-mode{margin-right:0}.row-actions{display:flex;align-items:center;white-space:nowrap}.detail-actions{display:flex;justify-content:flex-end;gap:8px;margin-bottom:16px}.source-images{margin-top:24px}.source-image-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(180px,1fr));gap:14px}.source-image-grid :deep(.el-image){width:100%;height:220px;border-radius:var(--el-border-radius-base);background:var(--el-fill-color-light)}
</style>
