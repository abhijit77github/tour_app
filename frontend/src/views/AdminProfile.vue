<template>
  <div class="admin-profile">
    <div class="page-header">
      <h1>My Profile</h1>
      <p class="subtitle">Manage your admin account and preferences</p>
    </div>

    <div v-if="adminUser" class="profile-container">
      <div class="profile-card">
        <div class="profile-header">
          <div class="avatar">{{ initials }}</div>
          <div class="info">
            <h2>{{ adminUser.full_name }}</h2>
            <p class="role">{{ roleLabel }}</p>
            <p class="email">{{ adminUser.email }}</p>
          </div>
        </div>

        <div class="profile-body">
          <div class="section">
            <h3>Account Information</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Full Name</span>
                <span class="value">{{ adminUser.full_name }}</span>
              </div>
              <div class="info-item">
                <span class="label">Email</span>
                <span class="value">{{ adminUser.email }}</span>
              </div>
              <div class="info-item">
                <span class="label">Phone</span>
                <span class="value">{{ adminUser.phone || 'N/A' }}</span>
              </div>
              <div class="info-item">
                <span class="label">Role</span>
                <span class="value">{{ roleLabel }}</span>
              </div>
              <div class="info-item">
                <span class="label">Status</span>
                <span :class="['value', adminUser.is_active ? 'active' : 'inactive']">
                  {{ adminUser.is_active ? 'Active' : 'Inactive' }}
                </span>
              </div>
              <div class="info-item">
                <span class="label">Member Since</span>
                <span class="value">{{ formatDate(adminUser.created_at) }}</span>
              </div>
            </div>
          </div>

          <div class="section">
            <h3>Security</h3>
            <p class="description">Manage your password and login credentials</p>
            <button @click="showChangePasswordForm = true" class="btn btn-primary">
              Change Password
            </button>
          </div>

          <div class="section">
            <h3>Recent Activity</h3>
            <p v-if="adminUser.last_login" class="description">
              Last login: {{ formatDate(adminUser.last_login) }}
            </p>
            <p v-else class="description">No login history</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Change Password Form -->
    <div v-if="showChangePasswordForm" class="modal-overlay" @click.self="showChangePasswordForm = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Change Password</h2>
          <button @click="showChangePasswordForm = false" class="close-btn">✕</button>
        </div>

        <form @submit.prevent="changePassword" class="modal-body">
          <div class="form-group">
            <label for="current-password">Current Password</label>
            <input
              id="current-password"
              v-model="passwordForm.current_password"
              type="password"
              required
              class="input"
              placeholder="Enter current password"
            />
          </div>

          <div class="form-group">
            <label for="new-password">New Password</label>
            <input
              id="new-password"
              v-model="passwordForm.new_password"
              type="password"
              required
              class="input"
              placeholder="Enter new password"
            />
          </div>

          <div class="form-group">
            <label for="confirm-password">Confirm Password</label>
            <input
              id="confirm-password"
              v-model="passwordForm.confirm_password"
              type="password"
              required
              class="input"
              placeholder="Confirm new password"
            />
          </div>

          <div v-if="passwordError" class="error-message">{{ passwordError }}</div>
          <div v-if="passwordSuccess" class="success-message">{{ passwordSuccess }}</div>

          <div class="modal-footer">
            <button type="button" @click="showChangePasswordForm = false" class="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" :disabled="passwordLoading" class="btn btn-primary">
              {{ passwordLoading ? 'Updating...' : 'Update Password' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'

const adminUser = ref(null)
const showChangePasswordForm = ref(false)
const passwordLoading = ref(false)
const passwordError = ref('')
const passwordSuccess = ref('')
const passwordForm = ref({
  current_password: '',
  new_password: '',
  confirm_password: ''
})

const roleLabel = computed(() => {
  return adminUser.value?.role === 'super_admin' ? 'Super Admin' : 'Moderator'
})

const initials = computed(() => {
  if (!adminUser.value) return '?'
  const parts = adminUser.value.full_name.split(' ')
  return parts.map(p => p[0]).join('').toUpperCase()
})

const formatDate = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString('en-IN', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const fetchAdminProfile = async () => {
  try {
    const token = localStorage.getItem('adminToken')
    const response = await api.get('/admin/profile', {
      headers: { Authorization: `Bearer ${token}` }
    })
    adminUser.value = response.data.admin
  } catch (error) {
    console.error('Error fetching admin profile:', error)
  }
}

const changePassword = async () => {
  passwordError.value = ''
  passwordSuccess.value = ''

  // Validate passwords match
  if (passwordForm.value.new_password !== passwordForm.value.confirm_password) {
    passwordError.value = 'New passwords do not match'
    return
  }

  // Validate password strength
  if (passwordForm.value.new_password.length < 8) {
    passwordError.value = 'Password must be at least 8 characters'
    return
  }

  try {
    passwordLoading.value = true
    const token = localStorage.getItem('adminToken')

    await api.post('/admin/change-password', {
      current_password: passwordForm.value.current_password,
      new_password: passwordForm.value.new_password
    }, {
      headers: { Authorization: `Bearer ${token}` }
    })

    passwordSuccess.value = 'Password updated successfully!'
    passwordForm.value = {
      current_password: '',
      new_password: '',
      confirm_password: ''
    }

    setTimeout(() => {
      showChangePasswordForm.value = false
      passwordSuccess.value = ''
    }, 2000)
  } catch (error) {
    passwordError.value = error.response?.data?.detail || 'Failed to change password'
  } finally {
    passwordLoading.value = false
  }
}

onMounted(() => {
  fetchAdminProfile()
})
</script>

<style scoped>
.admin-profile {
  width: 100%;
  max-width: 900px;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 0.5rem 0;
}

.subtitle {
  color: #718096;
  font-size: 1rem;
  margin: 0;
}

.profile-container {
  display: flex;
  gap: 2rem;
}

.profile-card {
  flex: 1;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.profile-header {
  display: flex;
  align-items: center;
  gap: 2rem;
  padding: 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.avatar {
  width: 4rem;
  height: 4rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 50%;
  font-size: 1.5rem;
  font-weight: 700;
}

.profile-header h2 {
  margin: 0 0 0.25rem 0;
  font-size: 1.5rem;
}

.profile-header .role {
  margin: 0 0 0.25rem 0;
  font-size: 0.9rem;
  opacity: 0.9;
}

.profile-header .email {
  margin: 0;
  font-size: 0.9rem;
  opacity: 0.8;
}

.profile-body {
  padding: 2rem;
}

.section {
  margin-bottom: 2.5rem;
}

.section:last-child {
  margin-bottom: 0;
}

.section h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 1rem 0;
  padding-bottom: 0.75rem;
  border-bottom: 2px solid #e2e8f0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.info-item .label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-item .value {
  font-size: 1rem;
  color: #2d3748;
  font-weight: 500;
}

.info-item .value.active {
  color: #166534;
}

.info-item .value.inactive {
  color: #991b1b;
}

.description {
  color: #718096;
  font-size: 0.95rem;
  margin: 0 0 1rem 0;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.95rem;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

.btn-primary:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 500px;
  width: 100%;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.3rem;
  color: #1a202c;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #718096;
}

.close-btn:hover {
  color: #2d3748;
}

.modal-body {
  padding: 1.5rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #2d3748;
  font-size: 0.9rem;
}

.input {
  width: 100%;
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border-left: 4px solid #ef4444;
  color: #991b1b;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.success-message {
  padding: 1rem;
  background: #dcfce7;
  border-left: 4px solid #22c55e;
  color: #166534;
  border-radius: 6px;
  margin-bottom: 1rem;
  font-size: 0.9rem;
}

.modal-footer {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  background: #f7fafc;
}

.btn-secondary {
  background: #e2e8f0;
  color: #2d3748;
}

.btn-secondary:hover {
  background: #cbd5e0;
}

/* Responsive */
@media (max-width: 768px) {
  .admin-profile {
    max-width: 100%;
  }

  .profile-header {
    flex-direction: column;
    text-align: center;
    gap: 1rem;
  }

  .info-grid {
    grid-template-columns: 1fr;
  }
}
</style>
