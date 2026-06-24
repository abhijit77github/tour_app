<template>
  <div class="tickets-admin-page">
    <section class="admin-hero">
      <div>
        <p class="eyebrow">Support operations</p>
        <h1>Ticket workspace</h1>
        <p>Review operator-reported issues, assign ownership, and send automatic status replies from one queue.</p>
      </div>
      <div class="hero-metrics">
        <div>
          <strong>{{ ticketSummary.total }}</strong>
          <span>Total</span>
        </div>
        <div>
          <strong>{{ ticketSummary.open }}</strong>
          <span>Open</span>
        </div>
      </div>
    </section>

    <div v-if="notice" :class="['notice', noticeType]">{{ notice }}</div>

    <div class="workspace-grid">
      <section class="panel queue-panel">
        <div class="panel-head">
          <div>
            <p class="panel-kicker">Queue</p>
            <h2>Incoming tickets</h2>
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
            :class="['filter-chip', { active: filters.status === status }]"
            @click="filters.status = status"
          >
            {{ humanize(status) }}
          </button>
        </div>
        <div class="queue-tools">
          <label class="search-field">
            <span>Ticket ID</span>
            <input v-model="filters.ticketId" type="text" placeholder="Search by full or partial ticket ID" />
          </label>
          <div class="results-copy">{{ tickets.length }} of {{ pagination.totalItems }}</div>
        </div>

        <div v-if="loading" class="state-box">Loading tickets…</div>
        <div v-else-if="!tickets.length" class="state-box">No tickets found for the selected filter.</div>

        <div v-else class="ticket-list">
          <article
            v-for="ticket in tickets"
            :key="ticket._id"
            :class="['queue-card', { active: selectedTicket?._id === ticket._id }]"
          >
            <div class="queue-card-top">
              <span class="ticket-id">#{{ ticket._id.slice(-6).toUpperCase() }}</span>
              <span :class="['status-pill', `status-${ticket.status}`]">{{ humanize(ticket.status) }}</span>
            </div>
            <h3>{{ ticket.title }}</h3>
            <p>{{ ticket.operator_business_name }}</p>
            <div class="queue-card-footer">
              <small>{{ formatDate(ticket.updated_at || ticket.created_at) }}</small>
              <button class="inline-tab" type="button" @click="toggleSelectedTicket(ticket)">
                {{ selectedTicket?._id === ticket._id ? 'Hide details' : 'View details' }}
              </button>
            </div>

            <div v-if="selectedTicket?._id === ticket._id" class="inline-detail-panel">
              <div class="inline-detail-head">
                <div>
                  <h4>{{ ticket.operator_business_name }}</h4>
                  <p class="subcopy">{{ ticket.requester_email }}</p>
                </div>
                <div class="detail-head-actions">
                  <button class="inline-tab" type="button" @click="discussionOpen = !discussionOpen">
                    {{ discussionOpen ? 'Hide discussion' : `Discussion${ticket.comments?.length ? ` (${ticket.comments.length})` : ''}` }}
                  </button>
                </div>
              </div>

              <div class="compact-meta-row">
                <span class="meta-chip"><strong>ID</strong> #{{ ticket._id.slice(-6).toUpperCase() }}</span>
                <span class="meta-chip"><strong>Priority</strong> {{ humanize(ticket.priority) }}</span>
                <span class="meta-chip"><strong>Category</strong> {{ humanize(ticket.category) }}</span>
                <span class="meta-chip"><strong>Assignee</strong> {{ ticket.assignee_admin_name || 'Unassigned' }}</span>
              </div>

              <article class="description-box compact-box">
                <p>{{ ticket.description }}</p>
                <div v-if="ticket.attachments?.length" class="attachment-gallery compact">
                  <a v-for="(attachment, idx) in ticket.attachments" :key="idx" :href="getImageUrl(attachment)" target="_blank" rel="noreferrer" class="attachment-thumb small">
                    <img :src="getImageUrl(attachment)" :alt="`Ticket attachment ${idx + 1}`" />
                  </a>
                </div>
              </article>

              <form class="update-form compact-form" @submit.prevent="updateTicket">
                <div class="field-row compact-field-row">
                  <label>
                    Status
                    <select v-model="updateForm.status">
                      <option value="open">Open</option>
                      <option value="acknowledged">Acknowledged</option>
                      <option value="in_progress">In Progress</option>
                      <option value="completed">Completed</option>
                    </select>
                  </label>
                  <label>
                    Assignee
                    <select v-model="updateForm.assignee_admin_id">
                      <option value="">Me</option>
                      <option v-for="member in assignableAdmins" :key="member._id" :value="member.principal_id">
                        {{ member.principal?.full_name || member.principal?.email }}
                      </option>
                    </select>
                  </label>
                </div>

                <label>
                  Public reply
                  <textarea v-model="updateForm.public_reply" rows="3" maxlength="2000" placeholder="Optional message sent automatically to the operator when the status changes."></textarea>
                </label>

                <div class="compact-actions">
                  <button class="btn-primary" type="submit" :disabled="saving">
                    {{ saving ? 'Saving…' : 'Update ticket' }}
                  </button>
                </div>
              </form>

              <div class="history-block compact-history-block">
                <h3>Status history</h3>
                <div class="history-list compact-history-list">
                  <article v-for="(item, idx) in ticket.status_history.slice().reverse()" :key="idx" class="history-card compact-history-card">
                    <div>
                      <strong>{{ humanize(item.status) }}</strong>
                      <p>{{ item.message }}</p>
                      <small>{{ item.actor_name }} • {{ formatDate(item.created_at) }}</small>
                    </div>
                    <p v-if="item.public_reply" class="public-reply">{{ item.public_reply }}</p>
                  </article>
                </div>
              </div>

              <div v-if="discussionOpen" class="history-block comments-block compact-history-block">
                <div class="discussion-head">
                  <h3>Discussion</h3>
                  <span class="discussion-count">{{ ticket.comments?.length || 0 }} updates</span>
                </div>
                <div v-if="ticket.comments?.length" class="history-list compact-history-list">
                  <div class="single-conversation-box">
                    <div v-for="(comment, idx) in ticket.comments.slice().reverse()" :key="idx" class="single-comment">
                      <div class="single-comment-head">
                        <strong>{{ comment.actor_name }}</strong>
                        <small>{{ formatDate(comment.created_at) }}</small>
                      </div>
                      <p v-if="comment.message">{{ comment.message }}</p>
                      <div v-if="comment.attachments?.length" class="attachment-gallery compact">
                        <a v-for="(attachment, attachmentIdx) in comment.attachments" :key="attachmentIdx" :href="getImageUrl(attachment)" target="_blank" rel="noreferrer" class="attachment-thumb small">
                          <img :src="getImageUrl(attachment)" :alt="`Comment attachment ${attachmentIdx + 1}`" />
                        </a>
                      </div>
                    </div>
                  </div>
                </div>
                <p v-else class="subcopy">No comments yet.</p>

                <form class="update-form compact-form" @submit.prevent="submitComment">
                  <label>
                    Comment
                    <textarea v-model="commentForm.message" rows="3" maxlength="2000" placeholder="Send a threaded update without changing ticket status."></textarea>
                  </label>
                  <div class="attachment-block compact-attachment-block">
                    <span>Attachments</span>
                    <ImageUpload
                      v-model="commentForm.attachments"
                      :multiple="true"
                      upload-endpoint="/upload/ticket-attachments"
                    />
                  </div>
                  <div class="compact-actions">
                    <button class="btn-secondary" type="submit" :disabled="commentSaving">
                      {{ commentSaving ? 'Sending…' : 'Post comment' }}
                    </button>
                  </div>
                </form>
              </div>
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
import { computed, onMounted, ref, watch } from 'vue'
import api from '../services/api'
import ImageUpload from '../components/ImageUpload.vue'

