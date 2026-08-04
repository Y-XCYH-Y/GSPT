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
        <thead><tr><th style="width:28px"></th><th>项目编号</th><th>项目名称</th><th>类型</th><th>计算工天</th><th>阶段</th><th>年份</th><th>操作</th></tr></thead>
        <tbody>
          <template v-for="w in filteredWorkloads" :key="w.id">
            <tr v-if="editingWlId !== w.id" class="wl-row" @click="toggleWlExpand(w.id)">
              <td><span class="expand-icon">{{ expandedWl[w.id] ? "&#x25BC;" : "&#x25B6;" }}</span></td>
              <td>{{ w.project_code || "-" }}</td><td>{{ w.project_name || "-" }}</td>
              <td><span class="badge-blue">{{ w.project_type || "-" }}</span></td>
              <td>{{ w.calculated_work_days || "-" }}</td><td>{{ w.stage || "-" }}</td><td>{{ w.year || "-" }}</td>
              <td><button class="btn btn-sm btn-outline" @click.stop="startWlEdit(w)">编辑</button><button class="btn btn-sm btn-danger" @click.stop="handleWlDelete(w.id)" style="margin-left:4px">删除</button></td>
            </tr>
            <tr v-if="expandedWl[w.id] && editingWlId !== w.id" class="wl-detail-row">
              <td colspan="8" style="padding:10px 14px;background:#f8fafc">
                <div class="wl-detail-grid">
                  <div><span class="dl">规模</span><span class="dv">{{ w.scale || "-" }}</span></div>
                  <div><span class="dl">总体/专册</span><span class="dv">{{ w.overall_lead || "-" }}</span></div>
                  <div><span class="dl">建筑专册</span><span class="dv">{{ w.architecture_lead || "-" }}</span></div>
                  <div><span class="dl">参与人员</span><span class="dv">{{ w.participants || "-" }}</span></div>
                  <div><span class="dl">具体工作</span><span class="dv">{{ w.specific_work || "-" }}</span></div>
                  <div><span class="dl">实际-建筑</span><span class="dv">{{ w.actual_work_days_architecture || "-" }}</span></div>
                  <div><span class="dl">实际-结构</span><span class="dv">{{ w.actual_work_days_structure || "-" }}</span></div>
                  <div><span class="dl">实际-其他</span><span class="dv">{{ w.actual_work_days_other || "-" }}</span></div>
                  <div><span class="dl">实际工期</span><span class="dv">{{ w.actual_duration_days || "-" }}</span></div>
                  <div><span class="dl">质量等级</span><span class="dv">{{ w.quality_grade || "-" }}</span></div>
                  <div><span class="dl">备注</span><span class="dv">{{ w.remark || "-" }}</span></div>
                </div>
              </td>
            </tr>
            <tr v-if="editingWlId === w.id">
              <td colspan="8" style="padding:12px;background:#f0f7ff">
                <div class="wl-edit-grid">
                  <label>项目编号 <input v-model="editWlForm.project_code" class="input input-sm" /></label>
                  <label>项目名称 <input v-model="editWlForm.project_name" class="input input-sm" /></label>
                  <label>类型 <input v-model="editWlForm.project_type" class="input input-sm" /></label>
                  <label>规模 <input v-model="editWlForm.scale" class="input input-sm" /></label>
                  <label>总体/专册 <input v-model="editWlForm.overall_lead" class="input input-sm" /></label>
                  <label>建筑专册 <input v-model="editWlForm.architecture_lead" class="input input-sm" /></label>
                  <label>计算工天 <input v-model.number="editWlForm.calculated_work_days" type="number" class="input input-sm" /></label>
                  <label>阶段 <input v-model="editWlForm.stage" class="input input-sm" /></label>
                  <label>参与人员 <input v-model="editWlForm.participants" class="input input-sm" /></label>
                  <label>具体工作 <input v-model="editWlForm.specific_work" class="input input-sm" /></label>
                  <label>实际工天-建筑 <input v-model.number="editWlForm.actual_work_days_architecture" type="number" class="input input-sm" /></label>
                  <label>实际工天-结构 <input v-model.number="editWlForm.actual_work_days_structure" type="number" class="input input-sm" /></label>
                  <label>实际工天-其他 <input v-model.number="editWlForm.actual_work_days_other" type="number" class="input input-sm" /></label>
                  <label>实际工期(天) <input v-model.number="editWlForm.actual_duration_days" type="number" class="input input-sm" /></label>
                  <label>质量等级 <input v-model="editWlForm.quality_grade" class="input input-sm" /></label>
                  <label>年份 <input v-model="editWlForm.year" class="input input-sm" /></label>
                  <label>备注 <input v-model="editWlForm.remark" class="input input-sm" /></label>
                </div>
                <div style="margin-top:8px;display:flex;gap:8px">
                  <button class="btn btn-sm btn-primary" @click="handleWlUpdate">保存</button>
                  <button class="btn btn-sm btn-outline" @click="editingWlId = null">取消</button>
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
            <span>计划人天：{{ p.planned_man_days }}</span>
            <span v-if="p.memberCount">成员：{{ p.memberCount }}人</span>
          </div>
        </div>
      </div>
      <div v-else class="empty-tip">暂无进行中的项目</div>
    </div>
  </div>
</template>


<script setup>
import { ref, computed, onMounted, reactive } from "vue"
import { useEmployeeStore } from "../stores/employees"
import { storeToRefs } from "pinia"
import api from "../api"

const activeLib = ref(null)
const employeeStore = useEmployeeStore()
const { employees } = storeToRefs(employeeStore)
const workloads = ref([])
const activeProjects = ref([])
const editingWlId = ref(null)
const editWlForm = reactive({})
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
    const [wlRes, projRes] = await Promise.all([
      api.get("/workload-records"),
      api.get("/projects")
    ])
    workloads.value = wlRes.data
    activeProjects.value = (projRes.data || []).filter(p => 
      p.status !== "completed" && p.status !== "closed"
    )
    await employeeStore.loadEmployees()
    for (let p of activeProjects.value) {
      try {
        const mRes = await api.get("/projects/" + p.id + "/members")
        p.memberCount = (mRes.data || []).length
      } catch(e) { p.memberCount = 0 }
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

function startWlEdit(w) {
  editingWlId.value = w.id
  Object.assign(editWlForm, {
    project_code: w.project_code || "", project_name: w.project_name || "",
    project_type: w.project_type || "", scale: w.scale || "",
    overall_lead: w.overall_lead || "", architecture_lead: w.architecture_lead || "",
    calculated_work_days: w.calculated_work_days || 0, stage: w.stage || "",
    participants: w.participants || "", specific_work: w.specific_work || "",
    actual_work_days_architecture: w.actual_work_days_architecture || 0,
    actual_work_days_structure: w.actual_work_days_structure || 0,
    actual_work_days_other: w.actual_work_days_other || 0,
    actual_duration_days: w.actual_duration_days || 0,
    quality_grade: w.quality_grade || "", year: w.year || "", remark: w.remark || ""
  })
}

async function handleWlUpdate() {
  try {
    await api.put("/workload-records/" + editingWlId.value, { ...editWlForm })
    editingWlId.value = null
    await loadWorkloads()
  } catch(e) { alert("保存失败: " + (e.response?.data?.detail || e.message)) }
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