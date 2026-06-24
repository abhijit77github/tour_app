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
      <button
        @click="activeTab = 'alerts'"
        :class="['tab', { active: activeTab === 'alerts' }]"
      >
        🚨 Alert Feed
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
              📊 {{ previewLoading ? 'Estimating recipients…' : `Estimated ${estimatedRecipients} recipient(s)` }}
            </p>
            <p v-if="audiencePreview.breakdown" class="recipient-breakdown">
              Tourists {{ audiencePreview.breakdown.tourists || 0 }} · Operators {{ audiencePreview.breakdown.operators || 0 }}
            </p>
          </div>

          <!-- Message Content -->
          <div class="form-section">
            <h3>Message</h3>

            <div class="form-group">
              <label for="message-type">Message Type</label>
              <select id="message-type" v-model="notification.type" class="input">
                <option value="notification">Notification</option>
                <option value="announcement">Announcement</option>
                <option value="alert">Alert</option>
              </select>
            </div>

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
              {{ sendingLoading ? 'Saving...' : notification.sendNow ? '📨 Send Message' : '🗓️ Schedule Message' }}
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

      <div v-if="!filteredHistory.length" class="empty-state">
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

      <div v-if="templateError" class="error-message">{{ templateError }}</div>
      <div v-if="templateSuccess" class="success-message">{{ templateSuccess }}</div>

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

    <div v-else-if="activeTab === 'alerts'" class="tab-content">
      <div class="alerts-toolbar">
        <div class="alerts-summary-card">
          <strong>{{ notificationSummary?.admin_alerts?.unread_count || 0 }}</strong>
          <span>Unread alerts</span>
        </div>
        <div class="alerts-summary-card">
          <strong>{{ notificationSummary?.totals?.scheduled || 0 }}</strong>
          <span>Scheduled campaigns</span>
        </div>
        <div class="alerts-summary-card">
          <strong>{{ notificationSummary?.totals?.failed || 0 }}</strong>
          <span>Failed campaigns</span>
        </div>
        <div class="alerts-actions">
          <button class="btn btn-secondary" type="button" @click="markAllAlertsRead">Mark all read</button>
          <button class="btn btn-primary" type="button" @click="runWorkerNow" :disabled="opsLoading">{{ opsLoading ? 'Running…' : 'Run worker now' }}</button>
        </div>
      </div>

      <div class="ops-grid">
        <section class="ops-panel">
          <div class="ops-head">
            <h3>Admin alerts</h3>
            <span class="muted-copy">Unread badge is sourced from this feed.</span>
          </div>
          <div v-if="!adminAlerts.length" class="empty-state compact-empty">
            <p>📭 No alerts yet</p>
          </div>
          <article v-for="alert in adminAlerts" :key="alert._id" class="alert-card" :class="`severity-${alert.severity}`">
            <div class="alert-top">
              <div>
                <strong>{{ alert.title }}</strong>
                <p>{{ alert.message }}</p>
              </div>
              <span class="alert-severity">{{ alert.severity_label }}</span>
            </div>
            <div class="alert-meta">
              <span>{{ formatDate(alert.created_at) }}</span>
              <span>{{ alert.category }}</span>
              <span>{{ alert.service }}</span>
            </div>
            <button v-if="!alert.read" class="inline-action" type="button" @click="markAlertRead(alert._id)">Mark read</button>
          </article>
        </section>

        <section class="ops-panel">
          <div class="ops-head">
            <h3>Worker runs</h3>
            <span class="muted-copy">Background execution and manual triggers.</span>
          </div>
          <div v-if="!workerRuns.length" class="empty-state compact-empty">
            <p>🛠️ No worker runs yet</p>
          </div>
          <article v-for="run in workerRuns" :key="run._id" class="worker-run-card">
            <div class="alert-top">
              <strong>{{ run.status }}</strong>
              <span class="worker-pill">{{ run.worker_id }}</span>
            </div>
            <div class="alert-meta">
              <span>Claimed {{ run.claimed_campaigns }}</span>
              <span>Processed {{ run.processed_campaigns }}</span>
              <span>Failed {{ run.failed_campaigns }}</span>
            </div>
            <p class="worker-timestamp">{{ formatDate(run.started_at) }} → {{ formatDate(run.finished_at) }}</p>
            <p v-if="run.last_error" class="error-message compact-error">{{ run.last_error }}</p>
          </article>
        </section>

        <section class="ops-panel full-span">
          <div class="ops-head">
            <h3>Recent delivery attempts</h3>
            <span class="muted-copy">Per-user adapter outcomes for admin visibility.</span>
          </div>
          <div v-if="!deliveryAttempts.length" class="empty-state compact-empty">
            <p>📬 No delivery attempts yet</p>
          </div>
          <div v-else class="delivery-table-wrap">
            <table class="delivery-table">
              <thead>
                <tr>
                  <th>Status</th>
                  <th>User</th>
                  <th>Channel</th>
                  <th>Campaign</th>
                  <th>Reason</th>
                  <th>Time</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="attempt in deliveryAttempts" :key="attempt._id">
                  <td>{{ attempt.status }}</td>
                  <td>{{ attempt.user_id }}</td>
                  <td>{{ attempt.channel }}</td>
                  <td>{{ attempt.campaign_id }}</td>
                  <td>{{ attempt.failure_reason || 'OK' }}</td>
                  <td>{{ formatDate(attempt.created_at) }}</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>
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
    <div v-if="showCreateTemplate" class="modal-overlay" @click.self="closeTemplateModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>{{ editingTemplate ? 'Edit Template' : 'Create New Template' }}</h2>
          <button @click="closeTemplateModal" class="close-btn">✕</button>
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
            <button type="button" @click="closeTemplateModal" class="btn btn-secondary">
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
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const router = useRouter()
const activeTab = ref('compose')
const sendingLoading = ref(false)
const sendError = ref('')
const sendSuccess = ref('')
const templateError = ref('')
const templateSuccess = ref('')
const previewLoading = ref(false)
const opsLoading = ref(false)

