﻿<template>
  <div class="performance-assessment">
    <div class="pa-header"><h3>绩效考核管理</h3></div>
    <div class="pa-tabs">
      <button v-for="t in tabs" :key="t.key" class="pa-tab" :class="{active:activeTab===t.key}" @click="switchTab(t.key)">{{ t.label }}</button>
    </div>
    <div class="pa-content">
      <div v-if="activeTab==='myproj'" class="pa-panel">
        <div class="pa-panel-head">我参与的项目</div>
        <div class="pa-scroll" v-if="myProjects.length">
          <table class="pa-table">
            <thead><tr><th>项目编号</th><th>项目名称</th><th>类型</th><th>角色</th><th>阶段</th><th>年份</th><th>计算工天</th></tr></thead>
            <tbody>
              <tr v-for="p in myProjects.filter(p => p.is_participant !== false)" :key="p.id">
                <td>{{ p.project_code || "-" }}</td><td>{{ p.project_name || "-" }}</td>
                <td><span class="badge-blue">{{ p.project_type || "-" }}</span></td>
                <td>{{ p.role || "-" }}</td>
                <td>{{ p.stage || "-" }}</td><td>{{ p.year || "-" }}</td>
                <td>{{ p.calculated_work_days || "-" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="pa-empty">暂无项目信息</div>
      </div>

      <div v-if="activeTab==='scoring'" class="pa-panel">
        <div class="pa-panel-head">项目工天</div>
        <!-- 工天统计摘要 -->
        <div v-if="myProjects.length" class="stats-summary">
          <div class="stat-card">
            <div class="stat-value">{{ Math.round(calcStats().totalG) }}</div>
            <div class="stat-label">个人总工天</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ myProjects.filter(p => p.is_participant !== false).length }}</div>
            <div class="stat-label">参与项目数</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ Math.round(calcStats().avgG) }}</div>
            <div class="stat-label">平均工天/项目</div>
          </div>
          <div class="stat-card">
            <div class="stat-value">{{ Math.round(calcStats().maxG) }}</div>
            <div class="stat-label">最大单项工天</div>
          </div>
        </div>
        <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
          <select v-model="currentAssessmentId" class="input" style="width:auto" @change="loadScores()">
            <option value="">-- 选择考核期 --</option>
            <option v-for="a in assessments" :key="a.id" :value="a.id">{{ a.year }} - {{ a.name || a.year }}</option>
          </select>
          <button class="btn btn-outline btn-sm" @click="createAssessment" :disabled="loading">新建当前考核</button>
        </div>
        <div class="pa-scroll" v-if="myProjects.length && currentAssessmentId">
          <table class="pa-table">
            <thead><tr><th>项目</th><th>类型</th><th>暂估工天</th><th>基本工天</th><th>阶段比例</th><th>复杂程度</th><th>质量系数</th><th>进展系数</th><th>修正系数</th><th>工天</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="(p, idx) in myProjects" :key="p.id || idx">
                <td>{{ p.project_name || "-" }}</td><td>{{ p.project_type || "-" }}</td>
                <td>{{ p.planned_man_days ?? "-" }}</td><td><input v-model.number="p.A" type="number" step="0.5" min="0" class="input score-input" @input="calcG(p)" :disabled="!p.can_edit" /></td>
                <td>
                  <select v-if="p.can_edit" :value="p.stageRatioCustom ? '__custom__' : String(p.B)" class="input score-input" @change="onStageRatioChange(p, $event)" :disabled="!p.can_edit">
                    <option v-for="opt in stageRatioOptions(p)" :key="opt.value" :value="String(opt.value)">{{ opt.label }}</option>
                    <option value="__custom__">其他</option>
                  </select>
                  <div v-if="p.can_edit && p.stageRatioCustom" style="margin-top:4px">
                    <input v-model.number="p.B" type="number" step="0.001" min="0" max="2" class="input score-input" style="width:90px" @input="calcG(p)" placeholder="比例" />
                  </div>
                  <template v-else-if="!p.can_edit">
                    <strong>{{ fmtRatio(p.B) }}</strong><br><span style="font-size:10px;color:#94a3b8">{{ p.stage || "方案设计" }}</span>
                  </template>
                </td>
                <td>
                  <select v-model.number="p.C" class="input score-input" @change="calcG(p)" :disabled="!p.can_edit">
                    <option :value="0.8">简单 0.8</option><option :value="1.0">一般 1.0</option>
                    <option :value="1.1">复杂新型 1.1</option><option :value="1.3">特别复杂 1.3</option>
                  </select>
                </td>
                <td><input v-model.number="p.D" type="number" step="0.05" min="0.8" max="1.2" class="input score-input" @input="calcG(p)" :disabled="!p.can_edit" /></td>
                <td><input v-model.number="p.E" type="number" step="0.1" min="0" class="input score-input" @input="calcG(p)" :disabled="!p.can_edit" /></td>
                <td><input v-model.number="p.F" type="number" step="0.1" min="0.5" max="1.5" class="input score-input" @input="calcG(p)" :disabled="!p.can_edit" /></td>
                <td><strong>{{ p.G !== undefined ? p.G : "-" }}</strong></td>
                                <td>
                  <button v-if="p.can_edit" class="btn btn-primary btn-sm" @click="saveScore(p)" :disabled="loading || !p.A">
                    <span v-if="authStore.isDirector || authStore.isDeputyDirector">保存</span>
                    <span v-else-if="p.hasPendingRequest" style="color:#f59e0b">修改</span>
                    <span v-else>申请</span>
                  </button>
                
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else-if="!currentAssessmentId" class="pa-empty">请选择考核期</div>
        <div v-else class="pa-empty">暂无项目信息</div>
      </div>

      <div v-if="activeTab==='score'" class="pa-panel">
        <div style="display:flex;gap:4px;margin-bottom:12px;border-bottom:2px solid #e2e8f0">
          <button class="pa-tab" :class="{active:scoreSubTab==='project'}" @click="switchScoreSubTab('project')">项目评分</button>
          <button v-if="canViewEvalScoring" class="pa-tab" :class="{active:scoreSubTab==='eval'}" @click="switchScoreSubTab('eval')">考核</button>
        </div>
        <div v-if="scoreSubTab==='project'">
        <div class="pa-panel-head">项目评分</div>
        <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <select v-model="scoreProjectId" class="input" style="width:auto" @change="changeScoreProject">
            <option value="">选择项目</option>
            <option v-for="p in scoreProjects" :key="p.id" :value="p.id">{{ p.project_name }}</option>
          </select>
          <button class="btn btn-primary btn-sm" @click="loadProjectScoreMembers">加载人员</button><button class="btn btn-outline btn-sm" @click="openScoreAlloc()">工天分配</button>
        </div>
        <div v-if="scoreProjectMembers.length" class="pa-scroll">
          <table class="pa-table">
            <thead><tr><th>工号</th><th>姓名</th><th>角色</th><th>评分</th><th>操作</th></tr></thead>
            <tbody>
              <tr v-for="m in scoreProjectMembers" :key="m.id">
                <td>{{ m.employee_id }}</td><td>{{ m.employee_name }}</td><td>{{ m.displayRole || m.role }}</td>
                <td><input v-model.number="m.score" type="number" min="0" max="100" class="input score-input" @input="clampProjectScore(m)" /></td>
                <td><button class="btn btn-primary btn-sm" @click="saveProjectScore(m)">保存</button></td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="pa-empty">选择项目后加载人员</div>
        </div>
        <div v-if="canViewEvalScoring && scoreSubTab==='eval'">
        <div class="pa-panel-head">考核</div>
        <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
          <select v-model="evalAssessmentId" class="input" style="width:auto">
            <option value="">-- 选择考核期 --</option>
            <option v-for="a in assessments" :key="a.id" :value="a.id">{{ a.year }} - {{ a.name || a.year }}</option>
          </select>
          <div class="role-display" v-if="evalRole">评分角色：<strong>{{ roleLabel() }}</strong></div>
          <select v-if="evalRole==='project_leader'" v-model="evalProject" class="input" style="width:auto">
            <option value="">选择项目</option>
            <option v-for="p in myProjects" :key="p.project_name" :value="p.project_name">{{ p.project_name }}</option>
          </select>
          <button class="btn btn-primary btn-sm" @click="loadScoreTargets" :disabled="!evalAssessmentId||!evalRole">加载待评人员</button>
        </div>
