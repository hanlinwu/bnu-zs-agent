<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, Check, Close } from '@element-plus/icons-vue'
import * as modelApi from '@/api/admin/model'
import type { ModelConfig } from '@/types/admin'

const loading = ref(false)
const models = ref<ModelConfig[]>([])
const loadBalanceStrategy = ref<'failover' | 'round_robin'>('failover')
const testingId = ref<string>('')

function providerLabel(provider: string) {
  const map: Record<string, string> = {
    qwen: '通义千问',
    glm: '智谱 GLM',
    local: '本地部署',
  }
  return map[provider] || provider
}

function providerColor(provider: string) {
  const map: Record<string, string> = {
    qwen: '#6366F1',
    glm: '#10B981',
    local: '#F59E0B',
  }
  return map[provider] || '#6B7280'
}

async function fetchModels() {
  loading.value = true
  try {
    const res = await modelApi.getModels()
    const data = res.data as any

    // API returns flat config object, transform into model card array
    if (data && !Array.isArray(data)) {
      const items: ModelConfig[] = []
      // Primary model
      if (data.primary_provider || data.primary_model) {
        items.push({
          id: 'primary',
          name: data.primary_model || 'unknown',
          provider: data.primary_provider || 'unknown',
          endpoint: data.primary_base_url || '',
          apiKey: data.primary_api_key || '',
          isPrimary: true,
          isReviewer: false,
          enabled: true,
          weight: 1,
          maxTokens: 4096,
          temperature: 0.7,
          createdAt: '',
          updatedAt: '',
        })
      }
      // Review model
      if (data.review_provider || data.review_model) {
        items.push({
          id: 'review',
          name: data.review_model || 'unknown',
          provider: data.review_provider || data.primary_provider || 'unknown',
          endpoint: data.review_base_url || data.primary_base_url || '',
          isPrimary: false,
          isReviewer: true,
          enabled: true,
          weight: 1,
          maxTokens: 2048,
          temperature: 0.3,
          createdAt: '',
          updatedAt: '',
        })
      }
      models.value = items
    } else {
      models.value = data || []
    }
  } catch {
    ElMessage.error('加载模型配置失败')
  } finally {
    loading.value = false
  }
}

async function handleSetPrimary(model: ModelConfig) {
  try {
    await modelApi.setPrimaryModel(model.id)
    ElMessage.success(`已设置「${model.name}」为主用模型`)
    fetchModels()
  } catch {
    ElMessage.error('设置失败')
  }
}

async function handleSetReviewer(model: ModelConfig) {
  try {
    await modelApi.setReviewerModel(model.id)
    ElMessage.success(`已设置「${model.name}」为审查模型`)
    fetchModels()
  } catch {
    ElMessage.error('设置失败')
  }
}

async function handleTest(model: ModelConfig) {
  testingId.value = model.id
  try {
    await modelApi.testModel(model.id)
    ElMessage.success('连接测试成功')
  } catch {
    ElMessage.error('连接测试失败，请检查配置')
  } finally {
    testingId.value = ''
  }
}

async function handleToggle(model: ModelConfig) {
  try {
    await modelApi.updateModels({ id: model.id, enabled: !model.enabled } as any)
    model.enabled = !model.enabled
    ElMessage.success(model.enabled ? '已启用' : '已停用')
  } catch {
    ElMessage.error('操作失败')
  }
}

onMounted(() => {
  fetchModels()
})
</script>

