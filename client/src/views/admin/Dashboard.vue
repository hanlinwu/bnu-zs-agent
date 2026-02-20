<script setup lang="ts">
import { ref, onMounted, onBeforeUnmount, computed, nextTick } from 'vue'
import {
  ChatDotRound,
  User,
  Document,
  Clock,
  TrendCharts,
  UserFilled,
  ChatLineRound,
  PictureFilled,
  DataAnalysis,
  LocationFilled,
} from '@element-plus/icons-vue'
import {
  getDashboardStats,
  getDashboardTrends,
  getDashboardHot,
  type DashboardStats,
  type TrendItem,
  type HotQuestion,
} from '@/api/admin/dashboard'
import * as echarts from 'echarts'
import chinaGeoJson from '@/assets/maps/china.json'

interface StatCard {
  title: string
  value: number
  icon: any
  color: string
  bgColor: string
}

const loading = ref(true)
const trendDays = ref<7 | 30>(7)
const chartRef = ref<HTMLElement | null>(null)
const mapRef = ref<HTMLElement | null>(null)
let trendChart: echarts.ECharts | null = null
let mapChart: echarts.ECharts | null = null
let autoHoverTimer: ReturnType<typeof setInterval> | null = null
let currentHoverIndex = -1
let isMapHoverPaused = false
let danmakuSpawnTimer: ReturnType<typeof setTimeout> | null = null
let danmakuId = 0

const provinceHeatMock: Array<{ name: string; value: number }> = [
  { name: '北京市', value: 96 },
  { name: '天津市', value: 42 },
  { name: '河北省', value: 68 },
  { name: '山西省', value: 39 },
  { name: '内蒙古自治区', value: 24 },
  { name: '辽宁省', value: 55 },
  { name: '吉林省', value: 28 },
  { name: '黑龙江省', value: 22 },
  { name: '上海市', value: 88 },
  { name: '江苏省', value: 91 },
  { name: '浙江省', value: 89 },
  { name: '安徽省', value: 61 },
  { name: '福建省', value: 58 },
  { name: '江西省', value: 43 },
  { name: '山东省', value: 95 },
  { name: '河南省', value: 78 },
  { name: '湖北省', value: 73 },
  { name: '湖南省', value: 66 },
  { name: '广东省', value: 98 },
  { name: '广西壮族自治区', value: 41 },
  { name: '海南省', value: 19 },
  { name: '重庆市', value: 64 },
  { name: '四川省', value: 75 },
  { name: '贵州省', value: 33 },
  { name: '云南省', value: 37 },
  { name: '西藏自治区', value: 8 },
  { name: '陕西省', value: 52 },
  { name: '甘肃省', value: 17 },
  { name: '青海省', value: 11 },
  { name: '宁夏回族自治区', value: 13 },
  { name: '新疆维吾尔自治区', value: 21 },
]

// Real data refs
const statsData = ref<DashboardStats | null>(null)
const trendsData = ref<TrendItem[]>([])
const hotData = ref<HotQuestion[]>([])
const animatedValues = ref<number[]>([0, 0, 0, 0, 0, 0, 0, 0])
const danmakuContainerRef = ref<HTMLElement | null>(null)
const danmakuContainerWidth = ref(1200)

interface DanmakuItem {
  id: number
  text: string
  track: number
  duration: number
  offset: number
}

const danmakuTracks = ref<DanmakuItem[][]>([[], [], []])
const danmakuMessages = [
  '北师大心理学专业录取分数线是多少？',
  '请问今年有哪些新增专业？',
  '珠海校区和北京校区有什么区别？',
  '转专业政策是怎样的？',
  '公费师范生和普通师范生培养区别？',
  '宿舍条件和床位规格可以介绍一下吗？',
  '是否支持双学位或辅修专业申请？',
  '提前批和普通批志愿填报有何差异？',
  '外语语种限制对报考影响大吗？',
  '奖学金覆盖比例和评定标准是什么？',
  '新生入学后可以申请转校区吗？',
  '教育学部有哪些热门研究方向？',
  '保研政策和推免比例大概是多少？',
  '国际交流项目的申请门槛高吗？',
  '今年招生章程预计何时发布？',
]

