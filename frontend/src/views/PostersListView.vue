<script setup lang="ts">
import { Delete, Edit, Download } from '@element-plus/icons-vue'
import { onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { api } from '@/api/client'

const rows = ref<any[]>([])
const loading = ref(false)
const templateNames = ref<Record<number, string>>({})

async function load() {
  loading.value = true
  try {
    const items = (await api.posterTasks()).data.data.items || []
    rows.value = items
    // preload template names by id
    const tplIds = new Set<number>()
    for (const item of items) tplIds.add(item.template_id)
    const list = (await api.posterTemplates()).data.data.items || []
    const map: Record<number, string> = {}
    for (const t of list) map[t.id] = t.name
    templateNames.value = map
  } finally {
    loading.value = false
  }
}

async function regenerate(item: any) {
  const res = await api.posterRender(item.id)
  ElMessage.success('已渲染')
  await load()
  return res.data.data
}

async function download(item: any) {
  const blob = (await api.posterDownload(item.id)).data
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `poster-${item.id}.png`
  a.click()
  URL.revokeObjectURL(url)
}

async function remove(item: any) {
  await ElMessageBox.confirm(`确认删除任务 "${item.name}"？`, '删除', { type: 'warning' })
  await api.deletePosterTask(item.id)
  ElMessage.success('已删除')
  await load()
}

onMounted(load)
</script>

<template>
  <div class="page">
    <ElCard shadow="never" class="page-card">
      <div class="toolbar">
        <h2>海报任务列表</h2>
        <ElButton type="primary" @click="() => $router.push('/posters/new')">新建海报</ElButton>
      </div>

      <ElTable v-loading="loading" :data="rows" empty-text="尚无任务，去新建一张海报">
        <ElTableColumn prop="id" label="ID" width="60" />
        <ElTableColumn prop="name" label="任务名" min-width="160" />
        <ElTableColumn label="模板" min-width="160">
          <template #default="scope">
            {{ templateNames[scope.row.template_id] || `#${scope.row.template_id}` }}
          </template>
        </ElTableColumn>
        <ElTableColumn label="item 数量" width="120">
          <template #default="scope">{{ (scope.row.items || []).length }}</template>
        </ElTableColumn>
        <ElTableColumn prop="status" label="状态" width="100" />
        <ElTableColumn label="操作" min-width="240" class-name="action-column">
          <template #default="scope">
            <ElButton text type="primary" :icon="Edit" @click="regenerate(scope.row)">渲染</ElButton>
            <ElButton text type="success" :icon="Download" :disabled="scope.row.status !== 'rendered'" @click="download(scope.row)">下载</ElButton>
            <ElButton text type="danger" :icon="Delete" @click="remove(scope.row)">删除</ElButton>
          </template>
        </ElTableColumn>
      </ElTable>
    </ElCard>
  </div>
</template>

<style scoped>
.page { padding: 24px; }
.page-card { max-width: 1280px; margin: 0 auto; }
.toolbar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 16px; }
.toolbar h2 { margin: 0; }
</style>