<div v-if="scoreTargets.length" class="pa-scroll">
        <table class="pa-table">
          <thead><tr><th>姓名</th><th>所长</th><th>副所长</th><th>项目维度综合评分</th><th>互评</th><th>操作</th></tr></thead>
          <tbody>
            <tr v-for="t in scoreTargets" :key="t.id">
              <td>{{ t.name }}</td>
              <td>
                <input v-if="evalRole==='director'" v-model.number="t.score" type="number" min="0" max="100" class="input score-input" style="width:60px;font-size:11px;padding:3px" placeholder="0-100" @input="clampEvalScore(t)" />
                <span v-else>{{ t.directorScore !== null && t.directorScore !== undefined ? t.directorScore.toFixed(1) : "-" }}</span>
              </td>
              <td>
                <input v-if="evalRole==='deputy_director'" v-model.number="t.score" type="number" min="0" max="100" class="input score-input" style="width:60px;font-size:11px;padding:3px" placeholder="0-100" @input="clampEvalScore(t)" />
                <span v-else>{{ t.deputyScore !== null && t.deputyScore !== undefined ? t.deputyScore.toFixed(1) : "-" }}</span>
              </td>
              <td>
                <input v-if="evalRole==='project_leader'" v-model.number="t.score" type="number" min="0" max="100" class="input score-input" style="width:60px;font-size:11px;padding:3px" placeholder="0-100" @input="clampEvalScore(t)" />
                <span v-else>{{ t.leaderScore !== null && t.leaderScore !== undefined ? t.leaderScore.toFixed(1) : "-" }}</span>
              </td>
              <td>
                <input v-if="evalRole==='peer'" v-model.number="t.score" type="number" min="0" max="100" class="input score-input" style="width:60px;font-size:11px;padding:3px" placeholder="0-100" @input="clampEvalScore(t)" />
                <span v-else>{{ t.peerScore !== null && t.peerScore !== undefined ? t.peerScore.toFixed(1) : "-" }}</span>
              </td>
              <td><button class="btn btn-primary btn-sm" @click="submitEvalScore(t)" :disabled="loading || t.score === null || t.score === undefined">提交</button></td>
            </tr>
          </tbody>
        </table>
      </div>
        <div v-else class="pa-empty">点击"加载待评人员"加载待评人员列表</div>
        </div>
      </div>

      <div v-if="activeTab==='result'" class="pa-panel">
        <div class="pa-panel-head">考核结果</div>
        <div style="margin-bottom:12px;display:flex;gap:8px;align-items:center">
          <select v-model="resultAssessmentId" class="input" style="width:auto">
            <option value="">-- 选择考核期 --</option>
            <option v-for="a in assessments" :key="a.id" :value="a.id">{{ a.year }} - {{ a.name || a.year }}</option>
          </select>
          <button class="btn btn-outline btn-sm" @click="loadResults" :disabled="!resultAssessmentId">加载</button>
          
        </div>
        <div v-if="results.length" class="pa-scroll" style="max-height:500px">
          <table class="pa-table">
            <thead><tr><th>排名</th><th>姓名</th><th>专业</th><th>工天</th><th>所长</th><th>副所长</th><th>项目负责人</th><th>互评</th><th>综合得分</th></tr></thead>
            <tbody>
              <tr v-for="(r, idx) in results" :key="r.id">
                <td>{{ idx + 1 }}</td><td>{{ r.user_name }}</td><td>{{ r.profession || "-" }}</td>
                <td>{{ r.total_workdays }}</td>
                <td>{{ r.director_score.toFixed(1) }}</td><td>{{ r.deputy_score.toFixed(1) }}</td>
                <td>{{ r.leader_score.toFixed(1) }}</td><td>{{ r.peer_score.toFixed(1) }}</td>
                <td><strong>{{ r.final_score.toFixed(1) }}</strong></td>
                
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="pa-empty">暂无结果</div>
      </div>

    </div>
  </div>
<!-- 项目评分对话框 -->
<div v-if="showProjectScoreDialog" class="score-overlay" @click.self="showProjectScoreDialog = false">
  <div class="score-dialog card">
    <h4 style="margin:0 0 12px">考评打分 - {{ scoreTarget?.employee_name }}</h4>
    <div style="font-size:12px;color:#64748b;margin-bottom:12px">角色：{{ scoreTarget?.displayRole || scoreTarget?.role || "—" }}</div>
    <div class="form-row"><label>综合评分 (0-100)</label><input v-model.number="scoreData.score" type="number" min="0" max="100" placeholder="0-100" @input="clampDialogScore()" /></div>
    <div class="form-row"><label>备注</label><textarea v-model="scoreData.comment" rows="3" placeholder="可选" style="width:100%;border:1px solid #d1d5db;border-radius:6px;padding:6px 10px;font-size:13px" /></div>
    <div class="form-actions">
      <button class="btn btn-primary" @click="saveProjectScore2" :disabled="!scoreData.score && scoreData.score !== 0">保存</button>
      <button class="btn btn-outline" @click="showProjectScoreDialog = false">取消</button>
    </div>
  </div>
