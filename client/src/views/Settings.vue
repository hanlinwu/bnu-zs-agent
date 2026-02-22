<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Edit } from '@element-plus/icons-vue'
import { ElMessage } from 'element-plus'
import { useThemeStore } from '@/stores/theme'
import { useUserStore } from '@/stores/user'
import { PROVINCE_OPTIONS } from '@/constants/profile'

const router = useRouter()
const themeStore = useThemeStore()
const userStore = useUserStore()

const fontSizeOptions = [
  { label: '小', value: 14 as const },
  { label: '标准', value: 16 as const },
  { label: '大', value: 18 as const },
  { label: '特大', value: 20 as const },
]
const themeModeOptions = [
  { label: '浅色', value: 'light' as const },
  { label: '深色', value: 'dark' as const },
  { label: '跟随系统', value: 'system' as const },
]

const isEditingNickname = ref(false)
const nicknameInput = ref('')
const province = ref('')
const identityType = ref<'student' | 'parent' | ''>('')
const sourceGroup = ref<'mainland_general' | 'hkmo_tw' | 'international' | ''>('')
const admissionStage = ref<'undergraduate' | 'master' | 'doctor' | ''>('')
const profileSaving = ref(false)

const stageOptions = [
  { label: '本科', value: 'undergraduate' as const },
  { label: '硕士研究生', value: 'master' as const },
  { label: '博士研究生', value: 'doctor' as const },
]

function startEditNickname() {
  nicknameInput.value = userStore.userInfo?.nickname || ''
  isEditingNickname.value = true
}

async function saveNickname() {
  const name = nicknameInput.value.trim()
  if (!name) return
  try {
    await userStore.updateProfile({ nickname: name })
    ElMessage.success('昵称修改成功')
  } catch {
    ElMessage.error('昵称修改失败')
  }
  isEditingNickname.value = false
}

function cancelEditNickname() {
  isEditingNickname.value = false
}

onMounted(() => {
  if (!userStore.userInfo) {
    userStore.fetchProfile().then(syncProfileForm)
  } else {
    syncProfileForm()
  }
})

function syncProfileForm() {
  const info = userStore.userInfo
  province.value = (info?.province as string) || ''
  identityType.value = (info?.identity_type as 'student' | 'parent' | '') || ''
  sourceGroup.value = (info?.source_group as 'mainland_general' | 'hkmo_tw' | 'international' | '') || ''
  const stages = Array.isArray(info?.admission_stages)
    ? (info?.admission_stages as Array<'undergraduate' | 'master' | 'doctor'>)
    : []
  admissionStage.value = stages[0] || ''
}

async function savePersonaConfig() {
  profileSaving.value = true
  try {
    await userStore.updateProfile({
      province: province.value || undefined,
      identity_type: identityType.value || undefined,
      source_group: sourceGroup.value || undefined,
      admission_stages: admissionStage.value ? [admissionStage.value] : [],
    })
    ElMessage.success('画像信息已保存')
  } catch {
    ElMessage.error('保存失败')
  } finally {
    profileSaving.value = false
  }
}
</script>