const tickets = ref([])
const assignableAdmins = ref([])
const selectedTicket = ref(null)
const ticketSummary = ref({ total: 0, open: 0 })
const pagination = ref({ totalItems: 0, totalPages: 1, pageSize: 10, hasMore: false })
const loading = ref(false)
const saving = ref(false)
const notice = ref('')
const noticeType = ref('success')
const statuses = ['all', 'open', 'acknowledged', 'in_progress', 'completed']
const filters = ref({ status: 'all', ticketId: '' })
const updateForm = ref({
  status: 'open',
  assignee_admin_id: '',
  public_reply: '',
})
const commentForm = ref({ message: '', attachments: [] })
const commentSaving = ref(false)
const discussionOpen = ref(false)
const currentPage = ref(1)
const pageSize = 10
const pageCursors = ref([null])

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

const syncUpdateForm = () => {
  if (!selectedTicket.value) return
  updateForm.value = {
    status: selectedTicket.value.status,
    assignee_admin_id: selectedTicket.value.assignee_admin_id || '',
    public_reply: selectedTicket.value.latest_public_reply || '',
  }
}

const resetCommentForm = () => {
  commentForm.value = { message: '', attachments: [] }
}

const loadAdmins = async () => {
  const response = await api.get('/admin/team')
  assignableAdmins.value = response.data.members || []
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
    if (filters.value.status !== 'all') {
      params.status_value = filters.value.status
    }
    if (filters.value.ticketId.trim()) {
      params.ticket_id = filters.value.ticketId.trim()
    }

    const response = await api.get('/admin/tickets', { params })
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
    if (selectedTicket.value) {
      selectedTicket.value = tickets.value.find((ticket) => ticket._id === selectedTicket.value._id) || null
    }
    syncUpdateForm()
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

const selectTicket = (ticket) => {
  selectedTicket.value = ticket
  syncUpdateForm()
  resetCommentForm()
  discussionOpen.value = false
}

const toggleSelectedTicket = (ticket) => {
  if (selectedTicket.value?._id === ticket._id) {
    selectedTicket.value = null
    discussionOpen.value = false
    resetCommentForm()
    return
  }
  selectTicket(ticket)
}

const updateTicket = async () => {
  if (!selectedTicket.value) return
  saving.value = true
  notice.value = ''
  try {
    const payload = {
      status: updateForm.value.status,
      public_reply: updateForm.value.public_reply || null,
      assignee_admin_id: updateForm.value.assignee_admin_id || null,
    }
    const response = await api.patch(`/admin/tickets/${selectedTicket.value._id}`, payload)
    selectedTicket.value = response.data.ticket
    noticeType.value = 'success'
    notice.value = 'Ticket updated successfully.'
    await loadTickets()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to update ticket'
  } finally {
    saving.value = false
  }
}

const submitComment = async () => {
  if (!selectedTicket.value) return
  commentSaving.value = true
  notice.value = ''
  try {
    const response = await api.post(`/admin/tickets/${selectedTicket.value._id}/comments`, commentForm.value)
    selectedTicket.value = response.data.ticket
    resetCommentForm()
    noticeType.value = 'success'
    notice.value = 'Comment posted successfully.'
    await loadTickets()
  } catch (error) {
    noticeType.value = 'error'
    notice.value = error.response?.data?.detail || 'Failed to post comment'
  } finally {
    commentSaving.value = false
  }
}

watch(
  () => [filters.value.status, filters.value.ticketId],
  () => {
    if (currentPage.value !== 1) {
      resetPagination()
      return
    }
    pageCursors.value = [null]
    loadTickets()
  },
)

watch(currentPage, () => {
  loadTickets()
})

watch(tickets, (nextTickets) => {
  if (currentPage.value > pagination.value.totalPages) {
    currentPage.value = pagination.value.totalPages
    pageCursors.value = pageCursors.value.slice(0, Math.max(1, pagination.value.totalPages))
    return
  }
  if (selectedTicket.value && !nextTickets.some((ticket) => ticket._id === selectedTicket.value._id)) {
    selectedTicket.value = null
    discussionOpen.value = false
    resetCommentForm()
  }
})

onMounted(async () => {
  await Promise.all([loadAdmins(), loadTickets()])
})
</script>

<style scoped>
.tickets-admin-page {
  display: grid;
  gap: 1.25rem;
}

.admin-hero {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  padding: 1.4rem;
  border-radius: 24px;
  background: linear-gradient(135deg, rgba(15, 23, 42, 0.98), rgba(37, 99, 235, 0.92));
  color: #fff;
}

.eyebrow,
.panel-kicker {
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.75rem;
  font-weight: 700;
  margin: 0 0 0.35rem;
}

.hero-metrics {
  display: flex;
  gap: 0.8rem;
}

.hero-metrics div,
.panel,
.meta-box,
.description-box,
.history-card {
  background: #fff;
  color: #0f172a;
  border: 1px solid #dbe4f0;
  border-radius: 16px;
}

.hero-metrics div {
  min-width: 110px;
  display: grid;
  place-items: center;
  padding: 0.9rem;
}

.hero-metrics strong {
  font-size: 1.6rem;
}

.workspace-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr);
  gap: 1rem;
}

