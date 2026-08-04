<template>
  <div class="audit-manager card fade-in">
    <h3 class="section-title">审核管理</h3>
    <div class="am-tabs">
      <button v-for="t in tabs" :key="t.key" class="am-tab" :class="{active:activeTab===t.key}" @click="activeTab=t.key; loadTab(t.key)">{{ t.label }}</button>
    </div>

    <div v-if="activeTab==='project'" class="am-panel">
      <div class="am-panel-head">项目建立申请</div>
      <div class="am-scroll" v-if="projectRequests.length">
        <table class="am-table">
          <thead><tr><th>项目名称</th><th>类型</th><th>阶段</th><th>规模</th><th>人天</th><th>起止</th><th>申请人</th><th>时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="r in projectRequests" :key="r.id">
              <td>{{ r.project_name }}</td><td>{{ r.project_type }}</td><td>{{ r.stage }}</td>
              <td>{{ r.area }}㎡</td><td>{{ r.planned_man_days }}</td>
              <td>{{ r.start_date || "—" }} ~ {{ r.planned_end_date || "—" }}</td>
              <td>{{ r.requester_name }}</td>
              <td>{{ (r.created_at || "").slice(0,10) }}</td>
              <td>
                <button class="btn btn-sm btn-success" @click="approveProject(r.id)" style="margin-right:4px">批准</button>
                <button class="btn btn-sm btn-danger" @click="rejectProject(r.id)">拒绝</button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="am-empty">暂无待审批的项目建立申请</div>
    </div>

    <div v-if="activeTab==='workday'" class="am-panel">
      <div class="am-panel-head">工天修改申请</div>
      <div class="am-scroll" v-if="workdayRequests.length">
        <table class="am-table">
          <thead><tr><th>申请人</th><th>项目</th><th>基本工天(A)</th><th>等级系数(B)</th><th>复杂程度(C)</th><th>质量系数(D)</th><th>进展系数(E)</th><th>修正系数(F)</th><th>状态</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="r in workdayRequests" :key="r.id">
              <td>{{ r.user_name }}</td><td>{{ r.project_name }}</td>
              <td>{{ r.A }}</td><td>{{ r.B }}</td><td>{{ r.C }}</td><td>{{ r.D }}</td><td>{{ r.E }}</td><td>{{ r.F }}</td>
              <td><span class="badge" :class="r.status==='pending'?'badge-yellow':r.status==='approved'?'badge-green':'badge-red'">{{ {pending:"待审批",approved:"已通过",rejected:"已拒绝"}[r.status] || r.status }}</span></td>
              <td v-if="r.status==='pending'">
                <button class="btn btn-sm btn-success" @click="approveWorkday(r.id)" style="margin-right:4px">批准</button>
                <button class="btn btn-sm btn-danger" @click="rejectWorkday(r.id)">拒绝</button>
              </td>
              <td v-else>{{ r.reviewer_name || "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="am-empty">暂无待审批的工天修改申请</div>
    </div>

    <div v-if="activeTab==='profile'" class="am-panel">
      <div class="am-panel-head">个人信息修改申请</div>
      <div class="am-scroll" v-if="changeRequests.length">
        <table class="am-table">
          <thead><tr><th>申请人</th><th>字段</th><th>旧值</th><th>新值</th><th>状态</th><th>时间</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="r in changeRequests" :key="r.id">
              <td>{{ r.user_name }}</td><td>{{ fieldLabel(r.field_name) }}</td>
              <td>{{ r.old_value || "—" }}</td><td>{{ r.new_value }}</td>
              <td><span class="badge" :class="r.status==='pending'?'badge-yellow':r.status==='approved'?'badge-green':'badge-red'">{{ {pending:"待审批",approved:"已通过",rejected:"已拒绝"}[r.status] || r.status }}</span></td>
              <td>{{ (r.created_at || "").slice(0,10) }}</td>
              <td v-if="r.status==='pending'">
                <button class="btn btn-sm btn-success" @click="approveChange(r.id)" style="margin-right:4px">通过</button>
                <button class="btn btn-sm btn-danger" @click="rejectChange(r.id)">拒绝</button>
              </td>
              <td v-else>{{ r.reviewer_name || "—" }}</td>
            </tr>
          </tbody>
        </table>
      </div>
      <div v-else class="am-empty">暂无待审批的信息修改申请</div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from "vue"
import { useAuthStore } from "../stores/auth"
import { changeRequestAPI } from "../api"
import api from "../api"

const authStore = useAuthStore()
const activeTab = ref("project")

const tabs = [
  { key: "project", label: "项目建立" },
  { key: "workday", label: "工天修改" },
  { key: "profile", label: "个人信息" },
]

const projectRequests = ref([])
const workdayRequests = ref([])
const changeRequests = ref([])

onMounted(() => { loadTab("project") })

function loadTab(key) {
  if (key === "project") loadProjectRequests()
  if (key === "workday") loadWorkdayRequests()
  if (key === "profile") loadChangeRequests()
}

// === 项目建立 ===
async function loadProjectRequests() {
  try { projectRequests.value = (await api.get("/project-requests?status=pending")).data } catch(e) {}
}
async function approveProject(id) {
  try {
    await api.put("/project-requests/" + id + "/approve")
    await loadProjectRequests()
  } catch(e) { alert("批准失败") }
}
async function rejectProject(id) {
  try {
    await api.put("/project-requests/" + id + "/reject")
    await loadProjectRequests()
  } catch(e) { alert("拒绝失败") }
}

// === 工天修改 ===
async function loadWorkdayRequests() {
  try { workdayRequests.value = (await api.get("/performance/workday-requests")).data } catch(e) {}
}
async function approveWorkday(id) {
  try {
    await api.put("/performance/workday-requests/" + id + "/approve", { comment: "" })
    await loadWorkdayRequests()
  } catch(e) { alert("批准失败") }
}
async function rejectWorkday(id) {
  var c = prompt("说明拒绝原因：")
  if (c === null) return
  try {
    await api.put("/performance/workday-requests/" + id + "/reject", { comment: c || "" })
    await loadWorkdayRequests()
  } catch(e) { alert("拒绝失败") }
}

// === 个人信息 ===
async function loadChangeRequests() {
  try { changeRequests.value = (await changeRequestAPI.list("pending")).data } catch(e) {}
}
async function approveChange(id) {
  try {
    await changeRequestAPI.review(id, { status: "approved", comment: "" })
    await loadChangeRequests()
  } catch(e) { alert("操作失败") }
}
async function rejectChange(id) {
  try {
    await changeRequestAPI.review(id, { status: "rejected", comment: "" })
    await loadChangeRequests()
  } catch(e) { alert("操作失败") }
}

function fieldLabel(field) {
  const map = { name: "姓名", profession: "专业方向", title: "职称", registration: "注册情况", remark: "备注" }
  return map[field] || field
}
</script>

<style scoped>
.audit-manager { padding: 20px; margin-bottom: 20px; }
.section-title { font-size: 16px; color: #1e293b; margin: 0 0 12px 0; }
.am-tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; }
.am-tab { padding: 8px 16px; border: none; background: none; font-size: 13px; color: #64748b; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.am-tab.active { color: #1a73e8; border-bottom-color: #1a73e8; font-weight: 500; }
.am-panel-head { margin-bottom: 12px; font-size: 14px; color: #334155; font-weight: 500; }
.am-scroll { max-height: 480px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; }
.am-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.am-table th, .am-table td { padding: 6px 8px; border: 1px solid #e2e8f0; text-align: left; }
.am-table th { background: #f8fafc; font-weight: 600; color: #475569; white-space: nowrap; }
.am-empty { color: #94a3b8; text-align: center; padding: 30px; font-size: 14px; }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.badge-green { background: #dcfce7; color: #166534; }
.badge-red { background: #fef2f2; color: #991b1b; }
.badge-yellow { background: #fef9c3; color: #854d0e; }
.btn-sm { padding: 4px 10px; font-size: 11px; }
.btn-success { background: #16a34a; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-danger { background: #dc2626; color: white; border: none; border-radius: 4px; cursor: pointer; }
.btn-success:hover { background: #15803d; }
.btn-danger:hover { background: #b91c1c; }
@media (max-width: 640px) { .am-table { font-size: 11px; display: block; overflow-x: auto; } }
</style>
