<script setup lang="ts">
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowLeft, Moon, Sunny } from '@element-plus/icons-vue'
import { useThemeStore } from '@/stores/theme'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const themeStore = useThemeStore()
const userStore = useUserStore()

const isDark = computed(() => themeStore.mode === 'dark')
const fontSizeOptions = [
  { label: '小', value: 14 as const },
  { label: '标准', value: 16 as const },
  { label: '大', value: 18 as const },
  { label: '特大', value: 20 as const },
]
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
          <span>夜间模式</span>
          <span class="setting-desc">切换明暗主题</span>
        </div>
        <el-switch
          :model-value="isDark"
          :active-action-icon="Moon"
          :inactive-action-icon="Sunny"
          @change="themeStore.toggleTheme()"
        />
      </div>

      <div class="setting-item">
        <div class="setting-label">
          <span>字体大小</span>
          <span class="setting-desc">调整全局文字大小</span>
        </div>
        <el-radio-group
          :model-value="themeStore.fontSize"
          size="small"
          @change="(val: number) => themeStore.setFontSize(val as 14 | 16 | 18 | 20)"
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
        <span class="setting-value">{{ userStore.userInfo?.nickname || '未设置' }}</span>
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
}

.settings-header {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-bottom: 24px;

  h2 {
    font-size: 20px;
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
  font-size: 15px;
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

.setting-label {
  display: flex;
  flex-direction: column;
  gap: 2px;

  span:first-child {
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text-primary);
  }
}

.setting-desc {
  font-size: 12px;
  color: var(--color-text-secondary);
}

.setting-value {
  font-size: 14px;
  color: var(--color-text-secondary);
}

.about-info {
  p {
    font-size: 14px;
    color: var(--color-text-primary);
    margin: 0 0 4px;
  }
}

.about-copyright {
  font-size: 12px;
  color: var(--color-text-secondary) !important;
}
</style>
