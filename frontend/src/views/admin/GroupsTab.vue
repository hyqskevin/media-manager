<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface GroupOut {
  id: number
  name: string
  description: string | null
  is_builtin: boolean
  permission_codes: string[]
}

interface PermissionOut {
  id: number
  code: string
  description: string | null
  is_builtin: boolean
}

const groups = ref<GroupOut[]>([])
const permissions = ref<PermissionOut[]>([])
const selectedId = ref<number | null>(null)
const selectedCodes = ref<string[]>([])

const selectedGroup = computed(() => groups.value.find((g) => g.id === selectedId.value) ?? null)

// 新建分组弹窗
const createDialogVisible = ref(false)
const createForm = ref({
  name: '',
  description: '',
})

async function load() {
  const [g, p] = await Promise.all([api.listGroups(), api.listPermissions()])
  // 后端 list_groups / list_permissions 返回裸数组，从 axios 响应里取 .data
  groups.value = (g as any).data as GroupOut[]
  permissions.value = (p as any).data as PermissionOut[]
  if (!selectedId.value && groups.value.length) {
    selectedId.value = groups.value[0].id
    selectedCodes.value = [...groups.value[0].permission_codes]
  }
}

function selectGroup(g: GroupOut) {
  selectedId.value = g.id
  selectedCodes.value = [...g.permission_codes]
}

async function savePermissions() {
  if (!selectedGroup.value) return
  await api.updateGroupPermissions(selectedGroup.value.id, selectedCodes.value)
  ElMessage.success('已保存')
  await load()
}

function openCreateGroup() {
  createForm.value = { name: '', description: '' }
  createDialogVisible.value = true
}

async function submitCreateGroup() {
  if (!createForm.value.name.trim()) {
    ElMessage.error('分组名不能为空')
    return
  }
  const created = await api.createGroup({
    name: createForm.value.name.trim(),
    description: createForm.value.description.trim() || null,
  }) as { data?: GroupOut } & GroupOut
  const createdId = (created.data?.id ?? created.id) as number
  ElMessage.success('分组已创建')
  createDialogVisible.value = false
  await load()
  // 自动选中新分组
  if (createdId) {
    const newGroup = groups.value.find((g) => g.id === createdId)
    if (newGroup) selectGroup(newGroup)
  }
}

onMounted(load)
</script>

<template>
  <div class="groups-tab">
    <div class="layout">
      <div class="left">
        <div class="left-header">
          <span>分组列表</span>
          <ElButton type="primary" size="small" :icon="Plus" style="float: right;" @click="openCreateGroup">
            新建
          </ElButton>
        </div>
        <div
          v-for="g in groups"
          :key="g.id"
          :class="['item', { active: g.id === selectedId }]"
          @click="selectGroup(g)"
        >
          {{ g.name }}
          <ElTag v-if="g.is_builtin" size="small" type="info">内置</ElTag>
        </div>
      </div>
      <div class="right">
        <template v-if="selectedGroup">
          <h3>{{ selectedGroup.name }}</h3>
          <p>{{ selectedGroup.description || '—' }}</p>
          <ElCheckboxGroup v-model="selectedCodes">
            <div v-for="p in permissions" :key="p.code" class="permission-row">
              <ElCheckbox :value="p.code">
                <strong>{{ p.code }}</strong> — {{ p.description }}
              </ElCheckbox>
            </div>
          </ElCheckboxGroup>
          <ElButton type="primary" @click="savePermissions">保存</ElButton>
        </template>
      </div>
    </div>

    <ElDialog v-model="createDialogVisible" title="新建分组" width="420">
      <ElForm :model="createForm" label-width="100">
        <ElFormItem label="分组名" required>
          <ElInput v-model="createForm.name" placeholder="例如：审核员" />
        </ElFormItem>
        <ElFormItem label="描述">
          <ElInput v-model="createForm.description" type="textarea" :rows="2" placeholder="可选" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="createDialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitCreateGroup">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.layout { display: flex; gap: 16px; }
.left { width: 220px; }
.left-header { font-weight: bold; margin-bottom: 8px; line-height: 32px; }
.item { padding: 8px; cursor: pointer; border-radius: 4px; }
.item.active { background: #ecf5ff; color: #409eff; }
.right { flex: 1; }
.permission-row { margin-bottom: 4px; }
</style>