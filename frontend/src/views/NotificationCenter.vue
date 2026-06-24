<template>
  <div class="container notification-center-page">
    <div class="notification-center-hero">
      <div>
        <p class="hero-kicker">Notification Center</p>
        <h1>Inbox and delivery preferences</h1>
        <p class="hero-copy">Review in-app notifications sent by the platform and control which message categories reach you.</p>
      </div>
      <div class="hero-pill">
        <strong>{{ notificationsStore.unreadCount }}</strong>
        <span>Unread</span>
      </div>
    </div>

    <div class="center-tabs">
      <button type="button" :class="['center-tab', { active: activeTab === 'inbox' }]" @click="activeTab = 'inbox'">Inbox</button>
      <button type="button" :class="['center-tab', { active: activeTab === 'preferences' }]" @click="activeTab = 'preferences'">Preferences</button>
    </div>

    <section v-if="activeTab === 'inbox'" class="center-panel">
      <div class="panel-head">
        <div>
          <h2>Recent notifications</h2>
          <p>Messages delivered through the in-app adapter appear here.</p>
        </div>
        <button class="btn btn-secondary" type="button" @click="markAllRead" :disabled="notificationsStore.unreadCount === 0">Mark all read</button>
      </div>

      <div v-if="loadingInbox" class="state-box">Loading inbox…</div>
      <div v-else-if="!inboxItems.length" class="state-box">No notifications yet.</div>

      <div v-else class="inbox-list">
        <article v-for="item in inboxItems" :key="item._id" class="inbox-card" :class="{ unread: !item.read_at }">
          <div class="inbox-top">
            <div>
              <span class="type-pill">{{ item.type_label }}</span>
              <h3>{{ item.subject }}</h3>
            </div>
            <small>{{ formatDate(item.delivered_at || item.created_at) }}</small>
          </div>
          <p>{{ item.message }}</p>
          <div class="inbox-actions">
            <span class="meta-copy">Channel: {{ item.channel }}</span>
            <button v-if="!item.read_at" class="btn btn-primary" type="button" @click="markRead(item._id)">Mark read</button>
          </div>
        </article>
        <div class="pager-row">
          <span class="pager-copy">{{ inboxRangeLabel }}</span>
          <div class="pager-controls">
            <button class="btn btn-secondary" type="button" @click="previousPage" :disabled="currentPage === 1 || loadingInbox">Prev</button>
            <span>Page {{ currentPage }} / {{ totalPages }}</span>
            <button class="btn btn-secondary" type="button" @click="nextPage" :disabled="!notificationsStore.inboxPagination.hasMore || loadingInbox">Next</button>
          </div>
        </div>
      </div>
    </section>

    <section v-else class="center-panel">
      <div class="panel-head">
        <div>
          <h2>Delivery preferences</h2>
          <p>These preferences are enforced during campaign execution without changing the admin compose contract.</p>
        </div>
      </div>

      <form class="prefs-form" @submit.prevent="savePreferences">
        <label class="prefs-toggle">
          <input v-model="preferencesForm.in_app_enabled" type="checkbox" />
          <span>Enable in-app notifications</span>
        </label>
        <label class="prefs-toggle">
          <input v-model="preferencesForm.marketing_enabled" type="checkbox" />
          <span>Receive general platform notifications</span>
        </label>
        <label class="prefs-toggle">
          <input v-model="preferencesForm.announcements_enabled" type="checkbox" />
          <span>Receive announcements</span>
        </label>
        <label class="prefs-toggle">
          <input v-model="preferencesForm.alerts_enabled" type="checkbox" />
          <span>Receive alerts</span>
        </label>
        <label class="prefs-toggle">
          <input v-model="preferencesForm.quiet_hours_enabled" type="checkbox" />
          <span>Enable quiet hours</span>
        </label>

        <div class="prefs-grid">
          <label class="field">
            <span>Quiet hours start</span>
            <input v-model="preferencesForm.quiet_hours_start" type="time" class="input" :disabled="!preferencesForm.quiet_hours_enabled" />
          </label>
          <label class="field">
            <span>Quiet hours end</span>
            <input v-model="preferencesForm.quiet_hours_end" type="time" class="input" :disabled="!preferencesForm.quiet_hours_enabled" />
          </label>
          <label class="field field-wide">
            <span>Timezone</span>
            <input v-model="preferencesForm.timezone" type="text" class="input" placeholder="UTC or Asia/Kolkata" />
          </label>
        </div>

        <div v-if="saveError" class="state-box error-box">{{ saveError }}</div>
        <div v-if="saveSuccess" class="state-box success-box">{{ saveSuccess }}</div>

        <div class="prefs-actions">
          <button class="btn btn-secondary" type="button" @click="resetPreferences">Reset</button>
          <button class="btn btn-primary" type="submit">Save preferences</button>
        </div>
      </form>
    </section>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useNotificationsStore } from '../stores/notifications'

