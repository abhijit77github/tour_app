<template>
  <div class="admin-login-page">
    <!-- Background -->
    <div class="login-background"></div>

    <!-- Login Container -->
    <div class="login-container">
      <div class="login-card">
        <!-- Logo/Header -->
        <div class="login-header">
          <h1>Admin Portal</h1>
          <p>Tour App Management System</p>
        </div>

        <!-- Form -->
        <form @submit.prevent="handleLogin" class="login-form">
          <!-- Email Field -->
          <div class="form-group">
            <label for="email">Email Address</label>
            <input
              id="email"
              v-model="credentials.email"
              type="email"
              placeholder="admin@tourapp.com"
              class="form-control"
              required
            />
          </div>

          <!-- Password Field -->
          <div class="form-group">
            <label for="password">Password</label>
            <div class="password-wrapper">
              <input
                id="password"
                v-model="credentials.password"
                :type="showPassword ? 'text' : 'password'"
                placeholder="Enter your password"
                class="form-control"
                required
              />
              <button
                type="button"
                @click="showPassword = !showPassword"
                class="toggle-password"
              >
                {{ showPassword ? '👁️' : '👁️‍🗨️' }}
              </button>
            </div>
          </div>

          <!-- Remember Me -->
          <div class="form-group checkbox">
            <input
              id="remember"
              v-model="rememberMe"
              type="checkbox"
              class="checkbox-control"
            />
            <label for="remember">Remember me</label>
          </div>

          <!-- Error Message -->
          <div v-if="error" class="error-message">
            {{ error }}
          </div>

          <!-- Submit Button -->
          <button
            type="submit"
            :disabled="loading"
            class="btn-login"
          >
            <span v-if="!loading">Login to Admin Dashboard</span>
            <span v-else class="loading">
              <span class="spinner"></span>
              Authenticating...
            </span>
          </button>
        </form>

        <!-- Footer -->
        <div class="login-footer">
          <p>For security issues, contact support@tourapp.com</p>
        </div>
      </div>

      <!-- Security Notice -->
      <div class="security-notice">
        <p>🔒 This is a secure area. Only authorized administrators have access.</p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'

const router = useRouter()
const authStore = useAuthStore()

const credentials = ref({
  email: '',
  password: ''
})

const showPassword = ref(false)
const rememberMe = ref(false)
const loading = ref(false)
const error = ref('')

const handleLogin = async () => {
  error.value = ''
  loading.value = true

  try {
    // Validate inputs
    if (!credentials.value.email || !credentials.value.password) {
      error.value = 'Please enter email and password'
      loading.value = false
      return
    }

    // Call admin login endpoint
    const response = await api.post('/admin/login', {
      email: credentials.value.email,
      password: credentials.value.password
    })

    if (response.data && response.data.access_token) {
      // Store admin token and info
      const token = response.data.access_token
      const admin = response.data.admin

      // Store in localStorage
      localStorage.setItem('adminToken', token)
      localStorage.setItem('adminUser', JSON.stringify(admin))

      // Update axios default header for admin token
      api.defaults.headers.common['Authorization'] = `Bearer ${token}`

      // Redirect to admin dashboard
      await router.push('/admin/dashboard')
    }
  } catch (err) {
    console.error('Login error:', err)
    if (err.response?.data?.detail) {
      error.value = err.response.data.detail
    } else {
      error.value = 'Login failed. Please try again.'
    }
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.admin-login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
  position: relative;
  overflow: hidden;
}

.login-background {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  opacity: 0.1;
  background-image: 
    radial-gradient(circle at 20% 50%, #fff 1px, transparent 1px),
    radial-gradient(circle at 80% 80%, #fff 1px, transparent 1px);
  background-size: 50px 50px, 80px 80px;
  pointer-events: none;
}

.login-container {
  position: relative;
  z-index: 1;
  width: 100%;
  max-width: 420px;
  padding: 2rem;
}

.login-card {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  padding: 3rem 2.5rem;
  backdrop-filter: blur(10px);
  animation: slideUp 0.5s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Header */
.login-header {
  text-align: center;
  margin-bottom: 2rem;
}

.login-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 0.5rem 0;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.login-header p {
  color: #718096;
  font-size: 0.95rem;
  margin: 0;
}

/* Form */
.login-form {
  width: 100%;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-size: 0.95rem;
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 0.5rem;
}

.form-control {
  width: 100%;
  padding: 0.75rem 1rem;
  font-size: 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  transition: all 0.3s ease;
  font-family: inherit;
}

.form-control:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
  background-color: #f7fafc;
}

.form-control::placeholder {
  color: #cbd5e0;
}

/* Password Wrapper */
.password-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.password-wrapper .form-control {
  width: 100%;
  padding-right: 2.5rem;
}

.toggle-password {
  position: absolute;
  right: 1rem;
  background: none;
  border: none;
  font-size: 1.2rem;
  cursor: pointer;
  color: #718096;
  transition: color 0.2s;
  padding: 0.5rem;
}

.toggle-password:hover {
  color: #667eea;
}

/* Checkbox */
.form-group.checkbox {
  display: flex;
  align-items: center;
  margin-bottom: 1.5rem;
}

.checkbox-control {
  width: 1.2rem;
  height: 1.2rem;
  cursor: pointer;
  accent-color: #667eea;
  margin-right: 0.5rem;
}

.form-group.checkbox label {
  margin: 0;
  font-weight: 500;
  cursor: pointer;
}

/* Error Message */
.error-message {
  background-color: #fed7d7;
  color: #c53030;
  padding: 0.75rem 1rem;
  border-radius: 8px;
  font-size: 0.9rem;
  margin-bottom: 1.5rem;
  border-left: 4px solid #c53030;
}

/* Login Button */
.btn-login {
  width: 100%;
  padding: 0.875rem 1rem;
  font-size: 1rem;
  font-weight: 600;
  color: white;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.3s ease;
  box-shadow: 0 4px 15px rgba(102, 126, 234, 0.3);
  margin-bottom: 1rem;
}

.btn-login:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.btn-login:active:not(:disabled) {
  transform: translateY(0);
}

.btn-login:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.btn-login .loading {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
}

.spinner {
  display: inline-block;
  width: 1rem;
  height: 1rem;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top-color: white;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

/* Footer */
.login-footer {
  text-align: center;
  color: #718096;
  font-size: 0.85rem;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.login-footer p {
  margin: 0;
}

/* Security Notice */
.security-notice {
  text-align: center;
  margin-top: 2rem;
  padding: 1rem;
  background: rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: white;
  font-size: 0.9rem;
  backdrop-filter: blur(10px);
}

.security-notice p {
  margin: 0;
}

/* Responsive */
@media (max-width: 480px) {
  .login-container {
    padding: 1rem;
  }

  .login-card {
    padding: 2rem 1.5rem;
  }

  .login-header h1 {
    font-size: 1.75rem;
  }

  .form-control {
    font-size: 16px; /* Prevents zoom on iOS */
  }
}
</style>
