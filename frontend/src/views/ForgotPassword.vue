<template>
  <div class="forgot-password-page">
    <div class="container">
      <div class="forgot-card card">
        <h2>Forgot Password</h2>
        
        <!-- Step 1: Request OTP -->
        <div v-if="step === 1">
          <p class="step-description">Enter your email address to receive a password reset code</p>
          <form @submit.prevent="requestOTP">
            <div class="form-group">
              <label for="email">Email Address</label>
              <input
                type="email"
                id="email"
                v-model="form.email"
                required
                placeholder="Enter your email"
              />
            </div>

            <div v-if="error" class="error">{{ error }}</div>
            <div v-if="successMessage" class="success">{{ successMessage }}</div>

            <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
              <span v-if="loading" class="loading"></span>
              <span v-else>Send OTP</span>
            </button>
          </form>
        </div>

        <!-- Step 2: Verify OTP -->
        <div v-if="step === 2">
          <p class="step-description">Enter the 6-digit code sent to {{ form.email }}</p>
          <form @submit.prevent="verifyOTP">
            <div class="form-group">
              <label for="otp">OTP Code</label>
              <input
                type="text"
                id="otp"
                v-model="form.otp"
                required
                placeholder="Enter 6-digit code"
                maxlength="6"
                class="otp-input"
              />
            </div>

            <p class="otp-info">OTP expires in 10 minutes</p>

            <div v-if="error" class="error">{{ error }}</div>
            <div v-if="successMessage" class="success">{{ successMessage }}</div>

            <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
              <span v-if="loading" class="loading"></span>
              <span v-else>Verify OTP</span>
            </button>

            <p class="resend-link">
              <button type="button" @click="requestOTP" class="link-button">
                Resend OTP
              </button>
            </p>
          </form>
        </div>

        <!-- Step 3: Reset Password -->
        <div v-if="step === 3">
          <p class="step-description">Enter your new password</p>
          <form @submit.prevent="resetPassword">
            <div class="form-group">
              <label for="newPassword">New Password</label>
              <input
                type="password"
                id="newPassword"
                v-model="form.newPassword"
                required
                placeholder="Enter new password (min. 8 characters)"
                minlength="8"
              />
              <span class="password-hint">Minimum 8 characters</span>
            </div>

            <div class="form-group">
              <label for="confirmPassword">Confirm Password</label>
              <input
                type="password"
                id="confirmPassword"
                v-model="form.confirmPassword"
                required
                placeholder="Confirm your password"
                minlength="8"
              />
            </div>

            <div v-if="error" class="error">{{ error }}</div>
            <div v-if="successMessage" class="success">{{ successMessage }}</div>

            <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
              <span v-if="loading" class="loading"></span>
              <span v-else>Reset Password</span>
            </button>
          </form>
        </div>

        <!-- Success State -->
        <div v-if="step === 4" class="success-state">
          <div class="success-icon">✓</div>
          <h3>Password Reset Successful</h3>
          <p>Your password has been successfully reset.</p>
          <router-link to="/login" class="btn btn-primary btn-block">
            Back to Login
          </router-link>
        </div>

        <p class="back-link" v-if="step < 4">
          <router-link to="/login">← Back to Login</router-link>
        </p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import axios from 'axios'

export default {
  name: 'ForgotPassword',
  setup() {
    const router = useRouter()
    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8808'

    const form = ref({
      email: '',
      otp: '',
      newPassword: '',
      confirmPassword: ''
    })

    const step = ref(1)
    const loading = ref(false)
    const error = ref(null)
    const successMessage = ref(null)

    const requestOTP = async () => {
      loading.value = true
      error.value = null
      successMessage.value = null

      try {
        await axios.post(`${API_URL}/auth/forgot-password`, {
          email: form.value.email
        })

        successMessage.value = 'OTP sent to your email'
        setTimeout(() => {
          step.value = 2
          successMessage.value = null
        }, 2000)
      } catch (err) {
        error.value = err.response?.data?.detail || 'Failed to send OTP'
      } finally {
        loading.value = false
      }
    }

    const verifyOTP = async () => {
      if (!form.value.otp || form.value.otp.length !== 6) {
        error.value = 'Please enter a valid 6-digit OTP'
        return
      }

      loading.value = true
      error.value = null
      successMessage.value = null

      try {
        const response = await axios.post(`${API_URL}/auth/verify-otp`, {
          email: form.value.email,
          otp: form.value.otp
        })

        form.value.verificationToken = response.data.verification_token
        successMessage.value = 'OTP verified successfully'
        setTimeout(() => {
          step.value = 3
          successMessage.value = null
        }, 2000)
      } catch (err) {
        error.value = err.response?.data?.detail || 'Invalid OTP'
      } finally {
        loading.value = false
      }
    }

    const resetPassword = async () => {
      error.value = null
      successMessage.value = null

      // Validation
      if (form.value.newPassword.length < 8) {
        error.value = 'Password must be at least 8 characters long'
        return
      }

      if (form.value.newPassword !== form.value.confirmPassword) {
        error.value = 'Passwords do not match'
        return
      }

      loading.value = true

      try {
        await axios.post(`${API_URL}/auth/reset-password`, {
          email: form.value.email,
          otp: form.value.otp,
          new_password: form.value.newPassword
        })

        successMessage.value = 'Password reset successfully!'
        setTimeout(() => {
          step.value = 4
        }, 1000)
      } catch (err) {
        error.value = err.response?.data?.detail || 'Failed to reset password'
      } finally {
        loading.value = false
      }
    }

    return {
      form,
      step,
      loading,
      error,
      successMessage,
      requestOTP,
      verifyOTP,
      resetPassword
    }
  }
}
</script>

<style scoped>
.forgot-password-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 200px);
  padding: 2rem 1rem;
}

.forgot-card {
  max-width: 450px;
  width: 100%;
}

.forgot-card h2 {
  text-align: center;
  margin-bottom: 1.5rem;
  color: #2c3e50;
}

.step-description {
  text-align: center;
  color: #666;
  margin-bottom: 1.5rem;
  font-size: 0.95rem;
}

.btn-block {
  width: 100%;
  margin-top: 1rem;
}

.error {
  background-color: #fee;
  color: #c33;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.success {
  background-color: #efe;
  color: #3a3;
  padding: 0.75rem;
  border-radius: 4px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.otp-input {
  font-size: 1.2rem;
  letter-spacing: 2px;
  text-align: center;
  font-family: monospace;
}

.otp-info {
  font-size: 0.85rem;
  color: #999;
  text-align: center;
  margin: 0.5rem 0 1rem;
}

.password-hint {
  font-size: 0.8rem;
  color: #999;
  display: block;
  margin-top: 0.25rem;
}

.resend-link,
.back-link {
  text-align: center;
  margin-top: 1rem;
}

.link-button {
  background: none;
  border: none;
  color: #3498db;
  text-decoration: none;
  cursor: pointer;
  font-size: 0.95rem;
  padding: 0;
}

.link-button:hover {
  text-decoration: underline;
}

.back-link a {
  color: #3498db;
  text-decoration: none;
}

.back-link a:hover {
  text-decoration: underline;
}

.success-state {
  text-align: center;
  padding: 2rem 0;
}

.success-icon {
  font-size: 3rem;
  color: #27ae60;
  margin-bottom: 1rem;
}

.success-state h3 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.success-state p {
  color: #666;
  margin-bottom: 1.5rem;
}

@media (max-width: 768px) {
  .forgot-password-page {
    min-height: 100vh;
  }
  
  .forgot-card {
    margin: 1rem;
  }
}
</style>
