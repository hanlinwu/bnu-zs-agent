<script setup lang="ts">
/**
 * Workflow nodes rendered as clickable filter tabs or status badges.
 *
 * Props:
 *   nodes      - Array of WorkflowNode objects from the workflow definition
 *   activeNode - Currently selected node id (default 'all')
 *   mode       - 'filter' renders el-tabs, 'status' renders inline tag badges
 *
 * Emits:
 *   update:activeNode - Fired when a tab/tag is clicked
 */
import type { WorkflowNode } from '@/api/admin/workflow'

const props = withDefaults(defineProps<{
  nodes: WorkflowNode[]
  activeNode?: string
  mode?: 'filter' | 'status'
}>(), {
  activeNode: 'all',
  mode: 'filter',
})

const emit = defineEmits<{
  'update:activeNode': [nodeId: string]
}>()

function nodeTagType(node: WorkflowNode): '' | 'success' | 'warning' | 'info' | 'danger' {
  if (node.type === 'start') return ''
  if (node.type === 'intermediate') return 'info'
  if (node.type === 'terminal') {
    if (node.id.includes('approved')) return 'success'
    if (node.id.includes('rejected')) return 'danger'
    return 'warning'
  }
  return ''
}

function handleTabChange(nodeId: string) {
  emit('update:activeNode', nodeId)
}

function handleTagClick(nodeId: string) {
  emit('update:activeNode', nodeId)
}
</script>

<template>
  <!-- Filter mode: el-tabs -->
  <div v-if="mode === 'filter'" class="workflow-node-tabs">
    <el-tabs
      :model-value="activeNode"
      @update:model-value="handleTabChange"
    >
      <el-tab-pane label="全部" name="all" />
      <el-tab-pane
        v-for="node in nodes"
        :key="node.id"
        :label="node.name"
        :name="node.id"
      />
    </el-tabs>
  </div>

  <!-- Status mode: inline tag badges -->
  <div v-else class="workflow-node-status">
    <template v-for="(node, index) in nodes" :key="node.id">
      <span
        v-if="index > 0"
        class="status-connector"
      />
      <el-tag
        :type="nodeTagType(node)"
        :effect="activeNode === node.id ? 'dark' : 'plain'"
        class="status-tag"
        @click="handleTagClick(node.id)"
      >
        {{ node.name }}
      </el-tag>
    </template>
  </div>
</template>

<style lang="scss" scoped>
.workflow-node-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 0;
  }

  :deep(.el-tabs__nav-wrap::after) {
    height: 1px;
  }
}

.workflow-node-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}

.status-tag {
  cursor: pointer;
  transition: all 0.2s;

  &:hover {
    opacity: 0.85;
  }
}

.status-connector {
  display: inline-block;
  width: 16px;
  height: 1px;
  background: var(--border-color, #E2E6ED);
  vertical-align: middle;
}
</style>