const recipientType = ref('tourists')
const recipientFilter = ref({
  status: false,
  lastDays: null,
})

const notification = ref({
  type: 'notification',
  subject: '',
  message: '',
  sendNow: true,
  scheduledDate: '',
  scheduledTime: '',
  templateId: '',
})

const historyFilter = ref({
  type: '',
  status: '',
})

const showHistoryModal = ref(false)
const selectedHistory = ref(null)

const communicationHistory = ref([])
const templates = ref([])
const adminAlerts = ref([])
const workerRuns = ref([])
const deliveryAttempts = ref([])
const notificationSummary = ref({ admin_alerts: { unread_count: 0 }, totals: {} })
const audiencePreview = ref({
  estimated_recipients: 0,
  breakdown: { tourists: 0, operators: 0 },
})

const showCreateTemplate = ref(false)
const editingTemplate = ref(null)
const templateForm = ref({
  name: '',
  category: '',
  subject: '',
  message: '',
})

const iconForTemplate = (template) => {
  const category = (template.category || '').toLowerCase()
  if (category.includes('welcome')) return '👋'
  if (category.includes('alert')) return '⚠️'
  if (category.includes('announcement')) return '📢'
  return '✉️'
}

const quickTemplates = computed(() =>
  templates.value.slice(0, 3).map(template => ({
    ...template,
    id: template._id,
    icon: iconForTemplate(template),
  }))
)

const estimatedRecipients = computed(() => audiencePreview.value?.estimated_recipients || 0)

const filteredHistory = computed(() => {
  let filtered = communicationHistory.value

  if (historyFilter.value.type) {
    filtered = filtered.filter(item => item.type === historyFilter.value.type)
  }

  if (historyFilter.value.status) {
    filtered = filtered.filter(item => item.status === historyFilter.value.status)
  }

  return filtered
})

const normalizeRecipientFilter = () => ({
  active_only: Boolean(recipientFilter.value.status),
  last_active_days: recipientFilter.value.lastDays ? Number(recipientFilter.value.lastDays) : null,
})

const formatDate = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const clearComposeFeedback = () => {
  sendError.value = ''
  sendSuccess.value = ''
}

const clearTemplateFeedback = () => {
  templateError.value = ''
  templateSuccess.value = ''
}

