<template>
  <div class="login-container">
    <div class="login-card">
      <div class="login-header">
        <div class="login-icon">🏛️</div>
        <h1>建筑一所</h1>
        <p>{{ isRegisterMode ? '注册新账号' : '生产调度助手平台' }}</p>
        
      </div>
      
      <!-- 登录表单 -->
      <form v-if="!isRegisterMode" @submit.prevent="handleLogin" class="login-form">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="username" type="text" class="input" placeholder="请输入用户名" required />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="password" type="password" class="input" placeholder="请输入密码" required />
        </div>
        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
        <button type="submit" class="btn btn-primary btn-lg login-btn" :disabled="loading">
          {{ loading ? '登录中...' : '登 录' }}
        </button>
        <button type="button" class="btn btn-link" @click="toggleMode">没有账号？立即注册</button>
      </form>
      
      <!-- 注册表单 -->
      <form v-else @submit.prevent="handleRegister" class="login-form">
        <div class="form-group">
          <label>用户名</label>
          <input v-model="regUsername" type="text" class="input" placeholder="请设置用户名" required />
        </div>
        <div class="form-group">
          <label>工号</label>
          <input v-model="regEmployeeId" type="text" class="input" placeholder="请输入员工工号" required />
        </div>
        <div class="form-group">
          <label>姓名</label>
          <input v-model="regName" type="text" class="input" placeholder="请输入真实姓名" required />
        </div>
        <div class="form-group">
          <label>密码</label>
          <input v-model="regPassword" type="password" class="input" placeholder="请设置密码" required />
        </div>
        <div class="form-group">
          <label>确认密码</label>
          <input v-model="regConfirm" type="password" class="input" placeholder="请再次输入密码" required />
        </div>
        <div class="form-group">
          <label>部门</label>
          <input v-model="regDepartment" type="text" class="input" placeholder="所属部门" />
        </div>
        <div v-if="errorMsg" class="error-msg">{{ errorMsg }}</div>
        <div v-if="successMsg" class="success-msg">{{ successMsg }}</div>
        <button type="submit" class="btn btn-primary btn-lg login-btn" :disabled="loading">
          {{ loading ? '注册中...' : '注 册' }}
        </button>
        <button type="button" class="btn btn-link" @click="toggleMode">已有账号？返回登录</button>
      </form>
      
            
          </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../api'

const router = useRouter()
const authStore = useAuthStore()

const isRegisterMode = ref(false)
const username = ref('')
const password = ref('')
const regUsername = ref('')
const regEmployeeId = ref('')
const regName = ref('')
const regPassword = ref('')
const regConfirm = ref('')
const regDepartment = ref('')
const loading = ref(false)
const errorMsg = ref('')
const successMsg = ref('')

function toggleMode() {
  isRegisterMode.value = !isRegisterMode.value
  errorMsg.value = ''
  successMsg.value = ''
}

async function handleLogin() {
  loading.value = true
  errorMsg.value = ''
  try {
    await authStore.login(username.value, password.value)
    router.push('/')
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || '登录失败，请检查用户名和密码'
  } finally {
    loading.value = false
  }
}

async function handleRegister() {
  loading.value = true
  errorMsg.value = ''
  successMsg.value = ''

  if (regPassword.value !== regConfirm.value) {
    errorMsg.value = '两次输入的密码不一致'
    loading.value = false
    return
  }

  try {
    await api.post('/register', {
      username: regUsername.value,
      password: regPassword.value,
      name: regName.value,
      employee_id: regEmployeeId.value,
      department: regDepartment.value,
    })
    successMsg.value = '注册成功，请登录'
    username.value = regUsername.value
    password.value = ''
    setTimeout(() => { isRegisterMode.value = false }, 1500)
  } catch (err) {
    errorMsg.value = err.response?.data?.detail || '注册失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container { min-height: 100vh; display: flex; align-items: center; justify-content: center; background: linear-gradient(135deg, #0f172a 0%, #1e3a5f 50%, #0f172a 100%); padding: 20px; }
.login-card { background: white; border-radius: 16px; padding: 40px; width: 100%; max-width: 420px; box-shadow: 0 20px 60px rgba(0,0,0,0.3); animation: slideUp 0.5s ease; }
@keyframes slideUp { from { opacity: 0; transform: translateY(40px); } to { opacity: 1; transform: translateY(0); } }
.login-header { text-align: center; margin-bottom: 30px; }
.login-icon { font-size: 48px; margin-bottom: 10px; }
.login-header h1 { font-size: 24px; color: #1e293b; margin-bottom: 4px; }
.login-header p { color: #64748b; font-size: 14px; margin-bottom: 12px; }
.login-form { margin-bottom: 20px; }
.form-group { margin-bottom: 16px; }
.form-group label { display: block; margin-bottom: 6px; font-size: 14px; font-weight: 500; color: #374151; }
.login-btn { width: 100%; justify-content: center; margin-top: 8px; padding: 12px; font-size: 16px; }
.btn-link { display: block; width: 100%; text-align: center; margin-top: 12px; background: none; border: none; color: #3b82f6; cursor: pointer; font-size: 14px; padding: 8px; }
.btn-link:hover { color: #2563eb; text-decoration: underline; }
.error-msg { color: #ef4444; font-size: 13px; margin-bottom: 12px; padding: 8px 12px; background: #fef2f2; border-radius: 6px; }
.success-msg { color: #16a34a; font-size: 13px; margin-bottom: 12px; padding: 8px 12px; background: #f0fdf4; border-radius: 6px; }
.login-tips { background: #f8fafc; padding: 16px; border-radius: 8px; margin-bottom: 16px; }
.login-tips p { font-size: 12px; color: #64748b; margin-bottom: 8px; }
.tip-item { font-size: 13px; color: #475569; padding: 2px 0; }
.login-footer { text-align: center; }
.login-footer p { font-size: 11px; color: #ef4444; }

/* 响应式 */
@media (max-width: 640px) {
  .login-card { padding: 24px 20px; max-width: 100%; margin: 0 8px; border-radius: 12px; }
  .login-header h1 { font-size: 20px; }
  .login-icon { font-size: 36px; }
  .login-btn { font-size: 14px; padding: 10px; }
}
@media (max-width: 480px) {
  .login-card { padding: 20px 16px; }
  .login-header h1 { font-size: 18px; }
  .login-icon { font-size: 32px; }
  .form-group { margin-bottom: 12px; }
  .form-group label { font-size: 13px; }
}
</style>

