<template>
  <div class="admin-notifications">
    <div class="page-header">
      <h1>Notifications & Communications</h1>
      <p class="subtitle">Send messages, manage notifications, and communicate with users</p>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        @click="activeTab = 'compose'"
        :class="['tab', { active: activeTab === 'compose' }]"
      >
        ✉️ Compose Message
      </button>
      <button
        @click="activeTab = 'history'"
        :class="['tab', { active: activeTab === 'history' }]"
      >
        📋 Communication History
      </button>
      <button
        @click="activeTab = 'templates'"
        :class="['tab', { active: activeTab === 'templates' }]"
      >
        📄 Message Templates
      </button>
    </div>

    <!-- Compose Tab -->
    <div v-if="activeTab === 'compose'" class="tab-content">
      <div class="compose-container">
        <form @submit.prevent="sendNotification" class="compose-form">
          <!-- Recipient Selection -->
          <div class="form-section">
            <h3>Recipients</h3>

            <div class="recipient-type">
              <label>Send to:</label>
              <div class="type-buttons">
                <button
                  type="button"
                  @click="recipientType = 'tourists'"
                  :class="['type-btn', { active: recipientType === 'tourists' }]"
                >
                  👥 Tourists
                </button>
                <button
                  type="button"
                  @click="recipientType = 'operators'"
                  :class="['type-btn', { active: recipientType === 'operators' }]"
                >
                  🚀 Operators
                </button>
                <button
                  type="button"
                  @click="recipientType = 'all'"
                  :class="['type-btn', { active: recipientType === 'all' }]"
                >
                  📢 All Users
                </button>
              </div>
            </div>

            <!-- Filters for recipients -->
            <div class="recipient-filters">
              <label>Filter recipients:</label>
              <div class="filter-group">
                <input
                  v-model="recipientFilter.status"
                  type="checkbox"
                />
                <span>Active users only</span>
              </div>
              <div class="filter-group">
                <input
                  v-model.number="recipientFilter.lastDays"
                  type="number"
                  placeholder="Last X days active"
                  class="filter-input"
                />
              </div>
            </div>

            <p class="recipient-count">
              📊 Estimated {{ estimatedRecipients }} recipient(s)
            </p>
          </div>

          <!-- Message Content -->
          <div class="form-section">
            <h3>Message</h3>

            <div class="form-group">
              <label for="subject">Subject</label>
              <input
                id="subject"
                v-model="notification.subject"
                type="text"
                placeholder="Message subject..."
                class="input"
                required
              />
            </div>

            <div class="form-group">
              <label for="message">Message Content</label>
              <textarea
                id="message"
                v-model="notification.message"
                placeholder="Write your message here..."
                class="textarea"
                rows="6"
                required
              ></textarea>
              <span class="char-count">{{ notification.message.length }}/1000</span>
            </div>

            <!-- Quick Templates -->
            <div class="templates-quick">
              <label>Quick templates:</label>
              <div class="template-buttons">
                <button
                  v-for="template in quickTemplates"
                  :key="template.id"
                  type="button"
                  @click="applyTemplate(template)"
                  class="template-btn"
                  :title="template.name"
                >
                  {{ template.icon }} {{ template.name }}
                </button>
              </div>
            </div>
          </div>

          <!-- Scheduling -->
          <div class="form-section">
            <h3>Schedule</h3>

            <div class="schedule-options">
              <label class="option">
                <input v-model="notification.sendNow" type="radio" :value="true" />
                <span>Send immediately</span>
              </label>
              <label class="option">
                <input v-model="notification.sendNow" type="radio" :value="false" />
                <span>Schedule for later</span>
              </label>
            </div>

            <div v-if="!notification.sendNow" class="schedule-inputs">
              <input
                v-model="notification.scheduledDate"
                type="date"
                class="input"
              />
              <input
                v-model="notification.scheduledTime"
                type="time"
                class="input"
              />
            </div>
          </div>

          <!-- Form Actions -->
          <div class="form-actions">
            <button type="button" @click="resetForm" class="btn btn-secondary">
              Clear
            </button>
            <button type="submit" :disabled="sendingLoading" class="btn btn-primary">
              {{ sendingLoading ? 'Sending...' : '📨 Send Message' }}
            </button>
          </div>

          <div v-if="sendError" class="error-message">{{ sendError }}</div>
          <div v-if="sendSuccess" class="success-message">{{ sendSuccess }}</div>
        </form>
      </div>
    </div>

    <!-- History Tab -->
    <div v-else-if="activeTab === 'history'" class="tab-content">
      <div class="history-filters">
        <select v-model="historyFilter.type" class="filter-select">
          <option value="">All Types</option>
          <option value="notification">🔔 Notifications</option>
          <option value="announcement">📢 Announcements</option>
          <option value="alert">⚠️ Alerts</option>
        </select>

        <select v-model="historyFilter.status" class="filter-select">
          <option value="">All Status</option>
          <option value="sent">✓ Sent</option>
          <option value="scheduled">⏳ Scheduled</option>
          <option value="failed">✗ Failed</option>
        </select>
      </div>

      <div v-if="communicationHistory.length === 0" class="empty-state">
        <p>📭 No communication history</p>
      </div>

      <div v-else class="history-container">
        <div v-for="item in filteredHistory" :key="item._id" class="history-item">
          <div class="history-header">
            <div class="history-title">
              <span class="type-badge" :class="`type-${item.type}`">{{ item.type_label }}</span>
              <h4>{{ item.subject }}</h4>
            </div>
            <span :class="['status-badge', `status-${item.status}`]">
              {{ item.status_label }}
            </span>
          </div>

          <div class="history-body">
            <p>{{ item.message }}</p>
            <div class="history-meta">
              <span>📨 {{ item.recipient_count }} recipients</span>
              <span>⏰ {{ formatDate(item.sent_at || item.scheduled_for) }}</span>
            </div>
          </div>

          <button
            @click="viewHistoryDetail(item)"
            class="view-btn"
          >
            👁️ View Details
          </button>
        </div>
      </div>
    </div>

    <!-- Templates Tab -->
    <div v-else-if="activeTab === 'templates'" class="tab-content">
      <div class="templates-toolbar">
        <button @click="showCreateTemplate = true" class="btn btn-primary">
          ➕ Create New Template
        </button>
      </div>

      <div v-if="templates.length === 0" class="empty-state">
        <p>📭 No templates yet</p>
      </div>

      <div v-else class="templates-grid">
        <div v-for="template in templates" :key="template._id" class="template-card">
          <div class="template-header">
            <h4>{{ template.name }}</h4>
            <span class="category-badge">{{ template.category }}</span>
          </div>

          <p class="template-subject">Subject: {{ template.subject }}</p>
          <p class="template-preview">{{ template.message.substring(0, 100) }}...</p>

          <div class="template-actions">
            <button @click="useTemplate(template)" class="action-btn use">
              ✓ Use
            </button>
            <button @click="editTemplate(template)" class="action-btn edit">
              ✏️ Edit
            </button>
            <button @click="deleteTemplate(template)" class="action-btn delete">
              🗑️ Delete
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- History Detail Modal -->
    <div v-if="showHistoryModal" class="modal-overlay" @click.self="closeHistoryModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Communication Details</h2>
          <button @click="closeHistoryModal" class="close-btn">✕</button>
        </div>

        <div v-if="selectedHistory" class="modal-body">
          <div class="detail-section">
            <h3>Message Information</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">Type:</span>
                <span class="value">{{ selectedHistory.type_label }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Status:</span>
                <span :class="['value', `status-${selectedHistory.status}`]">
                  {{ selectedHistory.status_label }}
                </span>
              </div>
              <div class="detail-item">
                <span class="label">Recipients:</span>
                <span class="value">{{ selectedHistory.recipient_count }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Date:</span>
                <span class="value">{{ formatDate(selectedHistory.sent_at || selectedHistory.scheduled_for) }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3>Subject</h3>
            <p class="detail-text">{{ selectedHistory.subject }}</p>
          </div>

          <div class="detail-section">
            <h3>Message</h3>
            <p class="detail-text">{{ selectedHistory.message }}</p>
          </div>

          <div v-if="selectedHistory.delivery_stats" class="detail-section">
            <h3>Delivery Statistics</h3>
            <div class="stats-grid">
              <div class="stat-item">
                <span class="stat-label">Delivered</span>
                <span class="stat-value">{{ selectedHistory.delivery_stats.delivered }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Opened</span>
                <span class="stat-value">{{ selectedHistory.delivery_stats.opened }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Clicked</span>
                <span class="stat-value">{{ selectedHistory.delivery_stats.clicked }}</span>
              </div>
              <div class="stat-item">
                <span class="stat-label">Failed</span>
                <span class="stat-value">{{ selectedHistory.delivery_stats.failed }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeHistoryModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>

    <!-- Create/Edit Template Modal -->
    <div v-if="showCreateTemplate" class="modal-overlay" @click.self="showCreateTemplate = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ editingTemplate ? 'Edit Template' : 'Create New Template' }}</h2>
          <button @click="showCreateTemplate = false" class="close-btn">✕</button>
        </div>

        <form @submit.prevent="saveTemplate" class="modal-body">
          <div class="form-group">
            <label for="template-name">Template Name</label>
            <input
              id="template-name"
              v-model="templateForm.name"
              type="text"
              placeholder="e.g., Welcome Message"
              class="input"
              required
            />
          </div>

          <div class="form-group">
            <label for="template-category">Category</label>
            <select v-model="templateForm.category" class="input" required>
              <option>Welcome</option>
              <option>Alert</option>
              <option>Announcement</option>
              <option>Support</option>
              <option>Other</option>
            </select>
          </div>

          <div class="form-group">
            <label for="template-subject">Subject</label>
            <input
              id="template-subject"
              v-model="templateForm.subject"
              type="text"
              placeholder="Message subject..."
              class="input"
              required
            />
          </div>

          <div class="form-group">
            <label for="template-message">Message</label>
            <textarea
              id="template-message"
              v-model="templateForm.message"
              placeholder="Write template message..."
              class="textarea"
              rows="5"
              required
            ></textarea>
          </div>

          <div class="form-actions">
            <button type="button" @click="showCreateTemplate = false" class="btn btn-secondary">
              Cancel
            </button>
            <button type="submit" class="btn btn-primary">
              {{ editingTemplate ? 'Update Template' : 'Create Template' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const activeTab = ref('compose')
const sendingLoading = ref(false)
const sendError = ref('')
const sendSuccess = ref('')

// Compose Form
const recipientType = ref('tourists')
const recipientFilter = ref({
  status: false,
  lastDays: null
})

const notification = ref({
  subject: '',
  message: '',
  sendNow: true,
  scheduledDate: '',
  scheduledTime: ''
})

// History
const historyFilter = ref({
  type: '',
  status: ''
})

const showHistoryModal = ref(false)
const selectedHistory = ref(null)

const communicationHistory = ref([
  {
    _id: '1',
    type: 'notification',
    type_label: '🔔 Notification',
    subject: 'New Quote Request Available',
    message: 'A new quote request has been posted in your serving area.',
    recipient_count: 45,
    status: 'sent',
    status_label: '✓ Sent',
    sent_at: new Date('2024-01-20'),
    delivery_stats: { delivered: 45, opened: 32, clicked: 15, failed: 0 }
  },
  {
    _id: '2',
    type: 'announcement',
    type_label: '📢 Announcement',
    subject: 'Platform Maintenance Scheduled',
    message: 'The platform will undergo maintenance on January 25th.',
    recipient_count: 250,
    status: 'sent',
    status_label: '✓ Sent',
    sent_at: new Date('2024-01-18'),
    delivery_stats: { delivered: 248, opened: 180, clicked: 50, failed: 2 }
  },
  {
    _id: '3',
    type: 'alert',
    type_label: '⚠️ Alert',
    subject: 'Suspicious Activity Detected',
    message: 'Unusual activity detected on your account.',
    recipient_count: 1,
    status: 'scheduled',
    status_label: '⏳ Scheduled',
    scheduled_for: new Date('2024-01-25'),
    delivery_stats: null
  }
])

const templates = ref([
  {
    _id: '1',
    name: 'Welcome New Operator',
    category: 'Welcome',
    subject: 'Welcome to Tour App!',
    message: 'Welcome to the Tour App platform. We are excited to have you onboard...'
  },
  {
    _id: '2',
    name: 'Low Rating Alert',
    category: 'Alert',
    subject: 'Your Rating Has Changed',
    message: 'Your platform rating has been updated. Check your profile for details...'
  },
  {
    _id: '3',
    name: 'Weekly Newsletter',
    category: 'Announcement',
    subject: 'This Week\'s Opportunities',
    message: 'Here are the top opportunities for this week from your area...'
  }
])

const quickTemplates = [
  { id: 1, name: 'Welcome', icon: '👋' },
  { id: 2, name: 'Alert', icon: '⚠️' },
  { id: 3, name: 'Update', icon: '📢' }
]

const showCreateTemplate = ref(false)
const editingTemplate = ref(null)
const templateForm = ref({
  name: '',
  category: '',
  subject: '',
  message: ''
})

const estimatedRecipients = computed(() => {
  let count = 0
  if (recipientType.value === 'tourists') count = 150
  else if (recipientType.value === 'operators') count = 75
  else count = 225
  return count
})

const filteredHistory = computed(() => {
  let filtered = communicationHistory.value

  if (historyFilter.value.type) {
    filtered = filtered.filter(h => h.type === historyFilter.value.type)
  }

  if (historyFilter.value.status) {
    filtered = filtered.filter(h => h.status === historyFilter.value.status)
  }

  return filtered
})

const formatDate = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString('en-IN')
}

const sendNotification = async () => {
  sendError.value = ''
  sendSuccess.value = ''

  if (!notification.value.subject.trim()) {
    sendError.value = 'Subject is required'
    return
  }

  if (!notification.value.message.trim()) {
    sendError.value = 'Message is required'
    return
  }

  if (notification.value.message.length > 1000) {
    sendError.value = 'Message cannot exceed 1000 characters'
    return
  }

  if (!notification.value.sendNow && (!notification.value.scheduledDate || !notification.value.scheduledTime)) {
    sendError.value = 'Please select a date and time for scheduled notification'
    return
  }

  try {
    sendingLoading.value = true
    // Simulate API call
    await new Promise(resolve => setTimeout(resolve, 1500))
    sendSuccess.value = `Message sent successfully to ${estimatedRecipients.value} recipient(s)!`
    resetForm()
    setTimeout(() => {
      sendSuccess.value = ''
    }, 3000)
  } catch (error) {
    sendError.value = 'Failed to send message'
  } finally {
    sendingLoading.value = false
  }
}

const applyTemplate = (template) => {
  notification.value.subject = template.name
  notification.value.message = `${template.name} content...`
}

const resetForm = () => {
  notification.value = {
    subject: '',
    message: '',
    sendNow: true,
    scheduledDate: '',
    scheduledTime: ''
  }
}

const viewHistoryDetail = (item) => {
  selectedHistory.value = item
  showHistoryModal.value = true
}

const closeHistoryModal = () => {
  showHistoryModal.value = false
  selectedHistory.value = null
}

const useTemplate = (template) => {
  notification.value.subject = template.subject
  notification.value.message = template.message
  activeTab.value = 'compose'
}

const editTemplate = (template) => {
  editingTemplate.value = template
  templateForm.value = { ...template }
  showCreateTemplate.value = true
}

const deleteTemplate = (template) => {
  const index = templates.value.findIndex(t => t._id === template._id)
  if (index > -1) {
    templates.value.splice(index, 1)
  }
}

const saveTemplate = () => {
  if (editingTemplate.value) {
    const index = templates.value.findIndex(t => t._id === editingTemplate.value._id)
    if (index > -1) {
      templates.value[index] = { ...templateForm.value }
    }
  } else {
    templates.value.push({
      _id: Date.now().toString(),
      ...templateForm.value
    })
  }
  showCreateTemplate.value = false
  editingTemplate.value = null
  templateForm.value = { name: '', category: '', subject: '', message: '' }
}
</script>

<style scoped>
.admin-notifications {
  width: 100%;
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

/* Tabs */
.tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  border-bottom: 2px solid #e2e8f0;
}

.tab {
  padding: 1rem 1.5rem;
  border: none;
  background: none;
  color: #718096;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
}

.tab:hover {
  color: #667eea;
}

.tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.tab-content {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Compose Form */
.compose-container {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  border: 1px solid #e2e8f0;
}

.compose-form {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.form-section {
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 2rem;
}

.form-section:last-child {
  border-bottom: none;
  padding-bottom: 0;
}

.form-section h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 1rem 0;
}

.recipient-type {
  margin-bottom: 1.5rem;
}

.recipient-type label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.75rem;
  color: #2d3748;
}

.type-buttons {
  display: flex;
  gap: 0.75rem;
}

.type-btn {
  padding: 0.75rem 1.5rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #2d3748;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.type-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.type-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: white;
}

.recipient-filters {
  background: #f7fafc;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1rem;
}

.recipient-filters label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  font-size: 0.9rem;
  color: #2d3748;
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.filter-group input[type="checkbox"] {
  cursor: pointer;
}

.filter-input {
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  width: 150px;
}

.recipient-count {
  margin: 0;
  color: #667eea;
  font-weight: 600;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.form-group label {
  font-weight: 600;
  color: #2d3748;
  font-size: 0.95rem;
}

.input,
.textarea {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  font-family: inherit;
  transition: all 0.2s;
}

.input:focus,
.textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.textarea {
  resize: vertical;
}

.char-count {
  font-size: 0.85rem;
  color: #a0aec0;
  text-align: right;
}

.templates-quick {
  background: #f0fdf4;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.templates-quick label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.75rem;
  font-size: 0.9rem;
}

.template-buttons {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.template-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  background: white;
  color: #166534;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border: 1px solid #bbf7d0;
}

.template-btn:hover {
  background: #bbf7d0;
}

.schedule-options {
  display: flex;
  gap: 2rem;
  margin-bottom: 1rem;
}

.option {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.option input[type="radio"] {
  cursor: pointer;
}

.schedule-inputs {
  display: flex;
  gap: 1rem;
}

.schedule-inputs .input {
  flex: 1;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
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

.btn-secondary {
  background: #e2e8f0;
  color: #2d3748;
}

.btn-secondary:hover {
  background: #cbd5e0;
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border-left: 3px solid #ef4444;
  color: #991b1b;
  border-radius: 6px;
  margin-top: 1rem;
}

.success-message {
  padding: 1rem;
  background: #dcfce7;
  border-left: 3px solid #22c55e;
  color: #166534;
  border-radius: 6px;
  margin-top: 1rem;
}

/* History */
.history-filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.filter-select {
  padding: 0.75rem 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  background: white;
  cursor: pointer;
}

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  color: #718096;
}

.history-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.history-item {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.history-item:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.history-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.history-title {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.type-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.type-notification {
  background: #dbeafe;
  color: #0284c7;
}

.type-announcement {
  background: #ddd6fe;
  color: #6d28d9;
}

.type-alert {
  background: #fecaca;
  color: #991b1b;
}

.history-title h4 {
  margin: 0;
  color: #1a202c;
  font-size: 1rem;
}

.status-badge {
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
}

.status-sent {
  background: #dcfce7;
  color: #166534;
}

.status-scheduled {
  background: #fef3c7;
  color: #b45309;
}

.status-failed {
  background: #fee2e2;
  color: #991b1b;
}

.history-body {
  margin-bottom: 1rem;
}

.history-body p {
  margin: 0 0 0.75rem 0;
  color: #4b5563;
  line-height: 1.5;
}

.history-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.9rem;
  color: #718096;
}

.view-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  background: #dbeafe;
  color: #0284c7;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.view-btn:hover {
  background: #bfdbfe;
}

/* Templates */
.templates-toolbar {
  margin-bottom: 2rem;
}

.templates-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.template-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.template-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.template-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.template-header h4 {
  margin: 0;
  color: #1a202c;
  font-size: 1rem;
}

.category-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #ddd6fe;
  color: #6d28d9;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
}

.template-subject {
  margin: 0.5rem 0;
  color: #667eea;
  font-weight: 600;
  font-size: 0.9rem;
}

.template-preview {
  margin: 0.5rem 0 1rem 0;
  color: #4b5563;
  font-size: 0.9rem;
  line-height: 1.4;
  max-height: 60px;
  overflow: hidden;
}

.template-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  flex: 1;
  padding: 0.5rem;
  border: none;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.use {
  background: #dcfce7;
  color: #166534;
}

.action-btn.use:hover {
  background: #bbf7d0;
}

.action-btn.edit {
  background: #fef3c7;
  color: #b45309;
}

.action-btn.edit:hover {
  background: #fde68a;
}

.action-btn.delete {
  background: #fee2e2;
  color: #991b1b;
}

.action-btn.delete:hover {
  background: #fecaca;
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
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
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
  font-size: 1.5rem;
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

.detail-section {
  margin-bottom: 2rem;
}

.detail-section h3 {
  font-size: 1rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e2e8f0;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.detail-item .label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-item .value {
  font-size: 1rem;
  color: #2d3748;
  font-weight: 500;
}

.detail-text {
  color: #4b5563;
  line-height: 1.6;
  margin: 0;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
  gap: 1rem;
}

.stat-item {
  text-align: center;
  padding: 1rem;
  background: #f7fafc;
  border-radius: 8px;
}

.stat-label {
  display: block;
  font-size: 0.85rem;
  font-weight: 600;
  color: #718096;
  margin-bottom: 0.5rem;
}

.stat-value {
  display: block;
  font-size: 2rem;
  font-weight: 700;
  color: #667eea;
}

.modal-footer {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  background: #f7fafc;
}

/* Responsive */
@media (max-width: 768px) {
  .tabs {
    flex-direction: column;
  }

  .tab {
    border-bottom: none;
    border-left: 3px solid transparent;
    padding-left: 1rem;
  }

  .tab.active {
    border-left-color: #667eea;
    border-bottom: none;
  }

  .type-buttons {
    flex-direction: column;
  }

  .schedule-inputs {
    flex-direction: column;
  }

  .templates-grid {
    grid-template-columns: 1fr;
  }

  .history-header {
    flex-direction: column;
    gap: 1rem;
  }

  .history-meta {
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>
