<template>
  <div class="login-page">
    <div class="login-box">
      <div class="login-header">
        <el-icon size="40" color="var(--zb-accent)"><ChatDotRound /></el-icon>
        <h1>知伴AI</h1>
        <p>双端智能体平台 · 管理后台</p>
      </div>

      <el-tabs v-model="activeTab" class="login-tabs">
        <el-tab-pane label="登录" name="login">
          <el-form
            ref="loginFormRef"
            :model="loginForm"
            :rules="loginRules"
            label-width="0"
          >
            <el-form-item prop="username">
              <el-input
                v-model="loginForm.username"
                placeholder="请输入用户名"
                :prefix-icon="User"
                size="large"
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="loginForm.password"
                type="password"
                placeholder="请输入密码"
                :prefix-icon="Lock"
                size="large"
                show-password
                @keyup.enter="handleLogin"
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="submit-btn"
              :loading="submitting"
              @click="handleLogin"
            >
              登录
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="注册" name="register">
          <el-form
            ref="registerFormRef"
            :model="registerForm"
            :rules="registerRules"
            label-width="0"
          >
            <el-form-item prop="username">
              <el-input
                v-model="registerForm.username"
                placeholder="请设置用户名"
                :prefix-icon="User"
                size="large"
              />
            </el-form-item>
            <el-form-item prop="password">
              <el-input
                v-model="registerForm.password"
                type="password"
                placeholder="请设置密码"
                :prefix-icon="Lock"
                size="large"
                show-password
              />
            </el-form-item>
            <el-form-item prop="confirmPassword">
              <el-input
                v-model="registerForm.confirmPassword"
                type="password"
                placeholder="请确认密码"
                :prefix-icon="Lock"
                size="large"
                show-password
              />
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="submit-btn"
              :loading="submitting"
              @click="handleRegister"
            >
              注册
            </el-button>
          </el-form>
        </el-tab-pane>

        <el-tab-pane label="手机号登录" name="phone">
          <el-form
            ref="phoneFormRef"
            :model="phoneForm"
            :rules="phoneRules"
            label-width="0"
          >
            <el-form-item prop="phone">
              <el-input
                v-model="phoneForm.phone"
                placeholder="请输入手机号"
                :prefix-icon="Iphone"
                size="large"
                maxlength="11"
              />
            </el-form-item>
            <el-form-item prop="code">
              <div class="code-row">
                <el-input
                  v-model="phoneForm.code"
                  placeholder="请输入验证码"
                  :prefix-icon="Key"
                  size="large"
                  maxlength="6"
                  @keyup.enter="handlePhoneLogin"
                />
                <el-button
                  size="large"
                  :disabled="countdown > 0"
                  :loading="sendingCode"
                  @click="handleSendCode"
                >
                  {{ countdown > 0 ? `${countdown}s` : '获取验证码' }}
                </el-button>
              </div>
            </el-form-item>
            <el-button
              type="primary"
              size="large"
              class="submit-btn"
              :loading="submitting"
              @click="handlePhoneLogin"
            >
              登录
            </el-button>
          </el-form>
        </el-tab-pane>
      </el-tabs>

      <!-- 游客模式入口（附件一 §4.1）-->
      <el-divider>或</el-divider>
      <el-button
        size="large"
        class="guest-btn"
        :loading="guestLoading"
        @click="handleGuestLogin"
      >
        <el-icon class="el-icon--left"><UserFilled /></el-icon>
        游客模式进入（无需注册）
      </el-button>

      <el-button text class="back-home" @click="$router.push('/')">
        返回首页
      </el-button>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { User, Lock, Iphone, Key, UserFilled } from '@element-plus/icons-vue'
import { login, register, guestLogin, sendSmsCode, phoneLogin } from '@/api/help'

const router = useRouter()
const activeTab = ref('login')
const submitting = ref(false)
const guestLoading = ref(false)
const sendingCode = ref(false)
const countdown = ref(0)