</div>

<!-- 工天分配对话框 -->
<div v-if="showAllocDialog" class="alloc-overlay">
  <div class="alloc-dialog card">
    <h3 style="margin:0 0 12px">工天分配 - {{ currentAllocProject?.project_name }}</h3>
    <div style="margin-bottom:8px">
      <label style="font-size:13px">项目负责人提取比例 (5%~8%)</label>
      <input v-model.number="allocData.leaderPct" type="number" step="1" min="5" max="8" class="input" style="width:70px" :disabled="isAllocLocked" />
      = <strong>{{ ((currentAllocProject?.G || 0) * ((allocData.leaderPct || 5) / 100)).toFixed(2) }}</strong>
    </div>
    <div style="margin-bottom:12px;border:1px solid #e2e8f0;border-radius:6px;padding:10px">
      <div style="font-size:13px;font-weight:500;margin-bottom:8px">角色分配比例</div>
      <div style="display:flex;gap:20px;flex-wrap:wrap;align-items:center">
        <span style="font-size:13px">专业负责人: <strong>{{ allocData.lv1.leader || 0 }}</strong>%</span>
        <span style="font-size:13px">设计人: <strong>{{ allocData.lv1.designer || 0 }}</strong>%</span>
        <span style="font-size:13px">复核人: <strong>{{ allocData.lv1.reviewer || 0 }}</strong>%</span>
        <span v-if="lv1Total !== 100" style="color:#dc2626;font-size:12px">合计：{{ lv1Total }}%（需等于100%）</span>
        <span v-else style="color:#059669;font-size:12px">合计：100% ✓</span>
      </div>
      <div style="font-size:13px;margin-top:6px;color:#64748b">
        已分配天数：<strong>{{ allocatedDays }}</strong>
         | 
        剩余未分配：<strong :style="{color: unallocatedDays > 0 ? '#dc2626' : '#059669'}">{{ unallocatedDays }}</strong>
      </div>
    </div>
    <div style="margin-bottom:12px;border:1px solid #e2e8f0;border-radius:6px;padding:10px">
      
      <!-- 专业负责人 -->
      <div v-if="allocDataRoleMembers('专业负责人').length" style="margin-bottom:10px;padding:8px;background:#f8fafc;border-radius:4px">
        <div style="font-size:12px;font-weight:500;margin-bottom:4px">专业负责人 (10%~25%)</div>
        <table class="am-table" style="font-size:12px">
          <thead><tr><th>姓名</th><th>分配比例(%)</th><th>天数</th></tr></thead>
          <tbody>
            <tr v-for="m in allocDataRoleMembers('专业负责人')" :key="m.id">
              <td>{{ m.name }}</td>
              <td><input v-model.number="m.pct" type="number" step="1" min="0" max="100" class="input" style="width:60px;font-size:11px" @input="onPctChange" :disabled="isAllocLocked" /></td>
              <td><input v-model.number="m.days" type="number" step="1" min="0" class="input" style="width:90px;font-size:11px" @input="onDaysChange('专业负责人', 'leader', m)" :disabled="isAllocLocked" /></td>
              
            </tr>
          </tbody>
        </table>
        <div v-if="roleSubTotal('专业负责人') !== (allocData.lv1.leader || 0)" style="font-size:11px;color:#dc2626">
          小计：{{ roleSubTotal('专业负责人') }}%（需等于专业负责人分配比例 {{ allocData.lv1.leader || 0 }}%）
        </div>
        <div v-else style="font-size:11px;color:#059669">
          小计：{{ roleSubTotal('专业负责人') }}% ✓
        </div>
      </div>

      <!-- 设计人 -->
      <div v-if="allocDataRoleMembers('设计人').length" style="margin-bottom:10px;padding:8px;background:#f8fafc;border-radius:4px">
        <div style="font-size:12px;font-weight:500;margin-bottom:4px">设计人 (60%~70%)</div>
        <table class="am-table" style="font-size:12px">
          <thead><tr><th>姓名</th><th>分配比例(%)</th><th>天数</th></tr></thead>
          <tbody>
            <tr v-for="m in allocDataRoleMembers('设计人')" :key="m.id">
              <td>{{ m.name }}</td>
              <td><input v-model.number="m.pct" type="number" step="1" min="0" max="100" class="input" style="width:60px;font-size:11px" @input="onPctChange" :disabled="isAllocLocked" /></td>
              <td><input v-model.number="m.days" type="number" step="1" min="0" class="input" style="width:90px;font-size:11px" @input="onDaysChange('设计人', 'designer', m)" :disabled="isAllocLocked" /></td>
              
            </tr>
          </tbody>
        </table>
        <div v-if="roleSubTotal('设计人') !== (allocData.lv1.designer || 0)" style="font-size:11px;color:#dc2626">
          小计：{{ roleSubTotal('设计人') }}%（需等于设计人分配比例 {{ allocData.lv1.designer || 0 }}%）
        </div>
        <div v-else style="font-size:11px;color:#059669">
          小计：{{ roleSubTotal('设计人') }}% ✓
        </div>
      </div>

      <!-- 复核人 -->
      <div v-if="allocDataRoleMembers('复核人').length" style="margin-bottom:10px;padding:8px;background:#f8fafc;border-radius:4px">
        <div style="font-size:12px;font-weight:500;margin-bottom:4px">复核人 (5%~15%)</div>
        <table class="am-table" style="font-size:12px">
          <thead><tr><th>姓名</th><th>分配比例(%)</th><th>天数</th></tr></thead>
          <tbody>
            <tr v-for="m in allocDataRoleMembers('复核人')" :key="m.id">
              <td>{{ m.name }}</td>
              <td><input v-model.number="m.pct" type="number" step="1" min="0" max="100" class="input" style="width:60px;font-size:11px" @input="onPctChange" :disabled="isAllocLocked" /></td>
              <td><input v-model.number="m.days" type="number" step="1" min="0" class="input" style="width:90px;font-size:11px" @input="onDaysChange('复核人', 'reviewer', m)" :disabled="isAllocLocked" /></td>
              
            </tr>
          </tbody>
        </table>
        <div v-if="roleSubTotal('复核人') !== (allocData.lv1.reviewer || 0)" style="font-size:11px;color:#dc2626">
          小计：{{ roleSubTotal('复核人') }}%（需等于复核人分配比例 {{ allocData.lv1.reviewer || 0 }}%）
        </div>
        <div v-else style="font-size:11px;color:#059669">
          小计：{{ roleSubTotal('复核人') }}% ✓
        </div>
      </div>

      <div v-if="noAllocMembers" style="font-size:12px;color:#94a3b8;padding:8px 0">暂无可分配的人员</div>
    </div><div class="form-actions">
      <button class="btn btn-primary" @click="saveAllocData()" :disabled="Math.abs(allocTotalPct - 100) > 1" v-if="!isAllocLocked">保存</button><button class="btn btn-outline" @click="unlockAlloc()" v-if="isAllocLocked && (authStore.isDirector || authStore.isDeputyDirector || authStore.user?.id === currentAllocProject?.project_leader_id)" style="margin-left:8px">解锁重新分配</button>
      <button class="btn btn-outline" @click="showAllocDialog = false">关闭</button>
    </div>
  </div>
