<template>
  <div class="platform-layout">
    <header class="p-topbar">
      <div class="p-left">
        <span class="p-logo">🏛️ 建筑一所</span>
        <span class="p-divider">|</span>
        <span class="p-sub">生产调度平台</span>
      </div>
      <nav class="p-nav">
        <button :class="{active:mainTab==='daily'}" @click="mainTab='daily'">日常</button>
        <button :class="{active:mainTab==='mine'}" @click="mainTab='mine'">我的</button>
      </nav>
      <div class="p-right">
        <span class="p-role" :class="authStore.isDirector?'role-dir':'role-member'">
          {{ authStore.isDirector ? '所长' : '成员' }}
        </span>
        <span class="p-user">{{ authStore.userName }}</span>
        <button class="p-logout" @click="handleLogout">退出</button>
      </div>
    </header>
    <div class="p-body">
      <div v-if="mainTab==='daily'" class="p-daily">
        <aside class="p-sidebar">
          <button v-for="item in dailyMenu" :key="item.key" :class="{active:subTab===item.key}" @click="subTab=item.key">
            <span class="s-icon">{{ item.icon }}</span>
            <span class="s-label">{{ item.label }}</span>
          </button>
        </aside>
        <main class="p-main">
          <EmployeeManager v-if="subTab==='employee'" />
          <ProjectManager v-if="subTab==='project'" />
          <PerformanceAssessment v-if="subTab==='assessment'" />
          <KnowledgeBase v-if="subTab==='knowledge'" />
          <AuditManager v-if="subTab==='audit'" />
        </main>
      </div>
      <div v-if="mainTab==='mine'" class="p-mine">
        <div class="mine-header"><h3>个人中心</h3></div>
        <AccountManager />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from "vue"
import AuditManager from "../components/AuditManager.vue"
import { useRouter } from "vue-router"
import { useAuthStore } from "../stores/auth"
import EmployeeManager from "../components/EmployeeManager.vue"
import ProjectManager from "../components/ProjectManager.vue"
import PerformanceAssessment from "../components/PerformanceAssessment.vue"
import KnowledgeBase from "../components/KnowledgeBase.vue"
import AccountManager from "../components/AccountManager.vue"

const router = useRouter()
const authStore = useAuthStore()

const mainTab = ref("daily")
const subTab = ref("")

const dailyMenu = computed(() => {
  var items = []
  if (authStore.isDirector || authStore.isDeputyDirector) {
    items.push({ key: "employee", icon: "👥", label: "员工" })
  }
  items.push({ key: "project", icon: "📋", label: "项目" })
  items.push({ key: "assessment", icon: "📊", label: "考核" })
  if (authStore.isDirector) {
    items.push({ key: "knowledge", icon: "📚", label: "库" })
    items.push({ key: "audit", icon: "✅", label: "审核" })
  }
  return items
})

if (!subTab.value && dailyMenu.value.length) {
  subTab.value = dailyMenu.value[0].key
}

function handleLogout() {
  authStore.logout()
  router.push("/login")
}
</script>

<style scoped>
.platform-layout { min-height: 100vh; background: #f1f5f9; display: flex; flex-direction: column; }
.p-topbar { display: flex; align-items: center; justify-content: space-between; height: 56px; padding: 0 24px; background: linear-gradient(135deg, #0f172a, #1e3a5f); color: white; flex-shrink: 0; }
.p-left { display: flex; align-items: center; gap: 8px; }
.p-logo { font-size: 16px; font-weight: 600; }
.p-divider { color: #475569; font-size: 14px; }
.p-sub { font-size: 13px; color: #94a3b8; }
.p-nav { display: flex; gap: 2px; }
.p-nav button { background: transparent; border: none; color: #94a3b8; padding: 8px 24px; font-size: 14px; cursor: pointer; border-radius: 6px; transition: all 0.15s; }
.p-nav button:hover { color: white; background: rgba(255,255,255,0.1); }
.p-nav button.active { color: white; background: rgba(255,255,255,0.15); font-weight: 500; }
.p-right { display: flex; align-items: center; gap: 10px; }
.p-role { font-size: 11px; padding: 2px 10px; border-radius: 4px; }
.role-dir { background: #059669; color: white; }
.role-member { background: #3b82f6; color: white; }
.p-user { font-size: 13px; color: #e2e8f0; }
.p-logout { background: transparent; border: 1px solid rgba(255,255,255,0.3); color: #cbd5e1; padding: 4px 12px; border-radius: 4px; font-size: 12px; cursor: pointer; transition: all 0.15s; }
.p-logout:hover { border-color: #ef4444; color: #fca5a5; }
.p-body { flex: 1; display: flex; }
.p-daily { display: flex; flex: 1; }
.p-sidebar { width: 160px; background: white; border-right: 1px solid #e2e8f0; padding: 12px 0; flex-shrink: 0; }
.p-sidebar button { display: flex; align-items: center; gap: 8px; width: 100%; padding: 10px 20px; border: none; background: transparent; font-size: 14px; color: #475569; cursor: pointer; text-align: left; transition: all 0.15s; }
.p-sidebar button:hover { background: #f1f5f9; color: #1a73e8; }
.p-sidebar button.active { background: #eff6ff; color: #1a73e8; font-weight: 500; border-right: 3px solid #1a73e8; }
.s-icon { font-size: 18px; }
.s-label { font-size: 14px; }
.p-main { flex: 1; padding: 20px 24px; overflow-y: auto; }
.p-mine { flex: 1; padding: 20px 24px; }
.mine-header h3 { font-size: 18px; color: #1e293b; margin: 0 0 20px 0; }


/* 响应式 */
@media (max-width: 768px) {
  .p-topbar {
    padding: 0 12px;
    height: 48px;
    flex-wrap: wrap;
  }
  .p-left { gap: 4px; }
  .p-logo { font-size: 14px; }
  .p-sub { display: none; }
  .p-divider { display: none; }
  .p-nav button { padding: 6px 14px; font-size: 13px; }
  .p-user { display: none; }
  .p-role { font-size: 10px; padding: 1px 8px; }
  .p-logout { padding: 3px 8px; font-size: 11px; }
  .p-body { flex-direction: column; }
  .p-daily { flex-direction: column; }
  .p-sidebar {
    width: 100%;
    display: flex;
    flex-direction: row;
    overflow-x: auto;
    border-right: none;
    border-bottom: 1px solid #e2e8f0;
    padding: 4px 8px;
    gap: 2px;
    -webkit-overflow-scrolling: touch;
  }
  .p-sidebar button {
    flex-shrink: 0;
    width: auto;
    padding: 8px 12px;
    white-space: nowrap;
    border-right: none;
    border-radius: 6px;
  }
  .p-sidebar button.active {
    border-right: none;
    background: #eff6ff;
  }
  .s-icon { font-size: 16px; }
  .s-label { font-size: 13px; }
  .p-main { padding: 12px; }
  .p-mine { padding: 12px; }
}
@media (max-width: 480px) {
  .p-topbar { height: 44px; padding: 0 8px; }
  .p-logo { font-size: 13px; }
  .p-nav button { padding: 4px 10px; font-size: 12px; }
  .p-sidebar button { padding: 6px 10px; }
  .p-main { padding: 8px; }
  .p-mine { padding: 8px; }
}

</style>