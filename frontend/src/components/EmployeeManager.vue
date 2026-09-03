```vue
<template>
  <div class="employee-manager">
    <div class="manager-header">
      <h3>👥 员工信息管理</h3>
      <div class="header-actions" v-if="authStore.isDirector">
        <button class="btn btn-outline" @click="downloadTemplate">📥 下载模板</button>
        <button class="btn btn-outline" @click="exportData">📊 导出数据</button>
        <button class="btn btn-success" @click="handleSyncEmployeeSkills">🔄 从员工库同步技能</button>
        <button class="btn btn-primary" @click="showAddForm">+ 添加员工</button>
        <button class="btn btn-danger" @click="handleClearAll">清空数据</button>
      </div>
    </div>

    <!-- 筛选栏 -->
    <div class="filter-bar">
      <input v-model="searchQuery" class="input" style="width:auto" placeholder="搜索姓名..." />
      <select v-model="filterProfession" class="input" style="width:auto">
        <option value="">专业方向</option>
        <option v-for="p in professions" :key="p" :value="p">{{ p }}</option>
      </select>
      <select v-model="filterLoad" class="input" style="width:auto">
        <option value="">负荷</option>
        <option v-for="l in loadStatuses" :key="l" :value="l">{{ l }}</option>
      </select>
      <transition name="fade">
<div v-if="notification.show" class="notification" :class="'notification-' + notification.type">
  {{ notification.text }}
</div>
</transition>
<span class="filter-count">共 {{ filteredEmployees.length }} 人</span>
    </div>

    <!-- 员工列表 -->
    <EmployeeList 
      :employees="filteredEmployees" 
      :emp-project-map="empProjectMap"
      :isDirector="authStore.isDirector"
      :currentUserId="authStore.user?.id"
      @edit="editEmployee"
      @delete="handleDelete"
    />

    <!-- 员工表单模态框 -->
    <EmployeeForm 
      :visible="formVisible"
      :isEdit="isEdit"
      :employeeData="currentEmployee"
      :professions="professions"
      :projectTypes="projectTypes"
      :loadStatuses="loadStatuses"
      @close="formVisible = false"
      @save="handleSave"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import { storeToRefs } from 'pinia'
import { useEmployeeStore } from '../stores/employees'
import api, { employeeAPI, configAPI } from '../api'
import EmployeeList from './EmployeeList.vue'
import EmployeeForm from './EmployeeForm.vue'

async function handleSyncEmployeeSkills() {
  try {
    const res = await api.post("/sync/employee-skills")
    alert("同步完成: 新建账号 " + res.data.users_created + " 个，新增技能矩阵 " + res.data.skills_created + " 个")
  } catch(e) {
    alert("同步失败: " + (e.response?.data?.detail || e.message))
  }
  location.reload()
}

const authStore = useAuthStore()

const employeeStore = useEmployeeStore()
const { employees } = storeToRefs(employeeStore)
const filterProfession = ref('')
const filterPosition = ref('')
const filterLoad = ref('')
const searchQuery = ref('')
const notification = ref({ show: false, text: "", type: "success" })

function showNotification(text, type, duration) {
  notification.value = { show: true, text: text, type: type || "success" }
  setTimeout(function() {
    notification.value.show = false
  }, duration || 4000)
}

const professions = ref([])
const projectTypes = ref([])
const loadStatuses = ref([])

const formVisible = ref(false)
const isEdit = ref(false)
const currentEmployee = ref({})
const empProjectMap = ref({})

const filteredEmployees = computed(() => {
  return employees.value.filter(emp => {
    if (filterProfession.value && emp.profession !== filterProfession.value) return false
    if (searchQuery.value && !emp.name.includes(searchQuery.value)) return false
    if (filterLoad.value && emp.current_load !== filterLoad.value) return false
    return true
  })
})


async function loadEmployeeProjectsMap() {
  try {
    const r = await api.get("/employee-project-map")
    empProjectMap.value = r.data
  } catch(e) {}
}

onMounted(async () => {
  await loadData()
})

async function loadData() {
  try {
    await employeeStore.loadEmployees()
    await loadEmployeeProjectsMap()
  } catch (err) {
    console.error('load employees error:', err)
  }
  try {
    const configRes = await configAPI.getConstants()
    professions.value = configRes.data.professions || []
    projectTypes.value = configRes.data.project_types || []
    loadStatuses.value = configRes.data.load_statuses || []
  } catch (err) {
    console.error('load config error:', err)
  }
}

function showAddForm() {
  isEdit.value = false
  currentEmployee.value = {}
  formVisible.value = true
}

function editEmployee(emp) {
  isEdit.value = true
  currentEmployee.value = { ...emp }
  formVisible.value = true
}

async function handleSave(formData) {
  try {
    if (isEdit.value) {
      const { username, password, ...updateData } = formData
      await employeeAPI.update(currentEmployee.value.id, updateData)
    } else {
      await employeeAPI.create(formData)
    }
    formVisible.value = false
    await employeeStore.loadEmployees()
  } catch (err) {
    showNotification("保存失败: " + (err.response?.data?.detail || "未知错误"), "error", 8000)
  }
}

async function handleDelete(id) {
  if (id === authStore.user?.id) {
    showNotification("不能删除自己的账号", "error", 5000)
    return
  }
  if (!confirm('确定删除该员工吗?')) return
  try {
    await employeeAPI.delete(id)
    await employeeStore.loadEmployees()
  } catch (err) {
    showNotification("删除失败", "error", 5000)
  }
}

async function handleClearAll() {
  if (!confirm('确定清空所有导入入的员工数据吗？此操作不可撤铺！')) return
  try {
    await employeeAPI.clearAll()
    showNotification('已清空所有员工数据', 'success')
    await loadData()
  } catch (err) {
    showNotification('清空失败：' + (err.response?.data?.detail || '未知错误'), 'error')
  }
}

// 下载模板
function downloadTemplate() {
  const token = localStorage.getItem('access_token')
  fetch('/api/employees/template/download', {
    headers: { 'Authorization': `Bearer ${token}` }
  }).then(res => res.blob()).then(blob => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = '人员信息导入模板.xlsx'
    a.click()
    URL.revokeObjectURL(url)
  }).catch(err => {
    alert('下载模板失败')
  })
}



// 导出数据
function exportData() {
  const token = localStorage.getItem('access_token')
  fetch('/api/employees/export', {
    headers: { 'Authorization': `Bearer ${token}` }
  }).then(res => res.blob()).then(blob => {
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    const date = new Date().toISOString().slice(0, 10)
    a.download = `人员技能矩阵_${date}.xlsx`
    a.click()
    URL.revokeObjectURL(url)
  }).catch(err => {
    alert('导出失败')
    console.error(err)
  })
}
</script>

<style scoped>
.employee-manager {
  margin-bottom: 20px;
}

.manager-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 12px;
  flex-wrap: wrap;
  gap: 10px;
}

.manager-header h3 {
  font-size: 16px;
  color: #1e293b;
  margin: 0;
}

.header-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.filter-bar {
  display: flex;
  gap: 10px;
  margin-bottom: 12px;
  flex-wrap: wrap;
  align-items: center;
}

.filter-bar .input {
  width: auto;
  min-width: 120px;
  padding: 8px 12px;
  border: 1px solid #d1d5db;
  border-radius: 6px;
  font-size: 13px;
  outline: none;
  background: white;
}

.filter-bar .input:focus {
  border-color: #1a73e8;
}

.filter-count {
  font-size: 13px;
  color: #64748b;
  margin-left: auto;
}

.btn {
  padding: 8px 14px;
  border: none;
  border-radius: 6px;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 500;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  white-space: nowrap;
}

.btn:hover {
  opacity: 0.85;
  transform: translateY(-1px);
}

.btn-primary {
  background: #1a73e8;
  color: white;
}

.btn-outline {
  background: white;
  color: #1a73e8;
  border: 1px solid #1a73e8;
}

.btn-outline:hover {
  background: #eff6ff;
}

.notification { padding: 10px 16px; border-radius: 8px; font-size: 13px; margin-bottom: 12px; white-space: pre-line; }
.notification-success { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }
.notification-error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.fade-enter-active, .fade-leave-active { transition: opacity 0.3s; }
.fade-enter-from, .fade-leave-to { opacity: 0; }
</style>
