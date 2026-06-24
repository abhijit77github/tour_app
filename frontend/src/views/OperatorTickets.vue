<template>
  <div class="operator-tickets-page">
    <section class="tickets-hero">
      <div>
        <p class="eyebrow">Operator support</p>
        <h1>Support tickets</h1>
        <p>Report platform issues, track progress, and review admin replies without leaving your workspace.</p>
      </div>
      <div class="hero-badge">
        <strong>{{ ticketSummary.total }}</strong>
        <span>Total tickets</span>
      </div>
    </section>

    <div v-if="notice" :class="['notice', noticeType]">{{ notice }}</div>

    <div class="tickets-grid">
      <section class="panel form-panel">
        <div class="panel-head">
          <div>
            <p class="panel-kicker">Create ticket</p>
            <h2>Report an issue</h2>
          </div>
        </div>

        <form class="ticket-form" @submit.prevent="submitTicket">
          <label>
            Subject
            <input v-model="form.title" type="text" maxlength="140" required />
          </label>

          <div class="field-row">
            <label>
              Category
              <select v-model="form.category">
                <option value="general">General</option>
                <option value="technical">Technical</option>
                <option value="billing">Billing</option>
                <option value="content">Content</option>
                <option value="access">Access</option>
              </select>
            </label>

            <label>
              Priority
              <select v-model="form.priority">
                <option value="low">Low</option>
                <option value="medium">Medium</option>
                <option value="high">High</option>
                <option value="urgent">Urgent</option>
              </select>
            </label>
          </div>

          <label>
            Description
            <textarea v-model="form.description" rows="8" maxlength="4000" required placeholder="Describe the problem, affected workflow, and any error details."></textarea>
          </label>

          <div class="attachment-block">
            <span class="attachment-label">Attachments</span>
            <ImageUpload
              v-model="form.attachments"
              :multiple="true"
              upload-endpoint="/upload/ticket-attachments"
            />
          </div>

          <button class="btn-primary" type="submit" :disabled="submitting">
            {{ submitting ? 'Submitting…' : 'Create ticket' }}
          </button>
        </form>
      </section>

      <section class="panel list-panel">
        <div class="panel-head">
          <div>
            <p class="panel-kicker">Ticket history</p>
            <h2>Your recent issues</h2>
          </div>
          <button class="panel-tab-button icon-only-button" type="button" @click="loadTickets" :disabled="loading" :aria-label="loading ? 'Refreshing tickets' : 'Refresh tickets'" :title="loading ? 'Refreshing tickets' : 'Refresh tickets'">
            {{ loading ? '↻' : '⟳' }}
          </button>
        </div>

        <div class="filter-row">
          <button
            v-for="status in statuses"
            :key="status"
            type="button"
            :class="['filter-chip', { active: activeStatus === status }]"
            @click="activeStatus = status"
          >
            {{ humanize(status) }}
          </button>
        </div>

        <div v-if="loading" class="state-box">Loading tickets…</div>
        <div v-else-if="!tickets.length" class="state-box">No tickets yet for this filter.</div>

        <div v-else class="ticket-list">
          <article v-for="ticket in tickets" :key="ticket._id" class="ticket-card">
            <div class="ticket-top">
              <div>
                <span class="ticket-id">#{{ ticket._id.slice(-6).toUpperCase() }}</span>
                <h3>{{ ticket.title }}</h3>
              </div>
              <span :class="['status-pill', `status-${ticket.status}`]">{{ humanize(ticket.status) }}</span>
            </div>

            <div class="meta-row">
              <span class="meta-pill">{{ humanize(ticket.category) }}</span>
              <span class="meta-pill priority">{{ humanize(ticket.priority) }}</span>
              <span class="meta-date">{{ formatDate(ticket.updated_at || ticket.created_at) }}</span>
            </div>

            <div class="ticket-actions">
              <button class="inline-tab" type="button" @click="toggleExpandedTicket(ticket._id)">
                {{ isTicketExpanded(ticket._id) ? 'Hide details' : 'View details' }}
              </button>
              <button class="inline-tab" type="button" @click="toggleDiscussion(ticket._id)">
                {{ isDiscussionExpanded(ticket._id) ? 'Hide discussion' : `Discussion${ticket.comments?.length ? ` (${ticket.comments.length})` : ''}` }}
              </button>
            </div>

            <div v-if="isTicketExpanded(ticket._id)" class="expand-panel details-panel">
              <p class="ticket-description">{{ ticket.description }}</p>

              <div v-if="ticket.attachments?.length" class="attachment-gallery">
                <a v-for="(attachment, idx) in ticket.attachments" :key="idx" :href="getImageUrl(attachment)" target="_blank" rel="noreferrer" class="attachment-thumb">
                  <img :src="getImageUrl(attachment)" :alt="`Attachment ${idx + 1}`" />
                </a>
              </div>

              <div v-if="ticket.latest_public_reply" class="reply-box">
                <strong>Latest admin reply</strong>
                <p>{{ ticket.latest_public_reply }}</p>
              </div>

              <div class="history-list">
                <div v-for="(item, idx) in ticket.status_history.slice().reverse().slice(0, 3)" :key="idx" class="history-item">
                  <span>{{ humanize(item.status) }}</span>
                  <small>{{ formatDate(item.created_at) }}</small>
                </div>
              </div>
            </div>

            <div v-if="isDiscussionExpanded(ticket._id)" class="comments-block expand-panel">
              <div class="discussion-head">
                <h4>Discussion</h4>
                <span class="discussion-count">{{ ticket.comments?.length || 0 }} updates</span>
              </div>
              <div v-if="ticket.comments?.length" class="comment-list">
                <article v-for="(comment, idx) in ticket.comments.slice().reverse()" :key="idx" class="comment-card">
                  <div class="comment-meta">
                    <strong>{{ comment.actor_name }}</strong>
                    <small>{{ formatDate(comment.created_at) }}</small>
                  </div>
                  <p v-if="comment.message">{{ comment.message }}</p>
                  <div v-if="comment.attachments?.length" class="attachment-gallery compact">
                    <a v-for="(attachment, attachmentIdx) in comment.attachments" :key="attachmentIdx" :href="getImageUrl(attachment)" target="_blank" rel="noreferrer" class="attachment-thumb small">
                      <img :src="getImageUrl(attachment)" :alt="`Comment attachment ${attachmentIdx + 1}`" />
                    </a>
                  </div>
                </article>
              </div>
              <p v-else class="empty-copy">No discussion yet.</p>

              <form class="comment-form" @submit.prevent="submitComment(ticket._id)">
                <textarea v-model="commentDrafts[ticket._id].message" rows="3" maxlength="2000" placeholder="Add a follow-up comment for the admin team."></textarea>
                <ImageUpload
                  v-model="commentDrafts[ticket._id].attachments"
                  :multiple="true"
                  upload-endpoint="/upload/ticket-attachments"
                />
                <button class="btn-secondary" type="submit" :disabled="commentSubmitting[ticket._id]">
                  {{ commentSubmitting[ticket._id] ? 'Sending…' : 'Post comment' }}
                </button>
              </form>
            </div>
          </article>

          <div class="pagination-bar">
            <button class="pagination-button" type="button" @click="previousPage" :disabled="currentPage === 1 || loading">
              Previous
            </button>
            <div class="pagination-status">Page {{ currentPage }} of {{ pagination.totalPages }}</div>
            <button class="pagination-button" type="button" @click="nextPage" :disabled="!pagination.hasMore || loading">
              Next
            </button>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref, watch } from 'vue'
