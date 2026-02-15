<script setup lang="ts">
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
}>()

function handleSelect(question: string) {
  emit('select', question)
}

const icons = ['&#127891;', '&#128218;', '&#127942;', '&#127961;']
</script>

<template>
  <div class="suggest-questions">
    <div class="suggest-header">
      <div class="suggest-logo">
        <svg viewBox="0 0 48 48" width="48" height="48" fill="none">
          <circle cx="24" cy="24" r="23" fill="var(--bnu-blue, #003DA5)" />
          <text
            x="24" y="32" text-anchor="middle"
            fill="#fff" font-size="22" font-weight="bold"
            font-family="serif"
          >智</text>
        </svg>
      </div>
      <h3 class="suggest-title">你好，我是京师小智</h3>
      <p class="suggest-subtitle">北京师范大学招生智能助手，有什么可以帮你的？</p>
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
  padding: 40px 20px 20px;
  max-width: 640px;
  margin: 0 auto;
}

.suggest-header {
  text-align: center;
  margin-bottom: 32px;
}

.suggest-logo {
  margin-bottom: 16px;
}

.suggest-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary, #1a1a2e);
  margin: 0 0 8px;
}

.suggest-subtitle {
  font-size: 14px;
  color: var(--text-secondary, #5a5a72);
  margin: 0;
}

.suggest-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  width: 100%;

  @media (max-width: 520px) {
    grid-template-columns: 1fr;
  }
}

.suggest-card {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 14px 16px;
  background: var(--bg-primary, #fff);
  border: 1px solid var(--border-color, #e2e6ed);
  border-radius: 12px;
  cursor: pointer;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.15s;

  &:hover {
    border-color: var(--bnu-blue, #003DA5);
    box-shadow: var(--shadow-md, 0 4px 12px rgba(0, 61, 165, 0.1));
    transform: translateY(-1px);
  }

  &:active {
    transform: translateY(0);
  }
}

.card-icon {
  font-size: 20px;
  flex-shrink: 0;
  line-height: 1;
  margin-top: 1px;
}

.card-text {
  font-size: 14px;
  color: var(--text-primary, #1a1a2e);
  line-height: 1.5;
}
</style>
