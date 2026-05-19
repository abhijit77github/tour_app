<template>
  <div class="login-page">
    <div class="container">
      <div class="login-card card">
        <p class="kicker">Welcome back</p>
        <h2>Sign In to Continue</h2>
        <p class="intro">Use your tourist or operator account to access your dashboard.</p>
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
  padding: 1rem 0;
}

.login-card {
  max-width: 400px;
  width: 100%;
  border-radius: 18px;
}

.kicker {
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 0.76rem;
  font-weight: 700;
  color: #0f766e;
}

.login-card h2 {
  text-align: center;
  margin: 0.25rem 0 0.35rem;
  color: #0f172a;
  font-size: 1.75rem;
  font-family: 'Fraunces', Georgia, serif;
}

.intro {
  text-align: center;
  margin-bottom: 1.35rem;
  color: #64748b;
  font-size: 0.95rem;
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
  color: #0f766e;
  text-decoration: none;
  font-weight: 700;
}

.register-link a:hover {
  text-decoration: underline;
}

.forgot-password-link {
  text-align: right;
  margin-bottom: 1rem;
}

.forgot-password-link a {
  color: #0f766e;
  text-decoration: none;
  font-size: 0.9rem;
  font-weight: 600;
}

.forgot-password-link a:hover {
  text-decoration: underline;
}

.error {
  background: rgba(220, 38, 38, 0.08);
  border: 1px solid rgba(220, 38, 38, 0.25);
  border-radius: 8px;
  padding: 0.55rem 0.65rem;
  margin-top: 0.25rem;
}
</style>
