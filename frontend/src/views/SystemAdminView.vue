<script setup lang="ts">
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import SystemAdminGuard from '@/components/SystemAdminGuard.vue'
import AccountsTab from './admin/AccountsTab.vue'
import GroupsTab from './admin/GroupsTab.vue'
import PermissionsTab from './admin/PermissionsTab.vue'
import AuditLogsTab from './admin/AuditLogsTab.vue'

const route = useRoute()
const tab = computed(() => (route.query.tab as string) || 'accounts')
</script>

<template>
  <SystemAdminGuard>
    <div class="system-admin">
      <h2>系统管理</h2>
      <div class="tab-body" style="margin-top: 16px;">
        <AccountsTab v-if="tab === 'accounts'" />
        <GroupsTab v-else-if="tab === 'groups'" />
        <PermissionsTab v-else-if="tab === 'permissions'" />
        <AuditLogsTab v-else-if="tab === 'audit'" />
      </div>
    </div>
  </SystemAdminGuard>
</template>
