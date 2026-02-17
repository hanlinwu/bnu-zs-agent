<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Edit, Check, Plus, Calendar } from '@element-plus/icons-vue'
import * as calendarApi from '@/api/admin/calendar'
import type { CalendarPeriod } from '@/types/admin'
import type { FormInstance, FormRules } from 'element-plus'

const loading = ref(false)
const periods = ref<CalendarPeriod[]>([])
const editingPeriod = ref<CalendarPeriod | null>(null)
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  id: '',
  name: '',
  startDate: '',
  endDate: '',
  style: '' as CalendarPeriod['style'],
  description: '',
  keywords: '' as string,
  enabled: true,
})

const rules: FormRules = {
  name: [{ required: true, message: '请输入阶段名称', trigger: 'blur' }],
  startDate: [{ required: true, message: '请选择开始日期', trigger: 'change' }],
  endDate: [{ required: true, message: '请选择结束日期', trigger: 'change' }],
  style: [{ required: true, message: '请选择话术风格', trigger: 'change' }],
}

function styleLabel(style: string) {
  const map: Record<string, string> = {
    motivational: '激励型',
    guidance: '指导型',
    enrollment: '服务型',
    general: '常态型',
  }
  return map[style] || style
}

function styleTagType(style: string): 'success' | 'warning' | 'info' {
  const map: Record<string, string> = {
    motivational: 'info',
    guidance: 'success',
    enrollment: 'warning',
    general: 'info',
  }
  return (map[style] as 'success' | 'warning' | 'info') || 'info'
}

function styleDescription(style: string) {
  const map: Record<string, string> = {
    motivational: '激励、备考建议、专业前景',
    guidance: '志愿填报、分数线预测、报名指南',
    enrollment: '录取结果查询、入学准备清单',
    general: '校园文化、师资力量、国际交流',
  }
  return map[style] || ''
}

function periodColor(style: string) {
  const map: Record<string, string> = {
    motivational: '#003DA5',
    guidance: '#2E7D32',
    enrollment: '#C4972F',
    general: '#6B7B8D',
  }
  return map[style] || '#6B7B8D'
}

function formatDate(date: string) {
  return new Date(date).toLocaleDateString('zh-CN', {
    month: 'long',
    day: 'numeric',
  })
}

function isCurrentPeriod(period: CalendarPeriod) {
  const now = new Date()
  const start = new Date(period.startDate)
  const end = new Date(period.endDate)
  return now >= start && now <= end
}

async function fetchPeriods() {
  loading.value = true
  try {
    const res = await calendarApi.getPeriods()
    const raw = (res.data as any[] | { items?: any[] })
    const list = Array.isArray(raw) ? raw : (raw.items || [])
    // Map backend fields (period_name, start_month, end_month) to frontend CalendarPeriod
    periods.value = list.map((item: any) => ({
      id: item.id,
      name: item.name || item.period_name || '',
      startDate: item.startDate || (item.start_month ? `2026-${String(item.start_month).padStart(2, '0')}-01` : ''),
      endDate: item.endDate || (item.end_month ? `2026-${String(item.end_month).padStart(2, '0')}-28` : ''),
      style: (item.style || item.tone_config?.style || 'general') as CalendarPeriod['style'],
      description: item.description || item.tone_config?.description || '',
      keywords: item.keywords || item.tone_config?.keywords || [],
      enabled: item.enabled ?? item.is_active ?? true,
      createdAt: item.createdAt || item.created_at || '',
      updatedAt: item.updatedAt || item.updated_at || '',
    }))
  } catch {
    ElMessage.error('加载招生日历失败')
  } finally {
    loading.value = false
  }
}

function editPeriod(period: CalendarPeriod) {
  editingPeriod.value = period
  form.id = period.id
  form.name = period.name
  form.startDate = period.startDate
  form.endDate = period.endDate
  form.style = period.style
  form.description = period.description
  form.keywords = period.keywords.join(', ')
  form.enabled = period.enabled
}

function cancelEdit() {
  editingPeriod.value = null
}

function openCreate() {
  // TODO: implement create calendar period dialog
  ElMessage.info('请通过数据库或 API 添加招生日历阶段')
}

async function savePeriod() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true
  try {
    await calendarApi.updatePeriod(form.id, {
      name: form.name,
      startDate: form.startDate,
      endDate: form.endDate,
      style: form.style,
      description: form.description,
      keywords: form.keywords.split(',').map(k => k.trim()).filter(Boolean),
      enabled: form.enabled,
    })
    ElMessage.success('保存成功')
    editingPeriod.value = null
    fetchPeriods()
  } catch {
    ElMessage.error('保存失败')
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  fetchPeriods()
})
</script>

