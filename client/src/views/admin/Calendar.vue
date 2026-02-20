<script setup lang="ts">
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Edit, Check, Plus, Calendar, Delete } from '@element-plus/icons-vue'
import * as calendarApi from '@/api/admin/calendar'
import type { CalendarPeriod } from '@/types/admin'
import type { FormInstance, FormRules } from 'element-plus'

const loading = ref(false)
const periods = ref<CalendarPeriod[]>([])
const years = ref<number[]>([])
const currentYear = ref<number | ''>('')

// Edit / Create dialog
const dialogVisible = ref(false)
const dialogMode = ref<'create' | 'edit'>('create')
const formRef = ref<FormInstance>()
const submitting = ref(false)

const form = reactive({
  id: '',
  period_name: '',
  start_month: null as number | null,
  end_month: null as number | null,
  year: new Date().getFullYear(),
  style: 'general' as string,
  description: '',
  keywords: '',
  additional_prompt: '',
  is_active: true,
})

const rules: FormRules = {
  period_name: [{ required: true, message: '请输入阶段名称', trigger: 'blur' }],
  start_month: [{ required: true, message: '请选择开始月份', trigger: 'change' }],
  end_month: [{ required: true, message: '请选择结束月份', trigger: 'change' }],
  year: [{ required: true, message: '请输入年度', trigger: 'blur' }],
  style: [{ required: true, message: '请选择话术风格', trigger: 'change' }],
}

const monthOptions = Array.from({ length: 12 }, (_, i) => ({
  label: `${i + 1}月`,
  value: i + 1,
}))

const dialogTitle = computed(() => dialogMode.value === 'create' ? '新增招生阶段' : '编辑招生阶段')

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

function formatMonthRange(period: CalendarPeriod) {
  return `${period.start_month}月 — ${period.end_month}月`
}

function isCurrentPeriod(period: CalendarPeriod) {
  const now = new Date()
  const currentMonth = now.getMonth() + 1
  const currentYearVal = now.getFullYear()
  if (period.year !== currentYearVal) return false
  if (period.start_month <= period.end_month) {
    return currentMonth >= period.start_month && currentMonth <= period.end_month
  }
  // Cross-year range (e.g., 11 -> 2)
  return currentMonth >= period.start_month || currentMonth <= period.end_month
}

async function fetchYears() {
  try {
    const res = await calendarApi.getYears()
    years.value = res.data.years || []
  } catch {
    // silently fail
  }
}

async function fetchPeriods() {
  loading.value = true
  try {
    const yearParam = currentYear.value || undefined
    const res = await calendarApi.getPeriods(yearParam as number | undefined)
    periods.value = res.data.items || []
  } catch {
    ElMessage.error('加载招生日历失败')
  } finally {
    loading.value = false
  }
}

function handleYearChange() {
  fetchPeriods()
}

function openCreate() {
  dialogMode.value = 'create'
  form.id = ''
  form.period_name = ''
  form.start_month = null
  form.end_month = null
  form.year = currentYear.value || new Date().getFullYear()
  form.style = 'general'
  form.description = ''
  form.keywords = ''
  form.additional_prompt = ''
  form.is_active = true
  dialogVisible.value = true
}

function openEdit(period: CalendarPeriod) {
  dialogMode.value = 'edit'
  form.id = period.id
  form.period_name = period.period_name
  form.start_month = period.start_month
  form.end_month = period.end_month
  form.year = period.year
  form.style = period.tone_config?.style || 'general'
  form.description = period.tone_config?.description || ''
  form.keywords = (period.tone_config?.keywords || []).join(', ')
  form.additional_prompt = period.additional_prompt || ''
  form.is_active = period.is_active
  dialogVisible.value = true
}

async function handleSubmit() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  submitting.value = true

  const toneConfig = {
    style: form.style,
    description: form.description,
    keywords: form.keywords ? form.keywords.split(',').map(k => k.trim()).filter(Boolean) : [],
  }

  try {
    if (dialogMode.value === 'create') {
      await calendarApi.createPeriod({
        period_name: form.period_name,
        start_month: form.start_month!,
        end_month: form.end_month!,
        year: form.year,
        tone_config: toneConfig,
        additional_prompt: form.additional_prompt || null,
        is_active: form.is_active,
      })
      ElMessage.success('创建成功')
    } else {
      await calendarApi.updatePeriod(form.id, {
        period_name: form.period_name,
        start_month: form.start_month!,
        end_month: form.end_month!,
        year: form.year,
        tone_config: toneConfig,
        additional_prompt: form.additional_prompt || null,
        is_active: form.is_active,
      })
      ElMessage.success('保存成功')
    }
    dialogVisible.value = false
    fetchYears()
    fetchPeriods()
  } catch {
    ElMessage.error(dialogMode.value === 'create' ? '创建失败' : '保存失败')
  } finally {
    submitting.value = false
  }
}

async function handleDelete(period: CalendarPeriod) {
  try {
    await ElMessageBox.confirm(
      `确定要删除「${period.period_name}」吗？`,
      '删除确认',
      { type: 'error', confirmButtonText: '删除', cancelButtonText: '取消' },
    )
    await calendarApi.deletePeriod(period.id)
    ElMessage.success('删除成功')
    fetchYears()
    fetchPeriods()
  } catch {
    // cancelled
  }
}

