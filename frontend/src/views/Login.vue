<template>
  <div class="login-page">
    <div class="container">
      <div class="login-card card">
        <h2>Login</h2>
        <form @submit.prevent="handleLogin">
          <div class="form-group">
            <label for="email">Email</label>
            <input
              type="email"
              id="email"
              v-model="form.email"
              required
              placeholder="Enter your email"
            />
          </div>
          
          <div class="form-group">
            <label for="password">Password</label>
            <input
              type="password"
              id="password"
              v-model="form.password"
              required
              placeholder="Enter your password"
            />
          </div>

          <div class="forgot-password-link">
            <router-link to="/forgot-password">Forgot Password?</router-link>
          </div>

          <div v-if="error" class="error">{{ error }}</div>

          <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
            <span v-if="loading" class="loading"></span>
            <span v-else>Login</span>
          </button>
        </form>

        <p class="register-link">
          Don't have an account? <router-link to="/register">Register here</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

export default {
  name: 'Login',
  setup() {
    const router = useRouter()
    const authStore = useAuthStore()

    const form = ref({
      email: '',
      password: ''
    })

    const loading = ref(false)
    const error = ref(null)

    const handleLogin = async () => {
      loading.value = true
      error.value = null

      try {
        await authStore.login(form.value)
        
        // Redirect based on user type
        if (authStore.isOperator) {
          router.push('/operator/home')
        } else {
          router.push('/tourist/home')
        }
      } catch (err) {
        error.value = err.response?.data?.detail || 'Login failed'
      } finally {
        loading.value = false
      }
    }

    return {
      form,
      loading,
      error,
      handleLogin
    }
  }
}
</script>

<style scoped>
.login-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 200px);
}

.login-card {
  max-width: 400px;
  width: 100%;
}

.login-card h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: #2c3e50;
}

.btn-block {
  width: 100%;
  margin-top: 1rem;
}

.register-link {
  text-align: center;
  margin-top: 1rem;
}

.register-link a {
  color: #3498db;
  text-decoration: none;
}

.register-link a:hover {
  text-decoration: underline;
}

.forgot-password-link {
  text-align: right;
  margin-bottom: 1rem;
}

.forgot-password-link a {
  color: #3498db;
  text-decoration: none;
  font-size: 0.9rem;
}

.forgot-password-link a:hover {
  text-decoration: underline;
}
</style>