import api from '../services/api'
import ImageUpload from '../components/ImageUpload.vue'

const tickets = ref([])
const ticketSummary = ref({ total: 0, open: 0 })
const pagination = ref({ totalItems: 0, totalPages: 1, pageSize: 10, hasMore: false })
const loading = ref(false)
const submitting = ref(false)
const notice = ref('')
const noticeType = ref('success')
const activeStatus = ref('all')
const statuses = ['all', 'open', 'acknowledged', 'in_progress', 'completed']
const currentPage = ref(1)
const pageSize = 10
const pageCursors = ref([null])

const form = ref({
  title: '',
  category: 'general',
  priority: 'medium',
  description: '',
  attachments: [],
})
const commentDrafts = ref({})
const commentSubmitting = ref({})
const expandedTickets = ref({})
const expandedDiscussions = ref({})

const humanize = (value) => String(value || '').replaceAll('_', ' ')

const getImageUrl = (url) => {
  if (!url) return ''
  if (url.startsWith('http')) return url
  return `http://localhost:8808${url}`
}

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

const ensureDraft = (ticketId) => {
  if (!commentDrafts.value[ticketId]) {
    commentDrafts.value[ticketId] = { message: '', attachments: [] }
  }
  return commentDrafts.value[ticketId]
}

const isTicketExpanded = (ticketId) => Boolean(expandedTickets.value[ticketId])

const isDiscussionExpanded = (ticketId) => Boolean(expandedDiscussions.value[ticketId])

