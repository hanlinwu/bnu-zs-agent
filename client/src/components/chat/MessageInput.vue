<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { Promotion } from '@element-plus/icons-vue'

const props = withDefaults(
  defineProps<{
    disabled?: boolean
  }>(),
  {
    disabled: false,
  }
)

const emit = defineEmits<{
  send: [content: string]
}>()

const content = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const MAX_CHARS = 2000
const MAX_LINES = 6
const LINE_HEIGHT = 22

const charCount = computed(() => content.value.length)
const isOverLimit = computed(() => charCount.value > MAX_CHARS)
const canSend = computed(() => content.value.trim().length > 0 && !isOverLimit.value && !props.disabled)

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

function handleSend() {
  if (!canSend.value) return
  emit('send', content.value.trim())
  content.value = ''
  nextTick(() => autoResize())
}

function autoResize() {
  const el = textareaRef.value
  if (!el) return
  el.style.height = 'auto'
  const maxHeight = LINE_HEIGHT * MAX_LINES + 16
  const scrollH = el.scrollHeight
  el.style.height = `${Math.min(scrollH, maxHeight)}px`
}

watch(content, () => {
  nextTick(() => autoResize())
})
</script>

<template>
  <div class="message-input" :class="{ 'is-disabled': disabled }">
    <div class="input-wrapper">
      <textarea
        ref="textareaRef"
        v-model="content"
        class="input-textarea"
        :placeholder="disabled ? 'AI正在回复中...' : '输入你的问题，按 Enter 发送'"
        :disabled="disabled"
        rows="1"
        @keydown="handleKeydown"
      ></textarea>

      <div class="input-footer">
        <span
          class="char-count"
          :class="{ 'is-over': isOverLimit }"
        >
          {{ charCount }} / {{ MAX_CHARS }}
        </span>
        <el-button
          class="send-btn"
          :disabled="!canSend"
          type="primary"
          circle
          @click="handleSend"
        >
          <el-icon :size="18"><Promotion /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.message-input {
  padding: 12px 16px 16px;
  background: var(--bg-primary, #fff);
  border-top: 1px solid var(--border-color, #e2e6ed);

  &.is-disabled {
    opacity: 0.7;
  }
}

.input-wrapper {
  max-width: 800px;
  margin: 0 auto;
  background: var(--bg-secondary, #f4f6fa);
  border: 1px solid var(--border-color, #e2e6ed);
  border-radius: 16px;
  padding: 12px 16px 8px;
  transition: border-color 0.2s, box-shadow 0.2s;

  &:focus-within {
    border-color: var(--bnu-blue, #003DA5);
    box-shadow: 0 0 0 2px rgba(0, 61, 165, 0.1);
  }
}

.input-textarea {
  width: 100%;
  border: none;
  outline: none;
  resize: none;
  font-size: 14px;
  line-height: 22px;
  color: var(--text-primary, #1a1a2e);
  background: transparent;
  font-family: inherit;
  min-height: 22px;
  max-height: calc(22px * 6 + 16px);

  &::placeholder {
    color: var(--text-secondary, #9e9eb3);
  }

  &:disabled {
    cursor: not-allowed;
  }
}

.input-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-top: 4px;
}

.char-count {
  font-size: 12px;
  color: var(--text-secondary, #9e9eb3);

  &.is-over {
    color: #c62828;
    font-weight: 500;
  }
}

.send-btn {
  width: 36px;
  height: 36px;
  background-color: var(--bnu-blue, #003DA5);
  border-color: var(--bnu-blue, #003DA5);

  &:hover:not(:disabled) {
    background-color: #1a5fbf;
    border-color: #1a5fbf;
  }

  &:disabled {
    background-color: var(--border-color, #e2e6ed);
    border-color: var(--border-color, #e2e6ed);
    color: var(--text-secondary, #9e9eb3);
  }
}
</style>