.panel {
  padding: 1.1rem;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.06);
}

.panel-head,
.detail-head,
.queue-card-top,
.field-row {
  display: flex;
  justify-content: space-between;
  gap: 0.9rem;
}

.filter-row,
.ticket-list,
.history-list {
  display: grid;
  gap: 0.75rem;
}

.queue-tools {
  display: flex;
  justify-content: space-between;
  gap: 0.9rem;
  align-items: end;
  margin-bottom: 1rem;
}

.search-field {
  display: grid;
  gap: 0.35rem;
  color: #334155;
  font-weight: 600;
  flex: 1;
}

.search-field span {
  font-size: 0.8rem;
}

.search-field input {
  width: 100%;
  max-width: 320px;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 0.72rem 0.9rem;
  font: inherit;
  background: #fff;
}

.results-copy {
  color: #64748b;
  font-size: 0.85rem;
  font-weight: 600;
  white-space: nowrap;
}

.filter-row {
  grid-template-columns: repeat(5, minmax(0, max-content));
  margin-bottom: 1rem;
  padding: 0.35rem;
  border: 1px solid #dbe4f0;
  border-radius: 16px;
  background: #f8fafc;
  justify-content: start;
  overflow-x: auto;
}

.filter-chip,
.btn-primary,
.btn-secondary,
.panel-tab-button,
.inline-tab {
  border-radius: 12px;
  font: inherit;
}

