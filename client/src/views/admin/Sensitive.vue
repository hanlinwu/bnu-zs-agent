<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Upload, Document } from '@element-plus/icons-vue'
import * as sensitiveApi from '@/api/admin/sensitive'
import type { GroupListItem, GroupDetail } from '@/api/admin/sensitive'
import type { FormInstance, FormRules } from 'element-plus'

const loading = ref(false)
const groups = ref<GroupListItem[]>([])
const selectedGroup = ref<GroupListItem | null>(null)
const groupDetail = ref<GroupDetail | null>(null)
const detailLoading = ref(false)

const groupDialogVisible = ref(false)
const uploadDialogVisible = ref(false)
const groupFormRef = ref<FormInstance>()
const submitting = ref(false)
const isEditGroup = ref(false)

const groupForm = reactive({
  id: '',
  name: '',
  description: '',
  level: 'block' as 'block' | 'warn' | 'review',
  is_active: true,
})

const wordEditorText = ref('')
const showPlainWords = ref(false)

const groupRules: FormRules = {
  name: [{ required: true, message: '请输入词库名称', trigger: 'blur' }],
  level: [{ required: true, message: '请选择处理级别', trigger: 'change' }],
}

const uploadForm = reactive({
  name: '',
  description: '',
  level: 'block' as 'block' | 'warn' | 'review',
  file: null as File | null,
})
const uploadFormRef = ref<FormInstance>()
const uploading = ref(false)
const uploadProgress = ref(0)
const uploadProcessing = ref(false)

const fileInputRef = ref<HTMLInputElement>()

function levelTagType(level: string) {
  const map: Record<string, string> = {
    block: 'danger',
    warn: 'warning',
    review: 'info',
  }
  return map[level] || 'info'
}

function levelLabel(level: string) {
  const map: Record<string, string> = {
    block: '屏蔽',
    warn: '警告',
    review: '审查',
  }
  return map[level] || level
}

async function fetchGroups() {
  loading.value = true
  try {
    const res = await sensitiveApi.getGroups()
    groups.value = res.data.items || []
  } catch {
    ElMessage.error('加载敏感词库失败')
  } finally {
    loading.value = false
  }
}

async function selectGroup(group: GroupListItem) {
  selectedGroup.value = group
  showPlainWords.value = false
  await fetchGroupDetail(group.id)
}

async function fetchGroupDetail(groupId: string) {
  detailLoading.value = true
  try {
    const res = await sensitiveApi.getGroup(groupId)
    groupDetail.value = res.data
    // Update form with current values
    groupForm.id = res.data.id
    groupForm.name = res.data.name
    groupForm.description = res.data.description || ''
    groupForm.level = res.data.level
    groupForm.is_active = res.data.is_active
    wordEditorText.value = res.data.word_list || ''
  } catch {
    ElMessage.error('加载词库详情失败')
  } finally {
    detailLoading.value = false
  }
}

function openCreateGroup() {
  isEditGroup.value = false
  groupForm.id = ''
  groupForm.name = ''
  groupForm.description = ''
  groupForm.level = 'block'
  groupForm.is_active = true
  groupDialogVisible.value = true
}

function openEditGroup(group: GroupListItem) {
  isEditGroup.value = true
  groupForm.id = group.id
  groupForm.name = group.name
  groupForm.description = group.description || ''
  groupForm.level = group.level
  groupForm.is_active = group.is_active
  groupDialogVisible.value = true
}