const loginFormRef = ref(null)
const registerFormRef = ref(null)
const phoneFormRef = ref(null)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const phoneForm = reactive({
  phone: '',
  code: ''
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const phoneRules = {
  phone: [
    { required: true, message: '请输入手机号', trigger: 'blur' },
    { pattern: /^1[3-9]\d{9}$/, message: '手机号格式不正确', trigger: 'blur' }
  ],
  code: [
    { required: true, message: '请输入验证码', trigger: 'blur' },
    { pattern: /^\d{4,6}$/, message: '验证码格式不正确', trigger: 'blur' }
  ]
}

const registerRules = {
  username: [
    { required: true, message: '请设置用户名', trigger: 'blur' },
    { min: 3, message: '用户名至少3个字符', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请设置密码', trigger: 'blur' },
    { min: 6, message: '密码至少6个字符', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次输入的密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

async function handleLogin() {
  if (!loginFormRef.value) return
  await loginFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await login({
        username: loginForm.username,
        password: loginForm.password
      })
      ElMessage.success('登录成功')
      router.push('/admin/articles')
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

async function handleRegister() {
  if (!registerFormRef.value) return
  await registerFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await register({
        username: registerForm.username,
        password: registerForm.password
      })
      ElMessage.success('注册成功，请登录')
      activeTab.value = 'login'
      loginForm.username = registerForm.username
      loginForm.password = ''
      Object.assign(registerForm, {
        username: '',
        password: '',
        confirmPassword: ''
      })
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

// 发送短信验证码（附件一 §3.1）
async function handleSendCode() {
  if (!phoneFormRef.value) return
  // 仅校验手机号字段
  try {
    await phoneFormRef.value.validateField('phone')
  } catch {
    return
  }

  sendingCode.value = true
  try {
    await sendSmsCode(phoneForm.phone)
    ElMessage.success('验证码已发送')
    countdown.value = 60
    const timer = setInterval(() => {
      countdown.value -= 1
      if (countdown.value <= 0) clearInterval(timer)
    }, 1000)
  } catch {
    // 错误已由拦截器处理
  } finally {
    sendingCode.value = false
  }
}

// 手机号 + 验证码登录
async function handlePhoneLogin() {
  if (!phoneFormRef.value) return
  await phoneFormRef.value.validate(async (valid) => {
    if (!valid) return
    submitting.value = true
    try {
      await phoneLogin({ phone: phoneForm.phone, code: phoneForm.code })
      ElMessage.success('登录成功')
      router.push('/admin/articles')
    } catch {
      // 错误已由拦截器处理
    } finally {
      submitting.value = false
    }
  })
}

// 游客模式登录（附件一 §4.1：游客模式入口）
async function handleGuestLogin() {
  guestLoading.value = true
  try {
    await guestLogin()
    ElMessage.success('已进入游客模式')
    router.push('/help')
  } catch {
    // 错误已由拦截器处理
  } finally {
    guestLoading.value = false
  }
}
</script>

<style scoped>
/* 去紫蓝 AI 渐变：改沉静墨青底 + 右上柔光，配玻璃质感卡片 */
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: var(--zb-space-6);
  background:
    radial-gradient(720px 480px at 100% 0%, rgba(43, 106, 119, 0.14), transparent 60%),
    radial-gradient(560px 380px at 0% 100%, rgba(43, 106, 119, 0.08), transparent 55%),
    var(--zb-bg);
}

.login-box {
  width: 420px;
  max-width: 100%;
  background: var(--zb-surface);
  border: 1px solid var(--zb-border);
  border-radius: var(--zb-radius-lg);
  padding: var(--zb-space-10) var(--zb-space-8) var(--zb-space-6);
  box-shadow: var(--zb-shadow-lg);
}

.login-header {
  text-align: center;
  margin-bottom: var(--zb-space-8);
}

.login-header h1 {
  font-size: 26px;
  font-weight: 700;
  letter-spacing: 0.02em;
  margin: var(--zb-space-3) 0 var(--zb-space-1);
  color: var(--zb-text);
}

.login-header p {
  font-size: 14px;
  color: var(--zb-text-3);
}

.login-tabs {
  margin-bottom: var(--zb-space-3);
}

.submit-btn {
  width: 100%;
  margin-top: var(--zb-space-2);
}

.code-row {
  display: flex;
  gap: var(--zb-space-2);
  width: 100%;
}

.code-row .el-input {
  flex: 1;
}

.guest-btn {
  width: 100%;
  margin-top: 2px;
}

.back-home {
  width: 100%;
  margin-top: var(--zb-space-2);
}
</style>
