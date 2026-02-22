<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import * as systemConfigApi from '@/api/admin/systemConfig'
import type { ChatGuardrailConfig } from '@/types/admin'

const loading = ref(false)
const saving = ref(false)
const activeFlowNode = ref('risk_medium_topic_specific')
const router = useRouter()

type FlowNodeMeta = {
  id: string
  label: string
  short: string
  module?: 'risk' | 'prompts'
  configPath?: string
}

type GraphNode = {
  id: string
  x: number
  y: number
  w: number
  h: number
  color?: 'default' | 'risk' | 'high' | 'medium' | 'low'
}

type GraphEdge = {
  from: string
  to: string
}

const flowNodeMap: Record<string, FlowNodeMeta> = {
  input: { id: 'input', label: '用户问题', short: '输入消息' },
  sensitive: { id: 'sensitive', label: '敏感词检测', short: 'block/warn/pass' },
  risk: { id: 'risk', label: '决策模型', short: 'risk + tools', module: 'risk' },
  risk_high_keyword: {
    id: 'risk_high_keyword',
    label: '高风险规则兜底',
    short: 'high fallback',
    module: 'risk',
    configPath: 'risk.high_keywords',
  },
  risk_medium_keyword: {
    id: 'risk_medium_keyword',
    label: '中风险规则兜底',
    short: 'medium fallback',
    module: 'risk',
    configPath: 'risk.medium_keywords',
  },
  risk_medium_topic_specific: {
    id: 'risk_medium_topic_specific',
    label: '主题 + 具体性兜底',
    short: 'topic + hint fallback',
    module: 'risk',
    configPath: 'risk.medium_topics + risk.medium_specific_hints',
  },
  high_strategy: {
    id: 'high_strategy',
    label: '高风险处理',
    short: '固定回复',
    module: 'prompts',
    configPath: 'prompts.high_risk_response',
  },
  medium_strategy: {
    id: 'medium_strategy',
    label: '工具链执行',
    short: '知识库/网页/媒体 检索',
    module: 'prompts',
    configPath: 'prompts.medium_* / no_knowledge_response',
  },
  low_strategy: {
    id: 'low_strategy',
    label: '生成回答',
    short: '注入上下文后流式回复',
    module: 'prompts',
    configPath: 'prompts.low_system_prompt',
  },
}

const graphNodes: GraphNode[] = [
  { id: 'input', x: 40, y: 80, w: 150, h: 72, color: 'default' },
  { id: 'sensitive', x: 240, y: 80, w: 170, h: 72, color: 'default' },
  { id: 'risk', x: 460, y: 80, w: 170, h: 72, color: 'risk' },

  { id: 'risk_high_keyword', x: 700, y: 16, w: 210, h: 62, color: 'high' },
  { id: 'risk_medium_keyword', x: 700, y: 100, w: 210, h: 62, color: 'medium' },
  { id: 'risk_medium_topic_specific', x: 700, y: 184, w: 210, h: 62, color: 'medium' },

  { id: 'high_strategy', x: 960, y: 16, w: 160, h: 62, color: 'high' },
  { id: 'medium_strategy', x: 960, y: 132, w: 160, h: 62, color: 'medium' },
  { id: 'low_strategy', x: 960, y: 256, w: 160, h: 62, color: 'low' },
]

const graphNodeMap = computed(() => {
  return graphNodes.reduce<Record<string, GraphNode>>((acc, node) => {
    acc[node.id] = node
    return acc
  }, {})
})

const graphEdges: GraphEdge[] = [
  { from: 'input', to: 'sensitive' },
  { from: 'sensitive', to: 'risk' },

  { from: 'risk', to: 'risk_high_keyword' },
  { from: 'risk', to: 'risk_medium_keyword' },
  { from: 'risk', to: 'risk_medium_topic_specific' },
  { from: 'risk', to: 'low_strategy' },

  { from: 'risk_high_keyword', to: 'high_strategy' },
  { from: 'risk_medium_keyword', to: 'medium_strategy' },
  { from: 'risk_medium_topic_specific', to: 'medium_strategy' },
]

