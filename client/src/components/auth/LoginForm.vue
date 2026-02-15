<template>
  <div class="login-form">
    <!-- Step 1: Phone + SMS Code -->
    <div v-if="step === 'login'" class="login-form__step">
      <div class="login-form__field">
        <label class="login-form__label">手机号</label>
        <el-input
          v-model="phone"
          placeholder="请输入11位手机号"
          maxlength="11"
          size="large"
          :prefix-icon="Iphone"
          :class="{ 'is-error': phoneError }"
          @input="onPhoneInput"
          @keydown.enter="handlePhoneEnter"
        />
        <p v-if="phoneError" class="login-form__error">{{ phoneError }}</p>
      </div>

      <div class="login-form__field">
        <div class="login-form__sms-row">
          <label class="login-form__label">验证码</label>
          <button
            class="login-form__sms-btn"
            :disabled="!canSendCode || smsSending"
            @click="handleSendCode"
          >
            <el-icon v-if="smsSending" class="is-loading">
              <Loading />
            </el-icon>
            <span v-if="countdown > 0">{{ countdown }}s 后重新发送</span>
            <span v-else>发送验证码</span>
          </button>
        </div>
        <SmsCodeInput
          ref="smsCodeRef"
          v-model="smsCode"
          @complete="handleCodeComplete"
        />
      </div>

      <el-button
        type="primary"
        size="large"
        class="login-form__submit"
        :loading="loginLoading"
        :disabled="!canSubmitLogin"
        @click="handleLogin"
      >
        登录
      </el-button>

      <p class="login-form__agreement">
        登录即表示您同意
        <a href="javascript:void(0)">用户协议</a>
        和
        <a href="javascript:void(0)">隐私政策</a>
      </p>
    </div>

    <!-- Step 2: Role Selection (for new users) -->
    <div v-else-if="step === 'role'" class="login-form__step">
      <RoleSelector v-model="selectedRole" />

      <el-button
        type="primary"
        size="large"
        class="login-form__submit login-form__submit--role"
        :loading="roleLoading"
        :disabled="!selectedRole"
        @click="handleRoleSubmit"
      >
        开始使用
      </el-button>

      <button class="login-form__skip" @click="handleSkipRole">
        稍后再选
      </button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Iphone, Loading } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { sendSmsCode } from '@/api/auth'
import SmsCodeInput from './SmsCodeInput.vue'
import RoleSelector from './RoleSelector.vue'

type Step = 'login' | 'role'

const router = useRouter()
const userStore = useUserStore()

// Form state
const phone = ref('')
const smsCode = ref('')
const phoneError = ref('')
const selectedRole = ref('')
const step = ref<Step>('login')

// Loading states
const smsSending = ref(false)
const loginLoading = ref(false)
const roleLoading = ref(false)

// SMS countdown
const countdown = ref(0)
let countdownTimer: ReturnType<typeof setInterval> | null = null

// Refs
const smsCodeRef = ref<InstanceType<typeof SmsCodeInput> | null>(null)

// Phone validation
const phonePattern = /^1[3-9]\d{9}$/
const isPhoneValid = computed(() => phonePattern.test(phone.value))
const canSendCode = computed(() => isPhoneValid.value && countdown.value === 0)
const canSubmitLogin = computed(() => isPhoneValid.value && smsCode.value.length === 6)

function onPhoneInput(value: string | number) {
  const strValue = String(value)
  // Strip non-digits
  phone.value = strValue.replace(/\D/g, '')
  if (phoneError.value) {
    phoneError.value = ''
  }
}

function validatePhone(): boolean {
  if (!phone.value) {
    phoneError.value = '请输入手机号'
    return false
  }
  if (!phonePattern.test(phone.value)) {
    phoneError.value = '请输入有效的11位中国手机号'
    return false
  }
  phoneError.value = ''
  return true
}

function startCountdown() {
  countdown.value = 60
  countdownTimer = setInterval(() => {
    countdown.value--
    if (countdown.value <= 0) {
      if (countdownTimer) {
        clearInterval(countdownTimer)
        countdownTimer = null
      }
    }
  }, 1000)
}

