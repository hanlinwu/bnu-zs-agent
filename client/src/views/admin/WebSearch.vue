<script setup lang="ts">
import { ref, computed, watch, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Search, Setting, CircleCheck, Close, Document } from '@element-plus/icons-vue'
import * as webSearchApi from '@/api/admin/webSearch'
import type { TavilyConfig, TavilySearchResult } from '@/api/admin/webSearch'

// ── Config ──────────────────────────────────────────────────

const DEFAULT_CONFIG: TavilyConfig = {
  enabled: true,
  api_key: '',
  search_depth: 'basic',
  max_results: 10,
  include_domains: [],
  exclude_domains: [],
  include_answer: false,
  include_raw_content: false,
  topic: 'general',
  country: '',
  time_range: '',
  chunks_per_source: 3,
  include_images: false,
}

const config = ref<TavilyConfig>({ ...DEFAULT_CONFIG })
const configLoading = ref(false)
const configSaving = ref(false)
const apiKeyValidating = ref(false)
const apiKeyValid = ref<boolean | null>(null)
const drawerVisible = ref(false)

const newIncludeDomain = ref('')
const newExcludeDomain = ref('')

const countryOptions = [
  { value: '', label: '不限' },
  { value: 'china', label: '中国' },
  { value: 'united states', label: '美国' },
  { value: 'united kingdom', label: '英国' },
  { value: 'japan', label: '日本' },
  { value: 'south korea', label: '韩国' },
  { value: 'germany', label: '德国' },
  { value: 'france', label: '法国' },
  { value: 'australia', label: '澳大利亚' },
  { value: 'canada', label: '加拿大' },
  { value: 'singapore', label: '新加坡' },
  { value: 'taiwan', label: '中国台湾' },
  { value: 'russia', label: '俄罗斯' },
]

const countryDisabled = computed(() => config.value.topic !== 'general')
const countryHint = computed(() =>
  config.value.topic !== 'general' ? '仅搜索类型为「通用」时可用' : ''
)

watch(() => config.value.topic, (topic) => {
  if (topic !== 'general' && config.value.country) {
    config.value.country = ''
  }
})

async function fetchConfig() {
  configLoading.value = true
  try {
    const res = await webSearchApi.getConfig()
    config.value = { ...DEFAULT_CONFIG, ...res.data.value }
  } catch {
    ElMessage.error('获取配置失败')
  } finally {
    configLoading.value = false
  }
}

async function saveConfig() {
  configSaving.value = true
  try {
    const res = await webSearchApi.updateConfig(config.value)
    config.value = { ...DEFAULT_CONFIG, ...res.data.value }
    ElMessage.success('配置已保存')
  } catch {
    ElMessage.error('保存配置失败')
  } finally {
    configSaving.value = false
  }
}

async function handleValidateKey() {
  apiKeyValidating.value = true
  apiKeyValid.value = null
  try {
    const res = await webSearchApi.validateApiKey()
    apiKeyValid.value = res.data.valid
    ElMessage[res.data.valid ? 'success' : 'error'](res.data.message)
  } catch {
    apiKeyValid.value = false
    ElMessage.error('验证失败')
  } finally {
    apiKeyValidating.value = false
  }
}

function addIncludeDomain() {
  const domain = newIncludeDomain.value.trim().toLowerCase()
  if (!domain) return
  if (config.value.include_domains.includes(domain)) {
    ElMessage.warning('域名已存在')
    return
  }
  config.value.include_domains.push(domain)
  newIncludeDomain.value = ''
}

function addExcludeDomain() {
  const domain = newExcludeDomain.value.trim().toLowerCase()
  if (!domain) return
  if (config.value.exclude_domains.includes(domain)) {
    ElMessage.warning('域名已存在')
    return
  }
  config.value.exclude_domains.push(domain)
  newExcludeDomain.value = ''
}

function removeDomain(list: string[], domain: string) {
  const idx = list.indexOf(domain)
  if (idx !== -1) list.splice(idx, 1)
}

// ── Search ──────────────────────────────────────────────────

const searchKeyword = ref('')
const searchResults = ref<TavilySearchResult[]>([])
const searchAnswer = ref('')
const searchResponseTime = ref(0)
const searchLoading = ref(false)
const searchExecuted = ref(false)
const rawResponse = ref<object | null>(null)
const rawDialogVisible = ref(false)