const activePathMap: Record<string, string[]> = {
  input: ['input'],
  sensitive: ['input', 'sensitive'],
  risk: ['input', 'sensitive', 'risk'],
  risk_high_keyword: ['input', 'sensitive', 'risk', 'risk_high_keyword'],
  risk_medium_keyword: ['input', 'sensitive', 'risk', 'risk_medium_keyword'],
  risk_medium_topic_specific: ['input', 'sensitive', 'risk', 'risk_medium_topic_specific'],
  high_strategy: ['input', 'sensitive', 'risk', 'risk_high_keyword', 'high_strategy'],
  medium_strategy: ['input', 'sensitive', 'risk', 'risk_medium_keyword', 'risk_medium_topic_specific', 'medium_strategy'],
  low_strategy: ['input', 'sensitive', 'risk', 'low_strategy'],
}

const activeNodeSet = computed(() => new Set(activePathMap[activeFlowNode.value] || [activeFlowNode.value]))

function getFlowNodeMeta(nodeId: string): FlowNodeMeta {
  return flowNodeMap[nodeId] || { id: nodeId, label: nodeId, short: '' }
}

function isEdgeActive(edge: GraphEdge): boolean {
  const pathNodes = activePathMap[activeFlowNode.value] || []
  const fromIdx = pathNodes.indexOf(edge.from)
  const toIdx = pathNodes.indexOf(edge.to)
  if (fromIdx === -1 || toIdx === -1) return false
  return toIdx > fromIdx
}

function edgePath(edge: GraphEdge): string {
  const from = graphNodeMap.value[edge.from]
  const to = graphNodeMap.value[edge.to]
  if (!from || !to) return ''

  const x1 = from.x + from.w
  const y1 = from.y + from.h / 2
  const x2 = to.x
  const y2 = to.y + to.h / 2

  if (edge.from === 'risk') {
    const laneX = x1 + 28
    return `M ${x1} ${y1} L ${laneX} ${y1} L ${laneX} ${y2} L ${x2} ${y2}`
  }

  if (edge.to === 'medium_strategy') {
    const laneX = x2 - 36
    const laneY = edge.from === 'risk_medium_keyword' ? y2 - 22 : y2 + 22
    const approachX = x2 - 14
    return `M ${x1} ${y1} L ${laneX} ${y1} L ${laneX} ${laneY} L ${approachX} ${laneY} L ${approachX} ${y2} L ${x2} ${y2}`
  }

  const midX = (x1 + x2) / 2
  return `M ${x1} ${y1} L ${midX} ${y1} L ${midX} ${y2} L ${x2} ${y2}`
}

function nodeFill(node: GraphNode, active: boolean): string {
  if (active) {
    switch (node.color) {
      case 'high': return '#FEE2E2'
      case 'medium': return '#FEF3C7'
      case 'low': return '#DCFCE7'
      case 'risk': return '#DBEAFE'
      default: return '#E2E8F0'
    }
  }
  switch (node.color) {
    case 'high': return '#FFF5F5'
    case 'medium': return '#FFFBEB'
    case 'low': return '#F0FDF4'
    case 'risk': return '#EFF6FF'
    default: return '#F8FAFC'
  }
}

function nodeStroke(node: GraphNode, active: boolean): string {
  if (active) {
    switch (node.color) {
      case 'high': return '#DC2626'
      case 'medium': return '#D97706'
      case 'low': return '#16A34A'
      case 'risk': return '#2563EB'
      default: return '#334155'
    }
  }
  return '#CBD5E1'
}

const form = reactive<ChatGuardrailConfig>({
  risk: {
    high_keywords: [],
    medium_keywords: [],
    medium_topics: [],
    medium_specific_hints: [],
  },
  prompts: {
    medium_system_prompt: '',
    low_system_prompt: '',
    medium_citation_hint: '',
    medium_knowledge_instructions: '',
    high_risk_response: '',
    no_knowledge_response: '',
  },
})

function parseKeywordText(text: string): string[] {
  return text
    .split(/\n|,|，/g)
    .map(item => item.trim())
    .filter(Boolean)
}

function toKeywordText(items: string[]): string {
  return items.join('\n')
}

const highKeywordsText = computed({
  get: () => toKeywordText(form.risk.high_keywords),
  set: (value: string) => { form.risk.high_keywords = parseKeywordText(value) },
})

const mediumKeywordsText = computed({
  get: () => toKeywordText(form.risk.medium_keywords),
  set: (value: string) => { form.risk.medium_keywords = parseKeywordText(value) },
})

