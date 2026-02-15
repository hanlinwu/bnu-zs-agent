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
      <h2 class="section-title">热门问题</h2>
      <p class="section-desc">考生与家长最关心的招生话题</p>
      <div class="questions-grid">
        <div
          v-for="item in questions"
          :key="item.id"
          class="question-card"
          @click="askQuestion(item.query)"
        >
          <div class="question-icon">
            <el-icon :size="28"><component :is="item.icon" /></el-icon>
          </div>
          <span class="question-text">{{ item.text }}</span>
          <el-icon class="question-arrow"><ArrowRight /></el-icon>
        </div>
      </div>
    </div>
  </section>
</template>

<script lang="ts">
import { ArrowRight } from '@element-plus/icons-vue'
export default { components: { ArrowRight } }
</script>

<style lang="scss" scoped>
.hot-questions {
  padding: 72px 24px;
  background: var(--bg-primary, #ffffff);
}

.section-container {
  max-width: 1100px;
  margin: 0 auto;
}

.section-title {
  text-align: center;
  font-size: 30px;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 8px;
}

.section-desc {
  text-align: center;
  font-size: 16px;
  color: var(--text-secondary, #5A5A72);
  margin: 0 0 40px;
}

.questions-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
}

.question-card {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px;
  background: var(--bg-secondary, #F4F6FA);
  border-radius: 12px;
  cursor: pointer;
  transition: all 0.25s ease;
  border: 1px solid transparent;

  &:hover {
    background: var(--bg-primary, #ffffff);
    border-color: var(--bnu-blue, #003DA5);
    box-shadow: var(--shadow-md, 0 4px 16px rgba(0, 61, 165, 0.1));
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
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  background: rgba(0, 61, 165, 0.08);
  color: var(--bnu-blue, #003DA5);
  transition: all 0.25s ease;
}

.question-text {
  flex: 1;
  font-size: 15px;
  font-weight: 500;
  color: var(--text-primary, #1A1A2E);
}

.question-arrow {
  flex-shrink: 0;
  opacity: 0;
  transform: translateX(-8px);
  transition: all 0.25s ease;
  color: var(--bnu-blue, #003DA5);
}

@media (max-width: 1024px) {
  .questions-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}

@media (max-width: 768px) {
  .hot-questions {
    padding: 48px 16px;
  }

  .section-title {
    font-size: 24px;
  }

  .questions-grid {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .question-card {
    padding: 16px;
  }

  .question-icon {
    width: 40px;
    height: 40px;
  }

  .question-text {
    font-size: 14px;
  }
}
</style>
