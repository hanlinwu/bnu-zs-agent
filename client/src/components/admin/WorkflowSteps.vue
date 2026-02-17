<script setup lang="ts">
/**
 * Unified workflow step display component.
 * Used across Workflows, KnowledgeReview, and Media pages.
 *
 * Props:
 *   steps - Array of workflow step objects [{step, name, role_code}]
 *   currentStep - Current active step (0 = not started, 1+ = in progress/completed)
 *   mode - "tags" for compact tag list, "progress" for step-by-step progress bar
 */
import type { WorkflowStep } from '@/api/admin/workflow'

const props = withDefaults(defineProps<{
  steps: WorkflowStep[]
  currentStep?: number
  mode?: 'tags' | 'progress'
}>(), {
  currentStep: 0,
  mode: 'tags',
})

const roleLabels: Record<string, string> = {
  reviewer: '审核员',
  admin: '管理员',
  super_admin: '超级管理员',
  teacher: '招生老师',
}

function stepTagType(step: WorkflowStep): 'success' | 'warning' | 'info' | 'danger' {
  if (props.mode === 'tags') return 'info'
  // In progress mode, color by completion status
  if (step.step < props.currentStep) return 'success'
  if (step.step === props.currentStep) return 'warning'
  return 'info'
}
</script>

<template>
  <div v-if="steps && steps.length > 0" class="workflow-steps" :class="[`mode-${mode}`]">
    <template v-if="mode === 'tags'">
      <el-tag
        v-for="s in steps"
        :key="s.step"
        size="small"
        :type="stepTagType(s)"
        class="step-tag"
      >
        {{ s.step }}. {{ s.name }}
      </el-tag>
    </template>
    <template v-else>
      <div
        v-for="s in steps"
        :key="s.step"
        class="step-item"
        :class="{
          'step-completed': s.step < currentStep,
          'step-current': s.step === currentStep,
          'step-pending': s.step > currentStep,
        }"
      >
        <div class="step-num">
          <el-icon v-if="s.step < currentStep" class="step-check">
            <svg viewBox="0 0 1024 1024" width="12" height="12"><path d="M384 691.2L204.8 512l-60.16 60.16L384 811.52l512-512-60.16-60.16z" fill="currentColor"/></svg>
          </el-icon>
          <span v-else>{{ s.step }}</span>
        </div>
        <div class="step-info">
          <span class="step-name">{{ s.name }}</span>
          <span class="step-role">{{ roleLabels[s.role_code] || s.role_code }}</span>
        </div>
        <div v-if="s.step < steps.length" class="step-connector" />
      </div>
    </template>
  </div>
  <span v-else class="workflow-steps-empty">-</span>
</template>

<style lang="scss" scoped>
.workflow-steps {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-wrap: wrap;

  &.mode-progress {
    gap: 0;
    flex-wrap: nowrap;
  }
}

.step-tag {
  font-size: 12px;
}

.workflow-steps-empty {
  color: var(--text-secondary, #9E9EB3);
}

// Progress mode styles
.step-item {
  display: flex;
  align-items: center;
  gap: 6px;
  position: relative;
}

.step-num {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  font-weight: 600;
  flex-shrink: 0;
  transition: all 0.2s;

  .step-completed & {
    background: var(--el-color-success, #67C23A);
    color: #fff;
  }

  .step-current & {
    background: var(--bnu-blue, #003DA5);
    color: #fff;
  }

  .step-pending & {
    background: var(--bg-secondary, #F4F6FA);
    color: var(--text-secondary, #5A5A72);
    border: 1px solid var(--border-color, #E2E6ED);
  }
}

.step-check {
  font-size: 12px;
}

.step-info {
  display: flex;
  flex-direction: column;
  gap: 1px;
  min-width: 0;
}

.step-name {
  font-size: 12px;
  font-weight: 500;
  color: var(--text-primary, #1A1A2E);
  white-space: nowrap;

  .step-pending & {
    color: var(--text-secondary, #9E9EB3);
  }
}

.step-role {
  font-size: 10px;
  color: var(--text-secondary, #9E9EB3);
  white-space: nowrap;
}

.step-connector {
  width: 20px;
  height: 1px;
  background: var(--border-color, #E2E6ED);
  margin: 0 4px;
  flex-shrink: 0;

  .step-completed + & {
    background: var(--el-color-success, #67C23A);
  }
}
</style>