async function handleSearch() {
  if (!searchKeyword.value.trim()) {
    ElMessage.warning('请输入搜索关键词')
    return
  }
  searchLoading.value = true
  searchExecuted.value = true
  rawResponse.value = null
  try {
    const res = await webSearchApi.searchQuery({ query: searchKeyword.value })
    rawResponse.value = res.data
    searchResults.value = res.data.results || []
    searchAnswer.value = res.data.answer || ''
    searchResponseTime.value = res.data.response_time || 0
  } catch {
    ElMessage.error('搜索失败，请检查API Key是否有效')
    searchResults.value = []
    searchAnswer.value = ''
  } finally {
    searchLoading.value = false
  }
}

// ── Lifecycle ───────────────────────────────────────────────

onMounted(() => {
  fetchConfig()
})
</script>

<template>
  <div class="web-search-page">
    <!-- Header -->
    <div class="page-header">
      <div>
        <h2 class="page-title">网页搜索</h2>
        <p class="page-desc">基于Tavily API的实时网页搜索</p>
      </div>
      <el-tag v-if="!config.enabled" type="danger" effect="dark">搜索已关闭</el-tag>
    </div>

    <!-- Search Bar -->
    <div class="search-card">
      <div class="search-bar">
        <el-input
          v-model="searchKeyword"
          placeholder="输入搜索内容，如：北京师范大学2025年招生简章"
          clearable
          size="large"
          :disabled="!config.enabled"
          @keyup.enter="handleSearch"
        >
          <template #prefix>
            <el-icon><Search /></el-icon>
          </template>
        </el-input>
        <el-button
          type="primary"
          size="large"
          :loading="searchLoading"
          :disabled="!config.enabled"
          @click="handleSearch"
        >
          搜索
        </el-button>
        <el-button
          size="large"
          :icon="Setting"
          @click="drawerVisible = true"
        >
          搜索配置
        </el-button>
      </div>
    </div>

    <!-- Answer -->
    <el-alert
      v-if="searchAnswer"
      :title="searchAnswer"
      type="info"
      :closable="false"
      show-icon
      class="search-answer"
    />

    <!-- Meta bar -->
    <div v-if="searchExecuted && !searchLoading" class="search-meta">
      <span>找到 {{ searchResults.length }} 条结果</span>
      <el-tag v-if="searchResponseTime" size="small" type="info">
        {{ searchResponseTime.toFixed(2) }}s
      </el-tag>
      <el-button
        v-if="rawResponse"
        text
        size="small"
        :icon="Document"
        @click="rawDialogVisible = true"
      >
        查看原始JSON
      </el-button>
    </div>

    <!-- Results -->
    <div v-if="searchResults.length > 0" class="search-results">
      <div v-for="(hit, idx) in searchResults" :key="idx" class="search-hit">
        <div class="search-hit-title">
          <a :href="hit.url" target="_blank" rel="noopener">{{ hit.title || hit.url }}</a>
        </div>
        <div class="search-hit-url">{{ hit.url }}</div>
        <div class="search-hit-snippet">{{ hit.content }}</div>
        <div class="search-hit-meta">
          <el-tag size="small" type="success">{{ hit.score.toFixed(2) }}</el-tag>
          <el-tag v-if="hit.published_date" size="small" type="info">{{ hit.published_date }}</el-tag>
        </div>
      </div>
    </div>
    <div v-else-if="searchExecuted && !searchLoading" class="search-empty">
      暂无搜索结果
    </div>

    <!-- Raw JSON Dialog -->
    <el-dialog v-model="rawDialogVisible" title="原始返回数据" width="720px" top="5vh">
      <pre class="raw-json">{{ JSON.stringify(rawResponse, null, 2) }}</pre>
    </el-dialog>

    <!-- Config Drawer -->
    <el-drawer
      v-model="drawerVisible"
      title="搜索配置"
      size="480px"
      :close-on-click-modal="true"
    >
      <div v-loading="configLoading" class="drawer-body">
        <!-- Global switch -->
        <div class="drawer-switch">
          <span>启用网页搜索</span>
          <el-switch
            v-model="config.enabled"
            active-text="开"
            inactive-text="关"
            inline-prompt
            style="--el-switch-on-color: #003DA5"
            @change="saveConfig"
          />
        </div>

        <el-divider />

        <el-form
          :model="config"
          label-position="top"
          class="drawer-form"
          :disabled="!config.enabled"
        >
          <!-- API Key -->
          <el-form-item label="API Key">
            <div class="api-key-row">
              <el-input
                v-model="config.api_key"
                type="password"
                show-password
                placeholder="tvly-..."
                style="flex: 1"
              />
              <el-button :loading="apiKeyValidating" @click="handleValidateKey">验证</el-button>
              <el-icon v-if="apiKeyValid === true" class="key-status key-valid"><CircleCheck /></el-icon>
              <el-icon v-if="apiKeyValid === false" class="key-status key-invalid"><Close /></el-icon>
            </div>
          </el-form-item>

          <!-- Search Depth -->
          <el-form-item label="搜索深度">
            <el-radio-group v-model="config.search_depth">
              <el-radio value="basic">标准 (1 credit)</el-radio>
              <el-radio value="advanced">深度 (2 credits)</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- Max Results -->
          <el-form-item label="最大结果数">
            <el-input-number v-model="config.max_results" :min="1" :max="20" />
          </el-form-item>

          <!-- Topic -->
          <el-form-item label="搜索类型">
            <el-radio-group v-model="config.topic">
              <el-radio value="general">通用</el-radio>
              <el-radio value="news">新闻</el-radio>
              <el-radio value="finance">财经</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- Country -->
          <el-form-item label="搜索地区">
            <el-select
              v-model="config.country"
              placeholder="不限地区"
              clearable
              :disabled="!config.enabled || countryDisabled"
              style="width: 100%"
            >
              <el-option
                v-for="opt in countryOptions"
                :key="opt.value"
                :label="opt.label"
                :value="opt.value"
              />
            </el-select>
            <div v-if="countryHint" class="form-hint-block">{{ countryHint }}</div>
          </el-form-item>

          <!-- Time Range -->
          <el-form-item label="时间范围">
            <el-radio-group v-model="config.time_range">
              <el-radio value="">不限</el-radio>
              <el-radio value="day">一天</el-radio>
              <el-radio value="week">一周</el-radio>
              <el-radio value="month">一月</el-radio>
              <el-radio value="year">一年</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- Include Answer -->
          <el-form-item label="生成摘要回答">
            <el-radio-group v-model="config.include_answer">
              <el-radio :value="false">关闭</el-radio>
              <el-radio value="basic">基础</el-radio>
              <el-radio value="advanced">详细</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- Include Raw Content -->
          <el-form-item label="包含原始内容">
            <el-radio-group v-model="config.include_raw_content">
              <el-radio :value="false">关闭</el-radio>
              <el-radio value="markdown">Markdown</el-radio>
              <el-radio value="text">纯文本</el-radio>
            </el-radio-group>
          </el-form-item>

          <!-- Chunks Per Source -->
          <el-form-item v-if="config.search_depth === 'advanced'" label="每源片段数">
            <el-input-number v-model="config.chunks_per_source" :min="1" :max="3" />
            <div class="form-hint-block">深度搜索模式下每个来源返回的内容片段数</div>
          </el-form-item>

          <!-- Include Images -->
          <el-form-item label="包含图片">
            <el-switch v-model="config.include_images" />
          </el-form-item>

          <!-- Include Domains -->
          <el-form-item label="域名白名单">
            <div class="domain-list">
              <el-tag
                v-for="domain in config.include_domains"
                :key="domain"
                closable
                :disabled="!config.enabled"
                @close="removeDomain(config.include_domains, domain)"
              >
                {{ domain }}
              </el-tag>
              <div class="domain-add">
                <el-input
                  v-model="newIncludeDomain"
                  placeholder="如 bnu.edu.cn"
                  size="small"
                  @keyup.enter="addIncludeDomain"
                />
                <el-button size="small" @click="addIncludeDomain">添加</el-button>
              </div>
            </div>
            <div class="form-hint-block">仅搜索这些域名，支持通配符 *.edu.cn</div>
          </el-form-item>

          <!-- Exclude Domains -->
          <el-form-item label="域名黑名单">
            <div class="domain-list">
              <el-tag
                v-for="domain in config.exclude_domains"
                :key="domain"
                closable
                type="danger"
                :disabled="!config.enabled"
                @close="removeDomain(config.exclude_domains, domain)"
              >
                {{ domain }}
              </el-tag>
              <div class="domain-add">
                <el-input
                  v-model="newExcludeDomain"
                  placeholder="如 spam.com"
                  size="small"
                  @keyup.enter="addExcludeDomain"
                />
                <el-button size="small" @click="addExcludeDomain">添加</el-button>
              </div>
            </div>
          </el-form-item>
        </el-form>

        <!-- Save -->
        <div class="drawer-footer">
          <el-button type="primary" :loading="configSaving" @click="saveConfig">
            保存配置
          </el-button>
        </div>
      </div>
    </el-drawer>
  </div>
