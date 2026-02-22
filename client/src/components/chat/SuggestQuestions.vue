<script setup lang="ts">
import { computed, nextTick, onMounted, ref } from 'vue'
import { Promotion } from '@element-plus/icons-vue'
import { useSystemStore } from '@/stores/system'

const props = withDefaults(
  defineProps<{
    questions?: string[]
  }>(),
  {
    questions: () => [
      '北师大2025年录取分数线是多少？',
      '北师大有哪些优势专业？',
      '公费师范生有什么政策？',
      '北师大珠海校区和北京校区有什么区别？',
    ],
  }
)

const emit = defineEmits<{
  select: [question: string]
  send: [question: string]
}>()

function handleSelect(question: string) {
  emit('select', question)
}

const icons = ['&#127891;', '&#128218;', '&#127942;', '&#127961;']
const systemStore = useSystemStore()
const systemName = computed(() => systemStore.basic.system_name || '京师小智')
const content = ref('')
const textareaRef = ref<HTMLTextAreaElement | null>(null)
const canSend = computed(() => content.value.trim().length > 0)

function handleSend() {
  const question = content.value.trim()
  if (!question) return
  emit('send', question)
  content.value = ''
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

onMounted(() => {
  nextTick(() => {
    textareaRef.value?.focus()
  })
})
</script>

<template>
  <div class="suggest-questions">
    <div class="suggest-header">
      <div class="suggest-logo" aria-hidden="true">
        <div class="bot-face">
          <div class="bot-antenna">
            <span class="bot-antenna-dot" />
          </div>
          <div class="bot-eye bot-eye--left" />
          <div class="bot-eye bot-eye--right" />
          <div class="bot-mouth" />
          <div class="bot-cheek bot-cheek--left" />
          <div class="bot-cheek bot-cheek--right" />
        </div>
      </div>
      <h3 class="suggest-title">你好，我是{{ systemName }}</h3>
      <p class="suggest-subtitle">北京师范大学招生智能助手，有什么可以帮你的？</p>
    </div>

    <div class="suggest-input">
      <textarea
        ref="textareaRef"
        v-model="content"
        class="suggest-input__textarea"
        placeholder="输入你的问题，按 Enter 发送"
        rows="1"
        @keydown="handleKeydown"
      />
      <button class="suggest-input__send" :disabled="!canSend" @click="handleSend">
        <el-icon :size="18"><Promotion /></el-icon>
      </button>
    </div>

    <div class="suggest-grid">
      <div
        v-for="(question, index) in props.questions"
        :key="index"
        class="suggest-card"
        @click="handleSelect(question)"
      >
        <span class="card-icon" v-html="icons[index % icons.length]"></span>
        <span class="card-text">{{ question }}</span>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.suggest-questions {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100%;
  padding: 20px 20px 24px;
  max-width: 980px;
  margin: 0 auto;
  width: 100%;
  transform: translateY(-80px);
}

.suggest-header {
  text-align: center;
  margin-bottom: 20px;
}

.suggest-logo {
  margin-bottom: 16px;
  display: flex;
  justify-content: center;
}

.bot-face {
  width: 64px;
  height: 64px;
  border-radius: 20px;
  background: linear-gradient(145deg, #fdfefe 0%, #eaf1ff 100%);
  border: 2px solid rgba(0, 61, 165, 0.2);
  box-shadow:
    0 8px 20px rgba(0, 61, 165, 0.18),
    inset 0 -6px 12px rgba(0, 61, 165, 0.08);
  position: relative;
  animation: bot-float 3.6s ease-in-out infinite;
}

.bot-antenna {
  position: absolute;
  top: -12px;
  left: 50%;
  width: 3px;
  height: 12px;
  transform: translateX(-50%);
  background: rgba(0, 61, 165, 0.55);
  border-radius: 99px;
}

.bot-antenna-dot {
  position: absolute;
  top: -5px;
  left: 50%;
  width: 8px;
  height: 8px;
  border-radius: 50%;
  transform: translateX(-50%);
  background: #f8b84a;
  box-shadow: 0 0 0 0 rgba(248, 184, 74, 0.45);
  animation: bot-pulse 2s ease-out infinite;
}

.bot-eye {
  position: absolute;
  top: 24px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #17417f;
  animation: bot-blink 4s infinite;
}

.bot-eye--left {
  left: 18px;
}

.bot-eye--right {
  right: 18px;
}

.bot-mouth {
  position: absolute;
  left: 50%;
  bottom: 15px;
  width: 22px;
  height: 10px;
  transform: translateX(-50%);
  border-bottom: 3px solid #17417f;
  border-radius: 0 0 16px 16px;
  animation: bot-smile 2.8s ease-in-out infinite;
}

.bot-cheek {
  position: absolute;
  bottom: 18px;
  width: 8px;
  height: 5px;
  border-radius: 999px;
  background: rgba(244, 126, 126, 0.45);
}

.bot-cheek--left {
  left: 10px;
}

.bot-cheek--right {
  right: 10px;
}

@keyframes bot-blink {
  0%, 44%, 48%, 100% { transform: scaleY(1); }
  46% { transform: scaleY(0.12); }
}

@keyframes bot-smile {
  0%, 100% { transform: translateX(-50%) scaleX(1); }
  50% { transform: translateX(-50%) scaleX(1.18); }
}

@keyframes bot-float {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-3px); }
}

