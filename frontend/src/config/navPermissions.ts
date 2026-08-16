/** 侧边栏导航权限配置(v0.2 完整 IA)。
 * 与 AppLayout.vue 的 isTopVisible / isSubVisible 契约兼容。
 * v0.2 仅 admin，后端强制鉴权，permission 字段一律置 null(全可见)。
 */
export interface SubItem {
  index: string
  label: string
  permission: string | null
}

export interface TopItem {
  index: string
  label: string
  hasChildren: boolean
  topLevelPermission: string | null
  children?: SubItem[]
}

export const NAV_ITEMS: TopItem[] = [
  {
    index: '/accounts',
    label: '账号总览',
    hasChildren: false,
    topLevelPermission: null,
  },
  {
    index: '/media-manage',
    label: '媒体账号管理',
    hasChildren: true,
    topLevelPermission: null,
    children: [
      { index: '/accounts/list', label: '账号列表', permission: null },
      { index: '/accounts/sessions', label: '登录态管理', permission: null },
      { index: '/accounts/activity', label: '账号活跃度', permission: null },
      { index: '/accounts/risk', label: '风控配置', permission: null },
    ],
  },
  {
    index: '/nurture',
    label: '养号任务',
    hasChildren: true,
    topLevelPermission: null,
    children: [
      { index: '/nurture/running', label: '执行中', permission: null },
      { index: '/nurture/history', label: '历史', permission: null },
      { index: '/nurture/schedules', label: '定时任务', permission: null },
      { index: '/nurture/actions', label: '动作集', permission: null },
      { index: '/nurture/favorites', label: '我的收藏夹', permission: null },
    ],
  },
  {
    index: '/admin',
    label: '管理台配置',
    hasChildren: true,
    topLevelPermission: null,
    children: [
      { index: '/admin/platforms', label: '平台配置', permission: null },
      { index: '/admin/notifications', label: '通知中心', permission: null },
      { index: '/admin/audit', label: '操作日志', permission: null },
      { index: '/admin/operators', label: '操作员管理', permission: null },
    ],
  },
]