</div>

</template>

<script setup>
import { ref, computed } from "vue"
import { useAuthStore } from "../stores/auth"
import { performanceAPI } from "../api"
import api from "../api"

const authStore = useAuthStore()
const activeTab = ref("myproj")
const myProjects = ref([])
const assessments = ref([])
const currentAssessmentId = ref("")
const loading = ref(false)

const tabs = computed(() => {
  const items = [
    { key: "myproj", label: "我的项目" },
    { key: "scoring", label: "项目工天" },
  ]
  if (canViewScoreTab.value) items.push({ key: "score", label: "评分" })
  if (authStore.isDirector || authStore.isDeputyDirector) items.push({ key: "result", label: "考核结果" })
  return items
})

const evalAssessmentId = ref("")
const evalRole = ref("")
const evalProject = ref("")

// Auto-detect scoring role from user role
function roleLabel() {
  var labels = { director: "所长评分", deputy_director: "副所长评分", project_leader: "项目负责人评分", peer: "员工互评" }
  return labels[evalRole.value] || ""
}

// Auto-set evalRole when authStore.user is available
function updateEvalRole() {
  if (!authStore.user) return
  const role = authStore.user.role
  if (role === "director") evalRole.value = "director"
  else if (role === "deputy_director") evalRole.value = "deputy_director"
  else if (role === "project_leader") evalRole.value = "project_leader"
  else evalRole.value = "peer"
}
// Try immediately and also on change
updateEvalRole()
if (authStore.isLoggedIn && !authStore.user) {
  api.get("/user/me").then(r => { authStore.user = r.data; updateEvalRole() }).catch(() => {})
}
const scoreTargets = ref([])
const resultAssessmentId = ref("")
const results = ref([])

if (authStore.isLoggedIn && !authStore.user) {
  api.get("/user/me").then(r => { authStore.user = r.data }).catch(() => {})
}

async function loadAssessments() {
  try {
    assessments.value = (await performanceAPI.getAssessments()).data
    assessments.value.sort(function(a, b) { return new Date(b.created_at) - new Date(a.created_at) })
    // Auto-select the latest assessment for scoring tab
    if (!currentAssessmentId.value && assessments.value.length) {
      currentAssessmentId.value = assessments.value[0].id
    }
  } catch(e) {}
}
loadAssessments()

function switchTab(key) {
  showAllocDialog.value = false
  activeTab.value = key
  if (key === "myproj") loadMyProj()
  if (key === "scoring") {
    if (assessments.value.length) {
      currentAssessmentId.value = assessments.value[0].id
      loadScores()
    }
  }
if (key === "score") {
  if (!canViewScoreTab.value) return
  loadScoreProjects()
}
  if (key === "result") {
    if (!authStore.isDirector && !authStore.isDeputyDirector) return
    if (assessments.value.length) {
      if (!resultAssessmentId.value) resultAssessmentId.value = assessments.value[0].id
      loadResults()
    }
  }
}

async function loadMyProj() {
  try { myProjects.value = (await performanceAPI.getMyProjects()).data } catch(e) { console.error(e) }
  loadScoreProjects()
}
loadMyProj()


async function createAssessment() {
  loading.value = true
  try {
    const year = new Date().getFullYear().toString()
    var exists = assessments.value.find(function(a) { return a.year === year })
    if (exists) {
      alert(year + "年度考核已存在，请直接选择")
      currentAssessmentId.value = exists.id
      loading.value = false
      return
    }
    await performanceAPI.createAssessment({ year, name: year + "年度考核", bonus_total: 0, gamma: 1 })
    await loadAssessments()
  } catch(e) { console.error(e) }
  loading.value = false
}

async function loadScores() {
  if (!currentAssessmentId.value) return
  try {
    const r = await performanceAPI.getWorkdays(currentAssessmentId.value)
    const saved = {}
    r.data.forEach(s => { saved[s.project_name] = s })
    myProjects.value.forEach(p => {
      const s = saved[p.project_name]
      if (s) {
        p.A = Number(s.A)
        p.B = s.B !== undefined && s.B !== null && s.B !== "" ? Number(s.B) : calcStageRatio(p.stage, p.project_type)
        p.stageRatioCustom = !isPresetStageRatio(p, p.B)
        p.C = Number(s.C); p.D = Number(s.D); p.E = Number(s.E); p.F = Number(s.F); p.G = Math.round(Number(s.G)); p.savedId = s.id
      }
      else { p.A = Number(p.A || 1); p.B = calcStageRatio(p.stage, p.project_type); p.stageRatioCustom = false; p.C = Number(p.C || 1); p.D = Number(p.D || 1); p.E = Number(p.E || 1); p.F = Number(p.F || 1); p.savedId = undefined; calcG(p) }
    })
    // Load workday requests to check pending status
    const reqs = (await api.get("/performance/workday-requests")).data
    const pendingMap = {}
    reqs.forEach(r => { if (r.status === 'pending') pendingMap[r.project_name] = true })
    myProjects.value.forEach(p => { p.hasPendingRequest = !!pendingMap[p.project_name]; calcG(p) })
  } catch(e) { console.error(e) }
}

function allocStageRatio(stage) {
  var ratios = { "方案设计": 0.05, "初步设计": 0.36, "施工图": 0.30, "施工图设计": 0.30, "施工配合": 0.38 }
  return ratios[stage] || 0
}

function calcStageRatio(stage, projectType) {
  if (!stage) stage = "方案设计"
  var isRailway = projectType === "大铁"
  var ratios = isRailway
    ? { "方案设计": 0.02, "初步设计": 0.353, "施工图": 0.55, "施工图设计": 0.55, "施工配合": 0.077 }
    : { "方案设计": 0.12, "初步设计": 0.303, "施工图": 0.50, "施工图设计": 0.50, "施工配合": 0.077 }
  return ratios[stage] || 0
}

