<template>
  <button 
    class="quota-badge-compact" 
    @click="showDetails = true"
    aria-label="View quota details"
    :aria-describedby="exhausted ? 'quota-exhausted' : 'quota-status'"
  >
    <div class="quota-status" :class="statusClass">
      <span id="quota-status" class="quota-text">{{ displayText }}</span>
      <span class="quota-icon" aria-hidden="true">{{ statusIcon }}</span>
    </div>
    <span v-if="exhausted" id="quota-exhausted" class="sr-only">Quota exhausted</span>
  </button>

  <!-- Details Modal -->
  <Teleport to="body">
    <div 
      v-if="showDetails" 
      class="quota-modal-overlay" 
      @click="showDetails = false"
      role="dialog"
      aria-modal="true"
      aria-labelledby="quota-modal-title"
    >
      <div class="quota-modal glass-card" @click.stop>
        <div class="modal-header">
          <h3 id="quota-modal-title">Planner Quota Details</h3>
          <button 
            class="btn-close" 
            @click="showDetails = false"
            aria-label="Close quota details"
          >
            <span aria-hidden="true">✕</span>
          </button>
        </div>

        <div v-if="loading && !quota" class="modal-loading" role="status" aria-live="polite">
          Loading quota information...
        </div>

        <div v-else-if="error" class="modal-error" role="alert">
          {{ error }}
        </div>

        <div v-else class="modal-content">
          <div class="quota-stats-grid">
            <div class="stat-card">
              <div class="stat-label">Today</div>
              <div class="stat-value" aria-label="`${quota?.daily_remaining ?? 0} requests remaining today`">
                {{ quota?.daily_remaining ?? '—' }}
              </div>
              <div class="stat-meta">of {{ quota?.effective_daily_limit ?? 0 }} requests</div>
            </div>
            <div class="stat-card">
              <div class="stat-label">This Month</div>
              <div class="stat-value" aria-label="`${quota?.monthly_remaining ?? 0} requests remaining this month`">
                {{ quota?.monthly_remaining ?? '—' }}
              </div>
              <div class="stat-meta">of {{ quota?.effective_monthly_limit ?? 0 }} requests</div>
            </div>
          </div>

          <div class="quota-resets">
            <div class="reset-item">
              <span class="reset-label">Daily resets:</span>
              <span class="reset-time">{{ formatReset(quota?.daily_resets_at) }}</span>
            </div>
            <div class="reset-item">
              <span class="reset-label">Monthly resets:</span>
              <span class="reset-time">{{ formatReset(quota?.monthly_resets_at) }}</span>
            </div>
          </div>

          <div v-if="exhausted" class="quota-exhausted-info" role="alert">
            <p class="exhausted-text">
              Your planner quota is currently exhausted. You can continue viewing your current session,
              but new planning requests will be available after the reset time.
            </p>
            <button class="btn-upgrade" aria-label="Upgrade for higher quota limits">
              <span aria-hidden="true">✨</span> Upgrade for Higher Limits
            </button>
          </div>

          <div v-else class="quota-usage-tips">
            <h4><span aria-hidden="true">💡</span> Tips for efficient planning</h4>
            <ul>
              <li>Provide detailed trip requirements in your first message</li>
              <li>Review itinerary ideas before requesting operator matches</li>
              <li>Add operators to cart as you find good matches</li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </Teleport>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  quota: {
    type: Object,
    default: null
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: ''
  }
})

const showDetails = ref(false)

const exhausted = computed(() => {
  if (!props.quota) return false
  return Number(props.quota.daily_remaining || 0) <= 0 || 
         Number(props.quota.monthly_remaining || 0) <= 0
})

const remaining = computed(() => {
  return props.quota?.daily_remaining ?? 0
})

const displayText = computed(() => {
  if (props.loading && !props.quota) return 'Loading...'
  if (props.error) return 'Error'
  if (exhausted.value) return 'Quota exhausted'
  return `${remaining.value}/${props.quota?.effective_daily_limit ?? 0} today`
})

const statusIcon = computed(() => {
  if (exhausted.value) return '🔴'
  if (remaining.value <= 2) return '🟡'
  return '🟢'
})

const statusClass = computed(() => {
  if (exhausted.value) return 'status-danger'
  if (remaining.value <= 2) return 'status-warning'
  return 'status-success'
})

function formatReset(dateString) {
  if (!dateString) return '—'
  try {
    const date = new Date(dateString)
    const now = new Date()
    const diff = date - now
    const hours = Math.floor(diff / (1000 * 60 * 60))
    const minutes = Math.floor((diff % (1000 * 60 * 60)) / (1000 * 60))
    
    if (hours > 24) {
      const days = Math.floor(hours / 24)
      return `in ${days}d ${hours % 24}h`
    }
    if (hours > 0) {
      return `in ${hours}h ${minutes}m`
    }
    return `in ${minutes}m`
  } catch (e) {
    return dateString
  }
}
</script>