.filter-chip,
.btn-secondary,
.panel-tab-button,
.inline-tab,
.queue-card {
  border: 1px solid #cbd5e1;
  background: #fff;
}

.filter-chip,
.btn-primary,
.btn-secondary {
  padding: 0.72rem 0.9rem;
  cursor: pointer;
}

.filter-chip {
  border: none;
  background: transparent;
  border-radius: 12px;
  color: #475569;
  font-weight: 700;
  white-space: nowrap;
}

.panel-tab-button,
.inline-tab {
  padding: 0.48rem 0.85rem;
  cursor: pointer;
  border-radius: 999px;
  font-weight: 700;
  transition: background-color 0.2s ease, border-color 0.2s ease;
}

.icon-only-button {
  width: 2.5rem;
  height: 2.5rem;
  padding: 0;
  display: inline-grid;
  place-items: center;
  font-size: 1rem;
}

.filter-chip.active,
.queue-card.active {
  border-color: #60a5fa;
  background: #eff6ff;
}

.filter-chip.active {
  background: #ffffff;
  box-shadow: 0 6px 18px rgba(15, 23, 42, 0.08);
  color: #1d4ed8;
}

.queue-card {
  padding: 0.9rem;
  text-align: left;
  display: grid;
  gap: 0.7rem;
  background: linear-gradient(180deg, #ffffff, #f8fbff);
}

.pagination-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding-top: 0.5rem;
}

