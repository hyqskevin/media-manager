import { createRouter, createWebHashHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import LoginView from '@/views/LoginView.vue'
import AccountsOverviewView from '@/views/accounts/AccountsOverviewView.vue'
import AccountsListView from '@/views/accounts/AccountsListView.vue'
import SessionsView from '@/views/accounts/SessionsView.vue'
import ActivityView from '@/views/accounts/ActivityView.vue'
import RiskConfigView from '@/views/accounts/RiskConfigView.vue'
import FavoritesView from '@/views/nurture/FavoritesView.vue'
import RunningTasksView from '@/views/nurture/RunningTasksView.vue'
import NurtureHistoryView from '@/views/nurture/NurtureHistoryView.vue'
import SchedulesView from '@/views/nurture/SchedulesView.vue'
import ActionSetsView from '@/views/nurture/ActionSetsView.vue'
import PlatformConfigsView from '@/views/admin/PlatformConfigsView.vue'
import NotificationsView from '@/views/admin/NotificationsView.vue'
import AuditLogsView from '@/views/admin/AuditLogsView.vue'
import OperatorsView from '@/views/admin/OperatorsView.vue'

const router = createRouter({
  history: createWebHashHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true, title: '登录' } },
    {
      path: '/',
      component: AppLayout,
      redirect: '/accounts',
      children: [
        { path: 'accounts', component: AccountsOverviewView, meta: { title: '账号总览' } },
        { path: 'accounts/list', component: AccountsListView, meta: { title: '账号列表' } },
        { path: 'accounts/sessions', component: SessionsView, meta: { title: '登录态管理' } },
        { path: 'accounts/activity', component: ActivityView, meta: { title: '账号活跃度' } },
        { path: 'accounts/risk', component: RiskConfigView, meta: { title: '风控配置' } },
        { path: 'nurture/running', component: RunningTasksView, meta: { title: '执行中' } },
        { path: 'nurture/history', component: NurtureHistoryView, meta: { title: '历史' } },
        { path: 'nurture/schedules', component: SchedulesView, meta: { title: '定时任务' } },
        { path: 'nurture/actions', component: ActionSetsView, meta: { title: '动作集' } },
        { path: 'nurture/favorites', component: FavoritesView, meta: { title: '我的收藏夹' } },
        { path: 'admin/platforms', component: PlatformConfigsView, meta: { title: '平台配置' } },
        { path: 'admin/notifications', component: NotificationsView, meta: { title: '通知中心' } },
        { path: 'admin/audit', component: AuditLogsView, meta: { title: '操作日志' } },
        { path: 'admin/operators', component: OperatorsView, meta: { title: '操作员管理' } },
      ],
    },
  ],
})

router.beforeEach(to => {
  if (!to.meta.public && !localStorage.getItem('token')) return '/login'
  if (to.path === '/login' && localStorage.getItem('token')) return '/accounts'
})

export default router