const loadNotificationData = async () => {
  try {
    const [templatesRes, campaignsRes, alertsRes, deliveriesRes, workerRunsRes, summaryRes] = await Promise.all([
      api.get('/admin/notifications/templates'),
      api.get('/admin/notifications/campaigns'),
      api.get('/admin/notifications/alerts'),
      api.get('/admin/notifications/deliveries'),
      api.get('/admin/notifications/worker-runs'),
      api.get('/admin/notifications/summary'),
    ])
    templates.value = templatesRes.data.templates || []
    communicationHistory.value = campaignsRes.data.campaigns || []
    adminAlerts.value = alertsRes.data.alerts || []
    deliveryAttempts.value = deliveriesRes.data.attempts || []
    workerRuns.value = workerRunsRes.data.runs || []
    notificationSummary.value = summaryRes.data || { admin_alerts: { unread_count: 0 }, totals: {} }
  } catch (error) {
    console.error('Failed to load notification data:', error)
    sendError.value = error.response?.data?.detail || 'Failed to load notifications'
  }
}

const markAlertRead = async (alertId) => {
  try {
    await api.post(`/admin/notifications/alerts/${alertId}/read`)
    await loadNotificationData()
  } catch (error) {
    console.error('Failed to mark alert as read:', error)
    sendError.value = error.response?.data?.detail || 'Failed to update alert'
  }
}

const markAllAlertsRead = async () => {
  try {
    await api.post('/admin/notifications/alerts/read-all')
    await loadNotificationData()
  } catch (error) {
    console.error('Failed to mark all alerts as read:', error)
    sendError.value = error.response?.data?.detail || 'Failed to update alerts'
  }
}

const runWorkerNow = async () => {
  opsLoading.value = true
  try {
    const response = await api.post('/admin/notifications/worker-runs/trigger')
    sendSuccess.value = `Worker completed: processed ${response.data?.result?.processed_campaigns || 0} campaign(s).`
    await loadNotificationData()
  } catch (error) {
    console.error('Failed to trigger notification worker:', error)
    sendError.value = error.response?.data?.detail || 'Failed to trigger worker'
  } finally {
    opsLoading.value = false
  }
}

const loadAudiencePreview = async () => {
  previewLoading.value = true
  try {
    const response = await api.post('/admin/notifications/audience-preview', {
      recipient_type: recipientType.value,
      recipient_filter: normalizeRecipientFilter(),
    })
    audiencePreview.value = response.data || {
      estimated_recipients: 0,
      breakdown: { tourists: 0, operators: 0 },
    }
  } catch (error) {
    console.error('Failed to preview audience:', error)
    sendError.value = error.response?.data?.detail || 'Failed to preview recipients'
  } finally {
    previewLoading.value = false
  }
}

const buildScheduledAtIso = () => {
  if (notification.value.sendNow) return null
  if (!notification.value.scheduledDate || !notification.value.scheduledTime) return null
  return new Date(`${notification.value.scheduledDate}T${notification.value.scheduledTime}`).toISOString()
}

const sendNotification = async () => {
  clearComposeFeedback()

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
    const response = await api.post('/admin/notifications/campaigns', {
      type: notification.value.type,
      subject: notification.value.subject,
      message: notification.value.message,
      channel: 'in_app',
      recipient_type: recipientType.value,
      recipient_filter: normalizeRecipientFilter(),
      send_now: notification.value.sendNow,
      scheduled_for: buildScheduledAtIso(),
      template_id: notification.value.templateId || null,
    })

    const campaign = response.data.campaign
    sendSuccess.value = campaign.status === 'scheduled'
      ? `Campaign scheduled for ${formatDate(campaign.scheduled_for)}.`
      : `Campaign stored for ${campaign.recipient_count} recipient(s).`
    resetForm()
    await Promise.all([loadNotificationData(), loadAudiencePreview()])
  } catch (error) {
    console.error('Failed to store campaign:', error)
    sendError.value = error.response?.data?.detail || 'Failed to store campaign'
  } finally {
    sendingLoading.value = false
  }
}

const applyTemplate = (template) => {
  notification.value.subject = template.subject || template.name
  notification.value.message = template.message || ''
  notification.value.templateId = template._id || ''
}