<template>
  <div class="calendar-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">招生日历</h2>
        <p class="page-desc">管理招生各阶段的话术风格与重点内容</p>
      </div>
    </div>

    <div v-loading="loading" class="calendar-content">
      <div v-if="periods.length === 0 && !loading" class="empty-state">
        <el-icon :size="48" color="#E2E6ED"><Calendar /></el-icon>
        <p class="empty-text">暂无招生日历数据</p>
        <el-button type="primary" :icon="Plus" @click="openCreate">添加阶段</el-button>
      </div>

      <div v-else class="timeline">
        <div
          v-for="(period, index) in periods"
          :key="period.id"
          class="timeline-item"
          :class="{ 'timeline-item--current': isCurrentPeriod(period) }"
        >
          <div class="timeline-marker" :style="{ background: periodColor(period.style) }">
            <span>{{ index + 1 }}</span>
          </div>
          <div class="timeline-connector" v-if="index < periods.length - 1" />

          <div class="period-card" :class="{ 'period-card--editing': editingPeriod?.id === period.id }">
            <template v-if="editingPeriod?.id !== period.id">
              <div class="period-header">
                <div class="period-title-row">
                  <h3 class="period-name">{{ period.name }}</h3>
                  <el-tag v-if="isCurrentPeriod(period)" type="success" size="small" effect="dark">
                    当前阶段
                  </el-tag>
                  <el-tag :type="(styleTagType(period.style) as any)" size="small">
                    {{ styleLabel(period.style) }}
                  </el-tag>
                </div>
                <el-button text :icon="Edit" @click="editPeriod(period)" />
              </div>
              <div class="period-dates">
                {{ formatDate(period.startDate) }} — {{ formatDate(period.endDate) }}
              </div>
              <p class="period-desc">{{ period.description }}</p>
              <div class="period-style-hint">
                话术重点：{{ styleDescription(period.style) }}
              </div>
              <div v-if="period.keywords.length" class="period-keywords">
                <el-tag
                  v-for="keyword in period.keywords"
                  :key="keyword"
                  size="small"
                  type="info"
                  class="keyword-tag"
                >
                  {{ keyword }}
                </el-tag>
              </div>
            </template>

            <template v-else>
              <el-form ref="formRef" :model="form" :rules="rules" label-width="80px">
                <el-form-item label="阶段名称" prop="name">
                  <el-input v-model="form.name" />
                </el-form-item>
                <el-form-item label="开始日期" prop="startDate">
                  <el-date-picker
                    v-model="form.startDate"
                    type="date"
                    value-format="YYYY-MM-DD"
                    style="width: 100%"
                  />
                </el-form-item>
                <el-form-item label="结束日期" prop="endDate">
                  <el-date-picker
                    v-model="form.endDate"
                    type="date"
                    value-format="YYYY-MM-DD"
                    style="width: 100%"
                  />
                </el-form-item>
                <el-form-item label="话术风格" prop="style">
                  <el-select v-model="form.style" style="width: 100%">
                    <el-option label="激励型 — 备考期" value="motivational" />
                    <el-option label="指导型 — 报名期" value="guidance" />
                    <el-option label="服务型 — 录取期" value="enrollment" />
                    <el-option label="常态型 — 全年" value="general" />
                  </el-select>
                </el-form-item>
                <el-form-item label="阶段描述">
                  <el-input v-model="form.description" type="textarea" :rows="2" />
                </el-form-item>
                <el-form-item label="关键词">
                  <el-input v-model="form.keywords" placeholder="用逗号分隔多个关键词" />
                </el-form-item>
                <el-form-item label="启用">
                  <el-switch v-model="form.enabled" />
                </el-form-item>
                <el-form-item>
                  <el-button type="primary" :icon="Check" :loading="submitting" @click="savePeriod">
                    保存
                  </el-button>
                  <el-button @click="cancelEdit">取消</el-button>
                </el-form-item>
              </el-form>
            </template>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.calendar-page {
}

.page-header {
  margin-bottom: 24px;
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

.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 80px 20px;
  gap: 16px;
}

.empty-text {
  font-size: 14px;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
}

.timeline {
  position: relative;
  padding-left: 48px;
}

.timeline-item {
  position: relative;
  margin-bottom: 24px;

  &:last-child {
    margin-bottom: 0;
  }

  &--current .period-card {
    border-color: #2E7D32;
    box-shadow: 0 0 0 1px rgba(46, 125, 50, 0.15);
  }
}

.timeline-marker {
  position: absolute;
  left: -48px;
  top: 20px;
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #ffffff;
  font-size: 14px;
  font-weight: 700;
  z-index: 1;
}

.timeline-connector {
  position: absolute;
  left: -33px;
  top: 52px;
  width: 2px;
  height: calc(100% - 12px);
  background: var(--border-color, #E2E6ED);
}

.period-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  padding: 20px;
  transition: all 0.2s;

  &--editing {
    border-color: var(--bnu-blue, #003DA5);
  }

  &:hover:not(&--editing) {
    box-shadow: var(--shadow-sm, 0 2px 8px rgba(0, 0, 0, 0.06));
  }
}

.period-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 8px;
}

.period-title-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.period-name {
  font-size: 17px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0;
}

.period-dates {
  font-size: 13px;
  color: var(--text-secondary, #5A5A72);
  margin-bottom: 8px;
}

.period-desc {
  font-size: 14px;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 8px;
  line-height: 1.6;
}

.period-style-hint {
  font-size: 13px;
  color: var(--bnu-blue, #003DA5);
  font-weight: 500;
  margin-bottom: 8px;
}

.period-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.keyword-tag {
  font-size: 12px;
}
</style>
