<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Delete } from '@element-plus/icons-vue'
import * as sensitiveApi from '@/api/admin/sensitive'
import type { FormInstance, FormRules } from 'element-plus'

interface GroupItem {
  id: string
  name: string
  description: string | null
  is_active: boolean
  word_count: number
}

interface WordItem {
  id: string
  word: string
  level: string
  created_at: string
}

const loading = ref(false)
const groups = ref<GroupItem[]>([])
const selectedGroup = ref<GroupItem | null>(null)

const words = ref<WordItem[]>([])
const wordsTotal = ref(0)
const wordsPage = ref(1)
const wordsLoading = ref(false)

const groupDialogVisible = ref(false)
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
    const data = res.data as any
    groups.value = data.items || data || []
  } catch {
    ElMessage.error('加载敏感词库失败')
  } finally {
    loading.value = false
  }
}

async function selectGroup(group: GroupItem) {
  selectedGroup.value = group
  wordsPage.value = 1
  await fetchWords()
}

async function fetchWords() {
  if (!selectedGroup.value) return
  wordsLoading.value = true
  try {
    const res = await sensitiveApi.getGroup(selectedGroup.value.id)
    const data = res.data as any
    words.value = data.words?.items || []
    wordsTotal.value = data.words?.total || 0
  } catch {
    ElMessage.error('加载敏感词失败')
  } finally {
    wordsLoading.value = false
  }
}

function openCreateGroup() {
  isEditGroup.value = false
  groupForm.id = ''
  groupForm.name = ''
  groupDialogVisible.value = true
}

async function handleSaveGroup() {
  const valid = await groupFormRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await sensitiveApi.createGroup({ name: groupForm.name })
    ElMessage.success('创建成功')
    groupDialogVisible.value = false
    fetchGroups()
  } catch {
    ElMessage.error('操作失败')
  } finally {
    submitting.value = false
  }
}

async function handleDeleteGroup(group: GroupItem) {
  try {
    await ElMessageBox.confirm(
      `确定要删除词库「${group.name}」吗？包含的所有敏感词将被移除。`,
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' }
    )
    await sensitiveApi.deleteGroup(group.id)
    if (selectedGroup.value?.id === group.id) {
      selectedGroup.value = null
      words.value = []
    }
    ElMessage.success('删除成功')
    fetchGroups()
  } catch {
    // cancelled
  }
}

async function handleToggleGroup(group: GroupItem) {
  try {
    await sensitiveApi.toggleGroup(group.id, !group.is_active)
    group.is_active = !group.is_active
    ElMessage.success(group.is_active ? '已启用' : '已停用')
  } catch {
    ElMessage.error('操作失败')
  }
}

async function addWord() {
  if (!newWord.value.trim() || !selectedGroup.value) return
  try {
    await sensitiveApi.addWord({
      group_id: selectedGroup.value.id,
      word: newWord.value.trim(),
      level: newWordLevel.value,
    })
    newWord.value = ''
    fetchWords()
    // Update word count in group list
    if (selectedGroup.value) {
      selectedGroup.value.word_count++
    }
  } catch {
    ElMessage.error('添加失败')
  }
}

async function removeWord(word: WordItem) {
  try {
    await sensitiveApi.deleteWord(word.id)
    fetchWords()
    if (selectedGroup.value) {
      selectedGroup.value.word_count = Math.max(0, selectedGroup.value.word_count - 1)
    }
  } catch {
    ElMessage.error('删除失败')
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
              <template #default="{ row }">{{ row.word_count }}</template>
            </el-table-column>
            <el-table-column label="状态" width="70" align="center">
              <template #default="{ row }">
                <el-switch
                  :model-value="row.is_active"
                  size="small"
                  @click.stop="handleToggleGroup(row)"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="80">
              <template #default="{ row }">
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
            <div v-loading="wordsLoading" class="words-list">
              <div
                v-for="word in words"
                :key="word.id"
                class="word-item"
              >
                <span class="word-text">{{ word.word }}</span>
                <el-tag size="small" :type="(levelTagType(word.level) as any)">
                  {{ levelLabel(word.level) }}
                </el-tag>
                <el-button
                  type="danger"
                  link
                  size="small"
                  :icon="Delete"
                  @click="removeWord(word)"
                />
              </div>
              <div v-if="words.length === 0 && !wordsLoading" class="words-empty">
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
