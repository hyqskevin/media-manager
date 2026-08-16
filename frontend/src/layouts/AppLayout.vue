<script setup lang="ts">
import {
  Avatar,
  Calendar,
  Connection,
  DataAnalysis,
  Document,
  Expand,
  Fold,
  List,
  Setting,
  SwitchButton,
  Timer,
} from '@element-plus/icons-vue'
import { computed, ref } from 'vue'
import { useRoute } from 'vue-router'
import { useUserStore } from '@/stores/user'
import { NAV_ITEMS, type SubItem, type TopItem } from '@/config/navPermissions'

const route = useRoute()
const isCollapse = ref(localStorage.getItem('sidebar_collapsed') === '1')
const userStore = useUserStore()

/** 顶级菜单是否可见：
 *  - hasChildren=false 且 topLevelPermission 为空：所有已登录用户可见
 *  - hasChildren=true 且 topLevelPermission 非空：该权限码可见
 *  - hasChildren=true 且 topLevelPermission 为空：只要有一个子项可见
 */
function isTopVisible(item: TopItem): boolean {
  if (!item.hasChildren) {
    return item.topLevelPermission === null || userStore.hasPermission(item.topLevelPermission)
  }
  if (item.topLevelPermission !== null && item.topLevelPermission !== undefined) {
    return userStore.hasPermission(item.topLevelPermission)
  }
  return (item.children || []).some(isSubVisible)
}

function isSubVisible(sub: SubItem): boolean {
  return sub.permission === null || userStore.hasPermission(sub.permission)
}

const visibleNavItems = computed(() => NAV_ITEMS.filter(isTopVisible))

/** 顶级菜单图标映射；新增顶级菜单时同步在这里登记 */
const ICON_MAP: Record<string, unknown> = {
  '/dashboard': DataAnalysis,
  '/activities': Calendar,
  '/duplicates': List,
  '/tasks': Connection,
  '/schedules': Timer,
  '/reports': Document,
  '/settings': Setting,
  '/system-admin': Avatar,
}

function toggleCollapse() {
  isCollapse.value = !isCollapse.value
  localStorage.setItem('sidebar_collapsed', isCollapse.value ? '1' : '0')
}

function logout(){localStorage.removeItem('token');userStore.clear();location.href='/login'}
</script>

<template>
  <ElContainer class="app-shell">
    <ElAside class="app-sidebar" :width="isCollapse ? '64px' : '220px'">
      <div class="brand">
        <ElIcon :size="22"><Connection /></ElIcon>
        <span v-if="!isCollapse">活动采集系统</span>
      </div>
      <ElMenu router :default-active="route.fullPath" :collapse="isCollapse" :collapse-transition="false" class="app-menu">
        <template v-for="item in visibleNavItems" :key="item.index">
          <!-- 叶子菜单 -->
          <ElMenuItem v-if="!item.hasChildren" :index="item.index">
            <ElIcon><component :is="ICON_MAP[item.index]" /></ElIcon>
            <span>{{ item.label }}</span>
          </ElMenuItem>
          <!-- 顶级子菜单 -->
          <ElSubMenu v-else :index="item.index">
            <template #title>
              <ElIcon><component :is="ICON_MAP[item.index]" /></ElIcon>
              <span>{{ item.label }}</span>
            </template>
            <ElMenuItem v-for="sub in (item.children || []).filter(isSubVisible)" :key="sub.index" :index="sub.index">
              {{ sub.label }}
            </ElMenuItem>
          </ElSubMenu>
        </template>
        <!-- 海报制作功能未完备，暂隐藏 -->
        <!-- <ElMenuItem index="/posters">
          <ElIcon><Film /></ElIcon>
          <span>海报制作</span>
        </ElMenuItem> -->
      </ElMenu>
    </ElAside>
    <ElContainer>
      <ElHeader class="app-header">
        <ElButton class="collapse-toggle" :icon="isCollapse ? Expand : Fold" text @click="toggleCollapse" />
        <h1>{{ route.meta.title }}</h1>
        <div><ElTag type="success" effect="plain">本地轻量版</ElTag><ElButton text :icon="SwitchButton" @click="logout">退出</ElButton></div>
      </ElHeader>
      <ElMain class="app-main">
        <RouterView />
      </ElMain>
    </ElContainer>
  </ElContainer>
</template>

<style scoped>
.app-sidebar { transition: width 0.3s; }
</style>