const toggleExpandedTicket = (ticketId) => {
  expandedTickets.value[ticketId] = !expandedTickets.value[ticketId]
}

const toggleDiscussion = (ticketId) => {
  expandedDiscussions.value[ticketId] = !expandedDiscussions.value[ticketId]
  ensureDraft(ticketId)
}

const loadTickets = async () => {
  loading.value = true
  try {
    const params = {
      page_size: pageSize,
    }
    const currentCursor = pageCursors.value[currentPage.value - 1]
    if (currentCursor) {
      params.cursor = currentCursor
    }
    if (activeStatus.value !== 'all') {
      params.status_value = activeStatus.value
    }

    const response = await api.get('/operator/tickets', { params })
    tickets.value = response.data.tickets || []
    ticketSummary.value = response.data.summary || { total: 0, open: 0 }
    pagination.value = {
      totalItems: response.data.pagination?.total_items || 0,
      totalPages: response.data.pagination?.total_pages || 1,
      pageSize: response.data.pagination?.page_size || pageSize,
      hasMore: Boolean(response.data.pagination?.has_more),
    }
    if (pageCursors.value.length === currentPage.value) {
      pageCursors.value.push(response.data.pagination?.next_cursor || null)
    } else {
      pageCursors.value[currentPage.value] = response.data.pagination?.next_cursor || null
    }
    pageCursors.value = pageCursors.value.slice(0, currentPage.value + 1)
    tickets.value.forEach((ticket) => ensureDraft(ticket._id))
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to load support tickets'
  } finally {
    loading.value = false
  }
}

const resetPagination = () => {
  currentPage.value = 1
  pageCursors.value = [null]
}

const previousPage = () => {
  if (currentPage.value === 1 || loading.value) return
  currentPage.value -= 1
}

const nextPage = () => {
  if (!pagination.value.hasMore || loading.value) return
  currentPage.value += 1
}

const resetForm = () => {
  form.value = {
    title: '',
    category: 'general',
    priority: 'medium',
    description: '',
    attachments: [],
  }
}

const submitTicket = async () => {
  submitting.value = true
  notice.value = ''
  try {
    await api.post('/operator/tickets', form.value)
    noticeType.value = 'success'
    notice.value = 'Support ticket created successfully.'
    resetForm()
    await loadTickets()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to create support ticket'
  } finally {
    submitting.value = false
  }
}

const submitComment = async (ticketId) => {
  const draft = ensureDraft(ticketId)
  commentSubmitting.value[ticketId] = true
  notice.value = ''
  try {
    await api.post(`/operator/tickets/${ticketId}/comments`, draft)
    draft.message = ''
    draft.attachments = []
    noticeType.value = 'success'
    notice.value = 'Comment posted successfully.'
    await loadTickets()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to post comment'
  } finally {
    commentSubmitting.value[ticketId] = false
  }
}

watch(activeStatus, () => {
  if (currentPage.value !== 1) {
    resetPagination()
    return
  }
  pageCursors.value = [null]
  loadTickets()
})

watch(currentPage, () => {
  loadTickets()
})

onMounted(loadTickets)
</script>

<style scoped>
.operator-tickets-page {
  padding: 2rem;
  display: grid;
  gap: 1.25rem;
}