function stageRatioOptions(p) {
  var isRailway = (p.project_type || "") === "大铁"
  return isRailway
    ? [
        { label: "方案设计 2.0%", value: 0.02 },
        { label: "初步设计 35.3%", value: 0.353 },
        { label: "施工图设计 55.0%", value: 0.55 },
        { label: "施工配合 7.7%", value: 0.077 }
      ]
    : [
        { label: "方案设计 12.0%", value: 0.12 },
        { label: "初步设计 30.3%", value: 0.303 },
        { label: "施工图设计 50.0%", value: 0.50 },
        { label: "施工配合 7.7%", value: 0.077 }
      ]
}

function isPresetStageRatio(p, b) {
  var n = Number(b)
  return stageRatioOptions(p).some(function(opt) { return Math.abs(opt.value - n) < 0.000001 })
}

function fmtRatio(v) {
  var n = Number(v)
  if (!isFinite(n)) return "0.0%"
  return (n * 100).toFixed(1) + "%"
}

function onStageRatioChange(p, ev) {
  var v = ev.target.value
  if (v === "__custom__") {
    p.stageRatioCustom = true
    if (p.B === undefined || p.B === null || p.B === 0) p.B = calcStageRatio(p.stage, p.project_type)
  } else {
    p.stageRatioCustom = false
    p.B = Number(v)
  }
  calcG(p)
}

function calcG(p) {
  var b = p.B !== undefined && p.B !== null ? Number(p.B) : calcStageRatio(p.stage || "方案设计", p.project_type)
  p.G = Math.round((p.A || 0) * b * (p.C || 1) * (p.D || 1) * (p.E || 1) * (p.F || 1))
}

function calcStats() {
  var total = 0, maxVal = 0, count = 0
  myProjects.value.forEach(function(p) {
    if (p.is_participant === false) return
    var g = p.G || p.calculated_work_days || 0
    total += g
    if (g > maxVal) maxVal = g
    count++
  })
  return { totalG: total, avgG: count > 0 ? total / count : 0, maxG: maxVal }
}

async function saveScore(p) {
  // \u9879\u76ee\u8d1f\u8d23\u4eba\u2192\u63d0\u4ea4\u5ba1\u6279\u7533\u8bf7
  if (!authStore.isDirector && !authStore.isDeputyDirector) {
    if (!confirm("确认提交修改申请？")) return
    if (!currentAssessmentId.value) { alert("\u8bf7\u5148\u65b0\u5efa\u6216\u9009\u62e9\u8003\u6838\u671f"); return }
    await api.post("/create-request", {
      assessment_id: currentAssessmentId.value,
      project_name: p.project_name,
      A: p.A || 0, B: p.B || 0, C: p.C || 1,
      D: p.D || 1, E: p.E || 1, F: p.F || 1
    })
    p.hasPendingRequest = true
    alert("已提交审批申请，等待所长批准")
    return
  }
  loading.value = true
  try {
    calcG(p)
    await performanceAPI.createWorkday({
      assessment_id: parseInt(currentAssessmentId.value),
      user_id: authStore.user?.id || 0,
      project_name: p.project_name, project_type: p.project_type,
      A: p.A || 0, B: p.B || 0, C: p.C || 1, D: p.D || 1, E: p.E || 1, F: p.F || 1
    })
    await loadScores()
  } catch(e) { console.error(e); alert("????: " + (e.message || "????")) }
  loading.value = false
}

async function deleteScore(p) {
  loading.value = true
  try { if (p.savedId) await performanceAPI.deleteWorkday(p.savedId); await loadScores() } catch(e) { console.error(e) }
  loading.value = false
}

const scoreSubTab = ref("project")
const canViewEvalScoring = computed(() => authStore.isDirector || authStore.isDeputyDirector)

function switchScoreSubTab(tab) {
  showAllocDialog.value = false
  scoreSubTab.value = tab
  if (tab === 'eval') {
    if (!canViewEvalScoring.value) return
    if (assessments.value.length && !evalAssessmentId.value) evalAssessmentId.value = assessments.value[0].id
    loadScoreTargets()
  }
}
const scoreProjects = ref([])
const scoreProjectId = ref("")
const scoreProjectMembers = ref([])
const canViewScoreTab = computed(() => {
  if (authStore.isDirector || authStore.isDeputyDirector) return true
  var uid = authStore.user?.id
  return myProjects.value.some(function(p) { return p.project_leader_id === uid }) ||
    scoreProjects.value.some(function(p) { return p.project_leader_id === uid })
})

async function loadScoreProjects() {
  try {
    const r = await api.get("/projects")
    scoreProjects.value = r.data
    if (scoreProjects.value.length && !scoreProjectId.value) {
      scoreProjectId.value = scoreProjects.value[0].id
      loadProjectScoreMembers()
    }
  } catch(e) { console.error(e) }
}

const scoreDesignMems = computed(() => scoreProjectMembers.value.filter(m => m.role === "设计" || m.role === "设计阶段"))
const scoreReviewMems = computed(() => scoreProjectMembers.value.filter(m => m.role === "复核" || m.role === "复核阶段"))
const scoreOtherMems = computed(() => scoreProjectMembers.value.filter(m => m.role !== "设计" && m.role !== "设计阶段" && m.role !== "复核" && m.role !== "复核阶段"))

const showProjectScoreDialog = ref(false)
const scoreTarget = ref(null)
const scoreData = ref({ score: null, comment: "" })
const scoreMap = ref({})

function clampScoreValue(v) {
  if (v === "" || v === null || v === undefined) return null
  return Math.max(0, Math.min(100, Number(v) || 0))
}

function clampProjectScore(m) {
  if (m) m.score = clampScoreValue(m.score)
}

function clampEvalScore(t) {
  if (t) t.score = clampScoreValue(t.score)
}

function clampDialogScore() {
  scoreData.value.score = clampScoreValue(scoreData.value.score)
}

function isScoreValid(v) {
  return v !== null && v !== undefined && v >= 0 && v <= 100
}

function scoreMemberValue(m) {
  var key = (m.employee_id || "") + "|" + (m.role || "")
  var s = scoreMap.value[key]
  if (!s) return ""
  return (s.score !== null && s.score !== undefined) ? s.score : ""
}

function openProjectScoreDialog(m) {
  var key = (m.employee_id || "") + "|" + (m.role || "")
  var s = scoreMap.value[key]
  scoreTarget.value = m
  scoreData.value = { score: (s && s.score !== null && s.score !== undefined) ? s.score : null, comment: (s && s.comment) || "" }
  showProjectScoreDialog.value = true
}