const mediumTopicsText = computed({
  get: () => toKeywordText(form.risk.medium_topics),
  set: (value: string) => { form.risk.medium_topics = parseKeywordText(value) },
})

const mediumSpecificHintsText = computed({
  get: () => toKeywordText(form.risk.medium_specific_hints),
  set: (value: string) => { form.risk.medium_specific_hints = parseKeywordText(value) },
})

function clickFlowNode(nodeId: string) {
  activeFlowNode.value = nodeId
}

function goToSensitiveManage() {
  router.push('/admin/sensitive')
}

const activeFlowDetail = computed(() => {
  switch (activeFlowNode.value) {
    case 'risk_high_keyword':
      return {
        ...flowNodeMap.risk_high_keyword,
        description: '当决策模型不可用或结果异常时，命中高风险关键词会直接判定为 high。',
        items: ['高风险关键词'],
      }
    case 'risk_medium_keyword':
      return {
        ...flowNodeMap.risk_medium_keyword,
        description: '当决策模型不可用或结果异常时，命中中风险关键词会判定为 medium。',
        items: ['中风险关键词'],
      }
    case 'risk_medium_topic_specific':
      return {
        ...flowNodeMap.risk_medium_topic_specific,
        description: '当决策模型不可用或结果异常时，同时命中主题词+具体性线索会判定为 medium。',
        items: ['中风险主题词', '中风险具体性线索'],
      }
    case 'high_strategy':
      return {
        ...flowNodeMap.high_strategy,
        description: '高风险问题不进入工具检索和自由生成，直接返回固定回复。',
        items: ['高风险固定回复'],
      }
    case 'medium_strategy':
      return {
        ...flowNodeMap.medium_strategy,
        description: '决策模型返回工具列表后，按顺序执行知识库/网页/媒体检索，重排筛选后注入上下文。',
        items: [
          '中风险系统 Prompt',
          '中风险引用提示',
          '中风险检索约束',
          '无有效证据时兜底回复',
        ],
      }
    case 'low_strategy':
      return {
        ...flowNodeMap.low_strategy,
        description: '最终由对话模型基于注入上下文流式生成回答，并返回工具链与来源明细。',
        items: ['低风险系统 Prompt', '工具链追踪信息'],
      }
    case 'sensitive':
      return {
        ...flowNodeMap.sensitive,
        description: '敏感词检测先于风险判定执行，block 会直接拦截。该配置在“敏感词库”模块维护。',
        items: [],
      }
    case 'risk':
      return {
        ...flowNodeMap.risk,
        description: '先由决策模型判定风险并输出工具列表；若失败则回退到规则判定（高风险关键词 -> 中风险关键词 -> 主题+具体性线索）。',
        items: [],
      }
    default:
      return {
        ...flowNodeMap.input,
        description: '用户输入后，系统依次执行敏感词检测、决策模型路由、工具检索、上下文注入和流式生成。',
        items: [],
      }
  }
})

function applyFormValue(value: ChatGuardrailConfig) {
  form.risk.high_keywords = [...(value.risk?.high_keywords || [])]
  form.risk.medium_keywords = [...(value.risk?.medium_keywords || [])]
  form.risk.medium_topics = [...(value.risk?.medium_topics || [])]
  form.risk.medium_specific_hints = [...(value.risk?.medium_specific_hints || [])]

  form.prompts.medium_system_prompt = value.prompts?.medium_system_prompt || ''
  form.prompts.low_system_prompt = value.prompts?.low_system_prompt || ''
  form.prompts.medium_citation_hint = value.prompts?.medium_citation_hint || ''
  form.prompts.medium_knowledge_instructions = value.prompts?.medium_knowledge_instructions || ''
  form.prompts.high_risk_response = value.prompts?.high_risk_response || ''
  form.prompts.no_knowledge_response = value.prompts?.no_knowledge_response || ''
}

