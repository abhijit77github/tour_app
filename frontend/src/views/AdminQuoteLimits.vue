<template>
  <div class="admin-quote-limits">
    <div class="page-header">
      <h1>Quote Request Limits</h1>
      <p class="subtitle">Configure maximum open quote requests per membership tier</p>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="status-message">
      <div class="spinner"></div>
      Loading configuration...
    </div>

    <!-- Error State -->
    <div v-else-if="errorMessage" class="error-message">
      ❌ {{ errorMessage }}
    </div>

    <!-- Main Content -->
    <div v-else class="config-container">
      <!-- Success Message -->
      <div v-if="successMessage" class="success-message">
        ✅ {{ successMessage }}
      </div>

      <!-- Info Card -->
      <div class="info-card">
        <div class="info-icon">ℹ️</div>
        <div class="info-content">
          <h3>About Quote Limits</h3>
          <p>
            Quote limits control how many open (pending/active) quote requests a tourist can have at any time.
            This helps manage operator workload and incentivizes membership upgrades.
          </p>
          <ul>
            <li><strong>Free Members:</strong> Basic access for trial users</li>
            <li><strong>Premium Members:</strong> Enhanced access for regular users</li>
            <li><strong>Enterprise Members:</strong> Unlimited-like access for power users</li>
          </ul>
        </div>
      </div>

      <!-- Configuration Form -->
      <div class="config-card">
        <h2>Current Limits</h2>
        
        <!-- Free Tier -->
        <div class="config-section">
          <div class="tier-header">
            <span class="tier-icon">🆓</span>
            <div class="tier-info">
              <h3>Free Members</h3>
              <p>Basic tier for new and trial users</p>
            </div>
          </div>
          <div class="limit-input-group">
            <input 
              v-model.number="limits.free" 
              type="number" 
              min="1" 
              max="50"
              class="limit-input"
              :class="{ 'has-error': validationErrors.free }"
            />
            <span class="limit-suffix">open requests</span>
          </div>
          <p v-if="validationErrors.free" class="validation-error">
            {{ validationErrors.free }}
          </p>
          <p class="hint">Recommended: 3-10 for trial users</p>
        </div>

        <!-- Premium Tier -->
        <div class="config-section">
          <div class="tier-header">
            <span class="tier-icon">⭐</span>
            <div class="tier-info">
              <h3>Premium Members</h3>
              <p>Enhanced tier for paying customers</p>
            </div>
          </div>
          <div class="limit-input-group">
            <input 
              v-model.number="limits.premium" 
              type="number" 
              min="1" 
              max="100"
              class="limit-input"
              :class="{ 'has-error': validationErrors.premium }"
            />
            <span class="limit-suffix">open requests</span>
          </div>
          <p v-if="validationErrors.premium" class="validation-error">
            {{ validationErrors.premium }}
          </p>
          <p class="hint">Recommended: 15-50 for regular users</p>
        </div>

        <!-- Enterprise Tier -->
        <div class="config-section">
          <div class="tier-header">
            <span class="tier-icon">💎</span>
            <div class="tier-info">
              <h3>Enterprise Members</h3>
              <p>Premium tier for power users and businesses</p>
            </div>
          </div>
          <div class="limit-input-group">
            <input 
              v-model.number="limits.enterprise" 
              type="number" 
              min="1" 
              max="500"
              class="limit-input"
              :class="{ 'has-error': validationErrors.enterprise }"
            />
            <span class="limit-suffix">open requests</span>
          </div>
          <p v-if="validationErrors.enterprise" class="validation-error">
            {{ validationErrors.enterprise }}
          </p>
          <p class="hint">Recommended: 50-200 for enterprise users</p>
        </div>

        <!-- Last Updated Info -->
        <div v-if="lastUpdated" class="last-updated">
          <span class="last-updated-label">Last updated:</span>
          <span class="last-updated-value">
            {{ formatDate(lastUpdated.date) }} by {{ lastUpdated.admin }}
          </span>
        </div>

        <!-- Action Buttons -->
        <div class="action-buttons">
          <button 
            @click="reset" 
            class="btn-secondary"
            :disabled="saving || !hasChanges"
          >
            Reset to Defaults
          </button>
          <button 
            @click="save" 
            class="btn-primary"
            :disabled="saving || !hasChanges || hasValidationErrors"
          >
            <span v-if="saving" class="spinner-small"></span>
            <span v-else>Save Changes</span>
          </button>
        </div>

        <!-- Changes Warning -->
        <div v-if="hasChanges" class="changes-warning">
          ⚠️ You have unsaved changes. Click "Save Changes" to apply them.
        </div>
      </div>

      <!-- Impact Preview -->
      <div class="impact-card" v-if="hasChanges">
        <h3>📊 Change Impact Preview</h3>
        <div class="impact-grid">
          <div v-if="limits.free !== originalLimits.free" class="impact-item">
            <span class="impact-label">Free Tier:</span>
            <span class="impact-change">
              {{ originalLimits.free }} → {{ limits.free }}
              <span :class="['impact-delta', limits.free > originalLimits.free ? 'increase' : 'decrease']">
                {{ limits.free > originalLimits.free ? '+' : '' }}{{ limits.free - originalLimits.free }}
              </span>
            </span>
          </div>
          <div v-if="limits.premium !== originalLimits.premium" class="impact-item">
            <span class="impact-label">Premium Tier:</span>
            <span class="impact-change">
              {{ originalLimits.premium }} → {{ limits.premium }}
              <span :class="['impact-delta', limits.premium > originalLimits.premium ? 'increase' : 'decrease']">
                {{ limits.premium > originalLimits.premium ? '+' : '' }}{{ limits.premium - originalLimits.premium }}
              </span>
            </span>
          </div>
          <div v-if="limits.enterprise !== originalLimits.enterprise" class="impact-item">
            <span class="impact-label">Enterprise Tier:</span>
            <span class="impact-change">
              {{ originalLimits.enterprise }} → {{ limits.enterprise }}
              <span :class="['impact-delta', limits.enterprise > originalLimits.enterprise ? 'increase' : 'decrease']">
                {{ limits.enterprise > originalLimits.enterprise ? '+' : '' }}{{ limits.enterprise - originalLimits.enterprise }}
              </span>
            </span>
          </div>
        </div>
        <p class="impact-note">
          Changes take effect immediately for all new quote requests.
        </p>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import api from '@/services/api'