.tickets-hero {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.5rem;
  border-radius: 22px;
  background: linear-gradient(135deg, #0f172a, #1d4ed8 70%, #38bdf8);
  color: #fff;
}

.eyebrow,
.panel-kicker {
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 0.75rem;
  font-weight: 700;
  margin: 0 0 0.35rem;
}

.hero-badge,
.panel {
  background: #fff;
  border: 1px solid #dbe4f0;
  border-radius: 18px;
  box-shadow: 0 14px 32px rgba(15, 23, 42, 0.06);
}

.hero-badge {
  min-width: 130px;
  color: #0f172a;
  display: grid;
  place-items: center;
  padding: 1rem;
}

.hero-badge strong {
  font-size: 1.8rem;
}

.tickets-grid {
  display: grid;
  grid-template-columns: minmax(320px, 420px) minmax(0, 1fr);
  gap: 1rem;
}

.panel {
  padding: 1.15rem;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  margin-bottom: 1rem;
}

.ticket-form,
.ticket-list {
  display: grid;
  gap: 0.9rem;
}

.ticket-form label,
.field-row label {
  display: grid;
  gap: 0.4rem;
  font-weight: 600;
  color: #334155;
}

.field-row {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

input,
select,
textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 0.8rem 0.9rem;
  font: inherit;
  background: #fff;
}

textarea {
  resize: vertical;
}

.btn-primary,
.btn-secondary {
  border: none;
  border-radius: 12px;
  padding: 0.78rem 1rem;
  font-weight: 700;
  cursor: pointer;
}

.btn-primary {
  background: #2563eb;
  color: #fff;
}

.btn-secondary {
  background: #e2e8f0;
  color: #0f172a;
}

.panel-tab-button,
.inline-tab {
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #0f172a;
  border-radius: 999px;
  padding: 0.48rem 0.85rem;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  transition: background-color 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.panel-tab-button:hover,
.inline-tab:hover {
  background: #eff6ff;
  border-color: #93c5fd;
}

.icon-only-button {
  width: 2.5rem;
  height: 2.5rem;
  padding: 0;
  display: inline-grid;
  place-items: center;
  font-size: 1rem;
}

.filter-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0;
  margin-bottom: 1rem;
  padding: 0.35rem;
  border: 1px solid #dbe4f0;
  border-radius: 16px;
  background: #f8fafc;
  overflow-x: auto;
}

.filter-chip {
  border: none;
  background: transparent;
  border-radius: 12px;
  padding: 0.65rem 0.9rem;
  cursor: pointer;
  color: #475569;
  font-weight: 700;
  white-space: nowrap;
}

.filter-chip.active {
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08);
  color: #1d4ed8;
}

.ticket-card {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
  display: grid;
  gap: 0.8rem;
  background: linear-gradient(180deg, #ffffff, #f8fbff);
}

.ticket-top {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
}

.ticket-id {
  font-size: 0.74rem;
  letter-spacing: 0.08em;
  color: #64748b;
}

.ticket-top h3 {
  margin: 0.2rem 0 0;
  color: #0f172a;
}

.status-pill,
.meta-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.28rem 0.7rem;
  font-size: 0.76rem;
  font-weight: 700;
}

.status-open { background: #fee2e2; color: #b91c1c; }
.status-acknowledged { background: #fef3c7; color: #b45309; }
.status-in_progress { background: #dbeafe; color: #1d4ed8; }
.status-completed { background: #dcfce7; color: #15803d; }

.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  align-items: center;
}

.meta-pill { background: #f1f5f9; color: #334155; }
.priority { text-transform: capitalize; }
.meta-date { color: #64748b; font-size: 0.85rem; }

.ticket-description,
.reply-box p {
  margin: 0;
  color: #475569;
  line-height: 1.6;
}

.ticket-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.expand-panel {
  display: grid;
  gap: 0.8rem;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 0.95rem;
  background: #fff;
}

.discussion-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
}

.discussion-count {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 600;
}

.reply-box {
  border-radius: 14px;
  background: #eff6ff;
  padding: 0.9rem;
}

.attachment-block,
.comments-block {
  display: grid;
  gap: 0.6rem;
}

.attachment-label,
.comments-block h4 {
  font-weight: 700;
  color: #0f172a;
}

.comments-block h4 {
  margin: 0;
}

.comment-list,
.comment-form {
  display: grid;
  gap: 0.75rem;
}

.comment-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 0.85rem;
  background: #fff;
}

.comment-card p,
.empty-copy {
  margin: 0;
  color: #475569;
}

.comment-meta {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.45rem;
}

.comment-form textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 0.8rem 0.9rem;
  resize: vertical;
  font: inherit;
}

.attachment-gallery {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
}

.attachment-thumb {
  width: 88px;
  height: 88px;
  border-radius: 12px;
  overflow: hidden;
  border: 1px solid #cbd5e1;
}

.attachment-thumb img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.attachment-gallery.compact .attachment-thumb.small {
  width: 72px;
  height: 72px;
}

.reply-box strong {
  display: block;
  margin-bottom: 0.35rem;
  color: #1e3a8a;
}

.history-list {
  display: grid;
  gap: 0.4rem;
}

.history-item {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  font-size: 0.86rem;
  color: #475569;
}

.notice,
.state-box {
  border-radius: 14px;
  padding: 0.9rem 1rem;
}

.notice.success,
.state-box {
  background: #f8fafc;
  border: 1px solid #dbe4f0;
}

.notice.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}

@media (max-width: 980px) {
  .tickets-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .operator-tickets-page {
    padding: 1rem;
  }

  .tickets-hero,
  .ticket-top,
  .panel-head,
  .history-item,
  .discussion-head {
    grid-template-columns: 1fr;
    display: grid;
  }

  .field-row {
    grid-template-columns: 1fr;
  }
}
</style>