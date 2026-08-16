<script setup lang="ts">
import { Delete, Edit } from '@element-plus/icons-vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'
import { usePagination } from '@/composables/usePagination'

const props = defineProps<{ cities: any[] }>()
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
const dialog = ref(false)
const editingId = ref<number | null>(null)
const form = reactive<any>({ name: '', description: '', city_codes: [], words: [], enabled: true })
const newWord = ref('')

async function load() {
  try {
    const resp = await api.keywordGroups()
    rows.value = resp.data.data.items || []
  } catch (error) {
    ElMessage.error('关键词组数据加载失败')
    rows.value = []
  }
}

function resetForm() {
  Object.keys(form).forEach((key) => delete form[key])
  Object.assign(form, { name: '', description: '', city_codes: [], words: [], enabled: true })
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
    city_codes: [...(row.city_codes || [])],
    words: [...(row.words || [])],
    enabled: row.enabled,
  })
  dialog.value = true
}

async function save() {
  if (!form.name?.trim()) {
    ElMessage.warning('请填写关键词组名称')
    return
  }
  if (editingId.value) {
    await api.patchKeywordGroup(editingId.value, {
      name: form.name.trim(),
      description: form.description?.trim() || null,
      enabled: form.enabled,
    })
    await api.updateKeywordGroupCities(editingId.value, form.city_codes)
    await api.updateKeywordGroupWords(editingId.value, form.words)
    ElMessage.success('已更新')
  } else {
    await api.createKeywordGroup({
      name: form.name.trim(),
      description: form.description?.trim() || null,
      city_codes: form.city_codes,
      words: form.words,
      enabled: form.enabled,
    })
    ElMessage.success('已创建')
  }
  dialog.value = false
  await load()
}

async function remove(row: any) {
  await ElMessageBox.confirm(`确认删除关键词组 "${row.name}"？`, '删除确认', { type: 'warning' })
  await api.deleteKeywordGroup(row.id)
  ElMessage.success('已删除')
  await load()
}

async function batchRemove() {
  if (selectedIds.value.length === 0) return
  await ElMessageBox.confirm(
    `确认批量删除选中的 ${selectedIds.value.length} 个关键词组？此操作不可撤销。`,
    '批量删除',
    { type: 'warning' },
  )
  try {
    await api.batchDeleteKeywordGroups(selectedIds.value)
    ElMessage.success(`已批量删除 ${selectedIds.value.length} 个关键词组`)
    selectedIds.value = []
    await load()
  } catch (error: any) {
    const reason = error.response?.data?.message || error.response?.data?.detail || '批量删除失败'
    ElMessage.error(reason)
  }
}

function addWordFromInput() {
  const w = newWord.value.trim()
  if (!w || form.words.includes(w)) {
    newWord.value = ''
    return
  }
  form.words.push(w)
  newWord.value = ''
}

function removeWord(value: string) {
  form.words = form.words.filter((w: string) => w !== value)
}

function addCity(code: string) {
  if (!code || form.city_codes.includes(code)) return
  form.city_codes.push(code)
}

function removeCity(code: string) {
  form.city_codes = form.city_codes.filter((c: string) => c !== code)
}

onMounted(load)
</script>

<template>
  <div class="keyword-group-settings">
    <div class="toolbar">
      <ElButton type="primary" :icon="Edit" @click="openCreate">新增关键词组</ElButton>
      <ElButton type="danger" :disabled="selectedIds.length === 0" @click="batchRemove">批量删除 ({{ selectedIds.length }})</ElButton>
    </div>

    <ElTable :data="pagedRows" @selection-change="(rows: any[]) => (selectedIds = rows.map((r: any) => r.id))">
      <ElTableColumn type="selection" width="50" />
      <ElTableColumn prop="name" label="名称" min-width="160" />
      <ElTableColumn prop="description" label="说明" min-width="220" show-overflow-tooltip />
      <ElTableColumn label="挂载城市" min-width="200">
        <template #default="scope">
          <template v-if="(scope.row.cities || []).length">
            <ElTag v-for="city in scope.row.cities" :key="city.code" type="primary" class="keyword-tag">
              {{ city.name }}
            </ElTag>
          </template>
          <span v-else>未挂载</span>
        </template>
      </ElTableColumn>
      <ElTableColumn label="关键词" min-width="240">
        <template #default="scope">
          <ElTag v-for="word in scope.row.words" :key="word" class="keyword-tag">{{ word }}</ElTag>
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

    <ElDialog v-model="dialog" :title="editingId ? '编辑关键词组' : '新增关键词组'" width="640">
      <ElForm label-width="90px">
        <ElFormItem label="名称">
          <ElInput v-model="form.name" placeholder="例如：展览" aria-label="关键词组名称" />
        </ElFormItem>
        <ElFormItem label="说明">
          <ElInput v-model="form.description" placeholder="可选" aria-label="说明" />
        </ElFormItem>
        <ElFormItem label="关键词">
          <div class="chips">
            <ElTag v-for="word in form.words" :key="word" closable @close="removeWord(word)">{{ word }}</ElTag>
          </div>
          <ElInput
            v-model="newWord"
            placeholder="回车添加"
            aria-label="关键词输入"
            @keyup.enter="addWordFromInput"
          />
        </ElFormItem>
        <ElFormItem label="挂载城市">
          <div class="chips">
            <ElTag v-for="code in form.city_codes" :key="code" type="primary" closable @close="removeCity(code)">
              {{ props.cities.find((c: any) => c.code === code)?.name || code }}
            </ElTag>
          </div>
          <ElSelect
            :model-value="''"
            placeholder="添加城市"
            @change="(v: any) => { addCity(v); form.city_codes = [...form.city_codes] }"
          >
            <ElOption v-for="city in props.cities" :key="city.code" :label="city.name" :value="city.code" />
          </ElSelect>
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
.keyword-group-settings { padding-top: 16px; }
.toolbar { margin-bottom: 16px; display: flex; gap: 8px; }
.chips { display: flex; flex-wrap: wrap; gap: 6px; margin-bottom: 8px; min-height: 24px; }
.chips:empty { display: none; }
.keyword-tag { margin-right: 4px; }
</style>
