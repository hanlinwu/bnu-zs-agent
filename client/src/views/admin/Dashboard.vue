<script setup lang="ts">
import { ref, onMounted } from 'vue'
import {
  ChatDotRound,
  User,
  Document,
  Clock,
  TrendCharts,
} from '@element-plus/icons-vue'

interface StatCard {
  title: string
  value: number
  icon: any
  color: string
  bgColor: string
}

const stats = ref<StatCard[]>([
  { title: '今日对话数', value: 1283, icon: ChatDotRound, color: '#003DA5', bgColor: 'rgba(0, 61, 165, 0.08)' },
  { title: '活跃用户数', value: 456, icon: User, color: '#2E7D32', bgColor: 'rgba(46, 125, 50, 0.08)' },
  { title: '知识库文档数', value: 89, icon: Document, color: '#C4972F', bgColor: 'rgba(196, 151, 47, 0.08)' },
  { title: '待审核文档数', value: 7, icon: Clock, color: '#C62828', bgColor: 'rgba(198, 40, 40, 0.08)' },
])

interface HotTopic {
  rank: number
  question: string
  count: number
}

const hotTopics = ref<HotTopic[]>([
  { rank: 1, question: '2026年北京师范大学录取分数线是多少？', count: 328 },
  { rank: 2, question: '公费师范生毕业后的就业政策是什么？', count: 256 },
  { rank: 3, question: '北京师范大学有哪些优势学科？', count: 213 },
  { rank: 4, question: '珠海校区和北京校区有什么区别？', count: 189 },
  { rank: 5, question: '研究生奖学金覆盖比例是多少？', count: 167 },
  { rank: 6, question: '北京师范大学国际交流项目有哪些？', count: 145 },
  { rank: 7, question: '转专业政策是什么？', count: 132 },
  { rank: 8, question: '北京师范大学宿舍条件如何？', count: 121 },
])

const loading = ref(false)

onMounted(() => {
  loading.value = true
  setTimeout(() => { loading.value = false }, 500)
})
</script>

<template>
  <div class="dashboard-page">
    <div class="page-header">
      <h2 class="page-title">仪表盘</h2>
      <p class="page-desc">系统运行概览</p>
    </div>

    <div class="stats-grid">
      <div
        v-for="stat in stats"
        :key="stat.title"
        class="stat-card"
      >
        <div class="stat-icon" :style="{ background: stat.bgColor, color: stat.color }">
          <el-icon :size="28"><component :is="stat.icon" /></el-icon>
        </div>
        <div class="stat-info">
          <span class="stat-value">{{ stat.value.toLocaleString() }}</span>
          <span class="stat-title">{{ stat.title }}</span>
        </div>
      </div>
    </div>

    <div class="dashboard-grid">
      <div class="chart-section">
        <div class="section-card">
          <div class="card-header">
            <h3 class="card-title">
              <el-icon><TrendCharts /></el-icon>
              对话趋势图
            </h3>
            <el-radio-group size="small" model-value="week">
              <el-radio-button value="week">近7天</el-radio-button>
              <el-radio-button value="month">近30天</el-radio-button>
            </el-radio-group>
          </div>
          <div class="chart-placeholder">
            <el-icon :size="48" color="#E2E6ED"><TrendCharts /></el-icon>
            <span>对话趋势图</span>
            <span class="chart-hint">集成 ECharts 后在此渲染图表</span>
          </div>
        </div>
      </div>

      <div class="topics-section">
        <div class="section-card">
          <div class="card-header">
            <h3 class="card-title">
              <el-icon><ChatDotRound /></el-icon>
              热门问题 TOP 8
            </h3>
          </div>
          <div class="topics-list">
            <div
              v-for="topic in hotTopics"
              :key="topic.rank"
              class="topic-item"
            >
              <span
                class="topic-rank"
                :class="{ 'topic-rank--top': topic.rank <= 3 }"
              >
                {{ topic.rank }}
              </span>
              <span class="topic-question">{{ topic.question }}</span>
              <el-tag size="small" type="info" round>{{ topic.count }}次</el-tag>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.dashboard-page {
  max-width: 1200px;
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 22px;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 14px;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  padding: 20px;
  display: flex;
  align-items: center;
  gap: 16px;
  border: 1px solid var(--border-color, #E2E6ED);
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: var(--shadow-sm, 0 2px 8px rgba(0, 0, 0, 0.06));
  }
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  line-height: 1.2;
}

.stat-title {
  font-size: 13px;
  color: var(--text-secondary, #5A5A72);
  margin-top: 2px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.section-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  overflow: hidden;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color, #E2E6ED);
}

.card-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
  margin: 0;
  display: flex;
  align-items: center;
  gap: 6px;

  .el-icon {
    color: var(--bnu-blue, #003DA5);
  }
}

.chart-placeholder {
  height: 320px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--text-secondary, #5A5A72);
  font-size: 16px;

  .chart-hint {
    font-size: 12px;
    color: var(--text-secondary, #9E9EB3);
  }
}

.topics-list {
  padding: 8px 0;
  max-height: 360px;
  overflow-y: auto;
}

.topic-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 20px;
  transition: background 0.15s;

  &:hover {
    background: var(--bg-secondary, #F4F6FA);
  }
}

.topic-rank {
  width: 24px;
  height: 24px;
  border-radius: 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 700;
  flex-shrink: 0;
  background: var(--bg-secondary, #F4F6FA);
  color: var(--text-secondary, #5A5A72);

  &--top {
    background: var(--bnu-blue, #003DA5);
    color: #ffffff;
  }
}

.topic-question {
  flex: 1;
  font-size: 13px;
  color: var(--text-primary, #1A1A2E);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

@media (max-width: 1024px) {
  .stats-grid {
    grid-template-columns: repeat(2, 1fr);
  }

  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
