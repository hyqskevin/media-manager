<script setup lang="ts">
import { useRoute, useRouter } from 'vue-router'
import { usePlatformStore } from '@/stores/platform'

const PLATFORMS = [
  { id: 'xhs', label: '小红书' },
  { id: 'weibo', label: '微博' },
  { id: 'douyin', label: '抖音' },
  { id: 'zhihu', label: '知乎' },
  { id: 'twitter', label: 'Twitter' },
  { id: 'bilibili', label: 'B站' },
  { id: 'xiaoyuzhou', label: '小宇宙' },
  { id: 'wechat-official', label: '公众号' },
]

const route = useRoute()
const router = useRouter()
const platformStore = usePlatformStore()

function select(platform: { id: string; label: string }) {
  if (platform.id !== 'xhs') return // 其余平台 v0.3 规划
  platformStore.setActivePlatform(platform.id)
  router.replace({ query: { ...route.query, platform: platform.id } })
}
</script>

<template>
  <div class="platform-tab-bar" role="toolbar" aria-label="平台筛选">
    <button
      v-for="p in PLATFORMS"
      :key="p.id"
      class="platform-tab"
      :class="{
        active: platformStore.activePlatform === p.id,
        disabled: p.id !== 'xhs',
      }"
      :disabled="p.id !== 'xhs'"
      :aria-pressed="platformStore.activePlatform === p.id"
      @click="select(p)"
    >
      <ElTooltip v-if="p.id !== 'xhs'" content="v0.3 规划中" placement="bottom">
        <span>{{ p.label }}</span>
      </ElTooltip>
      <span v-else>{{ p.label }}</span>
    </button>
  </div>
</template>

<style scoped>
.platform-tab-bar {
  display: flex;
  gap: var(--md-sys-spacing-1);
  padding: 0 var(--md-sys-spacing-4);
  height: 48px;
  align-items: stretch;
  border-bottom: 1px solid var(--md-sys-color-outline-variant);
  background: var(--md-sys-color-surface);
  position: sticky;
  top: 0;
  z-index: 20;
  overflow-x: auto;
}
.platform-tab {
  border: none;
  background: transparent;
  padding: 0 var(--md-sys-spacing-4);
  font: var(--md-sys-typescale-title-small);
  color: var(--md-sys-color-on-surface-variant);
  border-bottom: 3px solid transparent;
  cursor: pointer;
  white-space: nowrap;
}
.platform-tab.active {
  color: var(--md-sys-color-primary);
  border-bottom-color: var(--md-sys-color-primary);
}
.platform-tab.disabled {
  opacity: 0.45;
  cursor: not-allowed;
}
</style>