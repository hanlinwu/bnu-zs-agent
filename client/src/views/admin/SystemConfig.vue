<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import * as systemConfigApi from '@/api/admin/systemConfig'
import type { ChatGuardrailConfig } from '@/types/admin'

const loading = ref(false)
const saving = ref(false)
const formRef = ref<FormInstance>()
const activeModules = ref<string[]>(['risk', 'prompts'])

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

const riskText = reactive({
  high_keywords: '',
  medium_keywords: '',
  medium_topics: '',
  medium_specific_hints: '',
})

const rules: FormRules = {
  medium_system_prompt: [{ required: true, message: '请输入中风险系统提示词', trigger: 'blur' }],
  low_system_prompt: [{ required: true, message: '请输入低风险系统提示词', trigger: 'blur' }],
  high_risk_response: [{ required: true, message: '请输入高风险固定回复', trigger: 'blur' }],
  no_knowledge_response: [{ required: true, message: '请输入无知识库兜底回复', trigger: 'blur' }],
}

function parseKeywordText(text: string): string[] {
  return text
    .split(/\n|,|，/g)
    .map(item => item.trim())
    .filter(Boolean)
}

function toKeywordText(items: string[]): string {
  return items.join('\n')
}

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

  riskText.high_keywords = toKeywordText(form.risk.high_keywords)
  riskText.medium_keywords = toKeywordText(form.risk.medium_keywords)
  riskText.medium_topics = toKeywordText(form.risk.medium_topics)
  riskText.medium_specific_hints = toKeywordText(form.risk.medium_specific_hints)
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
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  form.risk.high_keywords = parseKeywordText(riskText.high_keywords)
  form.risk.medium_keywords = parseKeywordText(riskText.medium_keywords)
  form.risk.medium_topics = parseKeywordText(riskText.medium_topics)
  form.risk.medium_specific_hints = parseKeywordText(riskText.medium_specific_hints)

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
        <h2 class="page-title">风险与Prompt配置</h2>
        <p class="page-desc">配置风险判定关键词与低/中/高风险回复模板</p>
      </div>
      <el-button type="primary" :loading="saving" @click="saveConfig">保存配置</el-button>
    </div>

    <el-form ref="formRef" :model="form.prompts" :rules="rules" label-position="top" class="config-form">
      <el-collapse v-model="activeModules" class="module-collapse">
        <el-collapse-item name="risk" title="风险判定词表">
          <div class="section-card section-card--inner">
            <el-row :gutter="16">
              <el-col :xs="24" :md="12">
                <el-form-item label="高风险关键词（每行一个）">
                  <el-input v-model="riskText.high_keywords" type="textarea" :rows="8" placeholder="例如：保证录取" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="中风险关键词（每行一个）">
                  <el-input v-model="riskText.medium_keywords" type="textarea" :rows="8" placeholder="例如：分数线" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="中风险主题词（每行一个）">
                  <el-input v-model="riskText.medium_topics" type="textarea" :rows="8" placeholder="例如：招生" />
                </el-form-item>
              </el-col>
              <el-col :xs="24" :md="12">
                <el-form-item label="中风险具体性线索（每行一个）">
                  <el-input v-model="riskText.medium_specific_hints" type="textarea" :rows="8" placeholder="例如：什么时候" />
                </el-form-item>
              </el-col>
            </el-row>
          </div>
        </el-collapse-item>

        <el-collapse-item name="prompts" title="分级Prompt与回复模板">
          <div class="section-card section-card--inner">
            <el-form-item label="低风险系统Prompt" prop="low_system_prompt">
              <el-input v-model="form.prompts.low_system_prompt" type="textarea" :rows="6" />
            </el-form-item>
            <el-form-item label="中风险系统Prompt" prop="medium_system_prompt">
              <el-input v-model="form.prompts.medium_system_prompt" type="textarea" :rows="8" />
            </el-form-item>
            <el-form-item label="中风险引用提示语">
              <el-input v-model="form.prompts.medium_citation_hint" type="textarea" :rows="3" />
            </el-form-item>
            <el-form-item label="中风险知识库约束说明">
              <el-input v-model="form.prompts.medium_knowledge_instructions" type="textarea" :rows="6" />
            </el-form-item>
            <el-form-item label="高风险固定回复" prop="high_risk_response">
              <el-input v-model="form.prompts.high_risk_response" type="textarea" :rows="5" />
            </el-form-item>
            <el-form-item label="中风险无知识库兜底回复" prop="no_knowledge_response">
              <el-input v-model="form.prompts.no_knowledge_response" type="textarea" :rows="5" />
            </el-form-item>
          </div>
        </el-collapse-item>
      </el-collapse>
    </el-form>
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
  font-size: 22px;
  font-weight: 600;
  color: #1f2d3d;
}

.page-desc {
  margin: 6px 0 0;
  color: #6b7280;
  font-size: 14px;
}

.config-form {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.module-collapse {
  border: none;
  display: flex;
  flex-direction: column;
  gap: 12px;

  :deep(.el-collapse-item__header) {
    height: 48px;
    font-size: 15px;
    font-weight: 600;
    padding: 0 16px;
    border: 1px solid #ebeef5;
    border-radius: 12px;
    background: #fff;
  }

  :deep(.el-collapse-item__wrap) {
    border: none;
    background: transparent;
  }

  :deep(.el-collapse-item__content) {
    padding-bottom: 0;
  }
}

.section-card {
  background: #fff;
  border-radius: 12px;
  padding: 16px;
  border: 1px solid #ebeef5;
}

.section-card--inner {
  margin-top: 8px;
}

.section-title {
  margin: 0 0 12px;
  font-size: 16px;
  color: #1f2d3d;
}
</style>