<template>
  <div class="model-page">
    <div class="page-header">
      <div class="header-left">
        <h2 class="page-title">模型配置</h2>
        <p class="page-desc">配置与管理大语言模型接入</p>
      </div>
    </div>

    <div class="strategy-card">
      <div class="strategy-header">
        <h3 class="card-title">
          <el-icon><Connection /></el-icon>
          负载均衡策略
        </h3>
      </div>
      <div class="strategy-options">
        <el-radio-group v-model="loadBalanceStrategy" size="large">
          <el-radio-button value="failover">
            故障转移 (Failover)
          </el-radio-button>
          <el-radio-button value="round_robin">
            轮询 (Round Robin)
          </el-radio-button>
        </el-radio-group>
        <p class="strategy-desc">
          {{ loadBalanceStrategy === 'failover'
            ? '主模型不可用时自动切换到备用模型'
            : '请求按权重在多个模型间轮询分发' }}
        </p>
      </div>
    </div>

    <div v-loading="loading" class="models-grid">
      <div
        v-for="model in models"
        :key="model.id"
        class="model-card"
        :class="{
          'model-card--primary': model.isPrimary,
          'model-card--reviewer': model.isReviewer && !model.isPrimary,
          'model-card--disabled': !model.enabled,
        }"
      >
        <div class="model-card-header">
          <div class="model-badges">
            <el-tag v-if="model.isPrimary" type="success" size="small" effect="dark">主用模型</el-tag>
            <el-tag v-if="model.isReviewer" type="warning" size="small" effect="dark">审查模型</el-tag>
          </div>
          <el-switch :model-value="model.enabled" size="small" @change="handleToggle(model)" />
        </div>

        <div class="model-info">
          <div class="model-provider" :style="{ color: providerColor(model.provider) }">
            {{ providerLabel(model.provider) }}
          </div>
          <h3 class="model-name">{{ model.name }}</h3>
          <div class="model-endpoint">{{ model.endpoint }}</div>
        </div>

        <div class="model-stats">
          <div class="stat-item">
            <span class="stat-label">最大 Tokens</span>
            <span class="stat-value">{{ model.maxTokens.toLocaleString() }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">Temperature</span>
            <span class="stat-value">{{ model.temperature }}</span>
          </div>
          <div class="stat-item">
            <span class="stat-label">权重</span>
            <span class="stat-value">{{ model.weight }}</span>
          </div>
        </div>

        <div class="model-status">
          <div class="status-indicator" :class="model.enabled ? 'status--online' : 'status--offline'">
            <el-icon v-if="model.enabled"><Check /></el-icon>
            <el-icon v-else><Close /></el-icon>
            {{ model.enabled ? '运行中' : '已停用' }}
          </div>
        </div>

        <div class="model-actions">
          <el-button
            size="small"
            :loading="testingId === model.id"
            @click="handleTest(model)"
          >
            测试连接
          </el-button>
          <el-button
            v-if="!model.isPrimary"
            type="primary"
            size="small"
            plain
            @click="handleSetPrimary(model)"
          >
            设为主用
          </el-button>
          <el-button
            v-if="!model.isReviewer"
            type="warning"
            size="small"
            plain
            @click="handleSetReviewer(model)"
          >
            设为审查
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.model-page {
}

.page-header {
  margin-bottom: 20px;
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

.strategy-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #E2E6ED);
  padding: 20px;
  margin-bottom: 20px;
}

.strategy-header {
  margin-bottom: 12px;
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

.strategy-options {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.strategy-desc {
  font-size: 13px;
  color: var(--text-secondary, #5A5A72);
  margin: 0;
}

.models-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 16px;
}

.model-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 2px solid var(--border-color, #E2E6ED);
  padding: 20px;
  transition: all 0.2s;

  &--primary {
    border-color: #2E7D32;
    box-shadow: 0 0 0 1px rgba(46, 125, 50, 0.1);
  }

  &--reviewer {
    border-color: #F57C00;
    box-shadow: 0 0 0 1px rgba(245, 124, 0, 0.1);
  }

  &--disabled {
    opacity: 0.6;
  }

  &:hover {
    box-shadow: var(--shadow-md, 0 4px 16px rgba(0, 0, 0, 0.08));
  }
}

.model-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}

.model-badges {
  display: flex;
  gap: 6px;
}

.model-info {
  margin-bottom: 16px;
}

.model-provider {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  margin-bottom: 4px;
}

.model-name {
  font-size: 18px;
  font-weight: 700;
  color: var(--text-primary, #1A1A2E);
  margin: 0 0 4px;
}

.model-endpoint {
  font-size: 12px;
  font-family: monospace;
  color: var(--text-secondary, #5A5A72);
  word-break: break-all;
}

.model-stats {
  display: flex;
  gap: 16px;
  padding: 12px 0;
  border-top: 1px solid var(--border-color, #E2E6ED);
  border-bottom: 1px solid var(--border-color, #E2E6ED);
  margin-bottom: 12px;
}

.stat-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.stat-label {
  font-size: 11px;
  color: var(--text-secondary, #5A5A72);
}

.stat-value {
  font-size: 14px;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
}

.model-status {
  margin-bottom: 12px;
}

.status-indicator {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font-size: 13px;
  font-weight: 500;

  &.status--online {
    color: #2E7D32;
  }

  &.status--offline {
    color: #9E9EB3;
  }
}

.model-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

@media (max-width: 768px) {
  .models-grid {
    grid-template-columns: 1fr;
  }
}
</style>
