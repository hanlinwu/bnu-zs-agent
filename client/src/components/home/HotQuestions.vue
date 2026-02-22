<script setup lang="ts">
import { useRouter } from 'vue-router'
import {
  TrendCharts,
  School,
  Reading,
  OfficeBuilding,
  Connection,
  Trophy,
  Coffee,
  Postcard,
} from '@element-plus/icons-vue'
import { markRaw, ref, type Component } from 'vue'
import { setPendingChatQuestion } from '@/utils/chatNavigation'

const router = useRouter()
const activePopoverId = ref<number | null>(null)
const leftAlignedPopoverId = ref<number | null>(null)
let closeTimer: ReturnType<typeof setTimeout> | null = null

interface HotQuestion {
  id: number
  icon: Component
  text: string
  query: string
  subQuestions: string[]
}

const questions: HotQuestion[] = [
  {
    id: 1,
    icon: markRaw(TrendCharts),
    text: '录取分数线',
    query: '北京师范大学各专业录取分数线是多少？',
    subQuestions: ['近3年分数线变化趋势？', '省份位次大概要求？', '珠海校区分数线对比？'],
  },
  {
    id: 2,
    icon: markRaw(School),
    text: '优势专业',
    query: '北京师范大学有哪些优势专业和学科？',
    subQuestions: ['教育学最强方向有哪些？', '理科王牌专业推荐？', '双学位怎么选更合适？'],
  },
  {
    id: 3,
    icon: markRaw(Reading),
    text: '公费师范生政策',
    query: '北京师范大学公费师范生政策是什么？',
    subQuestions: ['毕业去向和服务年限？', '违约会有哪些后果？', '在校期间补助标准？'],
  },
  {
    id: 4,
    icon: markRaw(OfficeBuilding),
    text: '珠海校区',
    query: '北京师范大学珠海校区有哪些专业？',
    subQuestions: ['珠海校区住宿条件如何？', '校区之间能转专业吗？', '毕业证书是否一致？'],
  },
  {
    id: 5,
    icon: markRaw(Connection),
    text: '国际交流项目',
    query: '北京师范大学有哪些国际交流项目？',
    subQuestions: ['交换项目申请门槛？', '语言成绩具体要求？', '奖学金覆盖比例如何？'],
  },
  {
    id: 6,
    icon: markRaw(Trophy),
    text: '奖学金政策',
    query: '北京师范大学奖学金有哪些类型？',
    subQuestions: ['新生奖学金怎么评定？', '国家奖学金名额多少？', '助学金申请流程？'],
  },
  {
    id: 7,
    icon: markRaw(Coffee),
    text: '校园生活',
    query: '北京师范大学校园生活怎么样？',
    subQuestions: ['食堂和宿舍体验如何？', '社团活动活跃吗？', '学习氛围和压力大吗？'],
  },
  {
    id: 8,
    icon: markRaw(Postcard),
    text: '考研招生',
    query: '北京师范大学研究生招生有哪些要求？',
    subQuestions: ['复试占比和形式？', '跨专业报考建议？', '推免和统考差异？'],
  },
]

function askQuestion(query: string) {
  setPendingChatQuestion(query)
  router.push('/chat')
}

function askSubQuestion(query: string) {
  setPendingChatQuestion(query)
  router.push('/chat')
}

function clearCloseTimer() {
  if (!closeTimer) return
  clearTimeout(closeTimer)
  closeTimer = null
}

function handleCardEnter(itemId: number, event: MouseEvent) {
  clearCloseTimer()
  activePopoverId.value = itemId

  const target = event.currentTarget as HTMLElement | null
  if (!target) return
  const rect = target.getBoundingClientRect()
  const expectedPopoverWidth = 320
  const rightSpace = window.innerWidth - rect.right
  leftAlignedPopoverId.value = rightSpace < expectedPopoverWidth ? itemId : null
}

function scheduleClose(itemId: number) {
  clearCloseTimer()
  closeTimer = setTimeout(() => {
    if (activePopoverId.value === itemId) {
      activePopoverId.value = null
      leftAlignedPopoverId.value = null
    }
  }, 160)
}
</script>

<template>
  <section class="hot-questions">
    <div class="section-container">
      <div class="section-header">
        <h2 class="section-title">热门问题</h2>
        <p class="section-desc">考生与家长最关心的招生话题</p>
      </div>
      <div class="questions-grid">
        <div
          v-for="item in questions"
          :key="item.id"
          class="question-card"
          :class="{
            'is-active': activePopoverId === item.id,
            'is-left': activePopoverId === item.id && leftAlignedPopoverId === item.id,
          }"
          @click="askQuestion(item.query)"
          @mouseenter="handleCardEnter(item.id, $event)"
          @mouseleave="scheduleClose(item.id)"
        >
          <div class="question-icon">
            <el-icon :size="24"><component :is="item.icon" /></el-icon>
          </div>
          <span class="question-text">{{ item.text }}</span>
          <svg class="question-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>

          <div
            class="sub-questions"
            @mouseenter="clearCloseTimer"
            @mouseleave="scheduleClose(item.id)"
          >
            <div class="sub-questions__title">你可能还想问</div>
            <button
              v-for="(sub, idx) in item.subQuestions"
              :key="`${item.id}-${idx}`"
              class="sub-question-chip"
              @click.stop="askSubQuestion(sub)"
            >
              {{ sub }}
            </button>
          </div>
        </div>
      </div>
    </div>
  </section>
