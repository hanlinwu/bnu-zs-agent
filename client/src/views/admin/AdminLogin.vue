<script setup lang="ts">
import { reactive, ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAdminStore } from '@/stores/admin'
import { ElMessage } from 'element-plus'
import { Lock, User } from '@element-plus/icons-vue'
import type { FormInstance, FormRules } from 'element-plus'

const router = useRouter()
const adminStore = useAdminStore()
const formRef = ref<FormInstance>()
const loading = ref(false)
const showMfa = ref(false)
const showSms = ref(false)
const showBindPhone = ref(false)
const smsSending = ref(false)
const smsCooldown = ref(0)
let smsTimer: number | null = null

const form = reactive({
  username: '',
  password: '',
  mfaCode: '',
  smsCode: '',
  bindPhone: '',
  bindSmsCode: '',
})

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

function startSmsCooldown(seconds = 60) {
  smsCooldown.value = seconds
  if (smsTimer) window.clearInterval(smsTimer)
  smsTimer = window.setInterval(() => {
    smsCooldown.value -= 1
    if (smsCooldown.value <= 0) {
      if (smsTimer) window.clearInterval(smsTimer)
      smsTimer = null
    }
  }, 1000)
}

async function handleSendSmsCode() {
  if (!form.username || !form.password) {
    ElMessage.warning('请先输入用户名和密码')
    return
  }
  if (smsCooldown.value > 0) return

  smsSending.value = true
  try {
    const res = showBindPhone.value
      ? await adminStore.sendBindPhoneSmsCode(form.username, form.password, form.bindPhone)
      : await adminStore.sendLoginSmsCode(form.username, form.password)
    if (res?.required) {
      showSms.value = true
      ElMessage.success(res?.phone_masked ? `验证码已发送至 ${res.phone_masked}` : '验证码已发送')
      startSmsCooldown(60)
    } else {
      ElMessage.success(res?.phone_masked ? `验证码已发送至 ${res.phone_masked}` : (res?.message || '验证码已发送'))
      if (showBindPhone.value) {
        startSmsCooldown(60)
      } else {
        ElMessage.info(res?.message || '当前登录无需手机号验证')
      }
    }
  } catch (err: any) {
    const msg = err?.response?.data?.detail?.message
      || err?.response?.data?.message
      || '验证码发送失败'
    ElMessage.error(msg)
  } finally {
    smsSending.value = false
  }
}

async function handleBindAndLogin() {
  if (!form.bindPhone || !form.bindSmsCode) {
    ElMessage.warning('请输入手机号和验证码')
    return
  }

  loading.value = true
  try {
    await adminStore.bindPhoneAndLogin(
      form.username,
      form.password,
      form.bindPhone,
      form.bindSmsCode,
      form.mfaCode,
    )
    ElMessage.success('绑定成功并已登录')
    router.push('/admin/dashboard')
  } catch (err: any) {
    const msg = err?.response?.data?.detail?.message
      || err?.response?.data?.message
      || '手机号绑定失败'
    if (msg.includes('MFA') || msg.includes('mfa')) {
      showMfa.value = true
      ElMessage.warning('请输入多因素认证码')
      return
    }
    ElMessage.error(msg)
  } finally {
    loading.value = false
  }
}

async function handleLogin() {
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    await adminStore.login(form.username, form.password, form.mfaCode, form.smsCode)
    ElMessage.success('登录成功')
    router.push('/admin/dashboard')
  } catch (err: any) {
    const msg = err?.response?.data?.detail?.message
      || err?.response?.data?.message
      || (Array.isArray(err?.response?.data?.detail) ? '请检查输入格式' : '')
      || '登录失败，请检查用户名和密码'
    if (msg.includes('MFA') || msg.includes('mfa') || msg.includes('验证码')) {
      if (msg.includes('MFA') || msg.includes('mfa')) {
        showMfa.value = true
        ElMessage.warning('请输入多因素认证码')
      } else if (msg.includes('绑定手机号')) {
        showBindPhone.value = true
        showSms.value = false
        ElMessage.warning('首次登录需先绑定手机号')
      } else if (msg.includes('手机号')) {
        showSms.value = true
        showBindPhone.value = false
        ElMessage.warning('当前登录需要手机号验证码，请先获取验证码')
      } else {
        ElMessage.error(msg)
      }
    } else {
      ElMessage.error(msg)
    }
  } finally {
    loading.value = false
  }
}

onUnmounted(() => {
  if (smsTimer) {
    window.clearInterval(smsTimer)
    smsTimer = null
  }
})
</script>

