import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useEmployeeStore = defineStore('employees', () => {
  const employees = ref([])
  
  async function loadEmployees() {
    try {
      const res = await fetch('/api/employees', {
        headers: { Authorization: 'Bearer ' + localStorage.getItem('access_token') }
      })
      if (res.ok) {
        employees.value = await res.json()
      }
    } catch (e) {
      console.error('load employees error:', e)
    }
  }

  return { employees, loadEmployees }
})