</template>

<style lang="scss" scoped>
.hot-questions {
  padding: 56px 24px;
  background: var(--bg-primary, #ffffff);
}

.section-container {
  max-width: 1100px;
  margin: 0 auto;
}

.section-header {
  margin-bottom: 32px;
}

.section-title {
  text-align: center;
  font-size: 1.625rem;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 6px;
}

.section-desc {
  text-align: center;
  font-size: 0.9375rem;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
}

.questions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  overflow: visible;
}

.question-card {
  position: relative;
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  background: var(--bg-secondary, #F4F6FA);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;
  overflow: visible;
  z-index: 1;

  &:hover {
    background: var(--bg-primary, #ffffff);
    border-color: var(--bnu-blue, #003DA5);
    box-shadow: 0 4px 16px rgba(0, 61, 165, 0.08);
    transform: translateY(-2px);

    .question-icon {
      color: #ffffff;
      background: var(--bnu-blue, #003DA5);
    }

    .question-arrow {
      opacity: 1;
      transform: translateX(0);
    }

  }

  &.is-active {
    z-index: 30;
  }

  &.is-active .sub-questions {
    opacity: 1;
    transform: translate(0, -50%) scale(1);
    pointer-events: auto;
  }

  &.is-active .sub-question-chip {
    opacity: 1;
    transform: translateX(0) scale(1);
  }
}

.question-icon {
  flex-shrink: 0;
  width: 42px;
  height: 42px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(0, 61, 165, 0.08);
  color: var(--bnu-blue, #003DA5);
  transition: all 0.2s ease;
}

.question-text {
  flex: 1;
  font-size: 0.875rem;
  font-weight: 500;
  color: var(--text-primary, #1A1A2E);
}

.question-arrow {
  flex-shrink: 0;
  opacity: 0;
  transform: translateX(-6px);
  transition: all 0.2s ease;
  color: var(--bnu-blue, #003DA5);
}

.sub-questions {
  position: absolute;
  top: 50%;
  left: calc(100% + 14px);
  width: 296px;
  display: grid;
  gap: 8px;
  padding: 12px;
  border-radius: 14px;
  background: linear-gradient(155deg, #ffffff 0%, #f5f8ff 100%);
  border: 1px solid rgba(0, 61, 165, 0.2);
  box-shadow: 0 16px 36px rgba(8, 25, 54, 0.18);
  backdrop-filter: blur(6px);
  opacity: 0;
  transform: translate(8px, -50%) scale(0.98);
  transform-origin: left center;
  transition: opacity 0.2s ease, transform 0.2s ease;
  pointer-events: none;
  z-index: 40;

  &::before {
    content: '';
    position: absolute;
    left: -14px;
    top: 0;
    width: 14px;
    height: 100%;
  }
}

.question-card.is-left .sub-questions {
  left: auto;
  right: calc(100% + 14px);
  transform: translate(-8px, -50%) scale(0.98);
  transform-origin: right center;

  &::before {
    left: auto;
    right: -14px;
  }
}

.sub-questions__title {
  font-size: 0.75rem;
  color: #5f6b86;
  font-weight: 600;
  letter-spacing: 0.02em;
  margin-bottom: 2px;
}

.sub-question-chip {
  width: 100%;
  text-align: left;
  border: 1px solid rgba(0, 61, 165, 0.14);
  border-radius: 10px;
  padding: 9px 12px;
  font-size: 0.8rem;
  font-weight: 500;
  color: #1f2a44;
  background: #ffffff;
  cursor: pointer;
  opacity: 0;
  transform: translateX(8px) scale(0.98);
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(3, 35, 96, 0.06);

  &:nth-of-type(1) {
    transition-delay: 0ms;
  }

  &:nth-of-type(2) {
    transition-delay: 55ms;
  }

  &:nth-of-type(3) {
    transition-delay: 110ms;
  }

  &:nth-of-type(4) {
    transition-delay: 165ms;
  }

  &:hover {
    background: linear-gradient(135deg, rgba(0, 61, 165, 0.1) 0%, rgba(196, 151, 47, 0.12) 100%);
    border-color: rgba(0, 61, 165, 0.35);
    box-shadow: 0 6px 14px rgba(3, 35, 96, 0.12);
  }
}

@media (max-width: 1024px) {
  .questions-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .sub-questions {
    display: none;
  }
}

@media (max-width: 768px) {
  .hot-questions {
    padding: 40px 16px;
  }

  .section-title {
    font-size: 1.375rem;
  }

  .questions-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .sub-questions {
    display: none;
  }

  .question-card {
    padding: 14px;
  }

  .question-icon {
    width: 36px;
    height: 36px;
  }

  .question-text {
    font-size: 0.8125rem;
  }
}
</style>
