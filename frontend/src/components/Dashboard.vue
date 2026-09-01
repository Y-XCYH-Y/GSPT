<template>
  <div class="dashboard">
    <div class="dash-head">
      <h3>数据看板</h3>
      <span class="dash-year">{{ year }} 年</span>
    </div>
    <div v-if="loading" class="dash-loading">看板加载中...</div>
    <template v-else>
      <div class="stat-grid">
        <div class="stat-card" v-for="c in cards" :key="c.label">
          <div class="stat-value">{{ c.value }}</div>
          <div class="stat-label">{{ c.label }}</div>
        </div>
      </div>
      <div class="chart-grid">
        <div class="chart-box chart-span-2">
          <div class="chart-title">当年工天月度趋势</div>
          <div ref="trendRef" class="chart-canvas"></div>
        </div>
        <div class="chart-box">
          <div class="chart-title">项目状态分布</div>
          <div ref="statusRef" class="chart-canvas"></div>
        </div>
        <div class="chart-box">
          <div class="chart-title">各项目工天分布</div>
          <div ref="pieRef" class="chart-canvas"></div>
        </div>
        <div class="chart-box chart-span-2">
          <div class="chart-title">人员工天排名 TOP10</div>
          <div ref="rankRef" class="chart-canvas"></div>
        </div>
      </div>
    </template>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount, nextTick } from "vue"
import * as echarts from "echarts"
import { useAuthStore } from "../stores/auth"

const auth = useAuthStore()
const year = new Date().getFullYear()
const loading = ref(true)
const overview = ref(null)
const trendRef = ref()
const statusRef = ref()
const pieRef = ref()
const rankRef = ref()
let charts = []

const cards = computed(() => {
  const o = overview.value || {}
  return [
    { label: "项目总数", value: o.project_count ?? "-" },
    { label: "在手项目数", value: o.active_project_count ?? "-" },
    { label: "在职人员", value: o.staff_count ?? "-" },
    { label: year + "年工天", value: o.year_workdays ?? "-" }
  ]
})

function authHeaders() {
  return { "Content-Type": "application/json", Authorization: "Bearer " + (auth.token || "") }
}

async function loadData() {
  try {
    const [ov, wd] = await Promise.all([
      fetch("/api/dashboard/overview", { headers: authHeaders() }).then(r => r.json()),
      fetch("/api/dashboard/workdays?year=" + year, { headers: authHeaders() }).then(r => r.json())
    ])
    overview.value = ov
    loading.value = false
    await nextTick()
    renderCharts(wd)
  } catch (e) {
    loading.value = false
    console.error(e)
  }
}

function renderCharts(wd) {
  if (!wd) return
  charts.forEach(c => c.dispose())
  charts = []
  const palette = ["#1a73e8", "#0ea5e9", "#22c55e", "#f59e0b", "#ef4444", "#8b5cf6", "#14b8a6", "#64748b"]

  const trend = echarts.init(trendRef.value)
  trend.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 48, right: 18, top: 30, bottom: 30 },
    xAxis: { type: "category", data: wd.month_trend.map(d => d.month.slice(5)) },
    yAxis: { type: "value", name: "工天" },
    series: [{
      data: wd.month_trend.map(d => d.workdays),
      type: "line",
      smooth: true,
      areaStyle: { color: "rgba(26,115,232,0.14)" },
      itemStyle: { color: "#1a73e8" }
    }]
  })
  charts.push(trend)

  const status = echarts.init(statusRef.value)
  status.setOption({
    tooltip: { trigger: "item" },
    legend: { bottom: 0, textStyle: { fontSize: 11 } },
    color: palette,
    series: [{
      type: "pie",
      radius: ["36%", "62%"],
      center: ["50%", "44%"],
      label: { fontSize: 11 },
      data: (overview.value.status_distribution || []).filter(d => d.value > 0)
    }]
  })
  charts.push(status)

  const pie = echarts.init(pieRef.value)
  pie.setOption({
    tooltip: { trigger: "item" },
    legend: { type: "scroll", bottom: 0, textStyle: { fontSize: 10 } },
    color: palette,
    series: [{ type: "pie", radius: "62%", center: ["50%", "44%"], data: wd.project_distribution }]
  })
  charts.push(pie)

  const rank = echarts.init(rankRef.value)
  rank.setOption({
    tooltip: { trigger: "axis" },
    grid: { left: 84, right: 34, top: 18, bottom: 28 },
    xAxis: { type: "value" },
    yAxis: { type: "category", data: wd.person_ranking.map(d => d.name).reverse() },
    series: [{
      type: "bar",
      data: wd.person_ranking.map(d => d.workdays).reverse(),
      itemStyle: { color: "#1a73e8", borderRadius: [0, 4, 4, 0] },
      label: { show: true, position: "right", fontSize: 11 }
    }]
  })
  charts.push(rank)
}

function onResize() {
  charts.forEach(c => c.resize())
}

onMounted(() => {
  loadData()
  window.addEventListener("resize", onResize)
})

onBeforeUnmount(() => {
  window.removeEventListener("resize", onResize)
  charts.forEach(c => c.dispose())
})
</script>

<style scoped>
.dashboard { padding: 2px 0; }
.dash-head { display: flex; align-items: center; gap: 10px; margin-bottom: 14px; }
.dash-head h3 { margin: 0; font-size: 16px; color: #1e293b; }
.dash-year { font-size: 12px; color: #64748b; background: #f1f5f9; padding: 3px 10px; border-radius: 20px; }
.dash-loading { padding: 40px; color: #64748b; text-align: center; }
.stat-grid { display: grid; grid-template-columns: repeat(4, 1fr); gap: 12px; margin-bottom: 14px; }
.stat-card { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 14px 16px; }
.stat-value { font-size: 22px; font-weight: 600; color: #1a73e8; }
.stat-label { font-size: 12px; color: #64748b; margin-top: 4px; }
.chart-grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 12px; }
.chart-box { background: #fff; border: 1px solid #e2e8f0; border-radius: 8px; padding: 12px; }
.chart-span-2 { grid-column: span 2; }
.chart-title { font-size: 13px; font-weight: 600; color: #334155; margin-bottom: 8px; }
.chart-canvas { width: 100%; height: 280px; }
@media (max-width: 900px) {
  .stat-grid { grid-template-columns: repeat(2, 1fr); }
  .chart-grid { grid-template-columns: 1fr; }
  .chart-span-2 { grid-column: span 1; }
  .chart-canvas { height: 240px; }
}
</style>