<template>
  <div class="settings-page">
    <header class="settings-header">
      <el-button text :icon="ArrowLeft" @click="router.back()">返回</el-button>
      <h2>设置</h2>
    </header>

    <div class="settings-card">
      <h3 class="section-title">外观</h3>

      <div class="setting-item">
        <div class="setting-label">
          <span>主题模式</span>
          <span class="setting-desc">浅色、深色或跟随系统</span>
        </div>
        <el-radio-group
          :model-value="themeStore.themePreference"
          size="small"
          @change="(val: string | number | boolean | undefined) => themeStore.setThemePreference(val as 'light' | 'dark' | 'system')"
        >
          <el-radio-button
            v-for="opt in themeModeOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <div class="setting-item">
        <div class="setting-label">
          <span>字体大小</span>
          <span class="setting-desc">调整全局文字大小</span>
        </div>
        <el-radio-group
          :model-value="themeStore.fontSize"
          size="small"
          @change="(val: string | number | boolean | undefined) => themeStore.setFontSize(val as 14 | 16 | 18 | 20)"
        >
          <el-radio-button
            v-for="opt in fontSizeOptions"
            :key="opt.value"
            :value="opt.value"
          >
            {{ opt.label }}
          </el-radio-button>
        </el-radio-group>
      </div>
    </div>

    <div class="settings-card">
      <h3 class="section-title">账号</h3>

      <div class="setting-item">
        <div class="setting-label">
          <span>手机号</span>
        </div>
        <span class="setting-value">{{ userStore.userInfo?.phone || '未设置' }}</span>
      </div>

      <div class="setting-item">
        <div class="setting-label">
          <span>昵称</span>
        </div>
        <div v-if="!isEditingNickname" class="setting-value-row">
          <span class="setting-value">{{ userStore.userInfo?.nickname || '未设置' }}</span>
          <el-button text size="small" :icon="Edit" @click="startEditNickname" />
        </div>
        <div v-else class="setting-edit-row">
          <el-input
            v-model="nicknameInput"
            size="small"
            maxlength="20"
            style="width: 160px"
            @keydown.enter="saveNickname"
            @keydown.esc="cancelEditNickname"
          />
          <el-button type="primary" size="small" @click="saveNickname">保存</el-button>
          <el-button size="small" @click="cancelEditNickname">取消</el-button>
        </div>
      </div>

      <div class="setting-item">
        <div class="setting-label">
          <span>省份</span>
          <span class="setting-desc">默认来自IP识别，可手动修改（含港澳台/国际）</span>
        </div>
        <el-select v-model="province" placeholder="请选择省份/地区" size="small" style="width: 220px" filterable>
          <el-option v-for="item in PROVINCE_OPTIONS" :key="item" :label="item" :value="item" />
        </el-select>
      </div>

      <div class="setting-item setting-item--column">
        <div class="setting-label">
          <span>身份</span>
          <span class="setting-desc">学生本人或家长</span>
        </div>
        <el-radio-group v-model="identityType" size="small">
          <el-radio-button value="student">学生本人</el-radio-button>
          <el-radio-button value="parent">家长</el-radio-button>
        </el-radio-group>
      </div>

      <div class="setting-item setting-item--column">
        <div class="setting-label">
          <span>生源类型</span>
          <span class="setting-desc">用于匹配更准确的招生政策说明</span>
        </div>
        <el-radio-group v-model="sourceGroup" size="small">
          <el-radio-button value="mainland_general">内地生</el-radio-button>
          <el-radio-button value="hkmo_tw">港澳台生</el-radio-button>
          <el-radio-button value="international">国际生</el-radio-button>
        </el-radio-group>
      </div>

      <div class="setting-item setting-item--column">
        <div class="setting-label">
          <span>关心的招生阶段</span>
          <span class="setting-desc">单选，优先注入对话提示词</span>
        </div>
        <el-radio-group v-model="admissionStage" size="small">
          <el-radio-button v-for="opt in stageOptions" :key="opt.value" :value="opt.value">
            {{ opt.label }}
          </el-radio-button>
        </el-radio-group>
      </div>

      <div class="setting-item setting-item--actions">
        <el-button type="primary" size="small" :loading="profileSaving" @click="savePersonaConfig">
          保存
        </el-button>
      </div>
    </div>

    <div class="settings-card">
      <h3 class="section-title">关于</h3>
      <div class="about-info">
        <p>京师小智 · 招生智能助手 v1.0.0</p>
        <p class="about-copyright">&copy; 2026 北京师范大学招生办公室</p>
      </div>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.settings-page {
  max-width: 640px;
  margin: 0 auto;
  padding: 24px 16px;
  height: 100%;
  overflow-y: auto;
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;

  h2 {
    font-size: 1.25rem;
    font-weight: 700;
    color: var(--color-text-primary);
    margin: 0;
  }
}

.settings-card {
  background: var(--color-bg-primary);
  border: 1px solid var(--color-border);
  border-radius: 12px;
  padding: 20px;
  margin-bottom: 16px;
}

.section-title {
  font-size: 0.9375rem;
  font-weight: 600;
  color: var(--color-text-primary);
  margin: 0 0 16px;
}

.setting-item {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 0;
  border-bottom: 1px solid var(--color-border);

  &:last-child {
    border-bottom: none;
    padding-bottom: 0;
  }

  &:first-of-type {
    padding-top: 0;
  }
}

.setting-item--column {
  flex-direction: column;
  align-items: flex-start;
  gap: 8px;
}

.setting-item--actions {
  justify-content: flex-end;
}

.setting-label {
  display: flex;
  flex-direction: column;
  gap: 2px;

  span:first-child {
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-text-primary);
  }
}

.setting-desc {
  font-size: 0.75rem;
  color: var(--color-text-secondary);
}

.setting-value {
  font-size: 0.875rem;
  color: var(--color-text-secondary);
}

.setting-value-row {
  display: flex;
  align-items: center;
  gap: 4px;
}

.setting-edit-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.about-info {
  p {
    font-size: 0.875rem;
    color: var(--color-text-primary);
    margin: 0 0 4px;
  }
}

.about-copyright {
  font-size: 0.75rem;
  color: var(--color-text-secondary) !important;
}
</style>
