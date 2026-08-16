import { config } from '@vue/test-utils'
import ElementPlus from 'element-plus'

// 让组件测试中的 ElXXX 组件可正常渲染
config.global.plugins = [ElementPlus]
config.global.stubs = {
  transition: false,
  'el-tooltip': true,
}

// jsdom 未实现 Blob 下载相关 API，导出 CSV 测试需要
if (typeof URL.createObjectURL !== 'function') {
  URL.createObjectURL = () => 'blob:mock'
  URL.revokeObjectURL = () => {}
}