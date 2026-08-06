<template>
  <div class="knowledge-base card fade-in">
    <div v-if="!activeLib" class="kb-entry">
      <h3 class="section-title">库管理</h3>
      <div class="entry-cards">
        <div class="entry-card" @click="activeLib='employee'">
          <span class="entry-icon">&#x1F464;</span>
          <span class="entry-title">人员库</span>
          <span class="entry-desc">员工信息管理、导入导出、账户同步</span>
        </div>
        <div class="entry-card" @click="activeLib='history'">
          <span class="entry-icon">&#x1F4DA;</span>
          <span class="entry-title">项目库</span>
          <span class="entry-desc">历史工作量统计、项目记录管理</span>
        </div>
        <div class="entry-card" @click="activeLib='active'">
          <span class="entry-icon">&#x1F4CB;</span>
          <span class="entry-title">正在进行的项目</span>
          <span class="entry-desc">当前进行中的项目列表与状态</span>
        </div>
      </div>
    </div>
    <div v-if="activeLib==='employee'" class="kb-panel">
      <div class="kb-panel-header">
        <button class="btn btn-sm btn-outline" @click="activeLib=null">&larr; 返回</button>
        <span class="panel-title">人员库</span>
        <div class="kb-actions">
          <button class="btn btn-sm btn-outline" @click="downloadEmpTemplate">下载模板</button>
          <label class="btn btn-sm btn-outline import-btn">导入Excel<input type="file" accept=".xlsx" @change="handleEmpImport" hidden /></label>
        </div>
      </div>
      <div v-if="empImportResult" class="kb-import-result" :class="'result-' + (empImportResult.type || 'info')"><pre>{{ empImportResult.msg }}</pre></div>
      <div v-if="employees.length" class="kb-list">
        <div v-for="emp in employees" :key="emp.id" class="kb-item">
          <div class="kb-item-header"><strong>{{ emp.name }}</strong><span class="badge badge-blue">{{ emp.employee_id }}</span></div>
          <div class="kb-item-body"><span>专业：{{ emp.profession || "-" }}</span><span>负荷：{{ emp.current_load || "-" }}</span></div>
        </div>
      </div>
      <div v-else class="empty-tip">暂无数据，请导入Excel文件</div>
    </div>
    <div v-if="activeLib==='history'" class="kb-panel">
      <div class="kb-panel-header">
        <button class="btn btn-sm btn-outline" @click="activeLib=null">&larr; 返回</button>
        <span class="panel-title">项目库</span>
        <div class="kb-actions">
          <input v-model="wlSearchQuery" class="input" placeholder="搜索项目..." style="width:150px;font-size:12px" />
          <button class="btn btn-sm btn-outline" @click="downloadWlTemplate">导出模板</button><button class="btn btn-sm btn-outline" @click="exportWlData">导出数据</button>
