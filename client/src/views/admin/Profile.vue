<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Phone, Lock, Edit } from '@element-plus/icons-vue'
import request from '@/api/request'
import { updateProfile, changePassword, sendPasswordChangeSms, sendPhoneChangeSms, changePhone } from '@/api/admin/admin'
import { useAdminStore } from '@/stores/admin'

const adminStore = useAdminStore()

// 基本信息
const profileLoading = ref(false)
const profileSaving = ref(false)
const profileForm = reactive({
  username: '',
  real_name: '',
  employee_id: '',
  department: '',
  title: '',
  email: '',
  phone: '',
})

async function fetchProfile() {
  profileLoading.value = true
  try {
    const res = await request.get('/admin/auth/me')
    const data = res.data
    profileForm.username = data.username || ''
    profileForm.real_name = data.real_name || ''
    profileForm.employee_id = data.employee_id || ''
    profileForm.department = data.department || ''
    profileForm.title = data.title || ''
    profileForm.email = data.email || ''
    profileForm.phone = data.phone || ''
  } catch {
    ElMessage.error('加载个人信息失败')
  } finally {
    profileLoading.value = false
  }
}

async function saveProfile() {
  profileSaving.value = true
  try {
    await updateProfile({
      real_name: profileForm.real_name || undefined,
      employee_id: profileForm.employee_id || undefined,
      department: profileForm.department || undefined,
      title: profileForm.title || undefined,
      email: profileForm.email || undefined,
    })
    ElMessage.success('个人信息已更新')
    adminStore.fetchProfile()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '更新失败')
  } finally {
    profileSaving.value = false
  }
}

// 修改密码
const passwordSaving = ref(false)
const pwdSmsSending = ref(false)
const pwdSmsCountdown = ref(0)
let pwdSmsTimer: ReturnType<typeof setInterval> | null = null

const passwordForm = reactive({
  old_password: '',
  new_password: '',
  confirm_password: '',
  sms_code: '',
})

function calcPasswordStrength(password: string) {
  let score = 0
  if (password.length >= 8) score += 1
  if (/[a-z]/.test(password)) score += 1
  if (/[A-Z]/.test(password)) score += 1
  if (/\d/.test(password)) score += 1
  if (/[^A-Za-z0-9]/.test(password)) score += 1
  return score
}

const passwordStrength = computed(() => {
  const score = calcPasswordStrength(passwordForm.new_password)
  if (!passwordForm.new_password) {
    return { percent: 0, label: '未输入', color: '#909399' }
  }
  if (score <= 2) {
    return { percent: 30, label: '弱', color: '#F56C6C' }
  }
  if (score <= 4) {
    return { percent: 60, label: '中', color: '#E6A23C' }
  }
  return { percent: 100, label: '强', color: '#67C23A' }
})

async function sendPwdSmsCode() {
  pwdSmsSending.value = true
  try {
    const res = await sendPasswordChangeSms()
    ElMessage.success(`验证码已发送至 ${res.data.phone_masked}`)
    pwdSmsCountdown.value = 60
    pwdSmsTimer = setInterval(() => {
      pwdSmsCountdown.value--
      if (pwdSmsCountdown.value <= 0 && pwdSmsTimer) {
        clearInterval(pwdSmsTimer)
        pwdSmsTimer = null
      }
    }, 1000)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '验证码发送失败')
  } finally {
    pwdSmsSending.value = false
  }
}