const notificationsStore = useNotificationsStore()
const activeTab = ref('inbox')
const loadingInbox = ref(false)
const saveError = ref('')
const saveSuccess = ref('')
const currentPage = ref(1)
const pageCursors = ref([null])
const PAGE_SIZE = 10

const preferencesForm = ref({
  in_app_enabled: true,
  marketing_enabled: true,
  announcements_enabled: true,
  alerts_enabled: true,
  quiet_hours_enabled: false,
  quiet_hours_start: '',
  quiet_hours_end: '',
  timezone: 'UTC',
})

const inboxItems = computed(() => notificationsStore.inboxItems)
const totalPages = computed(() => Math.max(1, Math.ceil((notificationsStore.inboxPagination.totalItems || 0) / PAGE_SIZE)))
const inboxRangeLabel = computed(() => {
  const totalItems = notificationsStore.inboxPagination.totalItems || 0
  if (!totalItems || !inboxItems.value.length) return '0-0 of 0'
  const start = (currentPage.value - 1) * PAGE_SIZE + 1
  const end = start + inboxItems.value.length - 1
  return `${start}-${end} of ${totalItems}`
})

const formatDate = (value) => {
  if (!value) return 'N/A'
  return new Date(value).toLocaleString('en-IN', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}

const syncForm = () => {
  const prefs = notificationsStore.preferences || {}
  preferencesForm.value = {
    in_app_enabled: Boolean(prefs.in_app_enabled ?? true),
    marketing_enabled: Boolean(prefs.marketing_enabled ?? true),
    announcements_enabled: Boolean(prefs.announcements_enabled ?? true),
    alerts_enabled: Boolean(prefs.alerts_enabled ?? true),
    quiet_hours_enabled: Boolean(prefs.quiet_hours_enabled ?? false),
    quiet_hours_start: prefs.quiet_hours_start || '',
    quiet_hours_end: prefs.quiet_hours_end || '',
    timezone: prefs.timezone || 'UTC',
  }
}

const resetInboxPagination = () => {
  currentPage.value = 1
  pageCursors.value = [null]
}

const loadInboxPage = async (page = currentPage.value) => {
  const currentCursor = pageCursors.value[page - 1]
  const response = await notificationsStore.loadInbox({
    unreadOnly: false,
    cursor: currentCursor,
    pageSize: PAGE_SIZE,
  })
  if (pageCursors.value.length === page) {
    pageCursors.value.push(response?.pagination?.next_cursor || null)
  } else {
    pageCursors.value[page] = response?.pagination?.next_cursor || null
  }
  pageCursors.value = pageCursors.value.slice(0, page + 1)
  currentPage.value = page
}

const loadAll = async () => {
  loadingInbox.value = true
  try {
    await Promise.all([notificationsStore.loadSummary(), notificationsStore.loadPreferences()])
    await loadInboxPage(1)
    syncForm()
  } finally {
    loadingInbox.value = false
  }
}

const markRead = async (deliveryId) => {
  await notificationsStore.markRead(deliveryId)
  await loadInboxPage(currentPage.value)
}

const markAllRead = async () => {
  await notificationsStore.markAllRead()
  resetInboxPagination()
  await loadInboxPage(1)
}

const previousPage = async () => {
  if (currentPage.value === 1 || loadingInbox.value) return
  loadingInbox.value = true
  try {
    await loadInboxPage(currentPage.value - 1)
  } finally {
    loadingInbox.value = false
  }
}

const nextPage = async () => {
  if (!notificationsStore.inboxPagination.hasMore || loadingInbox.value) return
  loadingInbox.value = true
  try {
    await loadInboxPage(currentPage.value + 1)
  } finally {
    loadingInbox.value = false
  }
}

const savePreferences = async () => {
  saveError.value = ''
  saveSuccess.value = ''
  try {
    await notificationsStore.savePreferences({ ...preferencesForm.value })
    syncForm()
    saveSuccess.value = 'Preferences saved'
  } catch (error) {
    console.error('Failed to save notification preferences:', error)
    saveError.value = error.response?.data?.detail || 'Failed to save preferences'
  }
}

const resetPreferences = () => {
  syncForm()
}

onMounted(loadAll)
</script>

<style scoped>
.notification-center-page {
  display: grid;
  gap: 1.4rem;
}

.notification-center-hero {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  padding: 1.4rem;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(14, 116, 144, 0.08), rgba(59, 130, 246, 0.12));
  border: 1px solid rgba(125, 211, 252, 0.35);
}

