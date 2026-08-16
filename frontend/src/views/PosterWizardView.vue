<script setup lang="ts">
import { ArrowLeft, ArrowRight, UploadFilled } from '@element-plus/icons-vue'
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { api } from '@/api/client'

const step = ref(1)
const granularity = ref<'note' | 'activity'>('note')
const candidates = ref<any[]>([])
const city = ref('')
const q = ref('')
const selectedIds = ref<number[]>([])
const templates = ref<any[]>([])
const templateId = ref<number | null>(null)
const items = ref<any[]>([])
const overrideHtml = ref('')
const previewHtml = ref('')
const renderedUrl = ref('')
const taskId = ref<number | null>(null)

async function searchCandidates() {
  const params: any = { page_size: 50 }
  if (city.value) params.city_code = city.value
  if (q.value) params.q = q.value
  const resp = await api.posterCandidates(params)
  candidates.value = resp.data.data.items || []
}

async function loadTemplates() {
  templates.value = (await api.posterTemplates()).data.data.items || []
}

async function loadNoteImages(noteId: number): Promise<string[]> {
  const resp = await api.noteImages(noteId)
  return resp.data.data.image_urls || []
}

async function goStep2() {
  if (selectedIds.value.length === 0) {
    ElMessage.warning('请至少选择一个候选')
    return
  }
  // 物品化：每位入选的 note 一行
  const tmp: any[] = []
  for (const id of selectedIds.value) {
    const note = candidates.value.find((x: any) => x.id === id)
    if (!note) continue
    const images = await loadNoteImages(id)
    tmp.push({
      type: 'note',
      id,
      title: note.title,
      fields: { time_range: '', location: '', fee: '', content: '' },
      image_url: images[0] || '',
    })
  }
  items.value = tmp
  step.value = 2
}

function pickTemplate(t: any) {
  templateId.value = t.id
}

async function saveDraft() {
  if (!templateId.value) {
    ElMessage.warning('请选择模板')
    return
  }
  const payload = {
    name: `营销海报-${new Date().toISOString().slice(0, 16).replace(/[T:]/g, '-')}`,
    template_id: templateId.value,
    items: items.value,
    override_html: overrideHtml.value || null,
  }
  const resp = await api.createPosterTask(payload)
  taskId.value = resp.data.data.id
  ElMessage.success('已保存为草稿')
  return resp.data.data
}

async function preview() {
  await saveDraft()
  if (!taskId.value) return
  const resp = await api.posterPreview(taskId.value)
  previewHtml.value = resp.data.data.html
  step.value = 6
}

async function renderNow() {
  if (!taskId.value) {
    await saveDraft()
  }
  if (!taskId.value) return
  try {
    const resp = await api.posterRender(taskId.value)
    renderedUrl.value = resp.data.data.url
    ElMessage.success('渲染完成，可下载')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '渲染失败')
  }
}

async function download() {
  if (!taskId.value) return
  const blob = (await api.posterDownload(taskId.value)).data
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `poster-${taskId.value}.png`
  a.click()
  URL.revokeObjectURL(url)
}

onMounted(async () => {
  await Promise.all([searchCandidates(), loadTemplates()])
})
</script>

