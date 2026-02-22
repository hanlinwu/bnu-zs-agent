<template>
  <div class="login-form">
    <!-- Step 1: Phone + SMS Code -->
    <div v-if="step === 'login'" class="login-form__step">
      <div class="login-form__field">
        <label class="login-form__label">手机号</label>
        <div class="login-form__phone-row">
          <div class="login-form__country-code">
            <span class="country-flag">🇨🇳</span>
            <span class="country-number">+86</span>
          </div>
          <el-input
            v-model="phone"
            placeholder="请输入11位手机号"
            maxlength="11"
            size="large"
            class="login-form__phone-input"
            :class="{ 'is-error': phoneError }"
            @input="onPhoneInput"
            @keydown.enter="handlePhoneEnter"
          />
          <button
            class="login-form__sms-btn"
            :disabled="!canSendCode || smsSending"
            @click="handleSendCode"
          >
            <el-icon v-if="smsSending" class="is-loading">
              <Loading />
            </el-icon>
            <span v-if="countdown > 0">{{ countdown }}s</span>
            <span v-else>获取验证码</span>
          </button>
        </div>
        <p v-if="phoneError" class="login-form__error">{{ phoneError }}</p>
      </div>

      <div v-if="codeSent" class="login-form__field">
        <label class="login-form__label">验证码</label>
        <SmsCodeInput
          ref="smsCodeRef"
          v-model="smsCode"
          @complete="handleCodeComplete"
        />
      </div>

      <template v-if="codeSent">
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
          <a href="javascript:void(0)" @click.prevent="showAgreement('用户协议')">用户协议</a>
          和
          <a href="javascript:void(0)" @click.prevent="showAgreement('隐私政策')">隐私政策</a>
        </p>
      </template>
    </div>

    <el-dialog
      v-model="profileDialogVisible"
      title="完善基本信息"
      width="520px"
      :close-on-click-modal="false"
      :close-on-press-escape="false"
      :show-close="false"
    >
      <div class="profile-dialog__body">
        <div class="profile-dialog__row">
          <label>省份/地区</label>
          <el-select v-model="profileProvince" placeholder="请选择省份/地区" filterable>
            <el-option v-for="item in PROVINCE_OPTIONS" :key="item" :label="item" :value="item" />
          </el-select>
        </div>
        <div class="profile-dialog__row">
          <label>身份</label>
          <el-radio-group v-model="profileIdentity" size="small">
            <el-radio-button value="student">学生本人</el-radio-button>
            <el-radio-button value="parent">家长</el-radio-button>
          </el-radio-group>
        </div>
        <div class="profile-dialog__row">
          <label>生源类型</label>
          <el-radio-group v-model="profileSourceGroup" size="small">
            <el-radio-button value="mainland_general">内地生</el-radio-button>
            <el-radio-button value="hkmo_tw">港澳台生</el-radio-button>
            <el-radio-button value="international">国际生</el-radio-button>
          </el-radio-group>
        </div>
        <div class="profile-dialog__row">
          <label>关心招生阶段</label>
          <el-radio-group v-model="profileAdmissionStage" size="small">
            <el-radio-button value="undergraduate">本科</el-radio-button>
            <el-radio-button value="master">硕士研究生</el-radio-button>
            <el-radio-button value="doctor">博士研究生</el-radio-button>
          </el-radio-group>
        </div>
      </div>
      <template #footer>
        <el-button type="primary" :loading="profileSaving" @click="saveProfileAndEnter">
          保存并进入
        </el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Loading } from '@element-plus/icons-vue'
import { useUserStore } from '@/stores/user'
import { sendSmsCode } from '@/api/auth'
import { PROVINCE_OPTIONS } from '@/constants/profile'
import SmsCodeInput from './SmsCodeInput.vue'
type Step = 'login'

const router = useRouter()
const userStore = useUserStore()
const props = withDefaults(defineProps<{
  redirectOnSuccess?: boolean
}>(), {
  redirectOnSuccess: true,
})
const emit = defineEmits<{
  success: []
}>()

// Form state
const phone = ref('')
const smsCode = ref('')
const phoneError = ref('')
const step = ref<Step>('login')

// Loading states
const smsSending = ref(false)
const loginLoading = ref(false)

// SMS countdown
const countdown = ref(0)
const codeSent = ref(false)
let countdownTimer: ReturnType<typeof setInterval> | null = null