.hero-kicker {
  margin: 0 0 0.35rem;
  text-transform: uppercase;
  letter-spacing: 0.12em;
  font-size: 0.72rem;
  color: #0369a1;
}

.notification-center-hero h1 {
  margin: 0;
  color: #0f172a;
}

.hero-copy {
  margin: 0.45rem 0 0;
  color: #475569;
}

.hero-pill {
  min-width: 110px;
  padding: 1rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.85);
  border: 1px solid rgba(148, 163, 184, 0.24);
  display: grid;
  justify-items: center;
}

.hero-pill strong {
  font-size: 1.65rem;
  color: #0f172a;
}

.center-tabs {
  display: flex;
  gap: 0.75rem;
}

.center-tab {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: #fff;
  color: #334155;
  border-radius: 999px;
  padding: 0.7rem 1rem;
  cursor: pointer;
  font-weight: 700;
}

.center-tab.active {
  background: #0f766e;
  color: #fff;
  border-color: #0f766e;
}

.center-panel {
  background: #fff;
  border-radius: 24px;
  border: 1px solid rgba(226, 232, 240, 0.9);
  padding: 1.35rem;
  display: grid;
  gap: 1rem;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
}

.panel-head h2 {
  margin: 0;
  color: #0f172a;
}

.panel-head p {
  margin: 0.3rem 0 0;
  color: #64748b;
}

.inbox-list {
  display: grid;
  gap: 0.85rem;
}

.inbox-card {
  border: 1px solid rgba(226, 232, 240, 0.95);
  border-radius: 18px;
  padding: 1rem;
  background: #f8fafc;
  display: grid;
  gap: 0.7rem;
}

.inbox-card.unread {
  border-color: rgba(14, 116, 144, 0.4);
  background: rgba(239, 246, 255, 0.75);
}

.pager-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-top: 1rem;
}

.pager-copy {
  color: #64748b;
  font-size: 0.88rem;
}

.pager-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.inbox-top,
.inbox-actions {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.inbox-top h3 {
  margin: 0.35rem 0 0;
  color: #0f172a;
}

.type-pill {
  display: inline-flex;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-size: 0.74rem;
  font-weight: 700;
}

.meta-copy {
  color: #64748b;
  font-size: 0.84rem;
}

.prefs-form {
  display: grid;
  gap: 1rem;
}

.prefs-toggle {
  display: flex;
  align-items: center;
  gap: 0.65rem;
  color: #334155;
  font-weight: 600;
}

.prefs-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field span {
  font-size: 0.86rem;
  color: #475569;
  font-weight: 700;
}

.field-wide {
  grid-column: 1 / -1;
}

.input {
  border: 1px solid #dbe4ee;
  border-radius: 12px;
  padding: 0.8rem 0.85rem;
  font: inherit;
  background: #f8fafc;
}

.prefs-actions {
  display: flex;
  gap: 0.75rem;
}

.state-box {
  border-radius: 14px;
  padding: 0.95rem 1rem;
  background: #f8fafc;
  color: #475569;
}

.error-box {
  background: #fff1f2;
  color: #b91c1c;
}

.success-box {
  background: #ecfdf5;
  color: #047857;
}

@media (max-width: 900px) {
  .notification-center-hero,
  .panel-head,
  .inbox-top,
  .inbox-actions,
  .prefs-actions {
    flex-direction: column;
    align-items: flex-start;
  }

  .prefs-grid {
    grid-template-columns: 1fr;
  }
}
</style>