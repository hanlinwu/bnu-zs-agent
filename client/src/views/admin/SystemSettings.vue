<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import type { UploadProps } from 'element-plus'
import { Upload } from '@element-plus/icons-vue'
import * as systemConfigApi from '@/api/admin/systemConfig'
import type { BackendVersionInfo, SystemBasicConfig } from '@/types/admin'
import { useSystemStore } from '@/stores/system'

const loading = ref(false)
const saving = ref(false)
const logoUploading = ref(false)
const systemStore = useSystemStore()

const form = reactive<SystemBasicConfig>({
  system_name: '',
  system_logo: '',
})

const backendVersion = reactive<BackendVersionInfo>({
  app_name: '',
  app_version: '',
  git_commit: '',
  build_time: '',
})

const unifiedVersionText = computed(() => {
  const version = backendVersion.app_version || __APP_VERSION__
  const commit = backendVersion.git_commit && backendVersion.git_commit !== 'unknown'
    ? backendVersion.git_commit
    : __GIT_COMMIT__
  const buildTime = backendVersion.build_time && backendVersion.build_time !== 'unknown'
    ? backendVersion.build_time
    : __GIT_COMMIT_DATE__
  return `系统版本 ${version} · ${commit} · ${buildTime}`
})

const logoPreviewUrl = computed(() => form.system_logo.trim())

function applyFormValue(value: SystemBasicConfig) {
  form.system_name = value.system_name || ''
  form.system_logo = value.system_logo || ''
  systemStore.setBasic({
    system_name: form.system_name,
    system_logo: form.system_logo,
  })
}

function applyVersion(value: BackendVersionInfo) {
  backendVersion.app_name = value.app_name || ''
  backendVersion.app_version = value.app_version || ''
  backendVersion.git_commit = value.git_commit || ''
  backendVersion.build_time = value.build_time || ''
}

async function fetchConfig() {
  loading.value = true
  try {
    const res = await systemConfigApi.getSystemBasicConfig()
    applyFormValue(res.data.value)
    applyVersion(res.data.version)
  } catch {
    ElMessage.error('加载系统设置失败')
  } finally {
    loading.value = false
  }
}

async function saveConfig() {
  saving.value = true
  try {
    const payload: SystemBasicConfig = {
      system_name: form.system_name,
      system_logo: form.system_logo,
    }
    const res = await systemConfigApi.updateSystemBasicConfig(payload)
    applyFormValue(res.data.value)
    applyVersion(res.data.version)
    ElMessage.success('系统设置已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    saving.value = false
  }
}

const beforeLogoUpload: UploadProps['beforeUpload'] = (file) => {
  const isImage = file.type.startsWith('image/')
  if (!isImage) {
    ElMessage.error('只能上传图片文件')
    return false
  }
  return true
}

const handleLogoFileChange: UploadProps['onChange'] = async (uploadFile) => {
  const raw = uploadFile.raw
  if (!raw) return

  logoUploading.value = true
  try {
    const formData = new FormData()
    formData.append('file', raw)
    const res = await systemConfigApi.uploadSystemLogo(formData)
    form.system_logo = res.data.url
    systemStore.setBasic({
      system_name: form.system_name,
      system_logo: form.system_logo,
    })
    ElMessage.success('Logo上传成功')
  } catch {
    ElMessage.error('Logo上传失败')
  } finally {
    logoUploading.value = false
  }
}

function handleClearLogo() {
  form.system_logo = ''
  systemStore.setBasic({
    system_name: form.system_name,
    system_logo: '',
  })
  ElMessage.success('已清除Logo，请点击“保存设置”生效')
}

onMounted(() => {
  fetchConfig()
})
</script>

<template>
  <div v-loading="loading" class="system-settings-page">
    <div class="page-header">
      <div>
        <h2 class="page-title">系统设置</h2>
        <p class="page-desc">设置系统名称、系统Logo，并查看版本信息</p>
      </div>
      <el-button type="primary" :loading="saving" @click="saveConfig">保存设置</el-button>
    </div>

    <div class="section-card">
      <h3 class="section-title">基础信息</h3>
      <el-form label-position="left" label-width="120px">
        <el-form-item label="系统名称">
          <el-input v-model="form.system_name" maxlength="50" placeholder="请输入系统名称" />
        </el-form-item>
        <el-form-item label="系统Logo">
          <div class="logo-actions">
            <el-upload
              :auto-upload="false"
              :show-file-list="false"
              :before-upload="beforeLogoUpload"
              :on-change="handleLogoFileChange"
              accept="image/png,image/jpeg,image/webp,image/svg+xml"
            >
              <el-button :loading="logoUploading" :icon="Upload">
                {{ logoUploading ? '上传中...' : '选择并上传图片' }}
              </el-button>
            </el-upload>
            <el-button
              :disabled="!logoPreviewUrl || logoUploading"
              @click="handleClearLogo"
            >
              清除
            </el-button>
          </div>
        </el-form-item>
      </el-form>

      <div v-if="logoPreviewUrl" class="logo-preview">
        <span class="logo-preview__label">Logo预览</span>
        <img :src="logoPreviewUrl" alt="系统Logo预览" class="logo-preview__image">
      </div>
    </div>

    <div class="section-card">
      <h3 class="section-title">版本信息</h3>
      <div class="version-list">
        <p class="version-item">{{ unifiedVersionText }}</p>
        <p class="version-item">应用名称 {{ backendVersion.app_name || '-' }}</p>
      </div>
    </div>
  </div>
</template>

<style scoped lang="scss">
.system-settings-page {
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

.logo-preview {
  display: flex;
  flex-direction: column;
  gap: 8px;
  margin-top: 4px;
}

.logo-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.logo-preview__label {
  font-size: 0.8125rem;
  color: #6b7280;
}

.logo-preview__image {
  max-width: 220px;
  max-height: 80px;
  object-fit: contain;
  border: 1px solid #ebeef5;
  border-radius: 8px;
  background: #fff;
  padding: 8px;
}

.version-list {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.version-item {
  margin: 0;
  font-size: 0.875rem;
  color: #475569;
}
</style>