async function saveProjectScore2() {
  if (!scoreTarget.value || !scoreProjectId.value) return
  if (!isScoreValid(scoreData.value.score)) {
    alert("评分必须在0-100之间")
    return
  }
  try {
    await api.post("/projects/" + scoreProjectId.value + "/member-scores", {
      target_employee_id: scoreTarget.value.employee_id,
      role: scoreTarget.value.role,
      score: scoreData.value.score,
      comment: scoreData.value.comment || ""
    })
    var key = (scoreTarget.value.employee_id || "") + "|" + (scoreTarget.value.role || "")
    scoreMap.value[key] = {
      target_employee_id: scoreTarget.value.employee_id,
      role: scoreTarget.value.role,
      score: scoreData.value.score,
      comment: scoreData.value.comment || ""
    }
    var savedRow = scoreProjectMembers.value.find(function(m) {
      return (m.employee_id || "") === (scoreTarget.value.employee_id || "") && (m.role || "") === (scoreTarget.value.role || "")
    })
    if (savedRow) savedRow.score = scoreData.value.score
    showProjectScoreDialog.value = false
    showAllocDialog.value = false
    alert("评分已保存")
  } catch(e) { alert("保存失败") }
}

function changeScoreProject() {
  showProjectScoreDialog.value = false
  showAllocDialog.value = false
  scoreProjectMembers.value = []
  loadProjectScoreMembers()
}

async function loadProjectScoreMembers() {
  if (!scoreProjectId.value) return
  try {
    const r = await api.get("/projects/" + scoreProjectId.value + "/members")
    scoreProjectMembers.value = r.data.filter(m => m.role !== "项目负责人").map(m => ({
      ...m,
      score: null,
      displayRole: m.role === "专业审核" ? "专业负责人" : m.role
    }))
    const sr = await api.get("/projects/" + scoreProjectId.value + "/member-scores")
    sr.data.forEach(s => {
      const m = scoreProjectMembers.value.find(x => x.employee_id === s.target_employee_id && x.role === s.role)
      if (m) m.score = s.score
    })
    scoreProjectMembers.value.forEach(function(m) {
      var key = (m.employee_id || "") + "|" + (m.role || "")
      var s = scoreMap.value[key]
      if (s && (m.score === null || m.score === undefined)) m.score = s.score
    })
  } catch(e) { console.error(e) }
}

function canManageSelectedProject() {
  if (!scoreProjectId.value) return false
  var p = scoreProjects.value.find(function(x) { return x.id === scoreProjectId.value })
  if (!p) return false
  return authStore.isDirector || authStore.user?.id === p.project_leader_id
}

async function openScoreAlloc() {
  if (!scoreProjectId.value) { alert("请先选择项目"); return }
  var p = scoreProjects.value.find(function(x) { return x.id === scoreProjectId.value })
  if (!p) return
  var stage = p.current_stage || "方案设计"
  var b = calcStageRatio(stage, p.project_type)
  var base = p.planned_man_days || 0
  try {
    if (currentAssessmentId.value) {
      const wd = await performanceAPI.getWorkdays(currentAssessmentId.value)
      const rec = (wd.data || []).find(function(x) { return x.project_name === p.project_name })
      if (rec && rec.A !== undefined && rec.A !== null) base = Number(rec.A) || 0
    }
  } catch(e) {}
  p.G = Math.round((base || 0) * b)
  openAllocDialog(p)
}

async function saveProjectScore(m) {
  if (!scoreProjectId.value || m.score === null || m.score === undefined) return
  if (!isScoreValid(m.score)) {
    alert("评分必须在0-100之间")
    return
  }
  try {
    await api.post("/projects/" + scoreProjectId.value + "/member-scores", {
      target_employee_id: m.employee_id,
      role: m.role,
      score: m.score
    })
    var key = (m.employee_id || "") + "|" + (m.role || "")
    scoreMap.value[key] = {
      target_employee_id: m.employee_id,
      role: m.role,
      score: m.score,
      comment: m.comment || ""
    }
    showProjectScoreDialog.value = false
    showAllocDialog.value = false
    alert("评分已保存")
  } catch(e) { alert("保存失败") }
}

async function loadScoreTargets() {
  if (!authStore.user) {
    try { authStore.user = (await api.get("/user/me")).data } catch(e) {}
  }
  updateEvalRole()
  if (!evalAssessmentId.value || !evalRole.value) return
  try {
    const r = await api.get("/users")
    const allUsers = r.data
    scoreTargets.value = allUsers.filter(u => u.is_active).map(u => ({
      id: u.id, name: u.name, department: u.department, profession: u.profession || "",
      score: null, comment: "",
      directorScore: null, deputyScore: null, leaderScore: null, peerScore: null
    }))
    const sr = await performanceAPI.getScores(evalAssessmentId.value)
    sr.data.forEach(s => {
      const t = scoreTargets.value.find(x => x.id === s.target_user_id)
      if (!t) return
      if (s.evaluator_role === "director") t.directorScore = s.score
      else if (s.evaluator_role === "deputy_director") t.deputyScore = s.score
      else if (s.evaluator_role === "project_leader") t.leaderScore = s.score
      else if (s.evaluator_role === "peer") t.peerScore = s.score
    })
    // Load calculated project leader scores from ProjectMemberScore data
    const ls = await api.get("/performance/leader-scores")
    const leaderMap = {}
    ls.data.forEach(x => { leaderMap[x.user_id] = x.leader_score })
    scoreTargets.value.forEach(t => {
      if (leaderMap[t.id] !== undefined && leaderMap[t.id] !== 0) t.leaderScore = leaderMap[t.id]
    })
  } catch(e) { console.error(e) }
}

async function submitEvalScore(t) {
  if (!evalAssessmentId.value || !evalRole.value || t.score === null || t.score === undefined) return
  if (!isScoreValid(t.score)) {
    alert("评分必须在0-100之间")
    return
  }
  loading.value = true
  try {
    await performanceAPI.submitScore({
      assessment_id: parseInt(evalAssessmentId.value),
      target_user_id: t.id, score: t.score,
      evaluator_role: evalRole.value,
      project_name: evalRole.value === "project_leader" ? evalProject.value : null,
      comment: t.comment || ""
    })
    if (evalRole.value === "director") t.directorScore = t.score
    else if (evalRole.value === "deputy_director") t.deputyScore = t.score
    else if (evalRole.value === "project_leader") t.leaderScore = t.score
    else if (evalRole.value === "peer") t.peerScore = t.score
    t.score = null
    t.comment = ""
    await loadScoreTargets()
    alert("评分已提交")
  } catch(e) { console.error(e); alert("提交失败") }
  loading.value = false
}

