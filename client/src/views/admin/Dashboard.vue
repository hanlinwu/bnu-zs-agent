<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import {
  ChatDotRound,
  User,
  Document,
  Clock,
  TrendCharts,
} from '@element-plus/icons-vue'
import {
  getDashboardStats,
  getDashboardTrends,
  getDashboardHot,
  type DashboardStats,
  type TrendItem,
  type HotQuestion,
} from '@/api/admin/dashboard'

interface StatCard {
  title: string
  value: number
  icon: any
  color: string
  bgColor: string
}

const loading = ref(true)
const trendDays = ref<7 | 30>(7)

// Real data refs
const statsData = ref<DashboardStats | null>(null)
const trendsData = ref<TrendItem[]>([])
const hotData = ref<HotQuestion[]>([])

const stats = computed<StatCard[]>(() => {
  const s = statsData.value
  return [
    { title: '对话总数', value: s?.conversation_count ?? 0, icon: ChatDotRound, color: '#003DA5', bgColor: 'rgba(0, 61, 165, 0.08)' },
    { title: '今日活跃用户', value: s?.active_today ?? 0, icon: User, color: '#2E7D32', bgColor: 'rgba(46, 125, 50, 0.08)' },
    { title: '知识库文档数', value: s?.knowledge_count ?? 0, icon: Document, color: '#C4972F', bgColor: 'rgba(196, 151, 47, 0.08)' },
    { title: '待审核文档', value: s?.pending_review_count ?? 0, icon: Clock, color: '#C62828', bgColor: 'rgba(198, 40, 40, 0.08)' },
  ]
})

const chartData = computed(() => {
  if (trendsData.value.length === 0) return []
  const maxCount = Math.max(...trendsData.value.map(t => t.count), 1)
  return trendsData.value.map(t => {
    const d = new Date(t.date)
    const dayNames = ['日', '一', '二', '三', '四', '五', '六']
    const label = trendDays.value <= 7
      ? `周${dayNames[d.getDay()]}`
      : `${d.getMonth() + 1}/${d.getDate()}`
    return {
      label,
      value: t.count,
      height: Math.max((t.count / maxCount) * 100, 4),
    }
  })
})

const hotTopics = computed(() =>
  hotData.value.map((item, idx) => ({
    rank: idx + 1,
    question: item.question,
    count: item.count,
  }))
)

async function fetchStats() {
  try {
    const res = await getDashboardStats()
    statsData.value = res.data
  } catch { /* stats will show 0 */ }
}

async function fetchTrends() {
  try {
    const res = await getDashboardTrends(trendDays.value)
    trendsData.value = res.data.items
  } catch {
    trendsData.value = []
  }
}

async function fetchHot() {
  try {
    const res = await getDashboardHot(8, 7)
    hotData.value = res.data.items
  } catch {
    hotData.value = []
  }
}

async function handleTrendChange(days: string | number | boolean | undefined) {
  trendDays.value = Number(days) === 30 ? 30 : 7
  await fetchTrends()
}

onMounted(async () => {
  loading.value = true
  await Promise.all([fetchStats(), fetchTrends(), fetchHot()])
  loading.value = false
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
          <span class="stat-value">{{ loading ? '-' : stat.value.toLocaleString() }}</span>
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
            <el-radio-group size="small" :model-value="trendDays" @change="handleTrendChange">
              <el-radio-button :value="7">近7天</el-radio-button>
              <el-radio-button :value="30">近30天</el-radio-button>
            </el-radio-group>
          </div>
          <div class="chart-area">
            <template v-if="chartData.length > 0">
              <div class="chart-bars">
                <div v-for="(bar, idx) in chartData" :key="idx" class="chart-bar-group">
                  <div class="chart-bar" :style="{ height: bar.height + '%' }">
                    <span class="chart-bar-value">{{ bar.value }}</span>
                  </div>
                  <span class="chart-bar-label">{{ bar.label }}</span>
                </div>
              </div>
            </template>
            <div v-else class="chart-empty">
              <span>暂无数据</span>
            </div>
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
            <template v-if="hotTopics.length > 0">
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
            </template>
            <div v-else class="topics-empty">
              <span>暂无数据</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.dashboard-page {
}

.page-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 0.875rem;
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
  font-size: 1.75rem;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  line-height: 1.2;
}

.stat-title {
  font-size: 0.8125rem;
  color: var(--text-secondary, #5A5A72);
  margin-top: 2px;
}

.dashboard-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  min-width: 0;
}

.chart-section {
  min-width: 0;
  overflow: hidden;
}

.section-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  overflow: hidden;
  min-width: 0;
}

.card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 16px 20px;
  border-bottom: 1px solid var(--border-color, #E2E6ED);
}

.card-title {
  font-size: 0.9375rem;
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

.chart-area {
  height: 320px;
  padding: 20px;
  display: flex;
  align-items: flex-end;
  overflow-x: auto;
  min-width: 0;
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  gap: 12px;
  width: 100%;
  min-width: 100%;
  height: 100%;
}

.chart-bar-group {
  flex: 1 1 0;
  min-width: 32px;
  max-width: none;
  display: flex;
  flex-direction: column;
  align-items: center;
  height: 100%;
  justify-content: flex-end;
  gap: 8px;
}

.chart-bar {
  width: 100%;
  max-width: 48px;
  min-width: 24px;
  background: linear-gradient(180deg, var(--bnu-blue, #003DA5), #1A5FBF);
  border-radius: 6px 6px 0 0;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding-top: 8px;
  min-height: 24px;
  transition: height 0.6s ease;
}

.chart-bar-value {
  font-size: 0.6875rem;
  font-weight: 600;
  color: #ffffff;
}

.chart-bar-label {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
}

.chart-empty,
.topics-empty {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
  color: var(--text-secondary, #5A5A72);
  font-size: 0.875rem;
}

.topics-list {
  padding: 8px 0;
  max-height: 360px;
  overflow-y: auto;
}

.topics-empty {
  padding: 40px 0;
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
  font-size: 0.75rem;
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
  font-size: 0.8125rem;
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