const stats = computed<StatCard[]>(() => {
  const s = statsData.value
  return [
    { title: '用户总数', value: s?.user_count ?? 0, icon: User, color: '#003DA5', bgColor: 'rgba(0, 61, 165, 0.08)' },
    { title: '近7天新增用户', value: s?.new_user_7d ?? 0, icon: UserFilled, color: '#1B8A5A', bgColor: 'rgba(27, 138, 90, 0.10)' },
    { title: '对话总数', value: s?.conversation_count ?? 0, icon: ChatDotRound, color: '#2E7D32', bgColor: 'rgba(46, 125, 50, 0.08)' },
    { title: '今日活跃用户', value: s?.active_today ?? 0, icon: DataAnalysis, color: '#7A5AF8', bgColor: 'rgba(122, 90, 248, 0.10)' },
    { title: '消息总数', value: s?.message_count ?? 0, icon: ChatLineRound, color: '#C4972F', bgColor: 'rgba(196, 151, 47, 0.08)' },
    { title: '今日消息数', value: s?.message_today ?? 0, icon: Clock, color: '#F08C00', bgColor: 'rgba(240, 140, 0, 0.10)' },
    { title: '已通过知识文档', value: s?.knowledge_approved_count ?? 0, icon: Document, color: '#1565C0', bgColor: 'rgba(21, 101, 192, 0.10)' },
    { title: '待审核内容', value: (s?.pending_review_count ?? 0) + (s?.media_pending_review_count ?? 0), icon: PictureFilled, color: '#C62828', bgColor: 'rgba(198, 40, 40, 0.08)' },
  ]
})

function buildTrendOption(): echarts.EChartsOption {
  const labels = trendsData.value.map((t) => {
    const d = new Date(t.date)
    const dayNames = ['日', '一', '二', '三', '四', '五', '六']
    return trendDays.value === 7 ? `周${dayNames[d.getDay()]}` : `${d.getMonth() + 1}/${d.getDate()}`
  })
  const values = trendsData.value.map(t => t.count)
  const xAxisLabelInterval = trendDays.value === 30 ? 4 : 0

  return {
    animation: true,
    grid: {
      left: 24,
      right: 16,
      top: 16,
      bottom: 28,
      containLabel: true,
    },
    tooltip: {
      trigger: 'axis',
      axisPointer: { type: 'line' },
      formatter: (params: any) => {
        const p = Array.isArray(params) ? params[0] : params
        return `${p.axisValue}<br/>对话数：${p.data}`
      },
    },
    xAxis: {
      type: 'category',
      boundaryGap: false,
      data: labels,
      axisLabel: {
        interval: xAxisLabelInterval,
        color: '#5A5A72',
        fontSize: 11,
      },
      axisLine: { lineStyle: { color: '#D8DEE8' } },
      axisTick: { show: false },
    },
    yAxis: {
      type: 'value',
      minInterval: 1,
      splitLine: { lineStyle: { color: '#ECF0F6' } },
      axisLabel: { color: '#5A5A72', fontSize: 11 },
    },
    series: [
      {
        type: 'line',
        data: values,
        smooth: true,
        symbol: 'circle',
        symbolSize: 7,
        lineStyle: { width: 3, color: '#003DA5' },
        itemStyle: { color: '#003DA5', borderColor: '#fff', borderWidth: 2 },
        areaStyle: {
          color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
            { offset: 0, color: 'rgba(0, 61, 165, 0.25)' },
            { offset: 1, color: 'rgba(0, 61, 165, 0.02)' },
          ]),
        },
      },
    ],
    graphic: values.length === 0
      ? {
          type: 'text',
          left: 'center',
          top: 'middle',
          style: {
            text: '暂无数据',
            fill: '#5A5A72',
            fontSize: 14,
          },
        }
      : undefined,
  }
}

function renderTrendChart() {
  if (!chartRef.value) return
  if (!trendChart) {
    trendChart = echarts.init(chartRef.value)
  }
  trendChart.setOption(buildTrendOption(), true)
}