async function handleSendCode() {
  if (!validatePhone() || !canSendCode.value) return

  smsSending.value = true
  try {
    await sendSmsCode(phone.value)
    ElMessage.success('验证码已发送，请注意查收')
    startCountdown()
    // Auto-focus SMS code input
    smsCodeRef.value?.focus()
  } catch (error: any) {
    const msg = error?.response?.data?.message || '验证码发送失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    smsSending.value = false
  }
}

function handlePhoneEnter() {
  if (canSendCode.value) {
    handleSendCode()
  }
}

function handleCodeComplete(code: string) {
  smsCode.value = code
  if (isPhoneValid.value) {
    handleLogin()
  }
}

async function handleLogin() {
  if (!validatePhone()) return
  if (smsCode.value.length !== 6) {
    ElMessage.warning('请输入6位验证码')
    return
  }

  loginLoading.value = true
  try {
    const result = await userStore.login(phone.value, smsCode.value)

    // If API indicates new user, show role selection
    if (result.isNewUser) {
      step.value = 'role'
      ElMessage.success('验证成功，请选择您的身份')
    } else {
      ElMessage.success('登录成功')
      router.push('/')
    }
  } catch (error: any) {
    const msg = error?.response?.data?.message || '登录失败，请检查验证码是否正确'
    ElMessage.error(msg)
    smsCodeRef.value?.clear()
  } finally {
    loginLoading.value = false
  }
}

async function handleRoleSubmit() {
  if (!selectedRole.value) return

  roleLoading.value = true
  try {
    await userStore.updateProfile({ role: selectedRole.value as any })
    ElMessage.success('欢迎使用京师小智！')
    router.push('/')
  } catch (error: any) {
    const msg = error?.response?.data?.message || '设置失败，请稍后重试'
    ElMessage.error(msg)
  } finally {
    roleLoading.value = false
  }
}

function handleSkipRole() {
  router.push('/')
}
</script>

<style lang="scss" scoped>
.login-form {
  width: 100%;
  max-width: 400px;

  &__step {
    display: flex;
    flex-direction: column;
    gap: 24px;
  }

  &__field {
    display: flex;
    flex-direction: column;
    gap: 8px;
  }

  &__label {
    font-size: 14px;
    font-weight: 500;
    color: var(--color-text-primary);
  }

  &__error {
    font-size: 12px;
    color: var(--color-danger);
    margin-top: 2px;
  }

  &__sms-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__sms-btn {
    display: inline-flex;
    align-items: center;
    gap: 4px;
    font-size: 13px;
    font-weight: 500;
    color: var(--color-primary);
    background: none;
    border: none;
    cursor: pointer;
    padding: 0;
    transition: opacity 0.2s ease;

    &:hover:not(:disabled) {
      opacity: 0.8;
    }

    &:disabled {
      color: var(--color-text-placeholder);
      cursor: not-allowed;
    }
  }

  &__submit {
    width: 100%;
    height: 48px;
    font-size: 16px;
    font-weight: 600;
    border-radius: var(--radius-md);
    background-color: var(--color-primary);
    border-color: var(--color-primary);
    margin-top: 8px;

    &:hover {
      background-color: var(--color-primary-light);
      border-color: var(--color-primary-light);
    }

    &--role {
      margin-top: 12px;
    }
  }

  &__agreement {
    text-align: center;
    font-size: 12px;
    color: var(--color-text-secondary);

    a {
      color: var(--color-primary);
      text-decoration: none;

      &:hover {
        text-decoration: underline;
      }
    }
  }

  &__skip {
    display: block;
    width: 100%;
    text-align: center;
    font-size: 14px;
    color: var(--color-text-secondary);
    background: none;
    border: none;
    cursor: pointer;
    padding: 8px;
    transition: color 0.2s ease;

    &:hover {
      color: var(--color-primary);
    }
  }
}

// Override Element Plus input for this context
:deep(.el-input__wrapper) {
  border-radius: var(--radius-md);
  box-shadow: 0 0 0 1px var(--color-border) inset;

  &:hover {
    box-shadow: 0 0 0 1px var(--color-primary-light) inset;
  }

  &.is-focus {
    box-shadow: 0 0 0 1px var(--color-primary) inset !important;
  }
}

:deep(.el-input.is-error .el-input__wrapper) {
  box-shadow: 0 0 0 1px var(--color-danger) inset;
}
</style>
