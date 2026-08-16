<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Refresh } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface PlatformMeta {
  id: string
  display_name: string
  icon: string
  status: string
}
interface Account {
  id: number
  name: string
  platform: string
  session_name: string
  platform_user_id: string | null
  cdp_port: number | null
  login_status: string
  last_login_check_at: string | null
  enabled: boolean
  priority: number
  daily_quota_seconds: number
  created_at: string
  updated_at: string
}

const LOGIN_META: Record<string, { text: string; cls: string }> = {
  logged_in: { text: '已登录', cls: 'md-badge--success' },
  logged_out: { text: '未登录', cls: 'md-badge--error' },
  expired: { text: '已过期', cls: 'md-badge--warning' },
  unknown: { text: '未知', cls: 'md-badge--info' },
}

const platforms = ref<PlatformMeta[]>([])
const accounts = ref<Account[]>([])
const loading = ref(false)
const platformFilter = ref('')
const statusFilter = ref('')
const search = ref('')

const filtered = computed(() => {
  let list = accounts.value
  if (platformFilter.value) list = list.filter(a => a.platform === platformFilter.value)
  if (statusFilter.value) list = list.filter(a => a.login_status === statusFilter.value)
  if (search.value) list = list.filter(a => a.name.includes(search.value))
  return list
})

function platformIcon(platform: string): string {
  return platforms.value.find(p => p.id === platform)?.icon || platform
}

const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  name: '',
  platform: 'xhs',
  enabled: true,
  priority: 0,
  daily_quota_seconds: 14400,
})

const nurtureVisible = ref(false)
const nurtureTarget = ref<Account | null>(null)
const nurtureForm = reactive({
  actions: ['browse_home', 'fetch_favorites'] as string[],
  duration_minutes: 30,
})
const ACTION_OPTIONS = [
  { value: 'browse_home', label: '浏览首页' },
  { value: 'like_post', label: '点赞帖子' },
  { value: 'favorite_post', label: '收藏帖子' },
  { value: 'fetch_favorites', label: '抓取收藏夹' },
]

async function loadPlatforms() {
  const res = await api.platforms()
  platforms.value = res.data as PlatformMeta[]
}

