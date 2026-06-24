<template>
  <div class="register-page">
    <div class="container">
      <div class="register-card card">
        <p class="page-kicker">{{ verificationStep ? 'Secure verification' : 'Join Tour Local' }}</p>
        <h2>{{ verificationStep ? 'Verify Your Email' : 'Create Account' }}</h2>
        <p class="page-intro">
          {{ verificationStep
            ? 'Confirm the one-time passcode to activate your account and continue to login.'
            : 'Create your account to explore operators, request quotes, and plan trips with local experts.' }}
        </p>

        <form v-if="!verificationStep" @submit.prevent="handleRegister">
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

        <form v-else @submit.prevent="handleVerifyOtp">
          <div class="verification-panel">
            <span class="verification-badge">Email confirmation required</span>
            <p class="verification-copy">
              Enter the 6-digit OTP sent to <strong>{{ verificationEmail }}</strong>. Your account will stay inactive until verification is completed.
            </p>
          </div>

          <div class="form-group">
            <label for="otp">Verification OTP</label>
            <input
              type="text"
              id="otp"
              v-model="otp"
              maxlength="6"
              inputmode="numeric"
              required
              placeholder="Enter the 6-digit OTP"
              class="otp-input"
            />
          </div>

          <div v-if="error" class="error">{{ error }}</div>
          <div v-if="success" class="success">{{ success }}</div>

          <button type="submit" class="btn btn-primary btn-block" :disabled="loading">
            <span v-if="loading" class="loading"></span>
            <span v-else>Verify and Activate Account</span>
          </button>

          <button type="button" class="btn btn-secondary btn-block resend-btn" :disabled="loading" @click="handleResendOtp">
            Resend OTP
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
    const verificationStep = ref(false)
    const verificationEmail = ref('')
    const otp = ref('')

    const handleRegister = async () => {
      loading.value = true
      error.value = null
      success.value = null

      try {
        const response = await authStore.register(form.value)
        verificationEmail.value = response.email
        verificationStep.value = true
        success.value = response.message
      } catch (err) {
        error.value = err.response?.data?.detail || 'Registration failed'
      } finally {
        loading.value = false
      }
    }

    const handleVerifyOtp = async () => {
      loading.value = true
      error.value = null
      success.value = null

      try {
        const response = await authStore.verifyRegistrationOtp({
          email: verificationEmail.value,
          otp: otp.value.trim()
        })
        success.value = response.message + ' Redirecting to login...'

        setTimeout(() => {
          router.push('/login')
        }, 1800)
      } catch (err) {
        error.value = err.response?.data?.detail || 'OTP verification failed'
      } finally {
        loading.value = false
      }
    }

    const handleResendOtp = async () => {
      loading.value = true
      error.value = null
      success.value = null

      try {
        const response = await authStore.resendRegistrationOtp(verificationEmail.value)
        success.value = response.message
      } catch (err) {
        error.value = err.response?.data?.detail || 'Failed to resend OTP'
      } finally {
        loading.value = false
      }
    }

    return {
      form,
      loading,
      error,
      success,
      verificationStep,
      verificationEmail,
      otp,
      handleRegister,
      handleVerifyOtp,
      handleResendOtp
    }
  }
}
</script>

<style scoped>
.register-page {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: calc(100vh - 160px);
  padding: 4.5rem 0 2.5rem;
}

.register-card {
  max-width: 540px;
  width: 100%;
  padding: 2.3rem 2rem;
  border-radius: 22px;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.08);
}

.page-kicker {
  text-align: center;
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 0.75rem;
  font-weight: 800;
  color: #0f766e;
  margin-bottom: 0.55rem;
}

.register-card h2 {
  text-align: center;
  margin-bottom: 0.75rem;
  color: #0f172a;
  font-family: 'Fraunces', Georgia, serif;
  font-size: clamp(2rem, 3vw, 2.5rem);
}

.page-intro {
  text-align: center;
  margin: 0 auto 1.65rem;
  max-width: 420px;
  color: #64748b;
  line-height: 1.7;
}

.btn-block {
  width: 100%;
  margin-top: 1rem;
}

.verification-panel {
  margin-bottom: 1.1rem;
  padding: 1rem 1rem 0.9rem;
  border-radius: 16px;
  background: linear-gradient(180deg, rgba(15, 118, 110, 0.08), rgba(14, 165, 233, 0.04));
  border: 1px solid rgba(15, 118, 110, 0.14);
}

.verification-badge {
  display: inline-flex;
  align-items: center;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 800;
  color: #0f766e;
  background: rgba(255, 255, 255, 0.72);
  box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.08);
}

.verification-copy {
  margin: 0.85rem 0 0;
  color: #475569;
  line-height: 1.6;
}

.otp-input {
  text-align: center;
  letter-spacing: 0.32em;
  font-size: 1.15rem;
  font-weight: 700;
  color: #0f172a;
}

.resend-btn {
  margin-top: 0.75rem;
}

.login-link {
  text-align: center;
  margin-top: 1.15rem;
  color: #475569;
}

.login-link a {
  color: #0f766e;
  text-decoration: none;
  font-weight: 700;
}

.login-link a:hover {
  text-decoration: underline;
}

@media (max-width: 640px) {
  .register-page {
    padding: 4rem 0 2rem;
  }

  .register-card {
    padding: 1.6rem 1.1rem;
    border-radius: 18px;
  }

  .otp-input {
    letter-spacing: 0.18em;
    font-size: 1.02rem;
  }
}
</style>
