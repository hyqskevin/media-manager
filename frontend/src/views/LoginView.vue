<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const username = ref('')
const password = ref('')
const loading = ref(false)

async function submit() {
  if (!username.value || !password.value) {
    ElMessage.warning('请输入用户名和密码')
    return
  }
  loading.value = true
  try {
    const res = await api.login(username.value, password.value)
    const token = res.data?.access_token ?? res.data?.token
    if (token) userStore.setToken(token)
    router.replace('/accounts')
  } catch {
    ElMessage.error('登录失败，请检查用户名/密码')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-page">
    <ElCard class="login-card" shadow="always">
      <h1 class="md-typescale-title-large">media-manager 登录</h1>
      <ElForm label-position="top" @submit.prevent="submit">
        <ElFormItem label="用户名">
          <ElInput v-model="username" placeholder="admin" data-test="username" />
        </ElFormItem>
        <ElFormItem label="密码">
          <ElInput v-model="password" type="password" show-password placeholder="••••" data-test="password" @keyup.enter="submit" />
        </ElFormItem>
        <ElButton type="primary" class="login-btn" :loading="loading" @click="submit" data-test="submit">
          登录
        </ElButton>
      </ElForm>
    </ElCard>
  </div>
</template>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: var(--md-sys-color-background);
  padding: var(--md-sys-spacing-4);
}
.login-card {
  width: 360px;
  border-radius: var(--md-sys-shape-lg);
  padding: var(--md-sys-spacing-6);
}
.login-btn { width: 100%; margin-top: var(--md-sys-spacing-2); }
</style>