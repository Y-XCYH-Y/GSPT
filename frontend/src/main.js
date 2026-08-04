import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import './style.css'

const app = createApp(App)

// 先创建 pinia
const pinia = createPinia()
app.use(pinia)

// 延迟加载 router，避免循环依赖
import('./router/index.js').then(module => {
  app.use(module.default)
  app.mount('#app')
}).catch(err => {
  console.error('路由加载失败:', err)
  // 即使路由失败也挂载应用
  app.mount('#app')
})