<template>
  <div class="page">
    <ElCard shadow="never" class="page-card">
      <h2>新建海报</h2>
      <ElSteps :active="step" finish-status="success" class="steps">
        <ElStep title="选范围" />
        <ElStep title="选模板" />
        <ElStep title="填字段" />
        <ElStep title="人工改 HTML" />
        <ElStep title="选图" />
        <ElStep title="预览 / 渲染" />
      </ElSteps>

      <!-- 步骤 1 -->
      <div v-if="step === 1" class="step-panel">
        <ElRadioGroup v-model="granularity" class="granularity">
          <ElRadioButton value="note">推文为单位</ElRadioButton>
          <ElRadioButton value="activity">活动为单位（演示中用 note）</ElRadioButton>
        </ElRadioGroup>
        <div class="filters">
          <ElInput v-model="city" placeholder="city code (可选)" style="width: 200px" />
          <ElInput v-model="q" placeholder="搜索关键字" style="width: 240px" />
          <ElButton type="primary" @click="searchCandidates">搜索</ElButton>
        </div>
        <ElTable :data="candidates" @selection-change="(rows: any[]) => selectedIds = rows.map((r: any) => r.id)" empty-text="没有候选">
          <ElTableColumn type="selection" width="48" />
          <ElTableColumn prop="id" label="ID" width="60" />
          <ElTableColumn prop="title" label="标题" min-width="240" />
          <ElTableColumn prop="city_code" label="城市" width="120" />
          <ElTableColumn label="图片数" width="100">
            <template #default="scope">{{ scope.row.image_count }}</template>
          </ElTableColumn>
        </ElTable>
        <div class="step-actions">
          <ElButton type="primary" @click="goStep2">下一步<ElIcon class="el-icon--right"><ArrowRight /></ElIcon></ElButton>
        </div>
      </div>

      <!-- 步骤 2 -->
      <div v-else-if="step === 2" class="step-panel">
        <ElTable :data="templates" empty-text="请先去配置中心新增海报模板">
          <ElTableColumn prop="id" label="ID" width="60" />
          <ElTableColumn prop="name" label="名称" min-width="200" />
          <ElTableColumn prop="description" label="说明" min-width="240" show-overflow-tooltip />
          <ElTableColumn label="操作" width="120">
            <template #default="scope">
              <ElButton :type="templateId === scope.row.id ? 'primary' : 'default'" @click="pickTemplate(scope.row)">
                {{ templateId === scope.row.id ? '已选' : '选择' }}
              </ElButton>
            </template>
          </ElTableColumn>
        </ElTable>
        <div class="step-actions">
          <ElButton @click="step = 1"><ElIcon class="el-icon--left"><ArrowLeft /></ElIcon>上一步</ElButton>
          <ElButton type="primary" :disabled="!templateId" @click="step = 3">下一步</ElButton>
        </div>
      </div>

      <!-- 步骤 3 -->
      <div v-else-if="step === 3" class="step-panel">
        <div v-for="item in items" :key="item.id" class="fields-row">
          <h4>{{ item.title }} <small>#{{ item.id }}</small></h4>
          <div class="grid">
            <ElInput v-model="item.fields.time_range" placeholder="时间范围" />
            <ElInput v-model="item.fields.location" placeholder="地点" />
            <ElInput v-model="item.fields.fee" placeholder="费用 / 票" />
            <ElInput v-model="item.fields.content" type="textarea" placeholder="备注内容" />
          </div>
        </div>
        <div class="step-actions">
          <ElButton @click="step = 2">上一步</ElButton>
          <ElButton type="primary" @click="step = 4">下一步</ElButton>
        </div>
      </div>

      <!-- 步骤 4 -->
      <div v-else-if="step === 4" class="step-panel">
        <p class="hint">直接编辑 HTML 草稿。可继续使用 <code>title</code> 与 <code>items</code> 占位符。</p>
        <ElInput v-model="overrideHtml" type="textarea" :rows="10" placeholder="<div class='poster'>…</div>" />
        <div class="step-actions">
          <ElButton @click="step = 3">上一步</ElButton>
          <ElButton type="primary" @click="step = 5">下一步</ElButton>
        </div>
      </div>

      <!-- 步骤 5 -->
      <div v-else-if="step === 5" class="step-panel">
        <div v-for="item in items" :key="item.id" class="image-row">
          <h4>{{ item.title }} (note id={{ item.id }})</h4>
          <ElImage
            :src="item.image_url"
            fit="cover"
            style="width: 120px; height: 80px; margin-right: 8px"
            v-for="(_img, idx) in [item.image_url].filter(Boolean) === [] ? ['placeholder'] : [item.image_url]"
            :key="idx"
            v-show="false"
          />
          <ElRadioGroup v-model="item.image_url">
            <ElRadio v-for="(url, i) in [item.image_url].filter(Boolean)" :key="url" :value="url" :label="url">
              图 {{ i + 1 }}
            </ElRadio>
          </ElRadioGroup>
        </div>
        <div class="step-actions">
          <ElButton @click="step = 4">上一步</ElButton>
          <ElButton type="primary" :loading="!taskId" @click="preview">保存并预览</ElButton>
        </div>
      </div>

      <!-- 步骤 6 -->
      <div v-else-if="step === 6" class="step-panel">
        <div v-if="previewHtml" class="preview-wrap">
          <h4>预览</h4>
          <iframe class="preview-frame" :srcdoc="previewHtml"></iframe>
        </div>
        <div v-if="renderedUrl" class="rendered">
          <h4>已渲染</h4>
          <img :src="renderedUrl" alt="poster" />
          <ElButton type="primary" :icon="UploadFilled" @click="download">下载 PNG</ElButton>
        </div>
        <div class="step-actions">
          <ElButton @click="step = 5">上一步</ElButton>
          <ElButton type="primary" @click="renderNow">渲染为 PNG</ElButton>
          <ElButton @click="$router.push('/posters')">回到列表</ElButton>
        </div>
      </div>
    </ElCard>
  </div>
</template>

<style scoped>
.page { padding: 24px; }
.page-card { max-width: 1280px; margin: 0 auto; }
.steps { margin: 24px 0; }
.step-panel { padding-top: 12px; }
.filters { display: flex; gap: 8px; margin: 12px 0; }
.granularity { margin-bottom: 12px; }
.step-actions { margin-top: 24px; display: flex; gap: 8px; justify-content: flex-end; }
.grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 8px; }
.fields-row { padding: 12px 0; border-bottom: 1px dashed #eee; }
.preview-wrap { border: 1px solid #eee; padding: 12px; }
.preview-frame { width: 100%; height: 520px; border: 0; }
.rendered img { max-width: 100%; border: 1px solid #eee; margin-bottom: 12px; }
.hint { color: #888; font-size: 13px; margin-bottom: 8px; }
</style>
