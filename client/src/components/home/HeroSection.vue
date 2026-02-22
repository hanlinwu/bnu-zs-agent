<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import { Promotion } from '@element-plus/icons-vue'
import { useSystemStore } from '@/stores/system'
import { setPendingChatQuestion } from '@/utils/chatNavigation'

const router = useRouter()
const systemStore = useSystemStore()
const inputContent = ref('')
const systemName = computed(() => systemStore.basic.system_name || '京师小智')
const animatedPlaceholder = ref('')

const placeholderSamples = [
  '北京师范大学今年本科录取分数线是多少？',
  '公费师范生毕业后必须回生源地任教吗？',
  '北师大有哪些优势专业和拔尖班？',
  '研究生推免和统考招生政策有什么区别？',
]

let currentSampleIndex = 0
let currentCharIndex = 0
let typingTimer: ReturnType<typeof setTimeout> | null = null
let isDeleting = false
let pauseUntil = 0

function clearTypingTimer() {
  if (!typingTimer) return
  clearTimeout(typingTimer)
  typingTimer = null
}

function scheduleTypewriter() {
  clearTypingTimer()
  typingTimer = setTimeout(tickTypewriter, isDeleting ? 48 : 85)
}

function tickTypewriter() {
  const now = Date.now()
  if (now < pauseUntil) {
    scheduleTypewriter()
    return
  }

  const sample = placeholderSamples[currentSampleIndex] || ''
  if (!isDeleting) {
    currentCharIndex = Math.min(currentCharIndex + 1, sample.length)
    animatedPlaceholder.value = sample.slice(0, currentCharIndex)
    if (currentCharIndex >= sample.length) {
      isDeleting = true
      pauseUntil = Date.now() + 1200
    }
  } else {
    currentCharIndex = Math.max(currentCharIndex - 1, 0)
    animatedPlaceholder.value = sample.slice(0, currentCharIndex)
    if (currentCharIndex <= 0) {
      isDeleting = false
      currentSampleIndex = (currentSampleIndex + 1) % placeholderSamples.length
      pauseUntil = Date.now() + 320
    }
  }

  scheduleTypewriter()
}

function handleSend() {
  const text = inputContent.value.trim()
  if (!text) return
  setPendingChatQuestion(text)
  router.push('/chat')
}

function handleKeydown(e: KeyboardEvent) {
  if (e.key === 'Enter' && !e.shiftKey) {
    e.preventDefault()
    handleSend()
  }
}

onMounted(() => {
  animatedPlaceholder.value = ''
  currentSampleIndex = 0
  currentCharIndex = 0
  isDeleting = false
  pauseUntil = 0
  scheduleTypewriter()
})

onBeforeUnmount(() => {
  clearTypingTimer()
})
</script>

<template>
  <section class="hero-section">
    <!-- Background image with overlay -->
    <div class="hero-bg">
      <div class="hero-bg-image" />
      <div class="hero-bg-overlay" />
    </div>

    <!-- Floating decorative elements -->
    <div class="hero-particles">
      <div class="particle particle--1" />
      <div class="particle particle--2" />
      <div class="particle particle--3" />
    </div>

    <div class="hero-content">
      <!-- Badge -->
      <div class="hero-badge">
        <span class="badge-dot" />
        北京师范大学官方招生智能助手
      </div>

      <h1 class="hero-title">
        <span class="title-line">你好，我是</span>
        <span class="title-highlight">{{ systemName }}</span>
      </h1>

      <p class="hero-subtitle">
        有关招生政策、专业选择、录取分数等问题，随时向我提问
      </p>

      <!-- Chat input -->
      <div class="hero-input-wrapper">
        <div class="hero-input-box">
          <textarea
            v-model="inputContent"
            class="hero-textarea"
            :placeholder="animatedPlaceholder || '输入你想了解的招生问题'"
            rows="1"
            @keydown="handleKeydown"
          />
          <button
            class="hero-send-btn"
            :disabled="!inputContent.trim()"
            @click="handleSend"
          >
            <el-icon :size="20"><Promotion /></el-icon>
          </button>
        </div>
        <div class="hero-input-hint">
          按 Enter 发送，Shift + Enter 换行
        </div>
      </div>

      <!-- Quick suggestion chips -->
      <div class="hero-chips">
        <button
          v-for="chip in ['录取分数线', '公费师范生', '优势专业', '奖学金政策']"
          :key="chip"
          class="hero-chip"
          @click="setPendingChatQuestion(chip); router.push('/chat')"
        >
          {{ chip }}
        </button>
      </div>
    </div>
  </section>
</template>

<style lang="scss" scoped>
.hero-section {
  position: relative;
  overflow: hidden;
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 480px;
  padding: 48px 24px 56px;
}

.hero-bg {
  position: absolute;
  inset: 0;
  z-index: 0;
}

.hero-bg-image {
  position: absolute;
  inset: 0;
  background-image: url('/images/bnu-gate.jpg');
  background-size: cover;
  background-position: center 40%;
  filter: blur(1px);
  transform: scale(1.05);
}

.hero-bg-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(
    135deg,
    rgba(0, 45, 122, 0.88) 0%,
    rgba(0, 61, 165, 0.82) 40%,
    rgba(0, 26, 77, 0.90) 100%
  );
}