async function savePassword() {
  if (!passwordForm.old_password || !passwordForm.new_password) {
    ElMessage.warning('请填写完整密码信息')
    return
  }
  if (passwordForm.new_password !== passwordForm.confirm_password) {
    ElMessage.warning('两次输入的新密码不一致')
    return
  }
  if (passwordForm.new_password.length < 8) {
    ElMessage.warning('新密码至少8位')
    return
  }
  if (calcPasswordStrength(passwordForm.new_password) < 5) {
    ElMessage.warning('密码需包含大小写字母、数字和特殊字符')
    return
  }
  if (!passwordForm.sms_code || passwordForm.sms_code.length !== 6) {
    ElMessage.warning('请输入6位验证码')
    return
  }
  passwordSaving.value = true
  try {
    await changePassword({
      old_password: passwordForm.old_password,
      new_password: passwordForm.new_password,
      sms_code: passwordForm.sms_code,
    })
    ElMessage.success('密码已修改')
    passwordForm.old_password = ''
    passwordForm.new_password = ''
    passwordForm.confirm_password = ''
    passwordForm.sms_code = ''
    if (pwdSmsTimer) {
      clearInterval(pwdSmsTimer)
      pwdSmsTimer = null
      pwdSmsCountdown.value = 0
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '密码修改失败')
  } finally {
    passwordSaving.value = false
  }
}

// 修改手机号
const phoneSaving = ref(false)
const smsSending = ref(false)
const smsCountdown = ref(0)
let smsTimer: ReturnType<typeof setInterval> | null = null

const phoneForm = reactive({
  new_phone: '',
  sms_code: '',
})

async function sendSmsCode() {
  if (!/^1[3-9]\d{9}$/.test(phoneForm.new_phone)) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  smsSending.value = true
  try {
    await sendPhoneChangeSms(phoneForm.new_phone)
    ElMessage.success('验证码已发送')
    smsCountdown.value = 60
    smsTimer = setInterval(() => {
      smsCountdown.value--
      if (smsCountdown.value <= 0 && smsTimer) {
        clearInterval(smsTimer)
        smsTimer = null
      }
    }, 1000)
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '验证码发送失败')
  } finally {
    smsSending.value = false
  }
}

async function savePhone() {
  if (!/^1[3-9]\d{9}$/.test(phoneForm.new_phone)) {
    ElMessage.warning('请输入正确的手机号')
    return
  }
  if (!phoneForm.sms_code || phoneForm.sms_code.length !== 6) {
    ElMessage.warning('请输入6位验证码')
    return
  }
  phoneSaving.value = true
  try {
    await changePhone({
      new_phone: phoneForm.new_phone,
      sms_code: phoneForm.sms_code,
    })
    ElMessage.success('手机号已更换')
    profileForm.phone = phoneForm.new_phone
    phoneForm.new_phone = ''
    phoneForm.sms_code = ''
    if (smsTimer) {
      clearInterval(smsTimer)
      smsTimer = null
      smsCountdown.value = 0
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.message || '手机号更换失败')
  } finally {
    phoneSaving.value = false
  }
}

function maskPhone(phone: string) {
  if (!phone || phone.length < 7) return phone || '未绑定'
  return `${phone.slice(0, 3)}****${phone.slice(-4)}`
}

onMounted(fetchProfile)
</script>

