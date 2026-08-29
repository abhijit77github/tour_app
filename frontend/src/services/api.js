import axios from 'axios'

const api = axios.create({
  baseURL: import.meta?.env?.VITE_API_URL || 'http://localhost:8808',
  headers: {
    'Content-Type': 'application/json'
  }
})

export function resolveAuthTokenForRequest(requestUrl, storage = localStorage) {
  const url = requestUrl || ''
  const isAdminRequest = url.startsWith('/admin')
  return isAdminRequest ? storage.getItem('adminToken') : storage.getItem('token')
}

export function applyAuthorizationHeader(config, storage = localStorage) {
  const token = resolveAuthTokenForRequest(config.url, storage)

  if (!config.headers) {
    config.headers = {}
  }

  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  } else if (config.headers.Authorization) {
    delete config.headers.Authorization
  }

  return config
}

// Request interceptor to add auth token
api.interceptors.request.use(
  (config) => {
    return applyAuthorizationHeader(config)
  },
  (error) => {
    return Promise.reject(error)
  }
)

// Response interceptor to handle errors
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const requestUrl = error.config?.url || ''
    const isAdminRequest = requestUrl.startsWith('/admin')

    if (error.response?.status === 401) {
      if (isAdminRequest) {
        localStorage.removeItem('adminToken')
        localStorage.removeItem('adminUser')
        window.location.href = '/admin/login'
      } else {
        localStorage.removeItem('token')
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default api