function buildMapOption(): echarts.EChartsOption {
  const values = provinceHeatMock.map(x => x.value)
  const max = Math.max(...values, 100)
  return {
    tooltip: {
      trigger: 'item',
      formatter: (p: any) => `${p.name}<br/>访问热度：${p.value ?? 0}`,
    },
    visualMap: {
      min: 0,
      max,
      text: ['高', '低'],
      realtime: false,
      calculable: true,
      orient: 'horizontal',
      left: 'center',
      bottom: 8,
      inRange: {
        color: ['#4575B4', '#74ADD1', '#ABD9E9', '#E0F3F8', '#FFF7BC', '#FEE090', '#FDAE61', '#F46D43', '#D73027'],
      },
      outOfRange: {
        color: ['#F2F6FB'],
      },
      textStyle: {
        color: '#5A5A72',
      },
    },
    series: [
      {
        name: '访问热度',
        type: 'map',
        map: 'china',
        roam: true,
        scaleLimit: {
          min: 0.8,
          max: 6,
        },
        layoutCenter: ['50%', '48%'],
        layoutSize: '90%',
        zoom: 1,
        selectedMode: false,
        label: {
          show: false,
        },
        itemStyle: {
          borderColor: '#F7FAFF',
          borderWidth: 1,
          areaColor: '#EFF4FA',
        },
        emphasis: {
          label: { show: false },
          itemStyle: {
            areaColor: '#C92A2A',
            borderColor: '#FFFFFF',
            borderWidth: 1.2,
            shadowBlur: 14,
            shadowColor: 'rgba(201, 42, 42, 0.35)',
          },
        },
        data: provinceHeatMock,
      },
    ],
  }
}

function renderMapChart() {
  if (!mapRef.value) return
  if (!mapChart) {
    mapChart = echarts.init(mapRef.value)
  }
  mapChart.setOption(buildMapOption(), true)
}

function stopAutoHover() {
  if (autoHoverTimer) {
    clearInterval(autoHoverTimer)
    autoHoverTimer = null
  }
}

function runAutoHoverStep() {
  if (!mapChart || provinceHeatMock.length === 0) return
  if (currentHoverIndex >= 0) {
    mapChart.dispatchAction({ type: 'downplay', seriesIndex: 0, dataIndex: currentHoverIndex })
  }
  currentHoverIndex = (currentHoverIndex + 1) % provinceHeatMock.length
  mapChart.dispatchAction({ type: 'highlight', seriesIndex: 0, dataIndex: currentHoverIndex })
  mapChart.dispatchAction({ type: 'showTip', seriesIndex: 0, dataIndex: currentHoverIndex })
}

function startAutoHover() {
  if (!mapChart || autoHoverTimer || isMapHoverPaused || provinceHeatMock.length === 0) return
  if (currentHoverIndex < 0) {
    runAutoHoverStep()
  }
  autoHoverTimer = setInterval(() => {
    runAutoHoverStep()
  }, 2000)
}

function handleMapMouseOver(params: any) {
  if (params?.componentType !== 'series') return
  isMapHoverPaused = true
  stopAutoHover()
}

function handleMapMouseOut(params: any) {
  if (params?.componentType !== 'series') return
  isMapHoverPaused = false
  startAutoHover()
}

function bindMapHoverEvents() {
  if (!mapChart) return
  mapChart.off('mouseover', handleMapMouseOver)
  mapChart.off('mouseout', handleMapMouseOut)
  mapChart.on('mouseover', handleMapMouseOver)
  mapChart.on('mouseout', handleMapMouseOut)
}

function animateNumbers() {
  const targets = stats.value.map(s => s.value)
  const duration = 1500
  const start = performance.now()

  function tick(now: number) {
    const elapsed = now - start
    const progress = Math.min(elapsed / duration, 1)
    const eased = 1 - Math.pow(1 - progress, 3)
    animatedValues.value = targets.map(t => Math.round(t * eased))
    if (progress < 1) {
      requestAnimationFrame(tick)
    }
  }

  requestAnimationFrame(tick)
}

function updateDanmakuContainerWidth() {
  danmakuContainerWidth.value = danmakuContainerRef.value?.clientWidth ?? 1200
}