<label class="btn btn-sm btn-outline import-btn">导入Excel<input type="file" accept=".xlsx" @change="handleWlImport" hidden /></label>
          <button class="btn btn-sm btn-outline" @click="handleWlDedup">去重</button>
          <button class="btn btn-sm btn-danger" @click="handleWlClearAll">清空</button>
        </div>
      </div>
      <div v-if="wlImportResult" class="kb-import-result" :class="'result-' + (wlImportResult.type || 'info')"><pre>{{ wlImportResult.msg }}</pre></div>
      <div class="wl-scroll" v-if="filteredWorkloads.length">
      <table class="kb-table">
        <thead><tr><th style="width:28px"></th><th>项目编号</th><th>项目名称</th><th>类型</th><th>计划工天</th><th>阶段</th><th>年份</th><th>操作</th></tr></thead>
        <tbody>
          <template v-for="w in filteredWorkloads" :key="w.id">
            <tr class="wl-row" @click="toggleWlExpand(w.id)">
              <td><span class="expand-icon">{{ expandedWl[w.id] ? "&#x25BC;" : "&#x25B6;" }}</span></td>
              <td>{{ w.project_code || "-" }}</td><td>{{ w.project_name || "-" }}</td>
              <td><span class="badge-blue">{{ w.project_type || "-" }}</span></td>
              <td>{{ w.planned_work_days !== undefined && w.planned_work_days !== null ? w.planned_work_days : w.calculated_work_days || "-" }}</td><td>{{ w.stage || "-" }}</td><td>{{ w.year || "-" }}</td>
              <td><button class="btn btn-sm btn-danger" @click.stop="handleWlDelete(w.id)">删除</button></td>
            </tr>
            <tr v-if="expandedWl[w.id]" class="wl-detail-row">
              <td colspan="8" style="padding:10px 14px;background:#f8fafc">
                <div class="wl-detail-grid">
                  <div><span class="dl">项目编号</span><span class="dv">{{ w.project_code || "-" }}</span></div>
                  <div><span class="dl">项目类型</span><span class="dv">{{ w.project_type || "-" }}</span></div>
                  <div><span class="dl">规模</span><span class="dv">{{ w.scale || "-" }}</span></div>
                  <div><span class="dl">阶段</span><span class="dv">{{ w.stage || "-" }}</span></div>
                  <div><span class="dl">开始日期</span><span class="dv">{{ w.start_date || "-" }}</span></div>
                  <div><span class="dl">预计结束</span><span class="dv">{{ w.planned_end_date || "-" }}</span></div>
                  <div><span class="dl">计划工天</span><span class="dv">{{ w.planned_work_days !== undefined && w.planned_work_days !== null ? w.planned_work_days : w.calculated_work_days || "-" }}</span></div>
                  <div><span class="dl">项目负责人</span><span class="dv">{{ w.leader_names || w.overall_lead || "-" }}</span></div>
                  <div><span class="dl">设计</span><span class="dv">{{ w.design_names || "-" }}</span></div>
                  <div><span class="dl">复核</span><span class="dv">{{ w.review_names || "-" }}</span></div>
                  <div><span class="dl">专业负责人</span><span class="dv">{{ w.prolead_names || "-" }}</span></div>
                  <div><span class="dl">院审</span><span class="dv">{{ w.yuan_names || "-" }}</span></div>
                  <div><span class="dl">总体审核</span><span class="dv">{{ w.total_names || "-" }}</span></div>
                  <div><span class="dl">集团审核</span><span class="dv">{{ w.group_names || "-" }}</span></div>
                </div>
              </td>
            </tr>
          </template>
        </tbody>
      </table>
      </div>
      <div v-else class="empty-tip">暂无数据</div>
    </div>
    <div v-if="activeLib==='active'" class="kb-panel">
      <div class="kb-panel-header">
        <button class="btn btn-sm btn-outline" @click="activeLib=null">&larr; 返回</button>
        <span class="panel-title">正在进行的项目</span>
      </div>
      <div v-if="activeProjects.length" class="kb-list">
        <div v-for="p in activeProjects" :key="p.id" class="kb-item">
          <div class="kb-item-header">
            <strong>{{ p.project_name }}</strong>
            <span class="badge" :class="'badge-' + p.status">{{ statusLabel(p.status) }}</span>
          </div>
          <div class="kb-item-body">
            <span>类型：{{ p.project_type }}</span>
            <span>面积：{{ p.area }}&#x33A1;</span>
            <span>计划工天：{{ calcPlannedWorkdays(p) }}</span>
            <span v-if="p.memberCount">成员：{{ p.memberCount }}人</span>
          </div>
        </div>
      </div>
      <div v-else class="empty-tip">暂无进行中的项目</div>
    </div>
  </div>
</template>


<script setup>
import { ref, computed, onMounted } from "vue"
import { useEmployeeStore } from "../stores/employees"
import { storeToRefs } from "pinia"
import api from "../api"

const activeLib = ref(null)
const employeeStore = useEmployeeStore()
const { employees } = storeToRefs(employeeStore)
const workloads = ref([])
const activeProjects = ref([])

function calcPlannedWorkdays(p) {
  var stage = p.stage || p.current_stage || "方案设计"
  var type = p.project_type
  var ratios = type === "大铁"
    ? { "方案设计": 0.02, "初步设计": 0.353, "施工图": 0.55, "施工配合": 0.077 }
    : { "方案设计": 0.12, "初步设计": 0.303, "施工图": 0.50, "施工配合": 0.077 }
  var b = ratios[stage] || 0
  return Math.round((p.planned_man_days || 0) * b)
}
const wlSearchQuery = ref("")
const expandedWl = ref({})

const filteredWorkloads = computed(() => {
  const q = wlSearchQuery.value.toLowerCase()
  if (!q) return workloads.value
  return workloads.value.filter(w => 
    (w.project_name && w.project_name.toLowerCase().includes(q)) ||
    (w.project_code && w.project_code.toLowerCase().includes(q))
  )
})

function toggleWlExpand(id) {
  expandedWl.value[id] = !expandedWl.value[id]
}

function statusLabel(s) {
  const m = { planning:"方案", design:"设计", construction:"施工", completed:"已完成", closed:"已结项" }
  return m[s] || s
}

const empImportResult = ref(null)
const wlImportResult = ref(null)
const tk = localStorage.getItem("access_token") || ""
const authH = { Authorization: "Bearer " + tk }