.pagination-button {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #0f172a;
  border-radius: 999px;
  padding: 0.5rem 0.85rem;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.pagination-button:disabled {
  opacity: 0.45;
  cursor: not-allowed;
}

.pagination-status {
  color: #475569;
  font-size: 0.88rem;
  font-weight: 600;
}

.queue-card h3,
.inline-detail-head h4,
.description-box h3,
.history-block h3 {
  margin: 0;
}

.queue-card p,
.description-box p,
.history-card p,
.subcopy {
  margin: 0;
  color: #475569;
}

.ticket-id,
.queue-card small,
.history-card small {
  color: #64748b;
}

.queue-card-footer,
.detail-head-actions,
.discussion-head {
  display: flex;
  justify-content: space-between;
  gap: 0.9rem;
  align-items: center;
}

.inline-detail-panel {
  display: grid;
  gap: 0.8rem;
  border-top: 1px solid #dbe4f0;
  padding-top: 0.9rem;
}

.inline-detail-head {
  display: flex;
  justify-content: space-between;
  gap: 0.9rem;
  align-items: flex-start;
}

.discussion-count {
  color: #64748b;
  font-size: 0.82rem;
  font-weight: 600;
}

.status-pill {
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

.ticket-meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.compact-meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 0.35rem;
  padding: 0.35rem 0.6rem;
  border-radius: 999px;
  background: #f8fafc;
  border: 1px solid #dbe4f0;
  color: #475569;
  font-size: 0.8rem;
  line-height: 1.2;
}

.meta-chip strong {
  color: #0f172a;
  font-size: 0.75rem;
}

.meta-box,
.description-box,
.history-card {
  padding: 0.95rem;
}

.compact-box,
.compact-history-card {
  padding: 0.8rem;
}

.meta-box span {
  display: block;
  color: #64748b;
  font-size: 0.78rem;
  margin-bottom: 0.2rem;
}

.update-form {
  display: grid;
  gap: 0.9rem;
  margin: 1rem 0;
}

.compact-form {
  gap: 0.7rem;
  margin: 0;
}

.compact-field-row {
  align-items: end;
}

.compact-actions {
  display: flex;
  justify-content: flex-end;
}

.attachment-block {
  display: grid;
  gap: 0.55rem;
  color: #334155;
  font-weight: 600;
}

.compact-attachment-block {
  gap: 0.45rem;
}

.attachment-gallery {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  margin-top: 0.8rem;
}

.attachment-thumb {
  width: 92px;
  height: 92px;
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

.update-form label {
  display: grid;
  gap: 0.4rem;
  color: #334155;
  font-weight: 600;
}

select,
textarea {
  width: 100%;
  border: 1px solid #cbd5e1;
  border-radius: 12px;
  padding: 0.8rem 0.9rem;
  font: inherit;
}

textarea {
  resize: vertical;
}

.btn-primary {
  border: none;
  background: #2563eb;
  color: #fff;
  font-weight: 700;
}

.btn-secondary {
  color: #0f172a;
  background: #eef2f7;
}

.history-card {
  display: grid;
  gap: 0.5rem;
}

.compact-history-block {
  display: grid;
  gap: 0.6rem;
}

.compact-history-list {
  gap: 0.6rem;
}

.single-conversation-box {
  display: grid;
  gap: 0;
  border: 1px solid #dbe4f0;
  border-radius: 14px;
  background: #fff;
  overflow: hidden;
}

.single-comment {
  display: grid;
  gap: 0.35rem;
  padding: 0.8rem;
}

.single-comment + .single-comment {
  border-top: 1px solid #e2e8f0;
}

.single-comment-head {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  align-items: center;
}

.single-comment p {
  margin: 0;
  color: #475569;
}

.public-reply {
  background: #eff6ff;
  border-radius: 12px;
  padding: 0.8rem;
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

@media (max-width: 1080px) {
}

@media (max-width: 720px) {
  .admin-hero,
  .panel-head,
  .inline-detail-head,
  .field-row,
  .queue-tools,
  .queue-card-footer,
  .detail-head-actions,
  .discussion-head {
    display: grid;
  }

  .filter-row,
  .ticket-meta-grid {
    grid-template-columns: 1fr;
  }
}
</style>