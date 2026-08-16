<script setup lang="ts">
import { Delete, Edit, Plus } from '@element-plus/icons-vue'
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { useRoute } from 'vue-router'
import { api } from '@/api/client'

const route = useRoute()
const tab = ref<'schedules' | 'batch'>((route.query.tab as any) || 'schedules')
watch(() => route.query.tab, (newTab) => {
  if (newTab) {
    tab.value = newTab as any
    load()
  }
})
const batchConfig = ref<Record<string, any>>({})
const batchLoading = ref(false)
const batchSaving = ref(false)
const rows = ref<any[]>([])
const cities = ref<any[]>([])
const keywordGroups = ref<any[]>([])
const bloggerGroups = ref<any[]>([])
const dialog = ref(false)
const editingId = ref<number | null>(null)
const recentFilters = ['不限', '当天', '一天内', '一周内', '半年内']
// 后端约定：day_of_week == 8 表示"每天触发"（dispatch 时跳过星期匹配）
const weekdays = [
  { value: 1, label: '周一' }, { value: 2, label: '周二' }, { value: 3, label: '周三' },
  { value: 4, label: '周四' }, { value: 5, label: '周五' }, { value: 6, label: '周六' }, { value: 7, label: '周日' },
  { value: 8, label: '每天' },
]
const form = reactive<any>({})

function resetForm() {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, {
    name: '', day_of_week: 1, time: '09:00', city_code: '',
    keyword_group_ids: [], blogger_group_ids: [], recent_filter: null, enabled: true,
  })
}

async function load() {
  if (tab.value === 'batch') {
    await loadBatchConfig()
    return
  }
  const [schedulesResp, citiesResp, kgResp, bgResp] = await Promise.all([
    api.schedules(), api.settings('cities'), api.keywordGroups(), api.bloggerGroups(),
  ])
  rows.value = schedulesResp.data.data.items || []
  cities.value = citiesResp.data.data || []
  keywordGroups.value = kgResp.data.data.items || []
  bloggerGroups.value = bgResp.data.data.items || []
}

function openCreate() {
  editingId.value = null
  resetForm()
  dialog.value = true
}

function openEdit(row: any) {
  editingId.value = row.id
  resetForm()
  Object.assign(form, {
    name: row.name,
    day_of_week: row.day_of_week,
    time: `${pad(row.hour)}:${pad(row.minute)}`,
    city_code: row.city_code,
    keyword_group_ids: [...(row.keyword_group_ids || [])],
    blogger_group_ids: [...(row.blogger_group_ids || [])],
    recent_filter: row.recent_filter,
    enabled: row.enabled,
  })
  dialog.value = true
}

async function save() {
  if (!form.name?.trim()) {
    ElMessage.warning('请填写定时任务名称')
    return
  }
  if (!form.city_code) {
    ElMessage.warning('请选择抓取城市')
    return
  }
  if (!form.keyword_group_ids?.length && !form.blogger_group_ids?.length) {
    ElMessage.warning('请至少选择一个关键词组或博主组')
    return
  }
  const timeText = typeof form.time === 'string' ? form.time : '09:00'
  const [hour, minute] = timeText.split(':').map((part: string) => Number(part) || 0)
  const payload = {
    name: form.name.trim(),
    day_of_week: form.day_of_week,
    hour,
    minute,
    city_code: form.city_code,
    keyword_group_ids: form.keyword_group_ids,
    blogger_group_ids: form.blogger_group_ids,
    recent_filter: form.recent_filter || null,
    enabled: form.enabled,
  }
  if (editingId.value) {
    await api.updateSchedule(editingId.value, payload)
    ElMessage.success('已更新')
  } else {
    await api.createSchedule(payload)
    ElMessage.success('已创建')
  }
  dialog.value = false
  await load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`确认删除定时任务 "${row.name}"？`, '删除确认', { type: 'warning' })
  await api.deleteSchedule(row.id)
  ElMessage.success('已删除')
  await load()
}

const cityName = (code: string) => cities.value.find((c: any) => c.code === code)?.name || code
const keywordGroupName = (id: number) => keywordGroups.value.find((g: any) => g.id === id)?.name || `#${id}`
const bloggerGroupName = (id: number) => bloggerGroups.value.find((g: any) => g.id === id)?.name || `#${id}`
const weekdayLabel = (day: number) => weekdays.find((d) => d.value === day)?.label || `周${day}`
const pad = (n: number) => String(n).padStart(2, '0')

