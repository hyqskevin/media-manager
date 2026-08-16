import { config } from '@vue/test-utils'
import ElementPlus from 'element-plus'

// 注册 Element Plus,与 main.ts 对齐,确保 el-card 具名 slot 等组件特性在测试中生效
config.global.plugins = [ElementPlus]

// 全局 stub ElMessage 避免组件测试里弹出真实 DOM
config.global.mocks = {
  $message: {
    success: () => {},
    error: () => {},
    warning: () => {},
    info: () => {},
  },
}