@keyframes bot-pulse {
  0% {
    box-shadow: 0 0 0 0 rgba(248, 184, 74, 0.45);
  }
  80% {
    box-shadow: 0 0 0 7px rgba(248, 184, 74, 0);
  }
  100% {
    box-shadow: 0 0 0 0 rgba(248, 184, 74, 0);
  }
}

.suggest-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary, #1a1a2e);
  margin: 0 0 8px;
}

.suggest-subtitle {
  font-size: 0.875rem;
  color: var(--text-secondary, #5a5a72);
  margin: 0;
}

.suggest-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 10px;
  width: min(70%, 644px);
  max-width: 860px;
  margin: 0 auto;

  @media (max-width: 520px) {
    grid-template-columns: 1fr;
    width: 100%;
  }
}

.suggest-input {
  width: 100%;
  max-width: 920px;
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 28px;
  background: var(--bg-primary, #fff);
  border: 2px solid rgba(0, 61, 165, 0.22);
  border-radius: 20px;
  padding: 12px 12px 12px 18px;
  box-shadow: 0 12px 28px rgba(0, 45, 122, 0.16);
  transition: border-color 0.2s, box-shadow 0.2s;

  &:focus-within {
    border-color: var(--bnu-blue, #003DA5);
    box-shadow:
      0 14px 36px rgba(0, 61, 165, 0.2),
      0 0 0 4px rgba(0, 61, 165, 0.1);
  }
}

.suggest-input__textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  font-size: 0.98rem;
  line-height: 30px;
  color: var(--text-primary, #1a1a2e);
  font-family: inherit;
  min-height: 30px;
  height: 30px;
  max-height: 30px;
  padding: 0;
  box-sizing: border-box;
  overflow: hidden;

  &::placeholder {
    color: var(--text-secondary, #9e9eb3);
  }
}

.suggest-input__send {
  width: 42px;
  height: 42px;
  border-radius: 50%;
  border: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: var(--bnu-blue, #003DA5);
  color: #fff;
  cursor: pointer;
  transition: all 0.2s ease;

  &:hover:not(:disabled) {
    background: #1a5fbf;
    transform: translateY(-1px);
  }

  &:disabled {
    cursor: not-allowed;
    background: #d4dae6;
    color: #8f98ad;
  }
}

.suggest-card {
  display: flex;
  align-items: center;
  gap: 8px;
  min-width: 0;
  padding: 11px 16px;
  background: transparent;
  border: 1px solid rgba(130, 144, 174, 0.2);
  border-radius: 999px;
  cursor: pointer;
  transition: border-color 0.2s, background-color 0.2s, transform 0.15s;

  &:hover {
    border-color: rgba(0, 61, 165, 0.24);
    background: transparent;
    transform: translateY(-0.5px);
  }

  &:active {
    transform: translateY(0);
  }
}

.card-icon {
  font-size: 1rem;
  flex-shrink: 0;
  line-height: 1;
  margin-top: 0;
  opacity: 0.65;
  filter: grayscale(0.15);
}

.card-text {
  display: block;
  flex: 1;
  min-width: 0;
  font-size: 0.8125rem;
  color: var(--text-primary, #1a1a2e);
  opacity: 0.92;
  line-height: 1.5;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

:global([data-theme='dark']) .suggest-card {
  border-color: rgba(115, 126, 150, 0.34);
}

:global([data-theme='dark']) .suggest-card:hover {
  border-color: rgba(114, 159, 235, 0.52);
}

:global([data-theme='dark']) .card-text {
  color: #f2f5ff;
  opacity: 1;
}

:global([data-theme='dark']) .card-icon {
  opacity: 0.78;
  filter: grayscale(0.1) brightness(0.95);
}

@media (max-width: 768px) {
  .suggest-input__textarea {
    font-size: 16px;
  }
}
</style>
