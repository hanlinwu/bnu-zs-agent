<template>
  <div class="role-selector">
    <h3 class="role-selector__title">请选择您的身份</h3>
    <p class="role-selector__subtitle">这将帮助我们为您提供更精准的招生资讯</p>
    <div class="role-selector__grid">
      <div
        v-for="role in roles"
        :key="role.value"
        class="role-card"
        :class="{ 'role-card--active': modelValue === role.value }"
        tabindex="0"
        role="radio"
        :aria-checked="modelValue === role.value"
        @click="selectRole(role.value)"
        @keydown.enter.space.prevent="selectRole(role.value)"
      >
        <div class="role-card__icon">
          <el-icon :size="32">
            <component :is="role.icon" />
          </el-icon>
        </div>
        <div class="role-card__content">
          <span class="role-card__title">{{ role.label }}</span>
          <span class="role-card__desc">{{ role.description }}</span>
        </div>
        <div v-if="modelValue === role.value" class="role-card__check">
          <el-icon :size="18">
            <Select />
          </el-icon>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { markRaw } from 'vue'
import { Reading, School, Opportunity, UserFilled, Select } from '@element-plus/icons-vue'

interface Props {
  modelValue: string
}

defineProps<Props>()

const emit = defineEmits<{
  'update:modelValue': [value: string]
}>()

interface RoleOption {
  value: string
  label: string
  description: string
  icon: ReturnType<typeof markRaw>
}

const roles: RoleOption[] = [
  {
    value: 'gaokao',
    label: '高考生',
    description: '参加高考的高中毕业生',
    icon: markRaw(Reading),
  },
  {
    value: 'kaoyan',
    label: '考研生',
    description: '报考硕士/博士研究生',
    icon: markRaw(School),
  },
  {
    value: 'international',
    label: '国际学生',
    description: '申请留学的国际考生',
    icon: markRaw(Opportunity),
  },
  {
    value: 'parent',
    label: '家长',
    description: '考生家长或监护人',
    icon: markRaw(UserFilled),
  },
]

function selectRole(value: string) {
  emit('update:modelValue', value)
}
</script>

<style lang="scss" scoped>
.role-selector {
  &__title {
    font-size: 1.125rem;
    font-weight: 600;
    color: var(--color-text-primary);
    text-align: center;
    margin-bottom: 4px;
  }

  &__subtitle {
    font-size: 0.875rem;
    color: var(--color-text-secondary);
    text-align: center;
    margin-bottom: 20px;
  }

  &__grid {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 12px;
  }
}

.role-card {
  position: relative;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 8px;
  padding: 20px 12px;
  border: 2px solid var(--color-border);
  border-radius: var(--radius-md);
  background-color: var(--color-bg-primary);
  cursor: pointer;
  transition: all 0.2s ease;
  text-align: center;

  &:hover {
    border-color: var(--color-primary-light);
    background-color: var(--color-primary-lighter);
  }

  &--active {
    border-color: var(--color-primary);
    background-color: var(--color-primary-lighter);
    box-shadow: 0 0 0 3px rgba(0, 61, 165, 0.12);

    .role-card__icon {
      color: var(--color-primary);
    }

    .role-card__title {
      color: var(--color-primary);
    }
  }

  &__icon {
    color: var(--color-text-secondary);
    transition: color 0.2s ease;
  }

  &__content {
    display: flex;
    flex-direction: column;
    gap: 2px;
  }

  &__title {
    font-size: 0.9375rem;
    font-weight: 600;
    color: var(--color-text-primary);
    transition: color 0.2s ease;
  }

  &__desc {
    font-size: 0.75rem;
    color: var(--color-text-secondary);
    line-height: 1.4;
  }

  &__check {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
    background-color: var(--color-primary);
    color: #ffffff;
    border-radius: 50%;
  }
}

@media (max-width: 480px) {
  .role-selector__grid {
    grid-template-columns: 1fr;
  }
}
</style>
