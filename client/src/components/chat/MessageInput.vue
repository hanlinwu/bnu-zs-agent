<script setup lang="ts">
import { ref, watch, nextTick, computed } from 'vue'
import { Promotion, VideoPause } from '@element-plus/icons-vue'

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
  stop: []
}>()

const content = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)

const MAX_CHARS = 2000
const MAX_LINES = 6
const LINE_HEIGHT = 22

const canSend = computed(() => content.value.trim().length > 0 && content.value.length <= MAX_CHARS && !props.disabled)

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

function handleStop() {
  emit('stop')
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
    <div class="input-wrapper" @click="textareaRef?.focus()">
      <div class="input-row">
        <textarea
          ref="textareaRef"
          v-model="content"
          class="input-textarea"
          :placeholder="disabled ? 'AI正在回复中...' : '输入你的问题，按 Enter 发送'"
          :disabled="disabled"
          rows="1"
          @keydown="handleKeydown"
        ></textarea>
        <el-button
          v-if="disabled"
          class="stop-btn"
          type="danger"
          circle
          @click="handleStop"
        >
          <el-icon :size="18"><VideoPause /></el-icon>
        </el-button>
        <el-button
          v-else
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
  padding: 8px 16px 20px;
  background: transparent;

  &.is-disabled {
    opacity: 0.85;
  }
}

.input-wrapper {
  max-width: 800px;
  margin: 0 auto;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e2e6ed);
  border-radius: 20px;
  padding: 10px 10px 10px 16px;
  box-shadow: 0 2px 12px rgba(0, 0, 0, 0.08);
  transition: border-color 0.2s, box-shadow 0.2s;
  cursor: text;

  &:focus-within {
    border-color: var(--bnu-blue, #003DA5);
    box-shadow: 0 2px 16px rgba(0, 61, 165, 0.12);
  }
}

.input-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.input-textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 0.875rem;
  line-height: 22px;
  padding: 7px 0;
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

.stop-btn {
  width: 36px;
  height: 36px;
}

@media (max-width: 768px) {
  .input-textarea {
    font-size: 16px;
  }
}
</style>
