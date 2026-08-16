<script setup lang="ts">
import { onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const isAdmin = computed(() => userStore.isAdmin)
const isAuthenticated = computed(() => userStore.isAuthenticated)

/** 从 localStorage 的 JWT 中解析 role（page refresh 时 Pinia 状态丢失的 fallback）。 */
function readRoleFromToken(): 'admin' | 'editor' | null {
  const token = localStorage.getItem('token')
  if (!token) return null
  try {
    const parts = token.split('.')
    if (parts.length !== 3) return null
    const payload = JSON.parse(atob(parts[1]))
    return payload.role === 'admin' || payload.role === 'editor' ? payload.role : null
  } catch {
    return null
  }
}

const tokenRole = computed(() => readRoleFromToken())

onMounted(() => {
  // 优先用 store；store 未初始化（page refresh）时退到 localStorage 解析
  const role = isAdmin.value ? 'admin' : (tokenRole.value)
  const hasToken = isAuthenticated.value || !!localStorage.getItem('token')
  if (hasToken && role && role !== 'admin') {
    ElMessage.error('无权限访问系统管理')
    router.push('/dashboard')
  }
})
</script>

<template>
  <slot v-if="isAdmin || tokenRole === 'admin'" />
</template>