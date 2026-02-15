<script setup lang="ts">
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import * as sensitiveApi from '@/api/admin/sensitive'
import type { SensitiveWordGroup } from '@/types/admin'
import type { FormInstance, FormRules } from 'element-plus'

const loading = ref(false)
const groups = ref<SensitiveWordGroup[]>([])
const selectedGroup = ref<SensitiveWordGroup | null>(null)

const groupDialogVisible = ref(false)
const wordDialogVisible = ref(false)
const groupFormRef = ref<FormInstance>()
const submitting = ref(false)
const isEditGroup = ref(false)

const groupForm = reactive({
  id: '',
  name: '',
})

const groupRules: FormRules = {
  name: [{ required: true, message: '请输入词库名称', trigger: 'blur' }],
}

const newWord = ref('')
const newWordLevel = ref<string>('block')

interface SensitiveWord {
  text: string
  level: 'block' | 'warn' | 'review'
}

const wordsList = computed<SensitiveWord[]>(() => {
  if (!selectedGroup.value) return []
  return selectedGroup.value.words.map(w => {
    const parts = w.split(':')
    if (parts.length === 2) {
      return { text: parts[0], level: parts[1] as SensitiveWord['level'] }
    }
    return { text: w, level: 'block' as const }
  })
})

function levelTagType(level: string) {
  const map: Record<string, string> = {
    block: 'danger',
    warn: 'warning',
    review: '',
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
    groups.value = res.data
  } catch {
    ElMessage.error('加载敏感词库失败')
  } finally {
    loading.value = false
  }
}

function selectGroup(group: SensitiveWordGroup) {
  selectedGroup.value = group
}

async function toggleGroupStatus(group: SensitiveWordGroup) {
  try {
    await sensitiveApi.toggleGroup(group.id, !group.enabled)
    group.enabled = !group.enabled
    ElMessage.success(group.enabled ? '已启用' : '已停用')
  } catch {
    ElMessage.error('操作失败')
  }
}

function openCreateGroup() {
  isEditGroup.value = false
  groupForm.id = ''
  groupForm.name = ''
  groupDialogVisible.value = true
}

function openEditGroup(group: SensitiveWordGroup) {
  isEditGroup.value = true
  groupForm.id = group.id
  groupForm.name = group.name
  groupDialogVisible.value = true
}