const loading = ref(true)
const saving = ref(false)
const errorMessage = ref('')
const successMessage = ref('')

const limits = reactive({
  free: 5,
  premium: 20,
  enterprise: 100
})

const originalLimits = reactive({
  free: 5,
  premium: 20,
  enterprise: 100
})

const lastUpdated = ref(null)

const validationErrors = computed(() => {
  const errors = {}
  
  // Range validation
  if (limits.free < 1 || limits.free > 50) {
    errors.free = 'Free tier limit must be between 1 and 50'
  }
  if (limits.premium < 1 || limits.premium > 100) {
    errors.premium = 'Premium tier limit must be between 1 and 100'
  }
  if (limits.enterprise < 1 || limits.enterprise > 500) {
    errors.enterprise = 'Enterprise tier limit must be between 1 and 500'
  }
  
  // Ordering validation
  if (!errors.free && !errors.premium && limits.premium < limits.free) {
    errors.premium = 'Premium limit should be greater than or equal to Free limit'
  }
  if (!errors.premium && !errors.enterprise && limits.enterprise < limits.premium) {
    errors.enterprise = 'Enterprise limit should be greater than or equal to Premium limit'
  }
  
  return errors
})

const hasValidationErrors = computed(() => {
  return Object.keys(validationErrors.value).length > 0
})

const hasChanges = computed(() => {
  return limits.free !== originalLimits.free ||
         limits.premium !== originalLimits.premium ||
         limits.enterprise !== originalLimits.enterprise
})

