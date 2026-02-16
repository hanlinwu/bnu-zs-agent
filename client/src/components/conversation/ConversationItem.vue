<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { Edit, Delete, Star, StarFilled } from '@element-plus/icons-vue'
import type { Conversation } from '@/stores/conversation'

const props = defineProps<{
  conversation: Conversation
  active: boolean
}>()

const emit = defineEmits<{
  select: []
  delete: []
  updateTitle: [title: string]
  togglePin: []
}>()

const isEditing = ref(false)
const editValue = ref('')
const editInputRef = ref<HTMLInputElement | null>(null)
const isHovered = ref(false)

const relativeTime = computed(() => {
  const now = Date.now()
  const updated = new Date(props.conversation.updated_at).getTime()
  const diffMs = now - updated
  const diffMin = Math.floor(diffMs / 60000)
  const diffHour = Math.floor(diffMs / 3600000)
  const diffDay = Math.floor(diffMs / 86400000)

  if (diffMin < 1) return '刚刚'
  if (diffMin < 60) return `${diffMin}分钟前`
  if (diffHour < 24) return `${diffHour}小时前`
  if (diffDay < 7) return `${diffDay}天前`
  if (diffDay < 30) return `${Math.floor(diffDay / 7)}周前`
  return `${Math.floor(diffDay / 30)}月前`
})

function handleClick() {
  if (!isEditing.value) {
    emit('select')
  }
}

async function startEdit() {
  editValue.value = props.conversation.title
  isEditing.value = true
  await nextTick()
  editInputRef.value?.focus()
}

function saveEdit() {
  const trimmed = editValue.value.trim()
  if (trimmed && trimmed !== props.conversation.title) {
    emit('updateTitle', trimmed)
  }
  isEditing.value = false
}

function cancelEdit() {
  isEditing.value = false
}

function handleDelete(e: Event) {
  e.stopPropagation()
  emit('delete')
}
</script>

<template>
  <div
    class="conversation-item"
    :class="{ 'is-active': active }"
    @click="handleClick"
    @mouseenter="isHovered = true"
    @mouseleave="isHovered = false"
  >
    <div v-if="!isEditing" class="item-content">
      <div class="item-title">
        <el-icon v-if="conversation.pinned" class="pin-icon" :size="12"><StarFilled /></el-icon>
        <span>{{ conversation.title || '新对话' }}</span>
      </div>
      <div class="item-time">{{ relativeTime }}</div>
    </div>

    <div v-else class="item-edit" @click.stop>
      <input
        ref="editInputRef"
        v-model="editValue"
        class="edit-input"
        maxlength="50"
        @keydown.enter="saveEdit"
        @keydown.esc="cancelEdit"
        @blur="saveEdit"
      />
    </div>

    <div
      v-if="isHovered && !isEditing"
      class="item-actions"
      @click.stop
    >
      <el-button class="action-btn" text size="small" @click.stop="emit('togglePin')">
        <el-icon :size="14">
          <StarFilled v-if="conversation.pinned" />
          <Star v-else />
        </el-icon>
      </el-button>
      <el-button class="action-btn" text size="small" @click="startEdit">
        <el-icon :size="14"><Edit /></el-icon>
      </el-button>
      <el-button class="action-btn action-btn--danger" text size="small" @click="handleDelete">
        <el-icon :size="14"><Delete /></el-icon>
      </el-button>
    </div>
  </div>
</template>

<style scoped lang="scss">
.conversation-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  border-radius: 8px;
  cursor: pointer;
  transition: background-color 0.2s;
  position: relative;
  margin-bottom: 2px;

  &:hover {
    background-color: var(--bg-primary, #fff);
  }

  &.is-active {
    background-color: var(--color-primary-lighter, #e8f0fe);
    color: var(--bnu-blue, #003DA5);
  }
}

.item-content {
  flex: 1;
  min-width: 0;
}

.item-title {
  font-size: 14px;
  color: var(--text-primary, #1a1a2e);
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  line-height: 1.4;
  display: flex;
  align-items: center;
  gap: 4px;

  .is-active & {
    color: var(--bnu-blue, #003DA5);
    font-weight: 600;
  }

  .pin-icon {
    color: var(--bnu-blue, #003DA5);
    flex-shrink: 0;
  }

  span {
    overflow: hidden;
    text-overflow: ellipsis;
  }
}

.item-time {
  font-size: 12px;
  color: var(--text-secondary, #5a5a72);
  margin-top: 2px;
}

.item-edit {
  flex: 1;
  min-width: 0;
}

.edit-input {
  width: 100%;
  font-size: 14px;
  padding: 4px 8px;
  border: 1px solid var(--bnu-blue, #003DA5);
  border-radius: 4px;
  outline: none;
  color: var(--text-primary, #1a1a2e);
  background: var(--bg-primary, #fff);
}

.item-actions {
  display: flex;
  align-items: center;
  gap: 2px;
  flex-shrink: 0;
  margin-left: 4px;
}

.action-btn {
  padding: 2px 4px;
  color: var(--text-secondary, #5a5a72);

  &:hover {
    color: var(--bnu-blue, #003DA5);
  }

  &--danger:hover {
    color: #c62828;
  }
}
</style>
