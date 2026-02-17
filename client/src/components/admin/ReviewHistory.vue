<script setup lang="ts">
/**
 * Unified review history display component.
 * Shows workflow action records with from_node → action → to_node.
 */
import type { ReviewHistoryRecord } from '@/api/admin/workflow'

defineProps<{
  records: ReviewHistoryRecord[]
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

function actionTagType(action: string): 'success' | 'danger' | 'warning' | 'info' {
  if (action === 'approve') return 'success'
  if (action === 'reject') return 'danger'
  return 'warning'
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
        <span class="review-record-flow">
          <el-tag size="small" type="info">{{ record.from_node_name || record.from_node }}</el-tag>
          <span class="flow-arrow">&rarr;</span>
          <el-tag size="small" :type="actionTagType(record.action)">
            {{ record.action_name || record.action }}
          </el-tag>
          <span class="flow-arrow">&rarr;</span>
          <el-tag size="small" type="info">{{ record.to_node_name || record.to_node }}</el-tag>
        </span>
        <span class="review-record-meta">
          <span class="review-record-reviewer">{{ record.reviewer_name }}</span>
          <span class="review-record-time">{{ formatDate(record.created_at) }}</span>
        </span>
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
  justify-content: space-between;
  gap: 8px;
  flex-wrap: wrap;
}

.review-record-flow {
  display: flex;
  align-items: center;
  gap: 4px;
}

.flow-arrow {
  color: var(--text-secondary, #9E9EB3);
  font-size: 12px;
}

.review-record-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-left: auto;
}

.review-record-reviewer {
  font-size: 13px;
  font-weight: 500;
  color: var(--text-primary, #1A1A2E);
}

.review-record-time {
  font-size: 12px;
  color: var(--text-secondary, #5A5A72);
}

.review-record-note {
  font-size: 13px;
  color: var(--text-secondary, #5A5A72);
  margin: 8px 0 0;
  line-height: 1.6;
}
</style>