onMounted(async () => {
  try {
    try { await api.post("/projects/sync-library") } catch(e) { console.error("sync library error:", e) }
    const [wlRes, projRes] = await Promise.all([
      api.get("/workload-records"),
      api.get("/projects")
    ])
    const allProjects = projRes.data || []
    const projByCode = {}
    const projByName = {}
    for (let p of allProjects) {
      if (p.project_code && p.project_code.trim()) projByCode[p.project_code.trim()] = p
      if (p.project_name && p.project_name.trim()) projByName[p.project_name.trim()] = p
    }
    const memberResults = await Promise.allSettled(allProjects.map(p => api.get("/projects/" + p.id + "/members")))
    const membersByProject = {}
    memberResults.forEach((res, idx) => {
      if (res.status === "fulfilled") membersByProject[allProjects[idx].id] = res.value.data || []
    })
    function memberNames(members, roles) {
      const names = []
      const seen = {}
      for (const m of members || []) {
        if (roles.includes(m.role) && m.employee_name && !seen[m.employee_name]) {
          seen[m.employee_name] = 1
          names.push(m.employee_name)
        }
      }
      return names.join("、")
    }
    workloads.value = (wlRes.data || []).map(w => {
      const p = (w.project_code && projByCode[w.project_code.trim()]) || (w.project_name && projByName[w.project_name.trim()])
      const members = membersByProject[p ? p.id : null] || []
      return {
        ...w,
        planned_work_days: p && p.planned_man_days != null ? p.planned_man_days : undefined,
        project_type: (p && p.project_type) || w.project_type,
        stage: (p && (p.current_stage || p.stage)) || w.stage,
        project_name: (p && p.project_name) || w.project_name,
        project_code: w.project_code,
        start_date: p && p.start_date ? p.start_date : "",
        planned_end_date: p && p.planned_end_date ? p.planned_end_date : "",
        leader_names: memberNames(members, ["项目负责人"]),
        design_names: memberNames(members, ["设计", "设计阶段"]),
        review_names: memberNames(members, ["复核", "复核阶段"]),
        prolead_names: memberNames(members, ["专业负责人", "专业审核"]),
        yuan_names: memberNames(members, ["院审"]),
        total_names: memberNames(members, ["总体审核"]),
        group_names: memberNames(members, ["集团审核"])
      }
    })
    activeProjects.value = allProjects.filter(p => 
      p.status !== "completed" && p.status !== "closed"
    )
    await employeeStore.loadEmployees()
    for (let p of activeProjects.value) {
      p.memberCount = (membersByProject[p.id] || []).length
    }
  } catch (err) { console.error("load kb error:", err) }
})

async function handleEmpImport(ev) {
  const file = ev.target.files[0]
  if (!file) return
  const fd = new FormData(); fd.append("file", file)
  try {
    const res = await fetch("http://localhost:8000/api/employees/import", { method: "POST", headers: authH, body: fd })
    const r = await res.json()
    let m = "导入完成！\n新增: " + r.created + " 条"
    if (r.updated > 0) m += "\n更新: " + r.updated + " 条"
    if (r.failed > 0) m += "\n失败: " + r.failed + " 条"
    if (r.errors && r.errors.length) m += "\n\n错误: " + r.errors.slice(0,3).join("\n")
    empImportResult.value = { type: "success", msg: m }
    await employeeStore.loadEmployees()
  } catch (e) { empImportResult.value = { type: "error", msg: "导入失败，请检查文件格式" } }
  ev.target.value = ""
}

async function downloadEmpTemplate() {
  try {
    const res = await fetch("http://localhost:8000/api/employees/template/download", { headers: authH })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url; a.download = "人员信息导入模板.xlsx"; a.click()
    URL.revokeObjectURL(url)
  } catch(e) { console.error(e) }
}

async function loadWorkloads() {
  try { const r = await api.get("/workload-records"); workloads.value = r.data }
  catch(e) { console.error(e) }
}

async function handleWlDelete(id) {
  if (!confirm("确定删除该记录吗?")) return
  try { await api.delete("/workload-records/" + id); await loadWorkloads() }
  catch(e) { alert("删除失败") }
}

async function handleWlDedup() {
  try {
    const r = await api.post("/workload-records/dedup")
    wlImportResult.value = { type: "success", msg: "去重完成！删除 " + (r.data.deleted || 0) + " 条重复数据" }
    await loadWorkloads()
  } catch(e) { wlImportResult.value = { type: "error", msg: "去重失败" } }
}