const fetchLimits = async () => {
  loading.value = true
  errorMessage.value = ''
  
  try {
    const res = await api.get('/admin/config/quote-limits')
    
    if (res.data.quote_limits) {
      limits.free = res.data.quote_limits.free
      limits.premium = res.data.quote_limits.premium
      limits.enterprise = res.data.quote_limits.enterprise
      
      originalLimits.free = res.data.quote_limits.free
      originalLimits.premium = res.data.quote_limits.premium
      originalLimits.enterprise = res.data.quote_limits.enterprise
    }
    
    lastUpdated.value = res.data.updated
  } catch (err) {
    console.error('Failed to load quote limits:', err)
    errorMessage.value = err.response?.data?.detail || 'Failed to load configuration'
  } finally {
    loading.value = false
  }
}

const save = async () => {
  if (hasValidationErrors.value) {
    errorMessage.value = 'Please fix validation errors before saving'
    return
  }
  
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  
  try {
    const res = await api.put('/admin/config/quote-limits', {
      quote_limits: {
        free: limits.free,
        premium: limits.premium,
        enterprise: limits.enterprise
      }
    })
    
    // Update original limits to reflect saved state
    originalLimits.free = limits.free
    originalLimits.premium = limits.premium
    originalLimits.enterprise = limits.enterprise
    
    // Update last updated info
    if (res.data.config && res.data.config.updated) {
      lastUpdated.value = res.data.config.updated
    }
    
    successMessage.value = 'Quote limits updated successfully!'
    
    // Clear success message after 3 seconds
    setTimeout(() => {
      successMessage.value = ''
    }, 3000)
  } catch (err) {
    console.error('Failed to save quote limits:', err)
    errorMessage.value = err.response?.data?.detail || 'Failed to save changes'
  } finally {
    saving.value = false
  }
}

const reset = () => {
  limits.free = 5
  limits.premium = 20
  limits.enterprise = 100
}

const formatDate = (date) => {
  if (!date) return 'Never'
  return new Date(date).toLocaleString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  })
}

onMounted(() => {
  fetchLimits()
})
</script>

<style scoped>
.admin-quote-limits {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
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
  font-size: 1rem;
  color: #718096;
  margin: 0;
}

.status-message {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 1rem;
  background: #edf2f7;
  border-radius: 8px;
  color: #4a5568;
  font-size: 0.95rem;
}

.error-message {
  padding: 1rem;
  background: #fed7d7;
  border-left: 4px solid #f56565;
  border-radius: 8px;
  color: #c53030;
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
}

.success-message {
  padding: 1rem;
  background: #c6f6d5;
  border-left: 4px solid #48bb78;
  border-radius: 8px;
  color: #22543d;
  font-size: 0.95rem;
  margin-bottom: 1.5rem;
  animation: slideDown 0.3s ease-out;
}

@keyframes slideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.config-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.info-card {
  display: flex;
  gap: 1rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 12px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}

.info-icon {
  font-size: 2rem;
  flex-shrink: 0;
}

.info-content h3 {
  margin: 0 0 0.5rem 0;
  font-size: 1.25rem;
}

.info-content p {
  margin: 0 0 1rem 0;
  opacity: 0.95;
  line-height: 1.6;
}

.info-content ul {
  margin: 0;
  padding-left: 1.5rem;
  opacity: 0.95;
}

.info-content li {
  margin-bottom: 0.5rem;
  line-height: 1.6;
}

.config-card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.config-card h2 {
  font-size: 1.5rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 2rem 0;
  padding-bottom: 1rem;
  border-bottom: 2px solid #e2e8f0;
}

.config-section {
  margin-bottom: 2rem;
  padding: 1.5rem;
  background: #f7fafc;
  border-radius: 8px;
  border: 2px solid #e2e8f0;
  transition: border-color 0.2s;
}

.config-section:hover {
  border-color: #cbd5e0;
}

