<script setup lang="ts">
import { Delete, Edit } from '@element-plus/icons-vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import { usePagination } from '@/composables/usePagination'

const rows = ref<any[]>([])
const selectedIds = ref<number[]>([])
const {
  page: rowsPage,
  size: rowsSize,
  sizeOptions: rowsSizeOptions,
  total: rowsTotal,
  pagedRows,
  onSizeChange: onRowsSizeChange,
  onPageChange: onRowsPageChange,
} = usePagination(() => rows.value, { defaultSize: 20 })
const bloggers = ref<any[]>([])
const dialog = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<any>({ name: '', description: '', blogger_ids: [], enabled: true })

async function load() {
  const [groupsResp, bloggersResp] = await Promise.all([api.bloggerGroups(), api.settings('bloggers')])
  rows.value = groupsResp.data.data.items || []
  bloggers.value = bloggersResp.data.data || []
}

function resetForm() {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, { name: '', description: '', blogger_ids: [], enabled: true })
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
    description: row.description || '',
    blogger_ids: [...(row.blogger_ids || [])],
    enabled: row.enabled,
  })
  dialog.value = true
}

async function save() {
  if (!form.name?.trim()) {
    ElMessage.warning('请填写博主组名称')
    return
  }
  if (editingId.value) {
    await api.updateBloggerGroupMembers(editingId.value, form.blogger_ids)
    ElMessage.success('已更新')
  } else {
    await api.createBloggerGroup({
      name: form.name.trim(),
      description: form.description?.trim() || null,
      blogger_ids: form.blogger_ids,
      enabled: form.enabled,
    })
    ElMessage.success('已创建')
  }
  dialog.value = false
  await load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`确认删除博主组 "${row.name}"？`, '删除确认', { type: 'warning' })
  await api.deleteBloggerGroup(row.id)
  ElMessage.success('已删除')
  await load()
}

async function batchRemove() {
  if (selectedIds.value.length === 0) return
  await ElMessageBox.confirm(
    `确认批量删除选中的 ${selectedIds.value.length} 个博主组？此操作不可撤销。`,
    '批量删除',
    { type: 'warning' },
  )
  try {
    await api.batchDeleteBloggerGroups(selectedIds.value)
    ElMessage.success(`已批量删除 ${selectedIds.value.length} 个博主组`)
    selectedIds.value = []
    await load()
  } catch (error: any) {
    const reason = error.response?.data?.message || error.response?.data?.detail || '批量删除失败'
    ElMessage.error(reason)
  }
}

function bloggerName(id: number) {
  return bloggers.value.find((b: any) => b.id === id)?.username || `#${id}`
}

onMounted(load)
</script>

<template>
  <div class="blogger-group-settings">
    <div class="toolbar">
      <ElButton type="primary" :icon="Edit" @click="openCreate">新增博主组</ElButton>
      <ElButton type="danger" :disabled="selectedIds.length === 0" @click="batchRemove">批量删除 ({{ selectedIds.length }})</ElButton>
    </div>

    <ElTable :data="pagedRows" @selection-change="(rows: any[]) => (selectedIds = rows.map((r: any) => r.id))">
      <ElTableColumn type="selection" width="50" />
      <ElTableColumn prop="name" label="名称" min-width="160" />
      <ElTableColumn prop="description" label="说明" min-width="220" show-overflow-tooltip />
      <ElTableColumn label="成员博主" min-width="240">
        <template #default="scope">
          <template v-if="(scope.row.blogger_ids || []).length">
            <ElTag v-for="id in scope.row.blogger_ids" :key="id" class="member-tag">{{ bloggerName(id) }}</ElTag>
          </template>
          <span v-else>空组</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="状态" width="100">
        <template #default="scope">
          <ElTag :type="scope.row.enabled ? 'success' : 'info'">{{ scope.row.enabled ? '启用' : '停用' }}</ElTag>
        </template>
      </ElTableColumn>
      <ElTableColumn label="操作" min-width="200" class-name="action-column">
        <template #default="scope">
          <ElButton text type="primary" :icon="Edit" @click="openEdit(scope.row)">编辑</ElButton>
          <ElButton text type="danger" :icon="Delete" @click="remove(scope.row)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>
    <ElPagination
      v-if="rowsTotal > 0"
      class="pagination-bar"
      :page-size="rowsSize"
      :current-page="rowsPage"
      :page-sizes="rowsSizeOptions"
      :total="rowsTotal"
      layout="total, sizes, prev, pager, next, jumper"
      @size-change="onRowsSizeChange"
      @current-change="onRowsPageChange"
    />

    <ElDialog v-model="dialog" :title="editingId ? '编辑博主组' : '新增博主组'" width="640">
      <ElForm label-width="90px">
        <ElFormItem label="名称">
          <ElInput v-model="form.name" :disabled="!!editingId" placeholder="例如：本地活动号" aria-label="博主组名称" />
        </ElFormItem>
        <ElFormItem label="说明">
          <ElInput v-model="form.description" placeholder="可选" aria-label="说明" />
        </ElFormItem>
        <ElFormItem label="成员博主">
          <ElSelect v-model="form.blogger_ids" multiple collapse-tags collapse-tags-tooltip placeholder="选择博主" style="width: 100%">
            <ElOption v-for="blogger in bloggers" :key="blogger.id" :label="blogger.username" :value="blogger.id" />
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
  </div>
</template>

<style scoped>
.blogger-group-settings { padding-top: 16px; }
.toolbar { margin-bottom: 16px; display: flex; gap: 8px; }
.member-tag { margin: 3px 6px 3px 0; }
</style>