async function handleWlClearAll() {
  if (!confirm("确定清空所有工作量记录吗？")) return
  try {
    await api.delete("/workload-records/all")
    workloads.value = []
    wlImportResult.value = { type: "success", msg: "已清空所有记录" }
  } catch(e) { wlImportResult.value = { type: "error", msg: "清空失败" } }
}

async function downloadWlTemplate() {
  try {
    const res = await fetch("http://localhost:8000/api/workload-records/template/download", { headers: authH })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url; a.download = "项目库导入模板.xlsx"; a.click()
    URL.revokeObjectURL(url)
  } catch(e) { console.error(e) }
}

async function exportWlData() {
  try {
    const res = await fetch("http://localhost:8000/api/workload-records/export", { headers: authH })
    const blob = await res.blob()
    const url = URL.createObjectURL(blob)
    const a = document.createElement("a")
    a.href = url; a.download = "项目库数据.xlsx"; a.click()
    URL.revokeObjectURL(url)
  } catch(e) { console.error(e) }
}

async function handleWlImport(ev) {
  const file = ev.target.files[0]
  if (!file) return
  const fd = new FormData(); fd.append("file", file)
  try {
    const res = await fetch("http://localhost:8000/api/workload-records/import", { method: "POST", headers: authH, body: fd })
    const r = await res.json()
    let m = "导入完成！\n新增: " + (r.created || 0) + " 条"
    wlImportResult.value = { type: "success", msg: m }
    await loadWorkloads()
  } catch (e) { wlImportResult.value = { type: "error", msg: "导入失败，请检查文件格式" } }
  ev.target.value = ""
}
</script>

<style scoped>
.knowledge-base { margin-bottom: 20px; padding: 20px; }
.section-title { font-size: 16px; color: #1e293b; margin: 0 0 20px 0; }
.entry-cards { display: grid; grid-template-columns: repeat(3, 1fr); gap: 16px; margin-top: 8px; }
.entry-card { display: flex; flex-direction: column; align-items: center; gap: 8px; padding: 32px 20px; background: white; border: 1px solid #e2e8f0; border-radius: 12px; cursor: pointer; transition: all 0.2s; }
.entry-card:hover { border-color: #1a73e8; box-shadow: 0 4px 12px rgba(26,115,232,0.1); transform: translateY(-2px); }
.entry-icon { font-size: 36px; }
.entry-title { font-size: 16px; font-weight: 600; color: #1e293b; }
.entry-desc { font-size: 12px; color: #64748b; text-align: center; }
.kb-panel-header { display: flex; align-items: center; gap: 12px; margin-bottom: 12px; }
.panel-title { font-weight: 500; font-size: 14px; color: #374151; margin-right: auto; }
.kb-actions { display: flex; gap: 6px; margin-left: auto; }
.import-btn { cursor: pointer; }
.kb-import-result { padding: 10px 14px; border-radius: 8px; margin-bottom: 12px; font-size: 12px; white-space: pre-line; }
.result-success { background: #ecfdf5; color: #065f46; border: 1px solid #a7f3d0; }
.result-error { background: #fef2f2; color: #991b1b; border: 1px solid #fecaca; }
.result-info { background: #eff6ff; color: #1e40af; border: 1px solid #bfdbfe; }
.kb-list { display: grid; gap: 8px; max-height: 420px; overflow-y: auto; }
.kb-item { padding: 12px; background: #f8fafc; border-radius: 8px; font-size: 13px; }
.kb-item-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.kb-item-body { color: #64748b; display: flex; gap: 16px; font-size: 12px; }
.empty-tip { color: #94a3b8; text-align: center; padding: 30px; font-size: 14px; }
.btn-sm { padding: 6px 12px; font-size: 12px; }
.btn-outline { background: white; color: #1a73e8; border: 1px solid #1a73e8; border-radius: 6px; cursor: pointer; }
.btn-outline:hover { background: #eff6ff; }
.badge-blue { background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.badge { padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.badge-planning { background: #fef3c7; color: #92400e; }
.badge-design { background: #dbeafe; color: #1e40af; }
.badge-construction { background: #ede9fe; color: #5b21b6; }
.wl-scroll { max-height: 420px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; }
.wl-scroll .kb-table { border: none; }
.wl-row { cursor: pointer; }
.wl-row:hover { background: #f1f5f9; }
.expand-icon { font-size: 10px; color: #94a3b8; cursor: pointer; }
.wl-detail-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 6px 20px; font-size: 12px; }
.wl-detail-grid .dl { color: #64748b; margin-right: 6px; }
.wl-detail-grid .dv { color: #1e293b; font-weight: 500; }
.wl-edit-grid { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 8px; font-size: 12px; }
.wl-edit-grid label { display: flex; flex-direction: column; gap: 2px; color: #64748b; }
</style>
