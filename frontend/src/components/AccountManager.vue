<template>
  <div class="account-manager card fade-in">
    <h3 class="section-title">账号管理</h3>
    <div class="am-tabs">
      <button v-for="t in tabs" :key="t.key" class="am-tab" :class="{active:activeTab===t.key}" @click="activeTab=t.key">{{ t.label }}</button>
    </div>

    <div v-if="activeTab==='users'" class="am-panel">
      <div class="am-scroll" v-if="users.length">
        <table class="am-table">
          <thead><tr><th>ID</th><th>姓名</th><th>用户名</th><th>员工编号</th><th>专业</th><th>角色</th><th>状态</th></tr></thead>
          <tbody>
            <tr v-for="u in users" :key="u.id">
              <td>{{ u.id }}</td><td>{{ u.name }}</td><td>{{ u.username }}</td>
              <td>{{ u.employee_id || "-" }}</td><td>{{ u.profession || "-" }}</td>
              <td><select v-model="u.role" class="input input-sm" @change="updateRole(u)" :disabled="u.id===authStore.user?.id">
                <option value="director">所长</option><option value="deputy_director">副所长</option>
                <option value="member">成员</option>
              </select></td>
              <td><span class="badge" :class="u.is_on_leave?'badge-yellow':'badge-green'">{{ u.is_on_leave?"休假":"活跃" }}</span><button v-if="u.id!==authStore.user?.id" class="btn btn-sm btn-outline" @click="toggleLeave(u)" style="margin-left:4px">{{ u.is_on_leave?"活跃":"休假" }}</button></td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="empty-tip">加载中...</div>
    </div>


    <div v-if="activeTab==='profile'" class="am-panel">
      <div class="profile-basic-header" @click="showBasicInfo=!showBasicInfo">
        <h4 style="cursor:pointer;margin:0">📋 基本信息 {{ showBasicInfo ? '▲' : '▼' }}</h4>
      </div>
      <div v-if="showBasicInfo" class="profile-basic-grid">
        <div class="pf-item"><label>姓名</label><span>{{ profileData.name || '—' }}</span></div>
        <div class="pf-item"><label>工号</label><span>{{ profileData.employee_id || '—' }}</span></div>
        <div class="pf-item"><label>部门</label><span>{{ profileData.department || '—' }}</span></div>
        <div class="pf-item"><label>角色</label><span>{{ roleLabel(profileData.role) }}</span></div>
        <div class="pf-item"><label>专业方向</label><span>{{ profileData.profession || '—' }}</span></div>
        <div class="pf-item"><label>职称</label><span>{{ profileData.title || '—' }}</span></div>
        <div class="pf-item"><label>注册情况</label><span>{{ profileData.registration || '—' }}</span></div>
        <div class="pf-item"><label>负荷状态</label><span class="load-badge" :class="loadClass(profileData.current_load)">{{ profileData.current_load || '空闲' }}</span></div>
      </div>
      <div style="height:12px"></div>
      <h4 style="font-size:14px;color:#374151;margin:0 0 8px 0">修改信息</h4>
      <div class="profile-form">
        <div class="pf-row"><label>姓名</label><input v-model="profileForm.name" class="input" /><button class="btn btn-sm btn-outline" @click="submitChange('name')">申请修改</button></div>
        <div class="pf-row"><label>专业方向</label><select v-model="profileForm.profession" class="input"><option value="">请选择</option><option v-for="o in profileOptions.profession" :key="o" :value="o">{{ o }}</option></select><button class="btn btn-sm btn-outline" @click="submitChange('profession')">申请修改</button></div>
        <div class="pf-row"><label>职称情况</label><select v-model="profileForm.title" class="input"><option value="">请选择</option><option v-for="o in profileOptions.title" :key="o" :value="o">{{ o }}</option></select><button class="btn btn-sm btn-outline" @click="submitChange('title')">申请修改</button></div>
        <div class="pf-row"><label>注册情况</label><select v-model="profileForm.registration" class="input"><option value="">请选择</option><option v-for="o in profileOptions.registration" :key="o" :value="o">{{ o }}</option></select><button class="btn btn-sm btn-outline" @click="submitChange('registration')">申请修改</button></div>
        <div class="pf-row"><label>备注</label><input v-model="profileForm.remark" class="input" /><button class="btn btn-sm btn-outline" @click="submitChange('remark')">申请修改</button></div>
      </div>
      <div style="height:16px;border-top:1px solid #e2e8f0;margin:12px 0"></div>
      <h4 style="font-size:14px;color:#374151;margin:0 0 8px 0">账号安全</h4>
      <div class="profile-form">
        <div class="pf-row"><label>当前用户名</label><span style="padding:6px 0;color:#475569">{{ profileData.username || '—' }}</span></div>
        <div class="pf-row"><label>新用户名</label><input v-model="accountForm.newUsername" class="input" placeholder="留空不修改" /></div>
        <div class="pf-row"><label>当前密码</label><input v-model="accountForm.currentPassword" type="password" class="input" placeholder="请输入当前密码" /></div>
        <div class="pf-row"><label>新密码</label><input v-model="accountForm.newPassword" type="password" class="input" placeholder="留空不修改" /></div>
        <div class="pf-row"><label>确认密码</label><input v-model="accountForm.confirmPassword" type="password" class="input" placeholder="再次输入新密码" /></div>
        <div class="pf-row">
          <button class="btn btn-primary btn-sm" @click="updateAccount" :disabled="!accountForm.currentPassword">保存修改</button>
          <span v-if="accountMsg" style="font-size:12px;color:#059669;margin-left:8px">{{ accountMsg }}</span>
          <span v-if="accountErr" style="font-size:12px;color:#dc2626;margin-left:8px">{{ accountErr }}</span>
        </div>
      </div>
      <div v-if="myRequests.length" class="am-scroll" style="margin-top:16px">
        <h4 style="font-size:13px;color:#374151;margin:0 0 8px 0">我的申请历史</h4>
        <table class="am-table">
          <thead><tr><th>字段</th><th>旧值</th><th>新值</th><th>状态</th><th>审批人</th></tr></thead>
          <tbody>
            <tr v-for="r in myRequests" :key="r.id">
              <td>{{ fieldLabel(r.field_name) }}</td><td>{{ r.old_value || "-" }}</td><td>{{ r.new_value }}</td>
              <td><span class="badge" :class="r.status==='pending'?'badge-yellow':r.status==='approved'?'badge-green':'badge-red'">{{ r.status==='pending'?'待审批':r.status==='approved'?'已通过':'已拒绝' }}</span></td>
              <td>{{ r.reviewer_name || "-" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch, onMounted } from "vue"
import { useAuthStore } from "../stores/auth"
import { adminAPI, changeRequestAPI, userAPI } from "../api"
import api from "../api"

const authStore = useAuthStore()
const isDirector = computed(() => authStore.isDirector)
const isDeputy = computed(() => authStore.isDeputyDirector)
const activeTab = ref("users")
const users = ref([])
const myRequests = ref([])
const profileData = ref({})
const showBasicInfo = ref(true)

const tabs = ref([])
watch([isDirector, isDeputy], () => {
  const t = []
  if (isDirector.value) t.push({ key: "users", label: "用户管理" })
  t.push({ key: "profile", label: "我的信息" })
  tabs.value = t
  if (!t.find(x => x.key === activeTab.value)) activeTab.value = t[0]?.key || "profile"
}, { immediate: true })

const profileForm = ref({ name: "", profession: "", title: "", registration: "", remark: "" })
const profileOptions = ref({ profession: [], title: [], registration: [] })
const accountForm = ref({ newUsername: "", currentPassword: "", newPassword: "", confirmPassword: "" })
const accountMsg = ref("")
const accountErr = ref("")

onMounted(async () => { await loadAll() })

async function loadAll() {
  try {
    const [profileRes, optRes] = await Promise.all([userAPI.getMe(), api.get("/config/profile-options").catch(() => ({ data: { profession: [], title: [], registration: [] }}))])
    profileOptions.value = optRes.data || { profession: [], title: [], registration: [] }
    profileData.value = profileRes.data
    if (isDirector.value) {
      const r = await adminAPI.getUsers()
      users.value = r.data
    }
    const r2 = await changeRequestAPI.list()
    myRequests.value = r2.data.filter(x => x.user_id === authStore.user?.id)
    if (authStore.user) {
      profileForm.value = {
        name: authStore.user.name || "",
        profession: profileData.value.profession || "",
        title: profileData.value.title || "",
        registration: profileData.value.registration || "",
        remark: profileData.value.remark || ""
      }
    }
  } catch(e) { console.error(e) }
}

async function updateRole(u) {
  try { await adminAPI.updateUser(u.id, { role: u.role }) } catch(e) { alert("更新失败") }
}

async function toggleLeave(u) {
  const action = u.is_on_leave ? "恢复该员工为活跃状态" : "标记该员工为休假状态"
  if (!confirm("确定" + action + "吗？")) return
  try {
    await adminAPI.updateUser(u.id, { is_on_leave: !u.is_on_leave })
    await loadAll()
  } catch(e) { alert("操作失败") }
}

async function submitChange(field) {
  try {
    await changeRequestAPI.create({ field_name: field, new_value: profileForm.value[field] || "" })
    alert("已提交修改申请，请等待审批")
    await loadAll()
  } catch(e) { alert("提交失败: " + (e.response?.data?.detail || e.message)) }
}

function roleLabel(role) {
  const map = { director: "所长", deputy_director: "副所长", project_leader: "项目负责人", member: "成员" }
  return map[role] || role || "—"
}

function fieldLabel(field) {
  const map = { name: "姓名", profession: "专业方向", title: "职称", registration: "注册情况", remark: "备注" }
  return map[field] || field
}

function loadClass(load) {
  if (!load || load === "空闲") return "load-green"
  if (load === "轻度") return "load-blue"
  if (load === "中度") return "load-yellow"
  if (load === "饱满" || load === "超负荷") return "load-red"
  return "load-green"
}

async function updateAccount() {
  accountMsg.value = ""
  accountErr.value = ""
  if (!accountForm.value.currentPassword) { accountErr.value = "请输入当前密码"; return }
  if (accountForm.value.newPassword && accountForm.value.newPassword !== accountForm.value.confirmPassword) {
    accountErr.value = "两次输入的新密码不一致"; return
  }
  try {
    const r = await api.put("/user/update-account", {
      current_password: accountForm.value.currentPassword,
      new_username: accountForm.value.newUsername || undefined,
      new_password: accountForm.value.newPassword || undefined
    })
    accountForm.value = { newUsername: "", currentPassword: "", newPassword: "", confirmPassword: "" }
    accountMsg.value = r.data?.message || "修改成功"
    await loadAll()
  } catch(e) {
    accountErr.value = e.response?.data?.detail || "修改失败"
  }
}
</script>

<style scoped>
.account-manager { margin-bottom: 20px; padding: 20px; }
.section-title { font-size: 16px; color: #1e293b; margin: 0 0 12px 0; }
.am-tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; }
.am-tab { padding: 8px 16px; border: none; background: none; font-size: 13px; color: #64748b; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.am-tab.active { color: #1a73e8; border-bottom-color: #1a73e8; font-weight: 500; }
.am-scroll { max-height: 420px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; }
.am-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.am-table th, .am-table td { padding: 6px 8px; border: 1px solid #e2e8f0; text-align: left; }
.am-table th { background: #f8fafc; font-weight: 600; color: #475569; white-space: nowrap; }
.input-sm { width: 120px !important; padding: 4px 6px !important; font-size: 11px !important; }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.badge-green { background: #dcfce7; color: #166534; }
.badge-red { background: #fef2f2; color: #991b1b; }
.badge-yellow { background: #fef9c3; color: #854d0e; }
.profile-form { display: flex; flex-direction: column; gap: 10px; }
.pf-row { display: flex; align-items: center; gap: 10px; }
.pf-row label { font-size: 13px; color: #374151; width: 80px; flex-shrink: 0; }
.pf-row .input { flex: 1; }
.pf-row .btn { flex-shrink: 0; }
.profile-basic-header { padding: 8px 0; cursor: pointer; }
.profile-basic-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 8px; padding: 8px 0; border-bottom: 1px solid #e2e8f0; margin-bottom: 12px; }
.pf-item { display: flex; gap: 6px; align-items: center; font-size: 13px; }
.pf-item label { color: #64748b; width: 70px; flex-shrink: 0; }
.pf-item span { color: #1e293b; font-weight: 500; }
.load-badge { padding: 2px 8px; border-radius: 4px; font-size: 11px; }
.load-green { background: #dcfce7; color: #166534; }
.load-blue { background: #dbeafe; color: #1e40af; }
.load-yellow { background: #fef9c3; color: #854d0e; }
.load-red { background: #fee2e2; color: #991b1b; }
.empty-tip { color: #94a3b8; text-align: center; padding: 30px; font-size: 14px; }
.btn-sm { padding: 4px 10px; font-size: 11px; }
.btn-primary { background: #1a73e8; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-danger { background: #dc2626; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-outline { background: white; color: #1a73e8; border: 1px solid #1a73e8; border-radius: 4px; cursor: pointer; }
.btn-outline:hover { background: #eff6ff; }
@media (max-width: 640px) { .profile-basic-grid { grid-template-columns: 1fr; } .am-table { font-size: 11px; display: block; overflow-x: auto; } }
</style>
