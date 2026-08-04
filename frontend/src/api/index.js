import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 15000,
  headers: { 'Content-Type': 'application/json' }
})

api.interceptors.request.use(config => {
  const token = localStorage.getItem('access_token')
  if (token) {
    config.headers.Authorization = 'Bearer ' + token
  }
  return config
})

api.interceptors.response.use(
  response => response,
  error => {
    if (error.response?.status === 401) {
      localStorage.removeItem('access_token')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const userAPI = {
  getMe: () => api.get('/user/me'),
}

// ???? API
export const employeeAPI = {
  create: (data) => api.post('/employees', data),
  update: (id, data) => api.put('/employees/' + id, data),
  delete: (id) => api.delete('/employees/' + id),
  clearAll: () => api.post('/employees/clear-all'),
}

// ???? API
export const configAPI = {
  getConstants: () => api.get('/config/constants')
}

// ???? API
export const performanceAPI = {
  getMyProjects: () => api.get('/performance/my-projects'),
  getAssessments: () => api.get('/performance/assessments'),
  createAssessment: (data) => api.post('/performance/assessments', data),
  getWorkdays: (aid) => api.post('/performance/workday-list', { assessment_id: aid }),
  createWorkday: (data) => api.post('/performance/workdays', data),
  deleteWorkday: (id) => api.delete('/performance/workdays/' + id),
  getScores: (aid) => api.get('/performance/scores?assessment_id=' + aid),
  submitScore: (data) => api.post('/performance/scores', data),
  calculateResults: (id) => api.post('/performance/assessments/' + id + '/calculate'),
  getResults: (id) => api.get('/performance/assessments/' + id + '/results')
}

// ???? API
export const adminAPI = {
  getUsers: () => api.get('/admin/users'),
  updateUser: (id, data) => api.put('/admin/users/' + id, data),
}

// ???? API
export const changeRequestAPI = {
  create: (data) => api.post('/change-requests', data),
  list: (status) => api.get('/change-requests' + (status ? '?status=' + status : '')),
  review: (id, data) => api.put('/change-requests/' + id + '/review', data),
}

export default api
