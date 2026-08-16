import { defineStore } from 'pinia'

const KEY = 'media_manager_active_platform'

export const usePlatformStore = defineStore('platform', {
  state: () => ({
    activePlatform: localStorage.getItem(KEY) || 'xhs',
  }),
  actions: {
    setActivePlatform(platform: string) {
      this.activePlatform = platform
      localStorage.setItem(KEY, platform)
    },
  },
})