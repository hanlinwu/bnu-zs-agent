<script setup lang="ts">
import type { SourceReference } from '@/types/chat'

defineProps<{
  sources: SourceReference[]
}>()

const emit = defineEmits<{
  click: [source: SourceReference]
}>()

function handleClick(source: SourceReference) {
  emit('click', source)
}
</script>

<template>
  <div class="source-citation">
    <el-tooltip
      v-for="(source, index) in sources"
      :key="index"
      :content="source.snippet"
      placement="top"
      :show-after="300"
      max-width="320"
    >
      <span
        class="source-tag"
        @click="handleClick(source)"
      >
        <span class="source-icon">&#128196;</span>
        <span class="source-title">{{ source.title }}</span>
      </span>
    </el-tooltip>
  </div>
</template>

<style scoped lang="scss">
.source-citation {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}

.source-tag {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 3px 10px;
  background: var(--bg-tertiary, #eef1f6);
  border: 1px solid var(--border-color, #e2e6ed);
  border-radius: 12px;
  font-size: 0.75rem;
  color: var(--text-secondary, #5a5a72);
  cursor: pointer;
  transition: background-color 0.2s, color 0.2s;
  max-width: 200px;
  overflow: hidden;
  white-space: nowrap;
  text-overflow: ellipsis;

  &:hover {
    background: var(--bnu-blue, #003DA5);
    color: #fff;
    border-color: var(--bnu-blue, #003DA5);
  }
}

.source-icon {
  font-size: 0.8125rem;
  flex-shrink: 0;
}

.source-title {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
</style>
