<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'
import { formatUtcAsShanghai } from '@/utils/datetime'

const rows = ref<any[]>([])

async function load() {
  const items = (await api.duplicates()).data.data.items
  const resolved = await Promise.all(
    items.map(async (row: any) => {
      const [left, right] = await Promise.allSettled([
        api.note(row.note_a_id),
        api.note(row.note_b_id),
      ])
      // 任一侧不可见（候选指向已 MERGED/DELETED 推文）则丢弃本条
      if (left.status === 'rejected' || right.status === 'rejected') {
        return null
      }
      return {
        ...row,
        note_a: (left as any).value.data.data,
        note_b: (right as any).value.data.data,
      }
    }),
  )
  rows.value = resolved.filter((row): row is object => row !== null)
}

async function merge(id: number, keep = 'a') {
  await api.merge(id, keep)
  ElMessage.success('合并完成')
  await load()
}

async function ignore(id: number) {
  await api.ignore(id)
  ElMessage.success('已忽略')
  await load()
}

onMounted(load)
</script>

<template>
  <ElCard shadow="never">
    <ElTable :data="rows">
      <ElTableColumn label="推文 A" min-width="220">
        <template #default="scope"><strong>{{ scope.row.note_a?.title }}</strong><div>{{ scope.row.note_a?.published_at ? formatUtcAsShanghai(scope.row.note_a.published_at) : '发布时间待确认' }}</div><div>识别活动 {{ scope.row.note_a?.activity_count || 0 }} 条</div></template>
      </ElTableColumn>
      <ElTableColumn label="推文 B" min-width="220">
        <template #default="scope"><strong>{{ scope.row.note_b?.title }}</strong><div>{{ scope.row.note_b?.published_at ? formatUtcAsShanghai(scope.row.note_b.published_at) : '发布时间待确认' }}</div><div>识别活动 {{ scope.row.note_b?.activity_count || 0 }} 条</div></template>
      </ElTableColumn>
      <ElTableColumn prop="similarity" label="相似度"><template #default="scope"><ElProgress :percentage="Math.round(scope.row.similarity * 100)" /></template></ElTableColumn>
      <ElTableColumn prop="matched_fields" label="匹配字段" />
      <ElTableColumn label="操作" min-width="320" class-name="action-column">
        <template #default="scope">
          <ElButton size="small" type="primary" @click="merge(scope.row.id, 'a')">保留 A</ElButton>
          <ElButton size="small" @click="merge(scope.row.id, 'b')">保留 B</ElButton>
          <ElDropdown>
            <ElButton size="small">更多 ▾</ElButton>
            <template #dropdown>
              <ElDropdownMenu>
                <ElDropdownItem @click="ignore(scope.row.id)">不是重复</ElDropdownItem>
              </ElDropdownMenu>
            </template>
          </ElDropdown>
        </template>
      </ElTableColumn>
    </ElTable>
    <ElEmpty v-if="!rows.length" description="暂无去重候选" />
  </ElCard>
</template>
