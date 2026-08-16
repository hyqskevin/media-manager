<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CopyDocument, Delete, Plus, Refresh } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface ActionSet {
  id: number
  platform: string
  name: string
  duration_minutes: number
  actions: string[]
  actions_order: number[]
  created_at: string
  updated_at: string
}

const items = ref<ActionSet[]>([])
const loading = ref(false)
const dialogVisible = ref(false)
const editingId = ref<number | null>(null)
const form = reactive({
  platform: 'xhs',
  name: '',
  duration_minutes: 30,
  actions: ['browse_home'] as string[],
})
const ACTION_OPTIONS = [
  { value: 'browse_home', label: '浏览首页' },
  { value: 'like_post', label: '点赞帖子' },
  { value: 'favorite_post', label: '收藏帖子' },
  { value: 'fetch_favorites', label: '抓取收藏夹' },
]

async function load() {
  loading.value = true
  try {
    const res = await api.actionSets({})
    const data = res.data as { total: number; items: ActionSet[] }
    items.value = data.items ?? (res.data as ActionSet[])
  } finally {
    loading.value = false
  }
}

function openCreate() {
  editingId.value = null
  Object.assign(form, { platform: 'xhs', name: '', duration_minutes: 30, actions: ['browse_home'] })
  dialogVisible.value = true
}
function openEdit(s: ActionSet) {
  editingId.value = s.id
  Object.assign(form, { platform: s.platform, name: s.name, duration_minutes: s.duration_minutes, actions: [...s.actions] })
  dialogVisible.value = true
}
async function save() {
  try {
    if (editingId.value) {
      await api.updateActionSet(editingId.value, { ...form })
    } else {
      await api.createActionSet({ ...form })
    }
    ElMessage.success('已保存')
    dialogVisible.value = false
    load()
  } catch {
    ElMessage.error('保存失败')
  }
}
async function clone(s: ActionSet) {
  await api.cloneActionSet(s.id)
  ElMessage.success('已克隆')
  load()
}
async function remove(s: ActionSet) {
  await ElMessageBox.confirm(`确认删除动作集「${s.name}」？`, '删除确认', { type: 'warning' })
  await api.deleteActionSet(s.id)
  ElMessage.success('已删除')
  load()
}

onMounted(load)
</script>

<template>
  <div class="sets-page">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">动作集</h2>
      <div class="header-actions">
        <ElButton type="primary" :icon="Plus" @click="openCreate" data-test="new">新建</ElButton>
        <ElButton type="primary" plain :icon="Refresh" @click="load">刷新</ElButton>
      </div>
    </div>

    <div v-loading="loading" class="set-grid">
      <ElCard v-for="s in items" :key="s.id" shadow="hover" class="set-card" data-test="set-card">
        <template #header>
          <span class="md-typescale-title-medium">{{ s.name }}</span>
        </template>
        <p class="meta">平台：{{ s.platform }} · 时长 {{ s.duration_minutes }} 分</p>
        <div class="action-tags">
          <ElTag v-for="a in s.actions" :key="a" effect="plain">{{ a }}</ElTag>
        </div>
        <div class="card-actions">
          <ElButton size="small" plain :icon="CopyDocument" @click="clone(s)" data-test="clone">克隆</ElButton>
          <ElButton size="small" plain @click="openEdit(s)" data-test="edit">编辑</ElButton>
          <ElButton size="small" type="danger" plain :icon="Delete" @click="remove(s)" data-test="delete">删除</ElButton>
        </div>
      </ElCard>
      <ElEmpty v-if="!loading && items.length === 0" description="暂无动作集" />
    </div>

    <ElDialog v-model="dialogVisible" :title="editingId ? '编辑动作集' : '新建动作集'" width="520px">
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
.sets-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.header-actions { display: flex; gap: var(--md-sys-spacing-3); }
.set-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(260px, 1fr));
  gap: var(--md-sys-spacing-4);
}
.meta { margin: 0 0 var(--md-sys-spacing-2); color: var(--md-sys-color-on-surface-variant); }
.action-tags { display: flex; flex-wrap: wrap; gap: var(--md-sys-spacing-2); margin-bottom: var(--md-sys-spacing-4); }
.card-actions { display: flex; gap: var(--md-sys-spacing-2); }
</style>