onMounted(async () => {
  await fetchYears()
  if (years.value.length > 0) {
    const thisYear = new Date().getFullYear()
    currentYear.value = years.value.includes(thisYear) ? thisYear : (years.value[0] ?? '')
  }
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
      <div class="header-actions">
        <el-select
          v-if="years.length > 0"
          v-model="currentYear"
          placeholder="全部年度"
          clearable
          style="width: 120px; margin-right: 12px;"
          @change="handleYearChange"
        >
          <el-option
            v-for="y in years"
            :key="y"
            :label="`${y}年`"
            :value="y"
          />
        </el-select>
        <el-button type="primary" :icon="Plus" @click="openCreate">新增阶段</el-button>
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
          <div class="timeline-marker" :style="{ background: periodColor(period.tone_config?.style || 'general') }">
            <span>{{ index + 1 }}</span>
          </div>
          <div class="timeline-connector" v-if="index < periods.length - 1" />

          <div class="period-card">
            <div class="period-header">
              <div class="period-title-row">
                <h3 class="period-name">{{ period.period_name }}</h3>
                <el-tag v-if="isCurrentPeriod(period)" type="success" size="small" effect="dark">
                  当前阶段
                </el-tag>
                <el-tag :type="(styleTagType(period.tone_config?.style || 'general') as any)" size="small">
                  {{ styleLabel(period.tone_config?.style || 'general') }}
                </el-tag>
                <el-tag v-if="!period.is_active" type="info" size="small">已停用</el-tag>
              </div>
              <div class="period-actions">
                <el-button text :icon="Edit" @click="openEdit(period)" />
                <el-button text type="danger" :icon="Delete" @click="handleDelete(period)" />
              </div>
            </div>
            <div class="period-dates">
              {{ period.year }}年 {{ formatMonthRange(period) }}
            </div>
            <p v-if="period.tone_config?.description" class="period-desc">
              {{ period.tone_config.description }}
            </p>
            <div class="period-style-hint">
              话术重点：{{ styleDescription(period.tone_config?.style || 'general') }}
            </div>
            <div v-if="period.tone_config?.keywords?.length" class="period-keywords">
              <el-tag
                v-for="keyword in period.tone_config.keywords"
                :key="keyword"
                size="small"
                type="info"
                class="keyword-tag"
              >
                {{ keyword }}
              </el-tag>
            </div>
            <p v-if="period.additional_prompt" class="period-prompt">
              附加Prompt：{{ period.additional_prompt }}
            </p>
          </div>
        </div>
      </div>
    </div>

    <!-- Create / Edit Dialog -->
    <el-dialog
      v-model="dialogVisible"
      :title="dialogTitle"
      width="560px"
      destroy-on-close
    >
      <el-form ref="formRef" :model="form" :rules="rules" label-width="100px">
        <el-form-item label="阶段名称" prop="period_name">
          <el-input v-model="form.period_name" placeholder="如：备考冲刺期" />
        </el-form-item>
        <el-form-item label="年度" prop="year">
          <el-input-number v-model="form.year" :min="2020" :max="2099" style="width: 100%" />
        </el-form-item>
        <el-form-item label="开始月份" prop="start_month">
          <el-select v-model="form.start_month" placeholder="选择月份" style="width: 100%">
            <el-option
              v-for="m in monthOptions"
              :key="m.value"
              :label="m.label"
              :value="m.value"
            />
          </el-select>
        </el-form-item>
        <el-form-item label="结束月份" prop="end_month">
          <el-select v-model="form.end_month" placeholder="选择月份" style="width: 100%">
            <el-option
              v-for="m in monthOptions"
              :key="m.value"
              :label="m.label"
              :value="m.value"
            />
          </el-select>
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
          <el-input v-model="form.description" type="textarea" :rows="2" placeholder="该阶段的简要描述" />
        </el-form-item>
        <el-form-item label="关键词">
          <el-input v-model="form.keywords" placeholder="用逗号分隔多个关键词" />
        </el-form-item>
        <el-form-item label="附加Prompt">
          <el-input v-model="form.additional_prompt" type="textarea" :rows="2" placeholder="该阶段的额外Prompt指令（选填）" />
        </el-form-item>
        <el-form-item label="启用">
          <el-switch v-model="form.is_active" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :icon="Check" :loading="submitting" @click="handleSubmit">
          {{ dialogMode === 'create' ? '创建' : '保存' }}
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<style lang="scss" scoped>
.calendar-page {
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 24px;
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

.header-actions {
  display: flex;
  align-items: center;
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
  font-size: 0.875rem;
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
  font-size: 0.875rem;
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

  &:hover {
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
  font-size: 1.0625rem;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0;
}

.period-actions {
  display: flex;
  gap: 4px;
}

.period-dates {
  font-size: 0.8125rem;
  color: var(--text-secondary, #5A5A72);
  margin-bottom: 8px;
}

.period-desc {
  font-size: 0.875rem;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 8px;
  line-height: 1.6;
}

.period-style-hint {
  font-size: 0.8125rem;
  color: var(--bnu-blue, #003DA5);
  font-weight: 500;
  margin-bottom: 8px;
}

.period-keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 8px;
}

.keyword-tag {
  font-size: 0.75rem;
}

.period-prompt {
  font-size: 0.8125rem;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
  padding: 8px 12px;
  background: var(--bg-secondary, #F4F6FA);
  border-radius: 6px;
  line-height: 1.5;
}
</style>