.tier-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.tier-icon {
  font-size: 2.5rem;
  line-height: 1;
}

.tier-info h3 {
  margin: 0 0 0.25rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #2d3748;
}

.tier-info p {
  margin: 0;
  font-size: 0.9rem;
  color: #718096;
}

.limit-input-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 0.5rem;
}

.limit-input {
  width: 120px;
  padding: 0.75rem;
  font-size: 1.25rem;
  font-weight: 600;
  text-align: center;
  border: 2px solid #cbd5e0;
  border-radius: 8px;
  background: white;
  transition: all 0.2s;
}

.limit-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.limit-input.has-error {
  border-color: #f56565;
}

.limit-suffix {
  font-size: 1rem;
  color: #4a5568;
  font-weight: 500;
}

.validation-error {
  margin: 0.5rem 0;
  color: #e53e3e;
  font-size: 0.875rem;
  font-weight: 500;
}

.hint {
  margin: 0.5rem 0 0 0;
  font-size: 0.875rem;
  color: #718096;
  font-style: italic;
}

.last-updated {
  margin: 2rem 0 1.5rem 0;
  padding: 1rem;
  background: #edf2f7;
  border-radius: 8px;
  font-size: 0.9rem;
  color: #4a5568;
  display: flex;
  justify-content: center;
  gap: 0.5rem;
}

.last-updated-label {
  font-weight: 500;
}

.last-updated-value {
  font-weight: 600;
  color: #2d3748;
}

.action-buttons {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.btn-primary,
.btn-secondary {
  padding: 0.75rem 2rem;
  font-size: 1rem;
  font-weight: 600;
  border-radius: 8px;
  border: none;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  min-width: 140px;
  justify-content: center;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  box-shadow: 0 4px 6px rgba(102, 126, 234, 0.3);
}

.btn-primary:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
}

.btn-secondary {
  background: white;
  color: #4a5568;
  border: 2px solid #cbd5e0;
}

.btn-secondary:hover:not(:disabled) {
  background: #f7fafc;
  border-color: #a0aec0;
}

.btn-secondary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.changes-warning {
  margin-top: 1rem;
  padding: 0.75rem;
  background: #fef5e7;
  border-left: 4px solid #f59e0b;
  border-radius: 6px;
  color: #92400e;
  font-size: 0.9rem;
  font-weight: 500;
}

.impact-card {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
  border: 2px solid #fbbf24;
}

.impact-card h3 {
  margin: 0 0 1.5rem 0;
  font-size: 1.25rem;
  font-weight: 600;
  color: #1a202c;
}

.impact-grid {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1rem;
}

.impact-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 1rem;
  background: #fffbeb;
  border-radius: 6px;
}

.impact-label {
  font-weight: 600;
  color: #92400e;
}

.impact-change {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  font-size: 1rem;
  color: #451a03;
}

.impact-delta {
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-weight: 700;
  font-size: 0.875rem;
}

.impact-delta.increase {
  background: #d1fae5;
  color: #065f46;
}

.impact-delta.decrease {
  background: #fee2e2;
  color: #991b1b;
}

.impact-note {
  margin: 1rem 0 0 0;
  padding: 0.75rem;
  background: #f0fdf4;
  border-radius: 6px;
  color: #166534;
  font-size: 0.875rem;
  font-weight: 500;
  text-align: center;
}

.spinner {
  width: 24px;
  height: 24px;
  border: 3px solid #cbd5e0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

.spinner-small {
  display: inline-block;
  width: 16px;
  height: 16px;
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

/* Responsive Design */
@media (max-width: 768px) {
  .admin-quote-limits {
    padding: 1rem;
  }

  .page-header h1 {
    font-size: 1.5rem;
  }

  .config-card,
  .impact-card {
    padding: 1.5rem;
  }

  .tier-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .action-buttons {
    flex-direction: column;
  }

  .btn-primary,
  .btn-secondary {
    width: 100%;
  }

  .impact-item {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
}
</style>
