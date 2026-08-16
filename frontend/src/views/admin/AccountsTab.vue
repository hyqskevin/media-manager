<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface UserRow {
  id: number
  username: string
  display_name: string | null
  enabled: boolean
  role: string
  groups: string[]
}

interface GroupRow {
  id: number
  name: string
}

const users = ref<UserRow[]>([])
const groups = ref<GroupRow[]>([])
const dialogVisible = ref(false)
const form = ref({
  username: '',
  password: '',
  display_name: '',
  is_admin: true,
  group_ids: [] as number[],
})

// 重置密码弹窗
const passwordDialogVisible = ref(false)
const passwordTarget = ref<UserRow | null>(null)
const newPassword = ref('')

async function load() {
  const [u, g] = await Promise.all([api.listUsers(), api.listGroups()])
  // 后端 list_users / list_groups 返回裸数组（response_model=list[...])，需要从 axios 响应里取 .data
  users.value = (u as any).data as UserRow[]
  groups.value = (g as any).data as GroupRow[]
}

async function submit() {
  const payload = {
    username: form.value.username,
    password: form.value.password,
    display_name: form.value.display_name || null,
    is_admin: form.value.is_admin,
    group_ids: form.value.is_admin ? [] : form.value.group_ids,
  }
  await api.createUser(payload)
  ElMessage.success('创建成功')
  dialogVisible.value = false
  await load()
}

async function remove(u: UserRow) {
  try {
    await ElMessageBox.confirm(`确认删除账号 ${u.username}？`, '删除确认', { type: 'warning' })
  } catch {
    return
  }
  await api.deleteUser(u.id)
  ElMessage.success('已删除')
  await load()
}

function openResetPassword(u: UserRow) {
  passwordTarget.value = u
  newPassword.value = ''
  passwordDialogVisible.value = true
}

async function submitResetPassword() {
  if (!passwordTarget.value) return
  if (!newPassword.value || newPassword.value.length < 8) {
    ElMessage.error('密码长度至少 8 位')
    return
  }
  await api.updateUser(passwordTarget.value.id, { password: newPassword.value })
  ElMessage.success(`账号 ${passwordTarget.value.username} 密码已重置`)
  passwordDialogVisible.value = false
  passwordTarget.value = null
  newPassword.value = ''
}

// 行内可改：启用 / 分组（admin 行被禁用——保护兜底管理员）
async function toggleEnabled(u: UserRow, val: boolean) {
  try {
    await api.updateUser(u.id, { enabled: val })
    ElMessage.success(`已${val ? '启用' : '禁用'} ${u.username}`)
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message ?? '修改启用状态失败')
    await load()
  }
}

async function changeGroups(u: UserRow, vals: number[]) {
  try {
    await api.updateUserGroups(u.id, vals)
    ElMessage.success(`已更新 ${u.username} 的分组`)
    await load()
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message ?? '更新分组失败')
    await load()
  }
}

// 把行内的 group name 列表反查为 group id 列表（给 ElSelect 多选）
function selectedGroupIds(u: UserRow): number[] {
  const nameSet = new Set(u.groups)
  return groups.value.filter((g) => nameSet.has(g.name)).map((g) => g.id)
}

onMounted(load)
</script>

<template>
  <div class="accounts-tab">
    <div class="toolbar">
      <ElButton type="primary" :icon="Plus" @click="dialogVisible = true">新建账号</ElButton>
    </div>
    <ElTable :data="users" stripe>
      <ElTableColumn prop="username" label="用户名" />
      <ElTableColumn prop="display_name" label="显示名" />
      <ElTableColumn label="启用" width="100">
        <template #default="{ row }">
          <ElSwitch
            :model-value="row.enabled"
            :disabled="row.username === 'admin'"
            @change="(val: boolean | string | number) => toggleEnabled(row, Boolean(val))"
          />
        </template>
      </ElTableColumn>
      <ElTableColumn label="分组" width="280">
        <template #default="{ row }">
          <ElSelect
            :model-value="selectedGroupIds(row)"
            multiple
            clearable
            collapse-tags
            collapse-tags-tooltip
            :disabled="row.username === 'admin'"
            style="width: 100%;"
            @change="(vals: number[]) => changeGroups(row, vals)"
          >
            <ElOption
              v-for="g in groups"
              :key="g.id"
              :value="g.id"
              :label="g.name"
            />
          </ElSelect>
        </template>
      </ElTableColumn>
      <ElTableColumn label="操作" width="260">
        <template #default="{ row }">
          <ElButton v-if="row.username !== 'admin'" size="small" @click="openResetPassword(row)">重置密码</ElButton>
          <ElButton size="small" :disabled="row.username === 'admin'" @click="remove(row)">删除</ElButton>
        </template>
      </ElTableColumn>
    </ElTable>

    <ElDialog v-model="dialogVisible" title="新建账号" width="480">
      <ElForm :model="form" label-width="100">
        <ElFormItem label="用户名"><ElInput v-model="form.username" /></ElFormItem>
        <ElFormItem label="初始密码"><ElInput v-model="form.password" type="password" show-password /></ElFormItem>
        <ElFormItem label="显示名"><ElInput v-model="form.display_name" /></ElFormItem>
        <ElFormItem label="管理员账号">
          <ElSwitch v-model="form.is_admin" />
          <span style="margin-left: 8px; color: #909399;">开启后自动加入 Administrators 组</span>
        </ElFormItem>
        <ElFormItem v-if="!form.is_admin" label="所属分组">
          <ElSelect v-model="form.group_ids" multiple style="width: 100%;">
            <ElOption v-for="g in groups" :key="g.id" :value="g.id" :label="g.name" />
          </ElSelect>
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submit">保存</ElButton>
      </template>
    </ElDialog>

    <ElDialog
      v-model="passwordDialogVisible"
      :title="`重置密码 — ${passwordTarget?.username ?? ''}`"
      width="420"
    >
      <ElForm label-width="100">
        <ElFormItem label="新密码">
          <ElInput
            v-model="newPassword"
            type="password"
            show-password
            placeholder="≥ 8 位，含大小写+数字+符号"
          />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="passwordDialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="submitResetPassword">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>