<template>
  <div class="profile-page" v-loading="profileLoading">
    <div class="profile-cards">
      <!-- 基本信息 -->
      <el-card shadow="never" class="profile-card">
        <template #header>
          <div class="card-header">
            <el-icon><Edit /></el-icon>
            <span>基本信息</span>
          </div>
        </template>
        <el-form label-width="80px" :model="profileForm">
          <el-form-item label="用户名">
            <el-input v-model="profileForm.username" disabled />
          </el-form-item>
          <el-form-item label="姓名">
            <el-input v-model="profileForm.real_name" placeholder="请输入姓名" maxlength="50" />
          </el-form-item>
          <el-form-item label="工号">
            <el-input v-model="profileForm.employee_id" placeholder="请输入工号" maxlength="30" />
          </el-form-item>
          <el-form-item label="部门">
            <el-input v-model="profileForm.department" placeholder="请输入部门" maxlength="100" />
          </el-form-item>
          <el-form-item label="职位">
            <el-input v-model="profileForm.title" placeholder="请输入职位" maxlength="50" />
          </el-form-item>
          <el-form-item label="邮箱">
            <el-input v-model="profileForm.email" placeholder="请输入邮箱" maxlength="100" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="profileSaving" @click="saveProfile">保存修改</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 修改手机号 -->
      <el-card shadow="never" class="profile-card">
        <template #header>
          <div class="card-header">
            <el-icon><Phone /></el-icon>
            <span>修改手机号</span>
          </div>
        </template>
        <el-form label-width="100px" :model="phoneForm">
          <el-form-item label="当前手机号">
            <el-text>{{ maskPhone(profileForm.phone) }}</el-text>
          </el-form-item>
          <el-form-item label="新手机号">
            <el-input v-model="phoneForm.new_phone" placeholder="请输入新手机号" maxlength="11" />
          </el-form-item>
          <el-form-item label="验证码">
            <div class="sms-row">
              <el-input v-model="phoneForm.sms_code" placeholder="请输入验证码" maxlength="6" />
              <el-button
                :disabled="smsCountdown > 0 || smsSending"
                :loading="smsSending"
                @click="sendSmsCode"
              >
                {{ smsCountdown > 0 ? `${smsCountdown}s 后重发` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="phoneSaving" @click="savePhone">确认更换</el-button>
          </el-form-item>
        </el-form>
      </el-card>

      <!-- 修改密码 -->
      <el-card shadow="never" class="profile-card">
        <template #header>
          <div class="card-header">
            <el-icon><Lock /></el-icon>
            <span>修改密码</span>
          </div>
        </template>
        <el-form label-width="100px" :model="passwordForm">
          <el-form-item label="原密码">
            <el-input v-model="passwordForm.old_password" type="password" show-password placeholder="请输入原密码" />
          </el-form-item>
          <el-form-item label="新密码">
            <el-input v-model="passwordForm.new_password" type="password" show-password placeholder="请输入新密码（至少8位）" />
            <div class="password-strength" v-if="passwordForm.new_password">
              <el-progress
                :percentage="passwordStrength.percent"
                :show-text="false"
                :stroke-width="6"
                :color="passwordStrength.color"
              />
              <span class="password-strength__label" :style="{ color: passwordStrength.color }">
                密码强度：{{ passwordStrength.label }}
              </span>
            </div>
          </el-form-item>
          <el-form-item label="确认新密码">
            <el-input v-model="passwordForm.confirm_password" type="password" show-password placeholder="请再次输入新密码" />
          </el-form-item>
          <el-form-item label="验证码">
            <div class="sms-row">
              <el-input v-model="passwordForm.sms_code" placeholder="请输入验证码" maxlength="6" />
              <el-button
                :disabled="pwdSmsCountdown > 0 || pwdSmsSending"
                :loading="pwdSmsSending"
                @click="sendPwdSmsCode"
              >
                {{ pwdSmsCountdown > 0 ? `${pwdSmsCountdown}s 后重发` : '获取验证码' }}
              </el-button>
            </div>
          </el-form-item>
          <el-form-item>
            <el-button type="primary" :loading="passwordSaving" @click="savePassword">修改密码</el-button>
          </el-form-item>
        </el-form>
      </el-card>
    </div>
  </div>
</template>

<style lang="scss" scoped>
.profile-page {
  padding: 20px;
  height: 100%;
  overflow-y: auto;
  -webkit-overflow-scrolling: touch;
}

.profile-cards {
  max-width: 640px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.profile-card {
  :deep(.el-card__header) {
    padding: 14px 20px;
    border-bottom: 1px solid var(--border-color, #E2E6ED);
  }
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 1rem;
  font-weight: 600;
  color: var(--text-primary, #1A1A2E);
}

.sms-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

.sms-row .el-input {
  flex: 1;
}

.password-strength {
  margin-top: 8px;
}

.password-strength__label {
  display: inline-block;
  margin-top: 6px;
  font-size: 0.75rem;
}
</style>
