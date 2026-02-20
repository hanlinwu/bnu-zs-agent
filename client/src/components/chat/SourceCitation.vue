<script setup lang="ts">
import { computed } from 'vue'
import type { SourceReference } from '@/types/chat'

const props = defineProps<{
  sources: SourceReference[]
}>()

// Deduplicate sources by title — show each document only once
const uniqueSources = computed(() => {
  const seen = new Set<string>()
  return props.sources.filter((s) => {
    const key = s.title
    if (seen.has(key)) return false
    seen.add(key)
    return true
  })
})
</script>

<template>
  <div class="source-citation">
    <span
      v-for="(source, index) in uniqueSources"
      :key="index"
      class="source-tag"
    >
      <span class="source-icon">&#128196;</span>
      <span class="source-title">{{ source.title }}</span>
    </span>
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
  max-width: 100%;
}

.source-icon {
  font-size: 0.8125rem;
  flex-shrink: 0;
}

.source-title {
  word-break: break-all;
}
</style>