async function loadAccounts() {
  loading.value = true
  try {
    const res = await api.platformAccounts()
    accounts.value = res.data as Account[]
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { name: '', platform: 'xhs', enabled: true, priority: 0, daily_quota_seconds: 14400 })
  dialogVisible.value = true
}
function openEdit(a: Account) {
  editingId.value = a.id
  Object.assign(form, {
    name: a.name,
    platform: a.platform,
    enabled: a.enabled,
    priority: a.priority,
    daily_quota_seconds: a.daily_quota_seconds,
  })
  dialogVisible.value = true
}
async function save() {
  try {
    if (editingId.value) {
      await api.updatePlatformAccount(editingId.value, { ...form })
    } else {
      await api.createPlatformAccount({ ...form })
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    loadAccounts()
  } catch {
    ElMessage.error('保存失败')
  }
}
async function remove(a: Account) {
  await ElMessageBox.confirm(`确认删除账号「${a.name}」？该账号的所有收藏快照将一并删除。`, '删除确认', {
    type: 'warning',
  })
  await api.deletePlatformAccount(a.id)
  ElMessage.success('已删除')
  loadAccounts()
}
async function checkLogin(a: Account) {
  try {
    const res = await api.checkPlatformAccountLogin(a.id)
    const r = res.data as { logged_in: boolean; error?: string }
    ElMessage.success(r.logged_in ? '登录有效' : '未登录')
    loadAccounts()
  } catch {
    ElMessage.error('检查失败')
  }
}
function openNurture(a: Account) {
  nurtureTarget.value = a
  Object.assign(nurtureForm, { actions: ['browse_home', 'fetch_favorites'], duration_minutes: 30 })
  nurtureVisible.value = true
}
async function startNurture() {
  if (!nurtureTarget.value) return
  try {
    const res = await api.nurturePlatformAccount(nurtureTarget.value.id, {
      actions: nurtureForm.actions,
      duration_minutes: nurtureForm.duration_minutes,
    })
    ElMessage.success(`养号任务已入队 #${(res.data as { task_id: string }).task_id}`)
    nurtureVisible.value = false
  } catch {
    ElMessage.error('发起失败')
  }
}

onMounted(() => {
  loadPlatforms()
  loadAccounts()
})
</script>

<template>
  <div class="accounts-page">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">账号列表</h2>
      <ElButton type="primary" :icon="Plus" @click="openCreate">新建账号</ElButton>
    </div>

    <div class="filter-bar">
      <ElInput v-model="search" placeholder="搜索账号名" clearable class="filter-search" data-test="search" />
      <ElSelect v-model="platformFilter" placeholder="平台" clearable class="filter-select" data-test="platform-filter">
        <ElOption v-for="p in platforms" :key="p.id" :label="`${p.icon} ${p.display_name}`" :value="p.id" />
      </ElSelect>
      <ElSelect v-model="statusFilter" placeholder="登录态" clearable class="filter-select" data-test="status-filter">
        <ElOption label="已登录" value="logged_in" />
        <ElOption label="未登录" value="logged_out" />
        <ElOption label="已过期" value="expired" />
        <ElOption label="未知" value="unknown" />
      </ElSelect>
      <ElButton :icon="Refresh" circle @click="loadAccounts" data-test="refresh" />
    </div>

    <ElTable :data="filtered" v-loading="loading" class="accounts-table" data-test="accounts-table">
      <ElTableColumn prop="id" label="ID" width="70" />
      <ElTableColumn prop="name" label="名称" min-width="140" />
      <ElTableColumn label="平台" width="110">
        <template #default="{ row }">
          <span>{{ platformIcon(row.platform) }} {{ row.platform }}</span>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="session_name" label="会话名" min-width="140" />
      <ElTableColumn label="登录态" width="120">
        <template #default="{ row }">
          <span :class="['md-badge', LOGIN_META[row.login_status]?.cls || 'md-badge--info']">
            {{ LOGIN_META[row.login_status]?.text || row.login_status }}
          </span>
        </template>
      </ElTableColumn>
      <ElTableColumn prop="priority" label="优先级" width="90" />
      <ElTableColumn label="启用" width="90">
        <template #default="{ row }">
          <ElTag :type="row.enabled ? 'success' : 'info'" effect="plain">{{ row.enabled ? '是' : '否' }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <div class="table-actions">
            <ElButton size="small" @click="checkLogin(row)">检查登录</ElButton>
            <ElButton size="small" type="primary" plain @click="openNurture(row)">养号</ElButton>
            <ElButton size="small" plain @click="openEdit(row)">编辑</ElButton>
            <ElButton size="small" type="danger" plain @click="remove(row)">删除</ElButton>
          </div>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog v-model="dialogVisible" :title="editingId ? '编辑账号' : '新建账号'" width="480px">
      <ElForm label-width="120px">
        <ElFormItem label="名称">
          <ElInput v-model="form.name" data-test="form-name" />
        </ElFormItem>
        <ElFormItem label="平台">
          <ElSelect v-model="form.platform" :disabled="!!editingId" style="width: 100%">
            <ElOption v-for="p in platforms" :key="p.id" :label="`${p.icon} ${p.display_name}`" :value="p.id" />
          </ElSelect>
        </ElFormItem>
        <ElFormItem label="优先级">
          <ElSlider v-model="form.priority" :max="100" />
        </ElFormItem>
        <ElFormItem label="单日时长(秒)">
          <ElInputNumber v-model="form.daily_quota_seconds" :min="600" :max="28800" :step="600" />
        </ElFormItem>
        <ElFormItem label="启用">
          <ElSwitch v-model="form.enabled" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="save" data-test="save">保存</ElButton>
      </template>
    </ElDialog>

    <ElDialog v-model="nurtureVisible" title="发起养号" width="480px">
      <ElForm label-width="120px">
        <ElFormItem label="动作">
          <ElCheckboxGroup v-model="nurtureForm.actions">
            <ElCheckbox v-for="o in ACTION_OPTIONS" :key="o.value" :value="o.value">{{ o.label }}</ElCheckbox>
          </ElCheckboxGroup>
        </ElFormItem>
        <ElFormItem label="时长(分钟)">
          <ElInputNumber v-model="nurtureForm.duration_minutes" :min="5" :max="240" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="nurtureVisible = false">取消</ElButton>
        <ElButton type="primary" @click="startNurture" data-test="start-nurture">启动</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.accounts-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.filter-bar {
  display: flex;
  gap: var(--md-sys-spacing-3);
  margin-bottom: var(--md-sys-spacing-4);
}
.filter-search { width: 220px; }
.filter-select { width: 160px; }
</style>