async function handleSaveGroup() {
  const valid = await groupFormRef.value?.validate().catch(() => false)
  if (!valid) return

  submitting.value = true
  try {
    if (isEditGroup.value) {
      await sensitiveApi.updateGroup(groupForm.id, {
        name: groupForm.name,
        description: groupForm.description,
        level: groupForm.level,
        is_active: groupForm.is_active,
      })
      ElMessage.success('更新成功')
    } else {
      await sensitiveApi.createGroup({
        name: groupForm.name,
        description: groupForm.description,
        level: groupForm.level,
        is_active: groupForm.is_active,
      })
      ElMessage.success('创建成功')
    }
    groupDialogVisible.value = false
    fetchGroups()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDeleteGroup(group: GroupListItem) {
  try {
    await ElMessageBox.confirm(
      `确定要删除词库「${group.name}」吗？包含的所有敏感词将被移除。`,
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await sensitiveApi.deleteGroup(group.id)
    if (selectedGroup.value?.id === group.id) {
      selectedGroup.value = null
      groupDetail.value = null
    }
    ElMessage.success('删除成功')
    fetchGroups()
  } catch {
    // cancelled
  }
}

async function handleToggleGroup(group: GroupListItem, value: boolean) {
  try {
    await sensitiveApi.toggleGroup(group.id, value)
    group.is_active = value
    ElMessage.success(value ? '已启用' : '已停用')
  } catch {
    ElMessage.error('操作失败')
    // Revert UI on error
    fetchGroups()
  }
}

function handleToggleGroupChange(group: GroupListItem, value: string | number | boolean) {
  handleToggleGroup(group, Boolean(value))
}

async function handleSaveWordList() {
  if (!selectedGroup.value) return

  if (!showPlainWords.value) {
    ElMessage.warning('当前为打码显示，请先切换到明文显示后再编辑保存')
    return
  }

  submitting.value = true
  try {
    await sensitiveApi.updateGroup(selectedGroup.value.id, {
      word_list: wordEditorText.value,
    })
    ElMessage.success('保存成功')
    // Update local word count
    const count = wordEditorText.value.split('\n').filter(w => w.trim()).length
    selectedGroup.value.word_count = count
  } catch {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

function openUploadDialog() {
  uploadForm.name = ''
  uploadForm.description = ''
  uploadForm.level = 'block'
  uploadForm.file = null
  uploadProgress.value = 0
  uploadProcessing.value = false
  uploadDialogVisible.value = true
}

function handleFileSelect(event: Event) {
  const target = event.target as HTMLInputElement
  const file = target.files?.item(0)
  if (file) {
    uploadForm.file = file
  }
}

async function handleUpload() {
  const valid = await uploadFormRef.value?.validate().catch(() => false)
  if (!valid) return

  if (!uploadForm.file) {
    ElMessage.warning('请选择要上传的txt文件')
    return
  }
  const uploadFile: File = uploadForm.file

  uploading.value = true
  uploadProgress.value = 0
  uploadProcessing.value = false
  try {
    await sensitiveApi.uploadWordFile({
      name: uploadForm.name,
      description: uploadForm.description,
      level: uploadForm.level,
      file: uploadFile,
      onProgress: (percent) => {
        uploadProgress.value = percent
        if (percent >= 100) {
          uploadProcessing.value = true
        }
      },
    })
    uploadProgress.value = 100
    uploadProcessing.value = false
    ElMessage.success('上传成功')
    uploadDialogVisible.value = false
    fetchGroups()
  } catch {
    uploadProcessing.value = false
    ElMessage.error('上传失败')
  } finally {
    uploading.value = false
  }
}

function downloadTemplate() {
  const content = '# 敏感词库文件格式说明\n# 每行一个敏感词\n# 以 # 开头的行会被忽略（注释）\n\n# 示例敏感词\n敏感词1\n敏感词2\n敏感词3'
  const blob = new Blob([content], { type: 'text/plain;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = 'sensitive_words_template.txt'
  link.click()
  URL.revokeObjectURL(url)
}

function maskWord(word: string): string {
  const trimmed = word.trim()
  if (!trimmed) return ''
  if (trimmed.length === 1) return '＊'
  if (trimmed.length === 2) return `${trimmed[0]}＊`
  return `${trimmed[0]}${'＊'.repeat(trimmed.length - 2)}${trimmed[trimmed.length - 1]}`
}

const maskedWordEditorText = computed(() => {
  return wordEditorText.value
    .split('\n')
    .map((line) => {
      const trimmed = line.trim()
      if (!trimmed) return ''
      if (trimmed.startsWith('#')) return '#＊＊＊＊（注释）'
      return maskWord(trimmed)
    })
    .join('\n')
})

onMounted(() => {
  fetchGroups()
})
</script>

<template>
  <div class="sensitive-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">敏感词库</h2>
        <p class="page-desc">管理系统敏感词过滤规则，支持txt文件导入</p>
      </div>
      <div class="header-actions">
        <el-button :icon="Upload" @click="openUploadDialog">
          上传词库文件
        </el-button>
        <el-button type="primary" :icon="Plus" @click="openCreateGroup">
          新建词库
        </el-button>
      </div>
    </div>

    <div class="sensitive-layout">
      <!-- 词库列表 -->
      <div class="groups-panel">
        <div class="panel-card">
          <h3 class="panel-title">词库列表</h3>
          <el-table
            v-loading="loading"
            :data="groups"
            highlight-current-row
            @row-click="selectGroup"
            class="groups-table"
            height="calc(100vh - 240px)"
          >
            <el-table-column prop="name" label="词库名称" min-width="120" show-overflow-tooltip />
            <el-table-column label="级别" width="80" align="center">
              <template #default="{ row }">
                <el-tag size="small" :type="(levelTagType(row.level) as any)">
                  {{ levelLabel(row.level) }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="词数" width="70" align="center">
              <template #default="{ row }">{{ row.word_count }}</template>
            </el-table-column>
            <el-table-column label="状态" width="70" align="center">
              <template #default="{ row }">
                <el-switch
                  :model-value="row.is_active"
                  size="small"
                  @change="handleToggleGroupChange(row, $event)"
                  @click.stop
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button type="primary" link size="small" @click.stop="openEditGroup(row)">
                  编辑
                </el-button>
                <el-button type="danger" link size="small" @click.stop="handleDeleteGroup(row)">
                  删除
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <!-- 词库详情/编辑 -->
      <div class="words-panel">
        <div v-if="selectedGroup" v-loading="detailLoading" class="panel-card">
          <div class="words-header">
            <div class="header-info">
              <h3 class="panel-title">{{ selectedGroup.name }}</h3>
              <el-tag size="small" :type="(levelTagType(selectedGroup.level) as any)" class="level-tag">
                {{ levelLabel(selectedGroup.level) }}
              </el-tag>
            </div>
            <div class="header-stats">
              <span class="stat-item">共 {{ selectedGroup.word_count }} 个词</span>
              <span class="stat-item" :class="{ disabled: !selectedGroup.is_active }">
                {{ selectedGroup.is_active ? '已启用' : '已停用' }}
              </span>
            </div>
          </div>

          <div class="word-editor">
            <div class="editor-header">
              <span class="editor-label">敏感词列表</span>
              <div class="editor-controls">
                <span class="editor-hint">默认打码显示，减少有害内容暴露</span>
                <el-switch
                  v-model="showPlainWords"
                  inline-prompt
                  active-text="明文"
                  inactive-text="打码"
                />
              </div>
            </div>
            <el-alert
              v-if="!showPlainWords"
              type="info"
              :closable="false"
              show-icon
              title="当前为打码显示，切换到明文后可编辑与保存"
              class="editor-alert"
            />
            <el-input
              v-if="showPlainWords"
              v-model="wordEditorText"
              type="textarea"
              :rows="20"
              placeholder="在此输入敏感词，每行一个&#10;例如：&#10;敏感词1&#10;敏感词2&#10;敏感词3"
              class="word-textarea"
              resize="none"
            />
            <el-input
              v-else
              :model-value="maskedWordEditorText"
              type="textarea"
              :rows="20"
              class="word-textarea"
              resize="none"
              readonly
            />
            <div class="editor-actions">
              <el-button @click="fetchGroupDetail(selectedGroup.id)">重置</el-button>
              <el-button type="primary" :loading="submitting" :disabled="!showPlainWords" @click="handleSaveWordList">
                保存词列表
              </el-button>
            </div>
          </div>
        </div>

        <div v-else class="panel-card empty-state">
          <el-empty description="请从左侧选择一个词库查看详情">
            <template #image>
              <el-icon :size="60" color="#ccc"><Document /></el-icon>
            </template>
          </el-empty>
        </div>
      </div>
    </div>

    <!-- 新建/编辑词库对话框 -->
    <el-dialog
      v-model="groupDialogVisible"
      :title="isEditGroup ? '编辑词库' : '新建词库'"
      width="560px"
      destroy-on-close
    >
      <el-form ref="groupFormRef" :model="groupForm" :rules="groupRules" label-width="100px">
        <el-form-item label="词库名称" prop="name">
          <el-input v-model="groupForm.name" placeholder="如：政治敏感词" />
        </el-form-item>
        <el-form-item label="处理级别" prop="level">
          <el-select v-model="groupForm.level" placeholder="请选择处理方式" style="width: 100%">
            <el-option label="屏蔽（阻断回答）" value="block" />
            <el-option label="警告（允许但标记）" value="warn" />
            <el-option label="审查（需人工审核）" value="review" />
          </el-select>
          <div class="form-hint">该词库下所有敏感词统一使用此处理方式</div>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="groupForm.description"
            type="textarea"
            :rows="2"
            placeholder="词库用途说明（可选）"
          />
        </el-form-item>
        <el-form-item v-if="isEditGroup" label="启用状态">
          <el-switch v-model="groupForm.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="groupDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSaveGroup">
          {{ isEditGroup ? '保存' : '创建' }}
        </el-button>
      </template>
    </el-dialog>

    <!-- 上传词库文件对话框 -->
    <el-dialog
      v-model="uploadDialogVisible"
      title="上传敏感词库文件"
      width="520px"
      destroy-on-close
    >
      <el-form ref="uploadFormRef" :model="uploadForm" label-width="100px">
        <el-form-item label="词库名称" required>
          <el-input v-model="uploadForm.name" placeholder="如：广告敏感词" />
        </el-form-item>
        <el-form-item label="处理级别" required>
          <el-select v-model="uploadForm.level" placeholder="请选择处理方式" style="width: 100%">
            <el-option label="屏蔽（阻断回答）" value="block" />
            <el-option label="警告（允许但标记）" value="warn" />
            <el-option label="审查（需人工审核）" value="review" />
          </el-select>
        </el-form-item>
        <el-form-item label="描述">
          <el-input
            v-model="uploadForm.description"
            type="textarea"
            :rows="2"
            placeholder="词库用途说明（可选）"
          />
        </el-form-item>
        <el-form-item label="选择文件" required>
          <input
            ref="fileInputRef"
            type="file"
            accept=".txt"
            style="display: none"
            @change="handleFileSelect"
          />
          <div class="upload-area">
            <el-button @click="fileInputRef?.click()">
              <el-icon><Upload /></el-icon>
              选择txt文件
            </el-button>
            <span v-if="uploadForm.file" class="file-name">{{ uploadForm.file.name }}</span>
            <span v-else class="file-hint">支持 UTF-8 或 GBK 编码的txt文件</span>
          </div>
        </el-form-item>
        <el-form-item v-if="uploading || uploadProgress > 0" label="上传进度">
          <div class="upload-progress-wrap">
            <el-progress
              :percentage="uploadProgress"
              :stroke-width="10"
              :show-text="false"
              :indeterminate="uploadProcessing"
              :duration="2"
            />
            <span class="progress-text">{{ uploadProcessing ? '文件已上传，服务器处理中...' : `${uploadProgress}%` }}</span>
          </div>
        </el-form-item>
        <el-form-item>
          <div class="upload-help">
            <p>文件格式要求：</p>
            <ul>
              <li>文件扩展名为 .txt</li>
              <li>每行一个敏感词</li>
              <li>以 # 开头的行会被忽略（注释）</li>
              <li>建议使用 UTF-8 编码</li>
            </ul>
            <el-button link type="primary" @click="downloadTemplate">下载模板文件</el-button>
          </div>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="uploadDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="uploading" @click="handleUpload">
          {{ uploadProcessing ? '处理中...' : '上传' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.sensitive-page {
  height: 100%;
  display: flex;
  flex-direction: column;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
  flex-shrink: 0;
}

.header-left {
  flex: 1;
}

.header-actions {
  display: flex;
  gap: 12px;
}

.page-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 0.875rem;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
}

.sensitive-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  flex: 1;
  min-height: 0;
  overflow: hidden;
}

.groups-panel,
.words-panel {
  min-height: 0;
  overflow: hidden;
}

.panel-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  padding: 20px;
  height: 100%;
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.panel-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0;
}

.groups-table {
  flex: 1;
  overflow: hidden;

  :deep(.el-table__header th) {
    background: var(--bg-secondary, #F4F6FA);
    font-weight: 600;
  }

  :deep(.current-row) {
    background-color: var(--el-color-primary-light-9) !important;
  }
}

.words-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
  padding-bottom: 16px;
  border-bottom: 1px solid var(--border-color, #E2E6ED);
}

.header-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.level-tag {
  font-weight: 500;
}

.header-stats {
  display: flex;
  gap: 16px;
  font-size: 0.8125rem;
  color: var(--text-secondary, #5A5A72);
}

.stat-item {
  &.disabled {
    color: var(--el-color-danger);
  }
}

.word-editor {
  flex: 1;
  display: flex;
  flex-direction: column;
  min-height: 0;
}

.editor-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.editor-controls {
  display: flex;
  align-items: center;
  gap: 12px;
}

.editor-label {
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary, #1A1A2E);
}

.editor-hint {
  font-size: 0.75rem;
  color: var(--text-secondary, #9E9EB3);
}

.editor-alert {
  margin-bottom: 8px;
}

.word-textarea {
  flex: 1;

  :deep(.el-textarea__inner) {
    font-family: monospace;
    line-height: 1.6;
  }
}

.editor-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #E2E6ED);
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
}

.form-hint {
  font-size: 0.75rem;
  color: var(--text-secondary, #9E9EB3);
  margin-top: 4px;
  line-height: 1.4;
}

.upload-area {
  display: flex;
  align-items: center;
  gap: 12px;
}

.file-name {
  font-size: 0.8125rem;
  color: var(--text-primary, #1A1A2E);
}

.file-hint {
  font-size: 0.8125rem;
  color: var(--text-secondary, #9E9EB3);
}

.upload-help {
  background: var(--bg-secondary, #F4F6FA);
  border-radius: 8px;
  padding: 12px 16px;
  font-size: 0.8125rem;
  color: var(--text-secondary, #5A5A72);
  line-height: 1.6;

  p {
    margin: 0 0 8px;
    font-weight: 500;
    color: var(--text-primary, #1A1A2E);
  }

  ul {
    margin: 0 0 12px;
    padding-left: 18px;
  }

  li {
    margin-bottom: 4px;
  }
}

.upload-progress-wrap {
  width: 100%;
  display: flex;
  align-items: center;
  gap: 10px;
}

.progress-text {
  min-width: 48px;
  text-align: right;
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

@media (max-width: 992px) {
  .sensitive-layout {
    grid-template-columns: 1fr;
    grid-template-rows: 1fr 1fr;
  }
}
</style>