<template>
  <div class="admin-login-page">
    <div class="login-container">
      <div class="login-header">
        <div class="login-logo">
          <div class="logo-badge">
            <span>京</span>
          </div>
        </div>
        <h1 class="login-title">管理后台</h1>
        <p class="login-subtitle">北京师范大学招生智能体系统</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="管理员用户名"
            size="large"
            :prefix-icon="User"
          />
        </el-form-item>

        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
          />
        </el-form-item>

        <el-form-item v-if="showMfa" prop="mfaCode">
          <el-input
            v-model="form.mfaCode"
            placeholder="多因素认证码"
            size="large"
            :prefix-icon="Lock"
            maxlength="6"
          />
        </el-form-item>

        <el-form-item v-if="showSms" prop="smsCode">
          <el-input
            v-model="form.smsCode"
            placeholder="手机号验证码"
            size="large"
            :prefix-icon="Lock"
            maxlength="6"
          >
            <template #append>
              <el-button
                :disabled="smsCooldown > 0 || smsSending"
                :loading="smsSending"
                @click="handleSendSmsCode"
              >
                {{ smsCooldown > 0 ? `${smsCooldown}s` : '发送验证码' }}
              </el-button>
            </template>
          </el-input>
        </el-form-item>

        <template v-if="showBindPhone">
          <el-form-item prop="bindPhone">
            <el-input
              v-model="form.bindPhone"
              placeholder="绑定手机号（11位）"
              size="large"
              :prefix-icon="User"
              maxlength="11"
            />
          </el-form-item>

          <el-form-item prop="bindSmsCode">
            <el-input
              v-model="form.bindSmsCode"
              placeholder="手机号验证码"
              size="large"
              :prefix-icon="Lock"
              maxlength="6"
            >
              <template #append>
                <el-button
                  :disabled="smsCooldown > 0 || smsSending"
                  :loading="smsSending"
                  @click="handleSendSmsCode"
                >
                  {{ smsCooldown > 0 ? `${smsCooldown}s` : '发送验证码' }}
                </el-button>
              </template>
            </el-input>
          </el-form-item>
        </template>

        <el-form-item>
          <el-button
            v-if="!showBindPhone"
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            native-type="submit"
          >
            登 录
          </el-button>
          <el-button
            v-else
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleBindAndLogin"
          >
            绑定并登录
          </el-button>
        </el-form-item>
      </el-form>

      <div class="login-footer">
        <router-link to="/" class="back-link">返回首页</router-link>
      </div>
    </div>

    <div class="login-bg">
      <div class="bg-shape bg-shape--1" />
      <div class="bg-shape bg-shape--2" />
      <div class="bg-shape bg-shape--3" />
    </div>
  </div>
</template>

<style lang="scss" scoped>
.admin-login-page {
  min-height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #F0F2F5;
  position: relative;
  overflow: hidden;
}

.login-bg {
  position: absolute;
  inset: 0;
  pointer-events: none;
}

.bg-shape {
  position: absolute;
  border-radius: 50%;

  &--1 {
    width: 600px;
    height: 600px;
    background: radial-gradient(circle, rgba(0, 61, 165, 0.06) 0%, transparent 70%);
    top: -200px;
    right: -100px;
  }

  &--2 {
    width: 400px;
    height: 400px;
    background: radial-gradient(circle, rgba(196, 151, 47, 0.05) 0%, transparent 70%);
    bottom: -100px;
    left: -100px;
  }

  &--3 {
    width: 200px;
    height: 200px;
    border: 2px solid rgba(0, 61, 165, 0.04);
    top: 30%;
    left: 15%;
  }
}

.login-container {
  position: relative;
  z-index: 1;
  width: 400px;
  background: #ffffff;
  border-radius: 16px;
  padding: 48px 40px 40px;
  box-shadow: 0 8px 40px rgba(0, 0, 0, 0.08);
}

.login-header {
  text-align: center;
  margin-bottom: 36px;
}

.login-logo {
  display: flex;
  justify-content: center;
  margin-bottom: 16px;
}

.logo-badge {
  width: 56px;
  height: 56px;
  border-radius: 14px;
  background: linear-gradient(135deg, #003DA5, #1A5FBF);
  display: flex;
  align-items: center;
  justify-content: center;

  span {
    color: #ffffff;
    font-size: 1.75rem;
    font-weight: 700;
  }
}

.login-title {
  font-size: 1.5rem;
  font-weight: 700;
  color: #1A1A2E;
  margin: 0 0 6px;
}

.login-subtitle {
  font-size: 0.875rem;
  color: #5A5A72;
  margin: 0;
}

.login-form {
  :deep(.el-input__wrapper) {
    border-radius: 8px;
  }

  :deep(.el-form-item) {
    margin-bottom: 20px;
  }
}

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 8px;
  background: #003DA5;
  border-color: #003DA5;

  &:hover {
    background: #1A5FBF;
    border-color: #1A5FBF;
  }
}

.login-footer {
  text-align: center;
  margin-top: 16px;
}

.back-link {
  color: #5A5A72;
  text-decoration: none;
  font-size: 0.875rem;
  transition: color 0.2s;

  &:hover {
    color: #003DA5;
  }
}

@media (max-width: 480px) {
  .login-container {
    width: calc(100% - 32px);
    padding: 36px 24px 32px;
  }
}
</style>
