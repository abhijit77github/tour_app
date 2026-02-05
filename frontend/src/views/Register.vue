<template>
  <div class="register-page">
    <div class="container">
      <div class="register-card card">
        <h2>Create Account</h2>
        <form @submit.prevent="handleRegister">
          <div class="form-group">
            <label for="user_type">I am a</label>
            <select id="user_type" v-model="form.user_type" required>
              <option value="">Select type</option>
              <option value="tourist">Tourist</option>
              <option value="operator">Tour Operator</option>
            </select>
          </div>

          <div class="form-group">
            <label for="full_name">Full Name</label>
            <input
              type="text"
              id="full_name"
              v-model="form.full_name"
              required
              placeholder="Enter your full name"
            />
          </div>

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
            <label for="phone">Phone Number</label>
            <input
              type="tel"
              id="phone"
              v-model="form.phone"
              placeholder="Enter your phone number"
            />
          </div>

          <div class="form-group">
            <label for="password">Password</label>
            <input
              type="password"
              id="password"
              v-model="form.password"
              required
              placeholder="Create a password"
            />
          </div>

          <div v-if="error" class="error">{{ error }}</div>
          <div v-if="success" class="success">{{ success }}</div>

          <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
            <span v-if="loading" class="loading"></span>
            <span v-else>Register</span>
          </button>
        </form>

        <p class="login-link">
          Already have an account? <router-link to="/login">Login here</router-link>
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
  name: 'Register',
  setup() {
    const router = useRouter()
    const authStore = useAuthStore()

    const form = ref({
      email: '',
      full_name: '',
      phone: '',
      password: '',
      user_type: ''
    })

    const loading = ref(false)
    const error = ref(null)
    const success = ref(null)

    const handleRegister = async () => {
      loading.value = true
      error.value = null
      success.value = null

      try {
        await authStore.register(form.value)
        success.value = 'Registration successful! Redirecting to login...'
        
        setTimeout(() => {
          router.push('/login')
        }, 2000)
      } catch (err) {
        error.value = err.response?.data?.detail || 'Registration failed'
      } finally {
        loading.value = false
      }
    }

    return {
      form,
      loading,
      error,
      success,
      handleRegister
    }
  }
}
</script>

<style scoped>
.register-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 200px);
  padding: 2rem 0;
}

.register-card {
  max-width: 500px;
  width: 100%;
}

.register-card h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: #2c3e50;
}

.btn-block {
  width: 100%;
  margin-top: 1rem;
}

.login-link {
  text-align: center;
  margin-top: 1rem;
}

.login-link a {
  color: #3498db;
  text-decoration: none;
}

.login-link a:hover {
  text-decoration: underline;
}
</style>
