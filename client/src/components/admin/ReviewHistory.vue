<script setup lang="ts">
/**
 * Unified review history display component.
 * Used across KnowledgeReview and Media pages for consistent review record display.
 */

defineProps<{
  records: {
    id: string
    step: number
    action: string
    reviewer_name: string
    created_at: string
    note?: string
  }[]
}>()

function formatDate(date: string) {
  return new Date(date).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div v-if="records.length > 0" class="review-history">
    <div
      v-for="record in records"
      :key="record.id"
      class="review-record"
    >
      <div class="review-record-header">
        <el-tag size="small" :type="record.action === 'approve' ? 'success' : 'danger'">
          {{ record.action === 'approve' ? '通过' : '拒绝' }}
        </el-tag>
        <span class="review-record-step">第{{ record.step }}步</span>
        <span class="review-record-reviewer">{{ record.reviewer_name }}</span>
        <span class="review-record-time">{{ formatDate(record.created_at) }}</span>
      </div>
      <p v-if="record.note" class="review-record-note">{{ record.note }}</p>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.review-history {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.review-record {
  background: var(--bg-secondary, #F4F6FA);
  border-radius: 8px;
  padding: 12px 16px;
}

.review-record-header {
  display: flex;
  align-items: center;
  gap: 8px;
}

.review-record-step {
  font-size: 12px;
  color: var(--text-secondary, #5A5A72);
  font-weight: 500;
}

.review-record-reviewer {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #1A1A2E);
}

.review-record-time {
  font-size: 12px;
  color: var(--text-secondary, #5A5A72);
  margin-left: auto;
}

.review-record-note {
  font-size: 13px;
  color: var(--text-secondary, #5A5A72);
  margin: 8px 0 0;
  line-height: 1.6;
}
</style>
