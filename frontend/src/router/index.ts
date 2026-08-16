import { createRouter, createWebHistory } from 'vue-router'

import AppLayout from '@/layouts/AppLayout.vue'
import LoginView from '@/views/LoginView.vue'
import SettingsView from '@/views/SettingsView.vue'
import SystemAdminView from '@/views/SystemAdminView.vue'
import NurtureTasksView from '@/views/NurtureTasksView.vue'

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/login', component: LoginView, meta: { public: true, title: '登录' } },
    {
      path: '/',
      component: AppLayout,
      redirect: '/system-admin?tab=platform-accounts',
      children: [
        { path: 'settings', component: SettingsView, meta: { title: '配置中心' } },
        { path: 'system-admin', component: SystemAdminView, meta: { title: '系统管理' } },
        { path: 'nurture-tasks', component: NurtureTasksView, meta: { title: '养号任务' } },
      ],
    },
  ],
})

router.beforeEach(to => {
  if (!to.meta.public && !localStorage.getItem('token')) return '/login'
  if (to.path === '/login' && localStorage.getItem('token')) return '/system-admin?tab=platform-accounts'
})

export default router