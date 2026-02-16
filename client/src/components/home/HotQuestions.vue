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
import { markRaw, type Component } from 'vue'

const router = useRouter()

interface HotQuestion {
  id: number
  icon: Component
  text: string
  query: string
}

const questions: HotQuestion[] = [
  { id: 1, icon: markRaw(TrendCharts), text: '录取分数线', query: '北京师范大学各专业录取分数线是多少？' },
  { id: 2, icon: markRaw(School), text: '优势专业', query: '北京师范大学有哪些优势专业和学科？' },
  { id: 3, icon: markRaw(Reading), text: '公费师范生政策', query: '北京师范大学公费师范生政策是什么？' },
  { id: 4, icon: markRaw(OfficeBuilding), text: '珠海校区', query: '北京师范大学珠海校区有哪些专业？' },
  { id: 5, icon: markRaw(Connection), text: '国际交流项目', query: '北京师范大学有哪些国际交流项目？' },
  { id: 6, icon: markRaw(Trophy), text: '奖学金政策', query: '北京师范大学奖学金有哪些类型？' },
  { id: 7, icon: markRaw(Coffee), text: '校园生活', query: '北京师范大学校园生活怎么样？' },
  { id: 8, icon: markRaw(Postcard), text: '考研招生', query: '北京师范大学研究生招生有哪些要求？' },
]

function askQuestion(query: string) {
  router.push({ path: '/chat', query: { q: query } })
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
          @click="askQuestion(item.query)"
        >
          <div class="question-icon">
            <el-icon :size="24"><component :is="item.icon" /></el-icon>
          </div>
          <span class="question-text">{{ item.text }}</span>
          <svg class="question-arrow" width="16" height="16" viewBox="0 0 16 16" fill="none">
            <path d="M6 3l5 5-5 5" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round"/>
          </svg>
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
  font-size: 26px;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 6px;
}

.section-desc {
  text-align: center;
  font-size: 15px;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
}

.questions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 12px;
}

.question-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 18px;
  background: var(--bg-secondary, #F4F6FA);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.2s ease;
  border: 1px solid transparent;

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
  font-size: 14px;
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

@media (max-width: 1024px) {
  .questions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .hot-questions {
    padding: 40px 16px;
  }

  .section-title {
    font-size: 22px;
  }

  .questions-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 10px;
  }

  .question-card {
    padding: 14px;
  }

  .question-icon {
    width: 36px;
    height: 36px;
  }

  .question-text {
    font-size: 13px;
  }
}
</style>
