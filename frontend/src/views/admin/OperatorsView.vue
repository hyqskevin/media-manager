<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Key, Refresh } from '@element-plus/icons-vue'
import { api } from '@/api/client'

interface OperatorMe {
  id: number
  username: string
  is_admin: boolean
}

const me = ref<OperatorMe | null>(null)
const loading = ref(false)
const dialogVisible = ref(false)
const form = reactive({ old_password: '', new_password: '' })

async function load() {
  loading.value = true
  try {
    const res = await api.operatorsMe()
    me.value = res.data as OperatorMe
  } finally {
    loading.value = false
  }
}

function openChangePassword() {
  form.old_password = ''
  form.new_password = ''
  dialogVisible.value = true
}

async function savePassword() {
  if (!form.old_password || !form.new_password) {
    ElMessage.warning('请填写旧密码与新密码')
    return
  }
  try {
    await api.changePassword({ old_password: form.old_password, new_password: form.new_password })
    ElMessage.success('密码已修改')
    dialogVisible.value = false
  } catch {
    ElMessage.error('修改失败')
  }
}

onMounted(load)
</script>

<template>
  <div class="operators-page" v-loading="loading">
    <div class="page-header">
      <h2 class="md-typescale-headline-medium">操作员管理</h2>
      <ElButton type="primary" plain :icon="Refresh" @click="load">刷新</ElButton>
    </div>

    <ElCard shadow="never" class="me-card" v-if="me">
      <div class="me-row">
        <div>
          <span class="md-typescale-title-medium">{{ me.username }}</span>
          <p class="meta">用户ID：#{{ me.id }}</p>
          <ElTag :type="me.is_admin ? 'danger' : 'info'" effect="plain">{{ me.is_admin ? '管理员' : '普通操作员' }}</ElTag>
        </div>
        <ElButton type="primary" :icon="Key" @click="openChangePassword" data-test="open-change-password">修改密码</ElButton>
      </div>
    </ElCard>

    <ElDialog v-model="dialogVisible" title="修改密码" width="440px">
      <ElForm label-width="120px">
        <ElFormItem label="旧密码">
          <ElInput v-model="form.old_password" type="password" show-password data-test="old-password" />
        </ElFormItem>
        <ElFormItem label="新密码">
          <ElInput v-model="form.new_password" type="password" show-password data-test="new-password" />
        </ElFormItem>
      </ElForm>
      <template #footer>
        <ElButton @click="dialogVisible = false">取消</ElButton>
        <ElButton type="primary" @click="savePassword" data-test="save-password">保存</ElButton>
      </template>
    </ElDialog>
  </div>
</template>

<style scoped>
.operators-page { padding: var(--md-sys-spacing-6); }
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--md-sys-spacing-4);
}
.page-header h2 { margin: 0; }
.me-card { max-width: 640px; }
.me-row { display: flex; justify-content: space-between; align-items: center; }
.meta { margin: var(--md-sys-spacing-1) 0 var(--md-sys-spacing-2); color: var(--md-sys-color-on-surface-variant); }
</style>