<style scoped>
/* Screen Reader Only class */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

.quota-badge-compact {
  cursor: pointer;
  user-select: none;
  background: transparent;
  border: none;
  padding: 0;
  border-radius: 12px;
}

.quota-status {
  display: flex;
  align-items: center;
  gap: 8px;
  min-height: 42px;
  padding: 9px 13px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border-radius: 12px;
  border: 1px solid rgba(100, 116, 139, 0.35);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
  transition: all 0.2s ease;
}

.quota-status:hover {
  background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
  border-color: rgba(51, 65, 85, 0.45);
  transform: translateY(-1px);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.12);
}

.quota-text {
  font-size: 12px;
  font-weight: 700;
  color: #0f172a;
}

.quota-icon {
  font-size: 12px;
  line-height: 1;
}

.quota-badge-compact:focus-visible {
  outline: 3px solid #0891b2;
  outline-offset: 2px;
}

.status-success {
  border-color: rgba(16, 185, 129, 0.3);
}

.status-warning {
  border-color: rgba(245, 158, 11, 0.3);
}

.status-danger {
  border-color: rgba(244, 63, 94, 0.3);
}

/* Modal styles */
.quota-modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 20px;
}

.quota-modal {
  max-width: 500px;
  width: 100%;
  background: rgba(15, 23, 42, 0.95);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 20px;
  padding: 0;
  overflow: hidden;
  animation: slideUp 0.3s ease;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 24px 28px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}

.modal-header h3 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: white;
}

.btn-close {
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 8px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 18px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-close:hover {
  background: rgba(255, 255, 255, 0.1);
  color: white;
}

.modal-content {
  padding: 28px;
}

.modal-loading,
.modal-error {
  padding: 40px;
  text-align: center;
  color: rgba(255, 255, 255, 0.7);
}

.quota-stats-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  padding: 20px;
  background: rgba(255, 255, 255, 0.03);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 14px;
  text-align: center;
}

.stat-label {
  font-size: 12px;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: rgba(255, 255, 255, 0.5);
  margin-bottom: 8px;
}

.stat-value {
  font-size: 32px;
  font-weight: 700;
  color: white;
  margin-bottom: 4px;
}

.stat-meta {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.quota-resets {
  padding: 16px;
  background: rgba(255, 255, 255, 0.03);
  border-radius: 12px;
  margin-bottom: 24px;
}

.reset-item {
  display: flex;
  justify-content: space-between;
  padding: 8px 0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.05);
}

.reset-item:last-child {
  border-bottom: none;
}

.reset-label {
  font-size: 13px;
  color: rgba(255, 255, 255, 0.6);
}

.reset-time {
  font-size: 13px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.quota-exhausted-info {
  padding: 20px;
  background: linear-gradient(135deg, rgba(244, 63, 94, 0.1), rgba(244, 63, 94, 0.05));
  border: 1px solid rgba(244, 63, 94, 0.2);
  border-radius: 12px;
}

.exhausted-text {
  margin: 0 0 16px 0;
  font-size: 14px;
  line-height: 1.6;
  color: rgba(255, 255, 255, 0.8);
}

.btn-upgrade {
  width: 100%;
  padding: 12px 20px;
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-upgrade:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 16px rgba(245, 158, 11, 0.3);
}

.quota-usage-tips {
  padding: 20px;
  background: linear-gradient(135deg, rgba(8, 145, 178, 0.1), rgba(15, 118, 110, 0.05));
  border: 1px solid rgba(8, 145, 178, 0.2);
  border-radius: 12px;
}

.quota-usage-tips h4 {
  margin: 0 0 12px 0;
  font-size: 14px;
  font-weight: 600;
  color: rgba(255, 255, 255, 0.9);
}

.quota-usage-tips ul {
  margin: 0;
  padding-left: 20px;
  list-style: disc;
}

.quota-usage-tips li {
  margin-bottom: 8px;
  font-size: 13px;
  line-height: 1.5;
  color: rgba(255, 255, 255, 0.7);
}

.quota-usage-tips li:last-child {
  margin-bottom: 0;
}

@media (max-width: 768px) {
  .quota-status {
    min-height: 40px;
    padding: 8px 11px;
  }

  .quota-text {
    font-size: 11px;
  }

  .quota-modal {
    max-width: 100%;
    border-radius: 20px 20px 0 0;
  }

  .quota-stats-grid {
    grid-template-columns: 1fr;
  }
}
</style>
