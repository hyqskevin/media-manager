<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh, VideoPlay } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface Schedule {
  id: number
  platform: string
  account_id: number
  name: string
  cron: string
  duration_minutes: number
  actions: string[]
  action_set_id: number | null
  enabled: boolean
  next_run_at: string | null
  created_at: string
  updated_at: string
}
interface Account {
  id: number
  name: string
  platform: string
}

const items = ref<Schedule[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)
const accounts = ref<Account[]>([])
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  platform: 'xhs',
  account_id: undefined as number | undefined,
  name: '',
  cron: '0 9 * * *',
  duration_minutes: 30,
  actions: ['browse_home'] as string[],
})
const ACTION_OPTIONS = [
  { value: 'browse_home', label: '浏览首页' },
  { value: 'like_post', label: '点赞帖子' },
  { value: 'favorite_post', label: '收藏帖子' },
  { value: 'fetch_favorites', label: '抓取收藏夹' },
]

defineExpose({ form })

async function loadAccounts() {
  const res = await api.platformAccounts()
  accounts.value = res.data as Account[]
}

async function load() {
  loading.value = true
  try {
    const res = await api.schedules({ page: page.value, page_size: pageSize.value })
    const data = res.data as { total: number; items: Schedule[] }
    items.value = data.items
    total.value = data.total
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { platform: 'xhs', account_id: undefined, name: '', cron: '0 9 * * *', duration_minutes: 30, actions: ['browse_home'] })
  dialogVisible.value = true
}
function openEdit(s: Schedule) {
  editingId.value = s.id
  Object.assign(form, {
    platform: s.platform,
    account_id: s.account_id,
    name: s.name,
    cron: s.cron,
    duration_minutes: s.duration_minutes,
    actions: [...s.actions],
  })
  dialogVisible.value = true
}
async function save() {
  if (!form.account_id) {
    ElMessage.warning('请选择账号')
    return
  }
  const payload = { ...form }
  try {
    if (editingId.value) {
      await api.updateSchedule(editingId.value, payload)
    } else {
      await api.createSchedule(payload)
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    load()
  } catch {
    ElMessage.error('保存失败')
  }
}
async function remove(s: Schedule) {
  await ElMessageBox.confirm(`确认删除定时任务「${s.name}」？`, '删除确认', { type: 'warning' })
  await api.deleteSchedule(s.id)
  ElMessage.success('已删除')
  load()
}
async function toggle(s: Schedule) {
  if (s.enabled) {
    await api.disableSchedule(s.id)
  } else {
    await api.enableSchedule(s.id)
  }
  ElMessage.success(s.enabled ? '已禁用' : '已启用')
  load()
}
async function trigger(s: Schedule) {
  try {
    const res = await api.triggerSchedule(s.id)
    ElMessage.success(`已触发，任务 #${(res.data as { task_id: string }).task_id}`)
  } catch {
    ElMessage.error('触发失败')
  }
}

onMounted(() => {
  loadAccounts()
  load()
})
</script>

<template>
  <div class="schedules-page">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">定时任务</h2>
      <div class="header-actions">
        <ElButton type="primary" :icon="Plus" @click="openCreate" data-test="new">新建</ElButton>
        <ElButton type="primary" plain :icon="Refresh" @click="load">刷新</ElButton>
      </div>
    </div>

    <ElTable :data="items" v-loading="loading">
      <ElTableColumn prop="id" label="ID" width="70" />
      <ElTableColumn prop="name" label="名称" min-width="140" />
      <ElTableColumn prop="platform" label="平台" width="100" />
      <ElTableColumn prop="account_id" label="账号ID" width="90" />
      <ElTableColumn prop="cron" label="Cron" width="130" />
      <ElTableColumn prop="duration_minutes" label="时长(分)" width="90" />
      <ElTableColumn label="动作" min-width="150">
        <template #default="{ row }">{{ (row.actions || []).join('、') }}</template>
      </ElTableColumn>
      <ElTableColumn label="启用" width="90">
        <template #default="{ row }">
          <ElTag :type="row.enabled ? 'success' : 'info'" effect="plain">{{ row.enabled ? '是' : '否' }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="280" fixed="right">
        <template #default="{ row }">
          <ElButton size="small" type="primary" plain @click="trigger(row)" data-test="trigger">立即执行</ElButton>
          <ElButton size="small" plain @click="openEdit(row)">编辑</ElButton>
          <ElButton size="small" @click="toggle(row)" data-test="toggle-enable">{{ row.enabled ? '禁用' : '启用' }}</ElButton>
          <ElButton size="small" type="danger" plain @click="remove(row)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <div class="pager">
      <ElPagination
        v-model:current-page="page"
        v-model:page-size="pageSize"
        :total="total"
        layout="total, sizes, prev, pager, next"
        @current-change="load"
        @size-change="load"
      />
    </div>

    <ElDialog v-model="dialogVisible" :title="editingId ? '编辑定时任务' : '新建定时任务'" width="520px">
      <ElForm label-width="120px">
        <ElFormItem label="名称">
          <ElInput v-model="form.name" data-test="form-name" />
        </ElFormItem>
        <ElFormItem label="平台">
          <ElSelect v-model="form.platform" style="width: 100%">
            <ElOption label="小红书" value="xhs" />
            <ElOption label="微博" value="weibo" />
            <ElOption label="抖音" value="douyin" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="账号">
          <ElSelect v-model="form.account_id" filterable style="width: 100%">
            <ElOption v-for="a in accounts" :key="a.id" :label="`#${a.id} ${a.name} (${a.platform})`" :value="a.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="Cron 表达式">
          <ElInput v-model="form.cron" placeholder="例如 0 9 * * *" />
        </ElFormItem>
        <ElFormItem label="时长(分钟)">
          <ElInputNumber v-model="form.duration_minutes" :min="5" :max="240" />
        </ElFormItem>
        <ElFormItem label="动作">
          <ElCheckboxGroup v-model="form.actions">
            <ElCheckbox v-for="o in ACTION_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</ElCheckbox>
          </ElCheckboxGroup>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="save" data-test="save">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.schedules-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.header-actions { display: flex; gap: var(--md-sys-spacing-3); }
.pager { display: flex; justify-content: flex-end; margin-top: var(--md-sys-spacing-4); }
</style>