function spawnDanmaku() {
  if (danmakuMessages.length === 0 || danmakuTracks.value.length === 0) return
  const message = danmakuMessages[Math.floor(Math.random() * danmakuMessages.length)]
  const track = Math.floor(Math.random() * danmakuTracks.value.length)
  const duration = Math.floor(Math.random() * 8) + 8
  const offset = Math.floor(Math.random() * 160)
  const trackItems = danmakuTracks.value[track]
  if (!message || !trackItems) return
  trackItems.push({
    id: ++danmakuId,
    text: message,
    track,
    duration,
    offset,
  })
}

function scheduleDanmakuSpawn() {
  const delay = 1500 + Math.floor(Math.random() * 1000)
  danmakuSpawnTimer = setTimeout(() => {
    spawnDanmaku()
    scheduleDanmakuSpawn()
  }, delay)
}

function startDanmaku() {
  if (danmakuSpawnTimer) return
  for (let i = 0; i < danmakuTracks.value.length; i += 1) {
    spawnDanmaku()
  }
  scheduleDanmakuSpawn()
}

function stopDanmaku() {
  if (danmakuSpawnTimer) {
    clearTimeout(danmakuSpawnTimer)
    danmakuSpawnTimer = null
  }
}

function removeDanmaku(trackIndex: number, id: number) {
  const track = danmakuTracks.value[trackIndex]
  if (!track) return
  const index = track.findIndex(item => item.id === id)
  if (index >= 0) {
    track.splice(index, 1)
  }
}

function handleResize() {
  trendChart?.resize()
  mapChart?.resize()
  updateDanmakuContainerWidth()
}

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
    await nextTick()
    renderTrendChart()
  } catch {
    trendsData.value = []
    await nextTick()
    renderTrendChart()
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
  echarts.registerMap('china', chinaGeoJson as any)
  loading.value = true
  await Promise.all([fetchStats(), fetchTrends(), fetchHot()])
  await nextTick()
  renderTrendChart()
  renderMapChart()
  bindMapHoverEvents()
  startAutoHover()
  updateDanmakuContainerWidth()
  startDanmaku()
  window.addEventListener('resize', handleResize)
  loading.value = false
  animateNumbers()
})

onBeforeUnmount(() => {
  stopAutoHover()
  stopDanmaku()
  window.removeEventListener('resize', handleResize)
  mapChart?.off('mouseover', handleMapMouseOver)
  mapChart?.off('mouseout', handleMapMouseOut)
  trendChart?.dispose()
  mapChart?.dispose()
  trendChart = null
  mapChart = null
})
</script>