function calcAvgScore(t) {
  var vals = [t.tech_quality, t.work_attitude, t.emergency_task, t.extra_contribution].filter(function(v) { return v !== null && v !== undefined })
  if (vals.length === 0) return t.score || 0
  return vals.reduce(function(a, b) { return a + b }, 0) / vals.length
}

function hasAnyScore(t) {
  return t.tech_quality !== null || t.work_attitude !== null || t.emergency_task !== null || t.extra_contribution !== null || t.score !== null
}



async function loadResults() {
  if (!resultAssessmentId.value) return
  try {
    const r = await performanceAPI.getResults(resultAssessmentId.value)
    results.value = r.data.sort((a, b) => b.final_score - a.final_score)
  } catch(e) { console.error(e) }
}

async function calculateResults() {
  if (!resultAssessmentId.value) return
  loading.value = true
  try {
    await performanceAPI.calculateResults(resultAssessmentId.value)
    await loadResults()
  } catch(e) { console.error(e) }
  loading.value = false
}

function abcdGrade(score) {
  if (score >= 90) return "A"
  if (score >= 80) return "B"
  if (score >= 70) return "C"
  return "D"
}

function abcdClass(score) {
  if (score >= 90) return "abcd-a"
  if (score >= 80) return "abcd-b"
  if (score >= 70) return "abcd-c"
  return "abcd-d"
}

const showAllocDialog = ref(false)
const currentAllocProject = ref(null)
const currentAllocProjectId = ref(null)
const allocData = ref({ leaderPct: 5, lv1: { leader: 0, designer: 0, reviewer: 0 }, members: [], locked: false })

const isAllocLocked = computed(() => allocData.value.locked === true)

const totalG = computed(() => currentAllocProject.value?.G || 0)

const lv1Total = computed(() => {
  return ((allocData.value.lv1.leader || 0) + (allocData.value.lv1.designer || 0) + (allocData.value.lv1.reviewer || 0))
})

const allocatedDays = computed(() => {
  var total = 0
  for (var i = 0; i < allocData.value.members.length; i++) {
    total += (allocData.value.members[i].days || 0)
  }
  return total
})

const unallocatedDays = computed(() => {
  var avail = (remainingG.value || 0)
  var totalAvail = Math.round(avail)
  return Math.max(0, totalAvail - allocatedDays.value)
})

function allocDataRoleMembers(role) {
  return allocData.value.members.filter(function(m) { return m.role === role })
}

function roleSubTotal(role) {
  var ms = allocDataRoleMembers(role)
  var sum = 0
  ms.forEach(function(m) { sum += (m.pct || 0) })
  return Math.round(sum * 100) / 100
}

const noAllocMembers = computed(function() {
  return allocData.value.members.length === 0
})

function calcLv1FromMembers() {
  var ms = allocData.value.members
  var lv1 = allocData.value.lv1
  lv1.leader = roleSubTotal("专业负责人")
  lv1.designer = roleSubTotal("设计人")
  lv1.reviewer = roleSubTotal("复核人")
}
function computeDaysForMember(m) {
  var avail = (remainingG.value || 0)
  var exact = avail * ((m.pct || 0) / 100)
  return { exact: exact, rounded: Math.round(exact) }
}

function updateMemberDays(m) {
  var r = computeDaysForMember(m)
  m.days = r.rounded
}

function calcDaysFromPct() {
  var roles = {"\u4e13\u4e1a\u8d1f\u8d23\u4eba": "leader", "\u8bbe\u8ba1\u4eba": "designer", "\u590d\u6838\u4eba": "reviewer"}
  for (var key in roles) {
    var ms = allocDataRoleMembers(key)
    for (var i = 0; i < ms.length; i++) {
      updateMemberDays(ms[i], allocData.value.lv1[roles[key]] || 0)
    }
  }
}

function memberErr(m) {
  var roleMap = {"\u4e13\u4e1a\u8d1f\u8d23\u4eba": "leader", "\u8bbe\u8ba1\u4eba": "designer", "\u590d\u6838\u4eba": "reviewer"}
  var rpct = allocData.value.lv1[roleMap[m.role]] || 0
  var r = computeDaysForMember(m, rpct)
  var err = r.exact - r.rounded
  if (Math.abs(err) < 0.005) return ""
  return (err > 0 ? "+" : "") + err.toFixed(2)
}

function onPctChange() {
  calcDaysFromPct()
  calcLv1FromMembers()
}

function onDaysChange(roleName, lv1Key, m) {
  var avail = (remainingG.value || 0)
  if (avail > 0) {
    m.pct = Math.round(Math.max(0, (m.days || 0) * 100 / avail) * 10) / 10
  } else if ((m.days || 0) === 0) {
    m.pct = 0
  }
  calcLv1FromMembers()
}


function syncLv2() {
  calcLv1FromMembers()
}

const remainingG = computed(() => { var g = currentAllocProject.value?.G || 0; var lp = (allocData.value.leaderPct || 5) / 100; return g - g * lp })

const currentStagePct = computed(() => allocStageRatio(currentAllocProject.value?.stage))

const stageData = computed(() => [
  { name: "方案设计", pct: 0.05 },
  { name: "初步设计", pct: 0.36 },
  { name: "施工图", pct: 0.30 },
  { name: "施工图设计", pct: 0.30 },
  { name: "施工配合", pct: 0.38 },
])

async function openAllocDialog(p) {
  currentAllocProject.value = p
  currentAllocProjectId.value = null
  allocData.value = { leaderPct: 5, lv1: { leader: 0, designer: 0, reviewer: 0 }, members: [] }
  // Try to find actual project ID
  try {
    var allProjs = (await api.get("/projects")).data
    var matched = allProjs.find(function(x) { return x.project_name === p.project_name })
    if (matched) {
      currentAllocProjectId.value = matched.id
    }
  } catch(e) {}
  try {
    var allProjs = (await api.get("/projects")).data
    var matched = allProjs.find(function(pr) { return pr.project_name === p.project_name })
    if (matched) {
      var mr = await api.get("/projects/" + matched.id + "/members")
      var roleMap = { "设计": "设计人", "复核": "复核人", "专业审核": "专业负责人" }
      allocData.value.members = mr.data.filter(function(m) {
        return roleMap[m.role]
      }).map(function(m) {
        return { id: m.id, name: m.employee_name, role: roleMap[m.role], pct: 0 }
      })
      try {
        var sv = await api.get("/performance/workday-alloc/" + matched.id)
        if (sv && sv.data && sv.data.data && sv.data.data.members && sv.data.data.members.length > 0) {
          allocData.value = sv.data.data
          // Convert old decimal leaderPct (0.05) to percentage (5)
          if (allocData.value.leaderPct !== undefined && allocData.value.leaderPct <= 1) {
            allocData.value.leaderPct = Math.round(allocData.value.leaderPct * 100)
          }
        }
      } catch(e1) {}
    }
  } catch(e) { console.error(e) }
  calcLv1FromMembers()
  calcDaysFromPct()
  showAllocDialog.value = true
}