.hero-particles {
  position: absolute;
  inset: 0;
  pointer-events: none;
  z-index: 1;
}

.particle {
  position: absolute;
  border-radius: 50%;
  opacity: 0.15;

  &--1 {
    width: 300px;
    height: 300px;
    background: radial-gradient(circle, rgba(196, 151, 47, 0.5) 0%, transparent 70%);
    top: -60px;
    right: -40px;
    animation: float 8s ease-in-out infinite;
  }

  &--2 {
    width: 200px;
    height: 200px;
    border: 1.5px solid rgba(255, 255, 255, 0.15);
    bottom: -40px;
    left: 5%;
    animation: float 10s ease-in-out infinite reverse;
  }

  &--3 {
    width: 120px;
    height: 120px;
    background: radial-gradient(circle, rgba(255, 255, 255, 0.12) 0%, transparent 70%);
    top: 30%;
    left: 15%;
    animation: float 6s ease-in-out infinite 2s;
  }
}

@keyframes float {
  0%, 100% { transform: translateY(0) scale(1); }
  50% { transform: translateY(-20px) scale(1.05); }
}

.hero-content {
  position: relative;
  z-index: 2;
  text-align: center;
  max-width: 720px;
  width: 100%;
}

.hero-badge {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  padding: 6px 16px;
  background: rgba(255, 255, 255, 0.12);
  backdrop-filter: blur(8px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  border-radius: 100px;
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.9);
  margin-bottom: 24px;
  letter-spacing: 0.5px;
}

.badge-dot {
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: #4ade80;
  box-shadow: 0 0 8px rgba(74, 222, 128, 0.6);
  animation: pulse-dot 2s ease-in-out infinite;
}

@keyframes pulse-dot {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.4; }
}

.hero-title {
  font-size: 2.75rem;
  font-weight: 700;
  color: #ffffff;
  margin: 0 0 16px;
  line-height: 1.25;
  letter-spacing: 1px;
}

.title-line {
  display: block;
  font-size: 1.75rem;
  font-weight: 400;
  opacity: 0.9;
  letter-spacing: 2px;
  margin-bottom: 4px;
}

.title-highlight {
  background: linear-gradient(135deg, #ffffff 0%, #C4972F 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-subtitle {
  font-size: 1rem;
  color: rgba(255, 255, 255, 0.75);
  margin: 0 0 32px;
  line-height: 1.6;
}

.hero-input-wrapper {
  max-width: 600px;
  margin: 0 auto 20px;
}

.hero-input-box {
  display: flex;
  align-items: center;
  gap: 8px;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 8px 8px 8px 20px;
  box-shadow:
    0 8px 32px rgba(0, 0, 0, 0.15),
    0 0 0 1px rgba(255, 255, 255, 0.2);
  transition: box-shadow 0.3s, transform 0.2s;

  &:focus-within {
    box-shadow:
      0 12px 40px rgba(0, 0, 0, 0.2),
      0 0 0 2px rgba(196, 151, 47, 0.4);
    transform: translateY(-1px);
  }
}

.hero-textarea {
  flex: 1;
  border: none;
  outline: none;
  resize: none;
  font-size: 0.9375rem;
  line-height: 24px;
  color: #1a1a2e;
  background: transparent;
  font-family: inherit;
  min-height: 24px;
  max-height: 72px;

  &::placeholder {
    color: #7f8498;
  }
}

.hero-send-btn {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  border-radius: 12px;
  background: linear-gradient(135deg, #003DA5 0%, #0052D9 100%);
  color: #ffffff;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s;

  &:hover:not(:disabled) {
    background: linear-gradient(135deg, #0052D9 0%, #003DA5 100%);
    transform: scale(1.05);
  }

  &:disabled {
    background: #c8cdd4;
    cursor: not-allowed;
  }
}

.hero-input-hint {
  text-align: right;
  font-size: 0.75rem;
  color: rgba(255, 255, 255, 0.45);
  margin-top: 8px;
  padding-right: 4px;
}

.hero-chips {
  display: flex;
  flex-wrap: wrap;
  justify-content: center;
  gap: 8px;
}

.hero-chip {
  padding: 6px 16px;
  border-radius: 100px;
  font-size: 0.8125rem;
  color: rgba(255, 255, 255, 0.85);
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(4px);
  border: 1px solid rgba(255, 255, 255, 0.15);
  cursor: pointer;
  transition: all 0.2s;
  white-space: nowrap;

  &:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: rgba(255, 255, 255, 0.3);
    transform: translateY(-1px);
  }
}

@media (max-width: 768px) {
  .hero-section {
    min-height: 420px;
    padding: 36px 16px 40px;
  }

  .hero-title {
    font-size: 2rem;
  }

  .title-line {
    font-size: 1.25rem;
  }

  .hero-subtitle {
    font-size: 0.875rem;
    margin-bottom: 24px;
  }

  .hero-input-box {
    padding: 6px 6px 6px 14px;
  }

  .hero-textarea {
    font-size: 0.875rem;
  }

  .hero-send-btn {
    width: 38px;
    height: 38px;
  }

  .hero-chips {
    gap: 6px;
  }

  .hero-chip {
    padding: 5px 12px;
    font-size: 0.75rem;
  }
}
</style>