async function fetchConfig() {
  loading.value = true
  try {
    const res = await systemConfigApi.getChatGuardrailConfig()
    applyFormValue(res.data.value)
  } catch {
    ElMessage.error('加载系统配置失败')
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const payload: ChatGuardrailConfig = {
      risk: {
        high_keywords: form.risk.high_keywords,
        medium_keywords: form.risk.medium_keywords,
        medium_topics: form.risk.medium_topics,
        medium_specific_hints: form.risk.medium_specific_hints,
      },
      prompts: {
        medium_system_prompt: form.prompts.medium_system_prompt,
        low_system_prompt: form.prompts.low_system_prompt,
        medium_citation_hint: form.prompts.medium_citation_hint,
        medium_knowledge_instructions: form.prompts.medium_knowledge_instructions,
        high_risk_response: form.prompts.high_risk_response,
        no_knowledge_response: form.prompts.no_knowledge_response,
      },
    }

    const res = await systemConfigApi.updateChatGuardrailConfig(payload)
    applyFormValue(res.data.value)
    ElMessage.success('系统配置已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

onMounted(() => {
  fetchConfig()
})
</script>

<template>
  <div v-loading="loading" class="system-config-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">智能体配置</h2>
        <p class="page-desc">配置决策模型兜底规则与分级提示词（流程：风险判定 + 工具链路由 + 上下文注入）</p>
      </div>
      <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
    </div>

    <div class="config-form">
      <div class="section-card process-card">
        <h3 class="section-title">处理流程可视化（点击节点查看详情）</h3>
        <p class="process-desc">
          当前线上流程：先由决策模型输出风险等级与工具列表（知识库/网页/媒体），再执行检索并将证据注入上下文生成回答。
          下方风险关键词配置用于决策异常时的兜底判定。
        </p>

        <div class="graph-wrap">
          <svg class="process-graph" viewBox="0 0 1140 340" role="img" aria-label="风险管控流程图">
            <defs>
              <marker id="arrowBase" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
                <path d="M0,0 L10,4 L0,8 z" fill="#94A3B8" />
              </marker>
              <marker id="arrowActive" markerWidth="10" markerHeight="8" refX="9" refY="4" orient="auto">
                <path d="M0,0 L10,4 L0,8 z" fill="#2563EB" />
              </marker>
            </defs>

            <g v-for="edge in graphEdges" :key="`${edge.from}-${edge.to}`">
              <path
                :d="edgePath(edge)"
                fill="none"
                :stroke="isEdgeActive(edge) ? '#2563EB' : '#94A3B8'"
                :stroke-width="isEdgeActive(edge) ? 2.2 : 1.4"
                :marker-end="isEdgeActive(edge) ? 'url(#arrowActive)' : 'url(#arrowBase)'"
                :opacity="isEdgeActive(edge) ? 1 : 0.7"
              />
            </g>

            <g
              v-for="node in graphNodes"
              :key="node.id"
              class="graph-node"
              :class="{ 'is-active': activeNodeSet.has(node.id) }"
              @click="clickFlowNode(node.id)"
            >
              <rect
                :x="node.x"
                :y="node.y"
                :width="node.w"
                :height="node.h"
                rx="10"
                :fill="nodeFill(node, activeNodeSet.has(node.id))"
                :stroke="nodeStroke(node, activeNodeSet.has(node.id))"
                :stroke-width="activeNodeSet.has(node.id) ? 2 : 1.2"
              />
              <text :x="node.x + 12" :y="node.y + 28" class="graph-node-title">
                {{ getFlowNodeMeta(node.id).label }}
              </text>
              <text :x="node.x + 12" :y="node.y + 48" class="graph-node-sub">
                {{ getFlowNodeMeta(node.id).short }}
              </text>
            </g>
          </svg>
        </div>

        <div class="flow-detail">
          <div class="flow-detail__header">
            <span class="flow-detail__title">{{ activeFlowDetail.label }}</span>
            <el-tag size="small" type="info">{{ activeFlowDetail.configPath || '流程节点' }}</el-tag>
          </div>
          <p class="flow-detail__desc">{{ activeFlowDetail.description }}</p>
          <el-button
            v-if="activeFlowNode === 'sensitive'"
            class="flow-detail__action"
            type="primary"
            link
            @click="goToSensitiveManage"
          >
            前往敏感词库管理
          </el-button>

        </div>
      </div>

      <div class="section-card node-config-card">
        <h3 class="section-title">节点配置编辑</h3>

        <el-form label-position="left" label-width="180px" class="node-edit-form">

          <template v-if="activeFlowNode === 'risk_high_keyword'">
            <el-form-item label="高风险关键词（每行一个）">
              <el-input v-model="highKeywordsText" type="textarea" :rows="10" placeholder="例如：保证录取" />
            </el-form-item>
          </template>

          <template v-else-if="activeFlowNode === 'risk_medium_keyword'">
            <el-form-item label="中风险关键词（每行一个）">
              <el-input v-model="mediumKeywordsText" type="textarea" :rows="10" placeholder="例如：分数线" />
            </el-form-item>
          </template>

          <template v-else-if="activeFlowNode === 'risk_medium_topic_specific'">
            <el-form-item label="中风险主题词（每行一个）">
              <el-input v-model="mediumTopicsText" type="textarea" :rows="7" placeholder="例如：招生" />
            </el-form-item>
            <el-form-item label="中风险具体性线索（每行一个）">
              <el-input v-model="mediumSpecificHintsText" type="textarea" :rows="7" placeholder="例如：什么时候、多少" />
            </el-form-item>
          </template>

          <template v-else-if="activeFlowNode === 'high_strategy'">
            <el-form-item label="高风险固定回复">
              <el-input v-model="form.prompts.high_risk_response" type="textarea" :rows="8" />
            </el-form-item>
          </template>

          <template v-else-if="activeFlowNode === 'medium_strategy'">
            <el-form-item label="中风险系统 Prompt">
              <el-input v-model="form.prompts.medium_system_prompt" type="textarea" :rows="7" />
            </el-form-item>
            <el-form-item label="中风险引用提示语">
              <el-input v-model="form.prompts.medium_citation_hint" type="textarea" :rows="4" />
            </el-form-item>
            <el-form-item label="中风险知识库约束说明">
              <el-input v-model="form.prompts.medium_knowledge_instructions" type="textarea" :rows="6" />
            </el-form-item>
            <el-form-item label="中风险无知识库兜底回复">
              <el-input v-model="form.prompts.no_knowledge_response" type="textarea" :rows="6" />
            </el-form-item>
          </template>

          <template v-else-if="activeFlowNode === 'low_strategy'">
            <el-form-item label="低风险系统 Prompt">
              <el-input v-model="form.prompts.low_system_prompt" type="textarea" :rows="8" />
            </el-form-item>
          </template>

          <template v-else>
            <el-empty description="该节点暂无可直接编辑的配置项，请选择可配置节点" />
          </template>
        </el-form>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.system-config-page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.page-title {
  margin: 0;
  font-size: 1.375rem;
  font-weight: 600;
  color: #1f2d3d;
}

.page-desc {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 0.875rem;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #ebeef5;
}

.section-title {
  margin: 0 0 12px;
  font-size: 1rem;
  color: #1f2d3d;
}

.process-card {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.process-desc {
  margin: -2px 0 0;
  font-size: 0.8125rem;
  color: #475569;
  line-height: 1.5;
}

.graph-wrap {
  width: 100%;
  overflow-x: auto;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  padding: 8px;
}

.process-graph {
  width: 100%;
  min-width: 1060px;
  height: 340px;
}

.graph-node {
  cursor: pointer;
}

.graph-node-title {
  font-size: 0.8125rem;
  font-weight: 600;
  fill: #0f172a;
}

.graph-node-sub {
  font-size: 0.75rem;
  fill: #475569;
}

.flow-detail {
  border: 1px solid #ebeef5;
  border-radius: 10px;
  background: #fff;
  padding: 12px;
}

.flow-detail__header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.flow-detail__title {
  font-size: 0.875rem;
  font-weight: 600;
  color: #0f172a;
}

.flow-detail__desc {
  margin: 0;
  color: #475569;
  font-size: 0.8125rem;
  line-height: 1.5;
}

.flow-detail__action {
  margin-top: 8px;
  padding-left: 0;
}

.node-edit-form {
  max-width: 980px;
}

.node-edit-form :deep(.el-form-item__label) {
  font-size: 0.8125rem;
  color: #334155;
}

.node-edit-form :deep(.el-form-item__content) {
  max-width: 760px;
}

.node-edit-form :deep(.el-textarea__inner) {
  font-size: 0.8125rem;
  line-height: 1.5;
}

.node-config-card :deep(.el-form-item:last-child) {
  margin-bottom: 0;
}

@media (max-width: 960px) {
  .process-graph {
    min-width: 980px;
  }
}
</style>