const allocTotalPct = computed(() => {
  var sum = allocData.value.members.reduce(function(s, m) { return s + (m.pct || 0) }, 0)
  return Math.round(sum * 100) / 100
})

function validateAllocPct() {
  allocData.value.members.forEach(function(m) {
    if (m.pct < 0) m.pct = 0
    if (m.pct > 100) m.pct = 100
  })
}

const ROLE_RANGE = {
  "专业负责人": { min: 10, max: 25 },
  "设计人": { min: 60, max: 70 },
  "复核人": { min: 5, max: 15 }
}

function rolePctError(m) {
  var range = ROLE_RANGE[m.role]
  if (!range) return ""
  var pct = m.pct || 0
  if (pct < range.min) return "最低" + range.min + "%"
  if (pct > range.max) return "最高" + range.max + "%"
  return ""
}



async function saveAllocData() {
  try {
    allocData.value.locked = true
    await api.post("/performance/alloc-save-final", { project_id: currentAllocProjectId.value, data: allocData.value })
    alert("已保存")
    showAllocDialog.value = false
  } catch(e) { alert("保存失败") }
}

function unlockAlloc() {
  if (!confirm("解锁后可以重新分配比例，确定解锁？")) return
  allocData.value.locked = false
}
</script>

<style scoped>
.performance-assessment { margin-bottom: 20px; }
.pa-header h3 { font-size: 16px; color: #1e293b; margin: 0 0 12px 0; }
.pa-tabs { display: flex; gap: 4px; margin-bottom: 16px; border-bottom: 2px solid #e2e8f0; }
.pa-tab { padding: 8px 16px; border: none; background: none; font-size: 13px; color: #64748b; cursor: pointer; border-bottom: 2px solid transparent; margin-bottom: -2px; }
.pa-tab.active { color: #1a73e8; border-bottom-color: #1a73e8; font-weight: 500; }
.pa-panel-head { font-size: 13px; font-weight: 500; color: #374151; margin-bottom: 10px; }
.pa-scroll { max-height: 360px; overflow-y: auto; border: 1px solid #e2e8f0; border-radius: 8px; }
.pa-table { width: 100%; border-collapse: collapse; font-size: 12px; }
.pa-table th, .pa-table td { padding: 6px 8px; border: 1px solid #e2e8f0; text-align: left; }
.pa-table th { background: #f8fafc; font-weight: 600; color: #475569; white-space: nowrap; }
.pa-table tr:hover { background: #f1f5f9; }
.badge-blue { background: #dbeafe; color: #1e40af; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.ps-sec { margin-bottom: 14px; }
.ps-sec h5 { margin: 0 0 6px; font-size: 14px; color: #334155; }
.sec-count { font-size: 11px; color: #94a3b8; font-weight: normal; }
.score-badge { display: inline-block; background: #dbeafe; color: #1d4ed8; padding: 2px 8px; border-radius: 4px; font-size: 11px; margin-right: 6px; }
.score-overlay { position: fixed; inset: 0; background: rgba(15,23,42,0.45); display: flex; align-items: center; justify-content: center; z-index: 1000; padding: 16px; }
.score-dialog { background: #fff; border-radius: 8px; padding: 20px; width: 420px; max-width: 100%; max-height: 90vh; overflow-y: auto; }
.score-dialog .form-row { margin-bottom: 12px; }
.score-dialog label { display: block; font-size: 13px; color: #475569; margin-bottom: 4px; }
.score-dialog input[type="number"] { width: 100%; border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px; font-size: 13px; outline: none; }
.pa-empty { color: #94a3b8; text-align: center; padding: 30px; font-size: 14px; }
.score-input { width: 70px !important; padding: 4px 6px !important; font-size: 12px !important; text-align: center; }
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn { display: inline-flex; align-items: center; gap: 4px; border-radius: 6px; cursor: pointer; font-size: 13px; padding: 6px 14px; border: 1px solid transparent; transition: all 0.15s; }
.btn-primary { background: #1a73e8; color: white; border-color: #1a73e8; }
.btn-primary:hover { background: #1557b0; }
.btn-primary:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-outline { background: white; color: #475569; border-color: #d1d5db; }
.btn-outline:hover { background: #f8fafc; border-color: #3b82f6; color: #3b82f6; }
.btn-danger { background: #ef4444; color: white; border-color: #ef4444; }
.btn-danger:hover { background: #dc2626; }
.input { border: 1px solid #d1d5db; border-radius: 6px; padding: 6px 10px; font-size: 13px; outline: none; }
.input:focus { border-color: #3b82f6; box-shadow: 0 0 0 2px rgba(59,130,246,0.15); }
select.input { min-width: 100px; }
.abcd-badge { display: inline-block; padding: 2px 10px; border-radius: 4px; font-weight: 600; font-size: 12px; }
.abcd-a { background: #d1fae5; color: #059669; }
.abcd-b { background: #dbeafe; color: #1d4ed8; }
.abcd-c { background: #fef3c7; color: #b45309; }
.abcd-d { background: #fee2e2; color: #dc2626; }
.stats-summary { display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; }
.stat-card { background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px 20px; text-align: center; min-width: 100px; flex: 1; }
.stat-value { font-size: 22px; font-weight: 700; color: #1a73e8; }
.stat-label { font-size: 11px; color: #64748b; margin-top: 2px; }

.badge-pending { background: #fef3c7; color: #92400e; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.badge-approved { background: #d1fae5; color: #065f46; padding: 2px 8px; border-radius: 10px; font-size: 11px; }
.badge-rejected { background: #fee2e2; color: #991b1b; padding: 2px 8px; border-radius: 10px; font-size: 11px; }


/* 响应式 */
@media (max-width: 768px) {
  .pc-table { font-size: 12px; display: block; overflow-x: auto; }
  .pc-table th, .pc-table td { padding: 4px 6px; }
}
@media (max-width: 480px) {
  .pc-table { font-size: 11px; }
  .pc-table th, .pc-table td { padding: 3px 4px; }
}

</style>