const resetForm = () => {
  notification.value = {
    type: 'notification',
    subject: '',
    message: '',
    sendNow: true,
    scheduledDate: '',
    scheduledTime: '',
    templateId: '',
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
  applyTemplate(template)
  activeTab.value = 'compose'
}

const editTemplate = (template) => {
  clearTemplateFeedback()
  editingTemplate.value = template
  templateForm.value = {
    name: template.name,
    category: template.category,
    subject: template.subject,
    message: template.message,
  }
  showCreateTemplate.value = true
}

const deleteTemplate = async (template) => {
  clearTemplateFeedback()
  if (!window.confirm(`Delete template "${template.name}"?`)) return

  try {
    await api.delete(`/admin/notifications/templates/${template._id}`)
    templateSuccess.value = 'Template deleted'
    await loadNotificationData()
  } catch (error) {
    console.error('Failed to delete template:', error)
    templateError.value = error.response?.data?.detail || 'Failed to delete template'
  }
}

const closeTemplateModal = () => {
  showCreateTemplate.value = false
  editingTemplate.value = null
  templateForm.value = { name: '', category: '', subject: '', message: '' }
}

const saveTemplate = async () => {
  clearTemplateFeedback()
  try {
    if (editingTemplate.value) {
      await api.put(`/admin/notifications/templates/${editingTemplate.value._id}`, { ...templateForm.value })
      templateSuccess.value = 'Template updated'
    } else {
      await api.post('/admin/notifications/templates', { ...templateForm.value, channels: ['in_app'], is_active: true })
      templateSuccess.value = 'Template created'
    }
    closeTemplateModal()
    await loadNotificationData()
  } catch (error) {
    console.error('Failed to save template:', error)
    templateError.value = error.response?.data?.detail || 'Failed to save template'
  }
}

watch(
  [recipientType, () => recipientFilter.value.status, () => recipientFilter.value.lastDays],
  () => {
    clearComposeFeedback()
    loadAudiencePreview()
  }
)

watch(
  () => route.query.tab,
  (nextTab) => {
    if (["compose", "history", "templates", "alerts"].includes(nextTab)) {
      activeTab.value = nextTab
    }
  },
  { immediate: true }
)

watch(activeTab, (nextTab) => {
  const query = { ...route.query }
  if (nextTab === 'compose') {
    delete query.tab
  } else {
    query.tab = nextTab
  }
  router.replace({ query })
})

onMounted(async () => {
  await Promise.all([loadNotificationData(), loadAudiencePreview()])
})
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

.recipient-breakdown {
  margin: 0.35rem 0 0;
  color: #718096;
  font-size: 0.88rem;
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

.alerts-toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 1rem;
  margin-bottom: 1rem;
  align-items: stretch;
}

.alerts-summary-card {
  min-width: 140px;
  padding: 1rem;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  background: white;
  display: grid;
  gap: 0.25rem;
}

.alerts-summary-card strong {
  font-size: 1.35rem;
  color: #1a202c;
}

.alerts-summary-card span,
.muted-copy,
.worker-timestamp {
  color: #718096;
  font-size: 0.85rem;
}

.alerts-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  margin-left: auto;
}

.ops-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 1rem;
}

.ops-panel {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem;
  display: grid;
  gap: 0.85rem;
}

.ops-panel.full-span {
  grid-column: 1 / -1;
}

.ops-head,
.alert-top,
.alert-meta {
  display: flex;
  justify-content: space-between;
  gap: 0.75rem;
  align-items: flex-start;
}

.ops-head h3 {
  margin: 0;
  color: #1a202c;
}

.alert-card,
.worker-run-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.9rem;
  background: #f8fafc;
  display: grid;
  gap: 0.5rem;
}

.alert-card p,
.worker-run-card p {
  margin: 0;
  color: #4b5563;
}

.alert-card.severity-error {
  border-color: #fecaca;
  background: #fff5f5;
}

.alert-card.severity-warning {
  border-color: #fde68a;
  background: #fffbeb;
}

.alert-severity,
.worker-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 0.75rem;
  font-weight: 700;
}

.inline-action {
  border: none;
  padding: 0;
  background: none;
  color: #2563eb;
  font-weight: 700;
  cursor: pointer;
  width: fit-content;
}

.delivery-table-wrap {
  overflow-x: auto;
}

.delivery-table {
  width: 100%;
  border-collapse: collapse;
}

.delivery-table th,
.delivery-table td {
  padding: 0.75rem 0.5rem;
  border-bottom: 1px solid #e2e8f0;
  text-align: left;
}

.delivery-table th {
  font-size: 0.75rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: #94a3b8;
}

.compact-empty,
.compact-error {
  margin: 0;
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

  .alerts-toolbar,
  .alerts-actions,
  .ops-grid,
  .ops-head,
  .alert-top,
  .alert-meta {
    grid-template-columns: 1fr;
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
