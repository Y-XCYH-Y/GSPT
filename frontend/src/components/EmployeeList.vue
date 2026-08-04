<template>
  <div class="card">
    <div class="emp-scroll" v-if="employees.length > 0">
    <table v-if="employees.length > 0" class="emp-table">
      <thead>
        <tr>
          <th style="width:28px"></th>
          <th>姓名</th>
          <th>专业方向</th>
          <th>负荷</th>
          <th>参与项目</th>
          <th v-if="isDirector">操作</th>
        </tr>
      </thead>
      <tbody>
        <template v-for="emp in employees" :key="emp.id">
          <tr>
            <td>
              <button class="expand-btn" @click="toggleExpand(emp.id)">
                {{ expanded[emp.id] ? "\u25bc" : "\u25b6" }}
              </button>
            </td>
            <td>
              <strong>{{ emp.name }}</strong>
              <div style="font-size:11px;color:#94a3b8">{{ emp.gender }}</div>
            </td>
            <td>{{ emp.profession || '-' }}</td>
            <td>
              <span class="load-dot" :class="'load-' + getLoadColor(emp.current_load)" :title="emp.current_load || '空闲'"></span>
              <span class="load-text">{{ emp.current_load || "空闲" }}</span>
            </td>
            <td>
              <div class="proj-tags">
                <span v-for="pname in getEmployeeProjects(emp)" :key="pname" class="proj-tag">{{ pname }}</span>
                <span v-if="getEmployeeProjects(emp).length === 0" style="color:#94a3b8;font-size:12px">—</span>
              </div>
            </td>
            <td v-if="isDirector">
              <button class="btn btn-sm btn-info" @click="$emit('edit', emp)">编辑</button>
              <button class="btn btn-sm btn-danger" @click="$emit('delete', emp.id)" style="margin-left:4px">删除</button>
            </td>
          </tr>
          <tr v-if="expanded[emp.id]" class="detail-row">
            <td colspan="5">
              <div class="detail-panel">
                <div class="detail-section">
                  <div class="detail-item">
                    <span class="detail-label">注册情况</span>
                    <span class="detail-value">{{ emp.registration || "-" }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">职称情况</span>
                    <span class="detail-value">{{ emp.title || "-" }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">出生年月</span>
                    <span class="detail-value">{{ emp.birth_date || "-" }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">参加工作时间</span>
                    <span class="detail-value">{{ emp.work_start_date || "-" }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">攀长项目</span>
                    <span class="detail-value">{{ (emp.project_types || []).join(", ") || "-" }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">是否驻外</span>
                    <span class="detail-value">{{ emp.is_field || "-" }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">占用比例</span>
                    <span class="detail-value">{{ emp.occupancy_rate != null ? (emp.occupancy_rate * 100 + "%") : "-" }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">历史项目经验</span>
                    <span class="detail-value">{{ emp.experience || "暂无" }}</span>
                  </div>
                  <div class="detail-item">
                    <span class="detail-label">备注</span>
                    <span class="detail-value">{{ emp.remark || "无" }}</span>
                  </div>
                </div>
              </div>
            </td>
          </tr>
        </template>
      </tbody>
    </table>
    <div v-else class="empty">暂无员工数据</div>
  </div>
    </div>
</template>

<script setup>
import { reactive } from "vue"

const props = defineProps({
  employees: { type: Array, default: () => [] },
  empProjectMap: { type: Object, default: () => ({}) },
  isDirector: { type: Boolean, default: false }
})
const emit = defineEmits(["edit", "delete", "updateLoad"])

function getEmployeeProjects(emp) {
  if (!props.empProjectMap) return []
  var entries = props.empProjectMap[emp.name]
  if (!entries || !entries.length) return []
  return entries.map(function(e) { return e.project_name })
}



const expanded = reactive({})

function toggleExpand(id) {
  expanded[id] = !expanded[id]
}

function getLoadColor(load) {
  if (load === "超负荷" || load === "100%") return "red"
  if (load === "饱满" || load === "70%") return "orange"
  if (load === "适中" || load === "50%") return "yellow"
  if (load === "轻量") return "blue"
  return "green"
}
</script>

<style scoped>
.emp-table { width: 100%; border-collapse: collapse; font-size: 13px; }
.emp-table th { padding: 10px 12px; text-align: left; background: #f8fafc; border-bottom: 2px solid #e5e7eb; white-space: nowrap; }
.emp-table td { padding: 10px 12px; border-bottom: 1px solid #f1f5f9; }
.emp-table tr:hover > td { background: #f8fafc; }
.detail-row td { padding: 0; border-bottom: 1px solid #e5e7eb; }
.detail-panel { padding: 12px 16px 12px 44px; background: #fafbfc; }
.detail-section { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; }
.detail-item { display: flex; flex-direction: column; gap: 4px; }
.detail-label { font-size: 12px; color: #64748b; font-weight: 500; }
.detail-value { font-size: 13px; color: #1e293b; line-height: 1.5; }
.type-tags { display: flex; flex-wrap: wrap; gap: 3px; }
.type-tag { padding: 2px 6px; background: #eff6ff; color: #1e40af; border-radius: 4px; font-size: 11px; }
.expand-btn { background: none; border: 1px solid #d1d5db; border-radius: 4px; cursor: pointer; font-size: 11px; padding: 2px 6px; color: #64748b; }
.expand-btn:hover { background: #e5e7eb; }
.load-dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; vertical-align: middle; margin-right: 6px; }
.load-green { background: #16a34a; }
.load-blue { background: #3b82f6; }
.load-yellow { background: #eab308; }
.load-orange { background: #f97316; }
.load-red { background: #dc2626; }
.load-text { font-size: 12px; vertical-align: middle; }
.proj-tags { display: flex; flex-wrap: wrap; gap: 3px; max-width: 200px; }
.proj-tag { padding: 2px 6px; background: #f0fdf4; color: #166534; border-radius: 4px; font-size: 10px; white-space: nowrap; }
.input-sm { width: 100px !important; padding: 3px 6px !important; font-size: 11px !important; }
.emp-scroll { max-height: 420px; overflow-y: auto; border: 1px solid #e5e7eb; border-radius: 8px; }
.empty { text-align: center; padding: 40px; color: #94a3b8; }
</style>