const statusMeta: Record<string, { type: string; label: string }> = {
  COMPLETED: { type: 'success', label: '成功' },
  COMPLETED_WITH_ERRORS: { type: 'warning', label: '部分成功' },
  FAILED: { type: 'danger', label: '失败' },
  RUNNING: { type: 'primary', label: '运行中' },
  PENDING: { type: 'info', label: '等待中' },
  PAUSED: { type: 'warning', label: '已暂停' },
  STOPPED: { type: 'info', label: '已停止' },
}
const lastTaskMeta = computed(() => (task: any) => statusMeta[task?.status] || { type: 'info', label: task?.status || '' })

async function loadBatchConfig() {
  batchLoading.value = true
  try {
    const res = await api.systemConfig()
    batchConfig.value = res.data.data || {}
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '加载抓取批次配置失败')
  } finally {
    batchLoading.value = false
  }
}

async function saveBatchConfig() {
  batchSaving.value = true
  try {
    await api.updateSystemConfig(batchConfig.value)
    ElMessage.success('抓取批次配置已保存，重启服务后生效')
    await loadBatchConfig()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.message || '保存失败')
  } finally {
    batchSaving.value = false
  }
}

onMounted(load)
</script>

<template>
  <ElCard shadow="never" class="page-card">
    <div class="toolbar">
      <ElButton v-if="tab === 'schedules'" type="primary" :icon="Plus" @click="openCreate">新增定时任务</ElButton>
    </div>

    <template v-if="tab === 'schedules'">
      <ElTable :data="rows">
        <ElTableColumn prop="name" label="名称" min-width="150" />
        <ElTableColumn label="周期" width="130">
          <template #default="scope">每{{ weekdayLabel(scope.row.day_of_week) }} {{ pad(scope.row.hour) }}:{{ pad(scope.row.minute) }}</template>
        </ElTableColumn>
        <ElTableColumn label="城市" width="100">
          <template #default="scope">{{ cityName(scope.row.city_code) }}</template>
        </ElTableColumn>
        <ElTableColumn label="关键词组" min-width="140">
          <template #default="scope">
            <template v-if="(scope.row.keyword_group_ids || []).length">
              <ElTag v-for="id in scope.row.keyword_group_ids" :key="id" class="group-tag">{{ keywordGroupName(id) }}</ElTag>
            </template>
            <span v-else>—</span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="博主组" min-width="140">
          <template #default="scope">
            <template v-if="(scope.row.blogger_group_ids || []).length">
              <ElTag v-for="id in scope.row.blogger_group_ids" :key="id" type="warning" class="group-tag">{{ bloggerGroupName(id) }}</ElTag>
            </template>
            <span v-else>—</span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="时间范围" width="110">
          <template #default="scope">{{ scope.row.recent_filter || '城市默认' }}</template>
        </ElTableColumn>
        <ElTableColumn label="状态" width="90">
          <template #default="scope">
            <ElTag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? '启用' : '停用' }}</ElTag>
          </template>
        </ElTableColumn>
        <ElTableColumn label="最近抓取" width="110">
          <template #default="scope">
            <ElTag v-if="scope.row.last_task" :type="lastTaskMeta(scope.row.last_task).type as any">
              {{ lastTaskMeta(scope.row.last_task).label }}
            </ElTag>
            <span v-else>未执行</span>
          </template>
        </ElTableColumn>
        <ElTableColumn label="操作" min-width="170" class-name="action-column">
          <template #default="scope">
            <ElButton text type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</ElButton>
            <ElButton text type="danger" :icon="Delete" @click="remove(scope.row)">删除</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </template>

    <ElCard v-if="tab === 'batch'" v-loading="batchLoading" shadow="never" class="config-card">
      <template #header>抓取批次配置 <span class="config-hint">修改后需重启服务生效</span></template>

      <ElForm label-width="180px" label-position="left">
        <div class="config-group">
          <h4 class="config-group-title">抓取数量</h4>
          <ElFormItem label="单次搜索上限">
            <ElInputNumber v-model="batchConfig.search_limit" :min="10" :max="500" :step="10" style="width: 100%" />
          </ElFormItem>
          <ElFormItem label="每周搜索上限">
            <ElInputNumber v-model="batchConfig.weekly_search_limit" :min="0" :max="5000" :step="50" style="width: 100%" />
          </ElFormItem>
          <ElFormItem label="连续失败熔断阈值">
            <ElInputNumber v-model="batchConfig.consecutive_note_failure_limit" :min="1" :max="20" :step="1" style="width: 100%" />
          </ElFormItem>
          <ElFormItem label="活动有效窗口（天）">
            <ElInputNumber v-model="batchConfig.activity_future_window_days" :min="7" :max="365" :step="7" style="width: 100%" />
          </ElFormItem>
        </div>

        <div class="config-group">
          <h4 class="config-group-title">小红书滚动策略</h4>
          <ElFormItem label="目标笔记数">
            <ElInputNumber v-model="batchConfig.xhs_search_target_count" :min="10" :max="200" :step="10" style="width: 100%" />
          </ElFormItem>
          <ElFormItem label="最大滚动轮数">
            <ElInputNumber v-model="batchConfig.xhs_search_scroll_max_rounds" :min="1" :max="30" :step="1" style="width: 100%" />
          </ElFormItem>
          <ElFormItem label="滚动像素">
            <ElInputNumber v-model="batchConfig.xhs_scroll_pixels" :min="200" :max="2000" :step="100" style="width: 100%" />
          </ElFormItem>
          <ElFormItem label="停滞轮数阈值">
            <ElInputNumber v-model="batchConfig.xhs_scroll_stagnant_rounds" :min="1" :max="10" :step="1" style="width: 100%" />
          </ElFormItem>
        </div>

        <ElFormItem>
          <ElButton type="primary" :loading="batchSaving" @click="saveBatchConfig">保存配置</ElButton>
          <ElButton @click="loadBatchConfig">重置</ElButton>
        </ElFormItem>
      </ElForm>
    </ElCard>

    <ElDialog v-model="dialog" :title="editingId ? '编辑定时任务' : '新增定时任务'" width="620">
      <ElForm label-width="100px">
        <ElFormItem label="名称">
          <ElInput v-model="form.name" placeholder="例如：每周一早上" aria-label="定时任务名称" />
        </ElFormItem>
        <ElFormItem label="每周">
          <ElSelect v-model="form.day_of_week" style="width: 100%">
            <ElOption v-for="day in weekdays" :key="day.value" :label="day.label" :value="day.value" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="时间">
          <ElTimePicker v-model="form.time" format="HH:mm" value-format="HH:mm" placeholder="选择时间" style="width: 100%" />
        </ElFormItem>
        <ElFormItem label="抓取城市">
          <ElSelect v-model="form.city_code" placeholder="选择城市" style="width: 100%">
            <ElOption v-for="city in cities" :key="city.code" :label="city.name" :value="city.code" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="关键词组">
          <ElSelect v-model="form.keyword_group_ids" multiple collapse-tags collapse-tags-tooltip placeholder="有关键词组则抓关键词" style="width: 100%">
            <ElOption v-for="group in keywordGroups" :key="group.id" :label="group.name" :value="group.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="博主组">
          <ElSelect v-model="form.blogger_group_ids" multiple collapse-tags collapse-tags-tooltip placeholder="有博主组则抓博主白名单" style="width: 100%">
            <ElOption v-for="group in bloggerGroups" :key="group.id" :label="group.name" :value="group.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="时间范围">
          <ElSelect v-model="form.recent_filter" clearable placeholder="默认使用城市配置" style="width: 100%">
            <ElOption v-for="item in recentFilters" :key="item" :label="item" :value="item" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="启用">
          <ElSwitch v-model="form.enabled" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialog = false">取消</ElButton>
        <ElButton type="primary" @click="save">保存</ElButton>
      </template>
    </ElDialog>
  </ElCard>
</template>

<style scoped>
.toolbar { margin-bottom: 16px; display: flex; gap: 12px; }
.group-tag { margin: 3px 6px 3px 0; }
.config-card { margin-top: 16px; }
.config-hint { font-size: 13px; color: #909399; font-weight: normal; margin-left: 8px; }
.config-group { margin-bottom: 8px; }
.config-group-title { font-size: 15px; font-weight: 600; color: #303133; margin: 0 0 12px 0; padding-bottom: 8px; border-bottom: 1px solid #ebeef5; }
</style>