</template>

<style lang="scss" scoped>
.web-search-page {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-title {
  font-size: 1.375rem;
  font-weight: 700;
  color: var(--text-primary, #1a1a2e);
  margin: 0 0 4px;
}

.page-desc {
  font-size: 0.875rem;
  color: var(--text-secondary, #6B7280);
  margin: 0;
}

// ── Search ─────────────────────────────────────

.search-card {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #e2e6ed);
  padding: 16px 20px;
  margin-bottom: 16px;
}

.search-bar {
  display: flex;
  gap: 10px;
  align-items: center;
}

.search-answer {
  margin-bottom: 16px;
}

.search-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 0.875rem;
  color: var(--text-secondary, #6B7280);
  margin-bottom: 12px;
}

.search-results {
  background: var(--bg-primary, #ffffff);
  border-radius: 12px;
  border: 1px solid var(--border-color, #e2e6ed);
  padding: 4px 20px;
}

.search-hit {
  padding: 14px 0;
  border-bottom: 1px solid var(--border-color, #e2e6ed);

  &:last-child {
    border-bottom: none;
  }
}

.search-hit-title a {
  font-size: 1rem;
  font-weight: 500;
  color: var(--bnu-blue, #1a4b8c);
  text-decoration: none;

  &:hover {
    text-decoration: underline;
  }
}

.search-hit-url {
  font-size: 0.75rem;
  color: var(--text-tertiary, #9CA3AF);
  margin: 2px 0;
  word-break: break-all;
}

.search-hit-snippet {
  font-size: 0.875rem;
  color: var(--text-secondary, #6B7280);
  line-height: 1.5;
  margin: 4px 0;
}

.search-hit-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-top: 4px;
}

.search-empty {
  text-align: center;
  padding: 48px 0;
  color: var(--text-secondary, #6B7280);
}

// ── Raw JSON Dialog ────────────────────────────

.raw-json {
  background: var(--bg-secondary, #f5f7fa);
  border-radius: 8px;
  padding: 16px;
  font-size: 0.8rem;
  line-height: 1.5;
  max-height: 70vh;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-all;
  margin: 0;
}

// ── Drawer ─────────────────────────────────────

.drawer-body {
  display: flex;
  flex-direction: column;
  height: 100%;
}

.drawer-switch {
  display: flex;
  justify-content: space-between;
  align-items: center;
  font-size: 0.9375rem;
  font-weight: 500;
  color: var(--text-primary, #1a1a2e);
}

.drawer-form {
  flex: 1;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.drawer-footer {
  padding-top: 16px;
  border-top: 1px solid var(--border-color, #e2e6ed);
  flex-shrink: 0;
}

.api-key-row {
  display: flex;
  gap: 8px;
  align-items: center;
  width: 100%;
}

.key-status {
  font-size: 20px;
  flex-shrink: 0;
}

.key-valid {
  color: var(--el-color-success);
}

.key-invalid {
  color: var(--el-color-danger);
}

.form-hint-block {
  width: 100%;
  margin-top: 4px;
  font-size: 0.75rem;
  color: var(--text-tertiary, #9CA3AF);
}

.domain-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  align-items: center;
  width: 100%;
}

.domain-add {
  display: flex;
  gap: 6px;
  align-items: center;
  width: 100%;
  margin-top: 4px;
}
</style>