<template>
  <div class="dashboard-page">
    <div class="page-header">
      <div class="page-heading">
        <h2 class="page-title">仪表盘</h2>
        <p class="page-desc">系统运行概览</p>
      </div>
      <div ref="danmakuContainerRef" class="danmaku-floating">
        <div
          v-for="(trackItems, trackIndex) in danmakuTracks"
          :key="trackIndex"
          class="danmaku-track"
        >
          <span
            v-for="item in trackItems"
            :key="item.id"
            class="danmaku-item"
            :style="{
              '--duration': `${item.duration}s`,
              '--offset': `${item.offset}px`,
              '--track-width': `${danmakuContainerWidth}px`,
            }"
            @animationend="removeDanmaku(trackIndex, item.id)"
          >
            {{ item.text }}
          </span>
        </div>
      </div>
    </div>

    <div class="core-layout">
      <div class="side-column side-column--left">
        <div class="stats-block">
          <div class="stats-grid">
            <div
              v-for="(stat, index) in stats.slice(0, 4)"
              :key="stat.title"
              class="stat-card"
            >
              <div class="stat-icon" :style="{ background: stat.bgColor, color: stat.color }">
                <el-icon :size="22"><component :is="stat.icon" /></el-icon>
              </div>
              <div class="stat-info">
                <span class="stat-value">{{ loading ? '-' : (animatedValues[index] ?? 0).toLocaleString() }}</span>
                <span class="stat-title">{{ stat.title }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="section-card floating-card">
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
            <div ref="chartRef" class="echart-canvas" />
          </div>
        </div>
      </div>

      <div class="center-column">
        <div class="section-card map-core-card">
          <div class="card-header">
            <h3 class="card-title">
              <el-icon><LocationFilled /></el-icon>
              全国访问热度（Mock）
            </h3>
          </div>
          <div class="map-area">
            <div ref="mapRef" class="map-canvas" />
          </div>
        </div>
      </div>

      <div class="side-column side-column--right">
        <div class="stats-block">
          <div class="stats-grid">
            <div
              v-for="(stat, index) in stats.slice(4)"
              :key="stat.title"
              class="stat-card"
            >
              <div class="stat-icon" :style="{ background: stat.bgColor, color: stat.color }">
                <el-icon :size="22"><component :is="stat.icon" /></el-icon>
              </div>
              <div class="stat-info">
                <span class="stat-value">{{ loading ? '-' : (animatedValues[index + 4] ?? 0).toLocaleString() }}</span>
                <span class="stat-title">{{ stat.title }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="section-card floating-card">
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
  position: relative;
}

.page-header {
  display: grid;
  grid-template-columns: minmax(220px, auto) minmax(420px, 1fr);
  align-items: start;
  gap: 16px;
  margin-bottom: 16px;
}

.page-heading {
  min-width: 0;
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

.core-layout {
  display: grid;
  grid-template-columns: minmax(320px, 380px) minmax(320px, 1fr) minmax(320px, 380px);
  gap: 16px;
  min-height: 680px;
  align-items: stretch;
}

.danmaku-floating {
  position: relative;
  height: 74px;
  overflow: hidden;
  padding: 2px 0;
  pointer-events: none;
}

.danmaku-track {
  position: relative;
  height: 22px;
  overflow: hidden;
}

.danmaku-item {
  position: absolute;
  left: calc(100% + var(--offset, 0px));
  top: 1px;
  white-space: nowrap;
  font-size: 0.8125rem;
  line-height: 1.25;
  color: #2c3e50;
  padding: 1px 10px 2px;
  border-radius: 999px;
  border: 1px solid rgba(0, 61, 165, 0.14);
  background: rgba(255, 255, 255, 0.82);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
  animation: danmaku-scroll var(--duration) linear forwards;
}

@keyframes danmaku-scroll {
  from {
    transform: translateX(0);
  }

  to {
    transform: translateX(calc(-1 * (var(--track-width, 1200px) + 120%)));
  }
}

.side-column {
  display: grid;
  grid-template-rows: auto 1fr;
  gap: 16px;
  min-width: 0;
}

.center-column {
  min-width: 0;
}

.section-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  overflow: hidden;
  min-width: 0;
  height: 100%;
  display: flex;
  flex-direction: column;
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

.stats-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.stat-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  padding: 14px 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  border: 1px solid var(--border-color, #E2E6ED);
  transition: box-shadow 0.2s;

  &:hover {
    box-shadow: var(--shadow-sm, 0 2px 8px rgba(0, 0, 0, 0.06));
  }
}

.stat-icon {
  width: 40px;
  height: 40px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.stat-info {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.stat-value {
  font-size: 1.05rem;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  line-height: 1.2;
}

.stat-title {
  font-size: 0.75rem;
  color: var(--text-secondary, #5A5A72);
  margin-top: 2px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.chart-area {
  height: 100%;
  padding: 8px 12px 10px 8px;
  overflow: hidden;
  min-width: 0;
}

.floating-card {
  min-height: 0;
}

.echart-canvas {
  width: 100%;
  height: 100%;
}

.map-core-card {
  min-height: 680px;
}

.map-area {
  flex: 1;
  min-height: 620px;
  padding: 4px 8px 0;
}

.map-canvas {
  width: 100%;
  height: 100%;
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
  height: 100%;
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
  .page-header {
    grid-template-columns: 1fr;
    gap: 10px;
  }

  .core-layout {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .side-column {
    grid-template-rows: auto auto;
  }

  .map-core-card {
    min-height: 460px;
  }

  .map-area {
    min-height: 400px;
  }
}

@media (max-width: 768px) {
  .stats-grid {
    grid-template-columns: 1fr;
  }

  .card-header {
    padding: 14px 16px;
  }

  .danmaku-floating {
    height: 108px;
  }

  .danmaku-track {
    height: 34px;
  }
}
</style>