const profileDialogVisible = ref(false)
const profileSaving = ref(false)
const profileProvince = ref('')
const profileIdentity = ref<'student' | 'parent' | ''>('')
const profileSourceGroup = ref<'mainland_general' | 'hkmo_tw' | 'international' | ''>('')
const profileAdmissionStage = ref<'undergraduate' | 'master' | 'doctor' | ''>('')

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
    const res = await sendSmsCode(phone.value)
    if (!res?.data?.success) {
      throw new Error(res?.data?.message || '验证码发送失败，请稍后重试')
    }
    ElMessage.success('验证码已发送，请注意查收')
    codeSent.value = true
    startCountdown()
    // Auto-focus SMS code input after transition
    nextTick(() => smsCodeRef.value?.focus())
  } catch (error: any) {
    const msg = error?.response?.data?.message || error?.message || '验证码发送失败，请稍后重试'
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
    const loginResult = await userStore.login(phone.value, smsCode.value)
    ElMessage.success('登录成功')
    if (loginResult?.is_first_login) {
      initProfileDialog()
      profileDialogVisible.value = true
      return
    }
    emit('success')
    if (props.redirectOnSuccess) {
      router.push('/')
    }
  } catch (error: any) {
    // 403 表示账号被禁用，直接显示后端返回的消息
    if (error?.response?.status === 403) {
      const msg = error?.response?.data?.detail?.message || '账号暂时无法使用，如有疑问请联系客服'
      ElMessage.error(msg)
    } else {
      const msg = error?.response?.data?.message || '登录失败，请检查验证码是否正确'
      ElMessage.error(msg)
    }
    smsCodeRef.value?.clear()
  } finally {
    loginLoading.value = false
  }
}

function initProfileDialog() {
  const info = userStore.userInfo
  profileProvince.value = (info?.province as string) || ''
  profileIdentity.value = (info?.identity_type as 'student' | 'parent' | '') || ''
  profileSourceGroup.value = (info?.source_group as 'mainland_general' | 'hkmo_tw' | 'international' | '') || ''
  const stages = Array.isArray(info?.admission_stages)
    ? (info?.admission_stages as Array<'undergraduate' | 'master' | 'doctor'>)
    : []
  profileAdmissionStage.value = stages[0] || ''
}

async function saveProfileAndEnter() {
  if (!profileProvince.value) {
    ElMessage.warning('请选择省份/地区')
    return
  }
  profileSaving.value = true
  try {
    await userStore.updateProfile({
      province: profileProvince.value,
      identity_type: profileIdentity.value || undefined,
      source_group: profileSourceGroup.value || undefined,
      admission_stages: profileAdmissionStage.value ? [profileAdmissionStage.value] : [],
    })
    profileDialogVisible.value = false
    emit('success')
    if (props.redirectOnSuccess) {
      router.push('/')
    }
  } catch {
    ElMessage.error('保存失败，请重试')
  } finally {
    profileSaving.value = false
  }
}

function showAgreement(title: string) {
  const content = title === '用户协议'
    ? '本系统为北京师范大学招生咨询服务平台，仅供考生及家长咨询招生相关问题使用。使用本系统即表示您同意遵守相关法律法规，不得利用本系统发布违法违规信息。系统回答仅供参考，具体招生政策以北京师范大学招生办公室官方发布为准。'
    : '我们重视您的隐私保护。本系统仅收集提供服务所必需的信息（手机号、对话记录），不会向第三方泄露您的个人信息。您的对话数据将按照《个人信息保护法》《数据安全法》要求进行存储和管理。如有疑问，请联系北京师范大学招生办公室。'
  ElMessageBox.alert(content, title, {
    confirmButtonText: '我知道了',
    dangerouslyUseHTMLString: false,
  })
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
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-text-primary);
  }

  &__error {
    font-size: 0.75rem;
    color: var(--color-danger);
    margin-top: 2px;
  }

  &__phone-row {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  &__country-code {
    display: flex;
    align-items: center;
    gap: 4px;
    height: 40px;
    padding: 0 12px;
    background: var(--color-bg-secondary, #f4f6fa);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    font-size: 0.875rem;
    font-weight: 500;
    color: var(--color-text-primary);
    white-space: nowrap;
    flex-shrink: 0;

    .country-flag {
      font-size: 1rem;
      line-height: 1;
    }

    .country-number {
      font-size: 0.875rem;
    }
  }

  &__phone-input {
    flex: 1;
    min-width: 0;
  }

  &__sms-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 4px;
    height: 40px;
    padding: 0 16px;
    font-size: 0.8125rem;
    font-weight: 600;
    color: #ffffff;
    background: var(--color-primary);
    border: none;
    border-radius: var(--radius-md);
    cursor: pointer;
    white-space: nowrap;
    flex-shrink: 0;
    transition: background 0.2s ease, opacity 0.2s ease;

    &:hover:not(:disabled) {
      background: var(--color-primary-light);
    }

    &:disabled {
      background: var(--color-border, #e2e6ed);
      color: var(--color-text-placeholder);
      cursor: not-allowed;
    }
  }

  &__sms-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  &__submit {
    width: 100%;
    height: 48px;
    font-size: 1rem;
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
    font-size: 0.75rem;
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
    font-size: 0.875rem;
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

.profile-dialog__body {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.profile-dialog__row {
  display: flex;
  flex-direction: column;
  gap: 8px;

  label {
    font-size: 0.875rem;
    color: var(--color-text-primary);
    font-weight: 500;
  }
}
</style>