async function handleSaveGroup() {
  const valid = await groupFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    if (isEditGroup.value) {
      await sensitiveApi.updateGroup(groupForm.id, { name: groupForm.name })
      ElMessage.success('修改成功')
    } else {
      await sensitiveApi.createGroup({ name: groupForm.name, words: [], enabled: true })
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

async function handleDeleteGroup(group: SensitiveWordGroup) {
  try {
    await ElMessageBox.confirm(
      `确定要删除词库「${group.name}」吗？包含的所有敏感词将被移除。`,
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await sensitiveApi.deleteGroup(group.id)
    if (selectedGroup.value?.id === group.id) {
      selectedGroup.value = null
    }
    ElMessage.success('删除成功')
    fetchGroups()
  } catch {
    // cancelled
  }
}

function addWord() {
  if (!newWord.value.trim() || !selectedGroup.value) return
  const wordEntry = `${newWord.value.trim()}:${newWordLevel.value}`
  if (selectedGroup.value.words.includes(wordEntry)) {
    ElMessage.warning('该词已存在')
    return
  }
  selectedGroup.value.words.push(wordEntry)
  saveGroupWords()
  newWord.value = ''
}

function removeWord(index: number) {
  if (!selectedGroup.value) return
  selectedGroup.value.words.splice(index, 1)
  saveGroupWords()
}

async function saveGroupWords() {
  if (!selectedGroup.value) return
  try {
    await sensitiveApi.updateGroup(selectedGroup.value.id, {
      words: selectedGroup.value.words,
    })
  } catch {
    ElMessage.error('保存失败')
  }
}

onMounted(() => {
  fetchGroups()
})
</script>

<template>
  <div class="sensitive-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">敏感词库</h2>
        <p class="page-desc">管理系统敏感词过滤规则</p>
      </div>
      <el-button type="primary" :icon="Plus" @click="openCreateGroup">
        新建词库
      </el-button>
    </div>

    <div class="sensitive-layout">
      <div class="groups-panel">
        <div class="panel-card">
          <h3 class="panel-title">词库列表</h3>
          <el-table
            v-loading="loading"
            :data="groups"
            highlight-current-row
            @row-click="selectGroup"
            class="groups-table"
          >
            <el-table-column prop="name" label="词库名称" min-width="120" />
            <el-table-column label="词数" width="70" align="center">
              <template #default="{ row }">{{ row.words.length }}</template>
            </el-table-column>
            <el-table-column label="状态" width="70" align="center">
              <template #default="{ row }">
                <el-switch
                  :model-value="row.enabled"
                  size="small"
                  @click.stop="toggleGroupStatus(row)"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100">
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

      <div class="words-panel">
        <div class="panel-card">
          <template v-if="selectedGroup">
            <div class="words-header">
              <h3 class="panel-title">{{ selectedGroup.name }} — 敏感词列表</h3>
            </div>
            <div class="add-word-bar">
              <el-input
                v-model="newWord"
                placeholder="输入敏感词"
                clearable
                @keyup.enter="addWord"
              />
              <el-select v-model="newWordLevel" style="width: 100px">
                <el-option label="屏蔽" value="block" />
                <el-option label="警告" value="warn" />
                <el-option label="审查" value="review" />
              </el-select>
              <el-button type="primary" @click="addWord">添加</el-button>
            </div>
            <div class="words-list">
              <div
                v-for="(word, index) in wordsList"
                :key="index"
                class="word-item"
              >
                <span class="word-text">{{ word.text }}</span>
                <el-tag size="small" :type="levelTagType(word.level)">
                  {{ levelLabel(word.level) }}
                </el-tag>
                <el-button
                  type="danger"
                  link
                  size="small"
                  :icon="Delete"
                  @click="removeWord(index)"
                />
              </div>
              <div v-if="wordsList.length === 0" class="words-empty">
                暂无敏感词，请添加
              </div>
            </div>
          </template>
          <template v-else>
            <div class="words-empty-state">
              <p>请从左侧选择一个词库查看敏感词</p>
            </div>
          </template>
        </div>
      </div>
    </div>

    <el-dialog
      v-model="groupDialogVisible"
      :title="isEditGroup ? '编辑词库' : '新建词库'"
      width="400px"
      destroy-on-close
    >
      <el-form ref="groupFormRef" :model="groupForm" :rules="groupRules" label-width="80px">
        <el-form-item label="词库名称" prop="name">
          <el-input v-model="groupForm.name" placeholder="如：政治敏感词" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="groupDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="handleSaveGroup">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.sensitive-page {
  max-width: 1200px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 20px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
}

.sensitive-layout {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.panel-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  padding: 20px;
  height: 100%;
}

.panel-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 16px;
}

.groups-table {
  :deep(.el-table__header th) {
    background: var(--bg-secondary, #F4F6FA);
    font-weight: 600;
  }
}

.words-header {
  margin-bottom: 12px;
}

.add-word-bar {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
}

.words-list {
  max-height: 400px;
  overflow-y: auto;
}

.word-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 8px 12px;
  border-radius: 6px;
  transition: background 0.15s;

  &:hover {
    background: var(--bg-secondary, #F4F6FA);
  }
}

.word-text {
  flex: 1;
  font-size: 14px;
  color: var(--text-primary, #1A1A2E);
}

.words-empty,
.words-empty-state {
  text-align: center;
  padding: 48px 24px;
  color: var(--text-secondary, #9E9EB3);
  font-size: 14px;
}

@media (max-width: 768px) {
  .sensitive-layout {
    grid-template-columns: 1fr;
  }
}
</style>
