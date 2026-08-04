import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import api from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const token = ref(localStorage.getItem('access_token') || '')
  const currentRole = ref(localStorage.getItem('view_role') || '')

  const isLoggedIn = computed(() => !!token.value)
  const isDirector = computed(() => user.value?.role === 'director' || currentRole.value === 'director')
  const isDeputyDirector = computed(() => user.value?.role === 'deputy_director' || currentRole.value === 'deputy_director')
  const isProjectLeader = computed(() => user.value?.role === 'project_leader' || currentRole.value === 'project_leader')
  const userName = computed(() => user.value?.name || '')
  const userRole = computed(() => currentRole.value || user.value?.role || 'member')

  async function login(username, password) {
    const res = await api.post('/login', { username, password })
    token.value = res.data.access_token
    user.value = res.data.user
    currentRole.value = res.data.user.role
    localStorage.setItem('access_token', res.data.access_token)
    localStorage.setItem('view_role', res.data.user.role)
    // 设置 axios 默认头
    api.defaults.headers.common['Authorization'] = `Bearer ${res.data.access_token}`
    return res.data
  }

  function logout() {
    token.value = ''
    user.value = null
    currentRole.value = ''
    localStorage.removeItem('access_token')
    localStorage.removeItem('view_role')
    delete api.defaults.headers.common['Authorization']
  }

  function switchRole(role) {
    currentRole.value = role
    localStorage.setItem('view_role', role)
  }

  // 初始化时设置 token
  if (token.value) {
    api.defaults.headers.common['Authorization'] = `Bearer ${token.value}`
  }

  return { user, token, currentRole, isLoggedIn, isDirector, isDeputyDirector, isProjectLeader, userName, userRole, login, logout, switchRole }
})