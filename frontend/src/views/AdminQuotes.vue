<template>
  <div class="admin-quotes">
    <div class="page-header">
      <h1>Manage Quotes</h1>
      <p class="subtitle">View and manage all quote requests on the platform</p>
    </div>

    <!-- Search and Filter Bar -->
    <div class="toolbar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by tourist name, location, or destination..."
          @input="handleSearch"
          class="search-input"
        />
        <span class="search-icon">🔍</span>
      </div>

      <div class="filter-controls">
        <select v-model="statusFilter" class="filter-select">
          <option value="">All Status</option>
          <option value="open">📂 Open</option>
          <option value="closed">✓ Closed</option>
        </select>

        <select v-model="responseFilter" class="filter-select">
          <option value="">All Responses</option>
          <option value="0">0 Responses</option>
          <option value="1plus">1+ Responses</option>
          <option value="5plus">5+ Responses</option>
        </select>
      </div>

      <div class="pagination-info">
        Showing {{ currentPage * pageSize - pageSize + 1 }} to {{ Math.min(currentPage * pageSize, totalQuotes) }} of {{ totalQuotes }}
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading quotes...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredQuotes.length === 0" class="empty-state">
      <p>📭 No quotes found</p>
      <span v-if="searchQuery" class="hint">Try adjusting your search criteria</span>
    </div>

    <!-- Quotes Table -->
    <div v-else class="table-container">
      <table class="quotes-table">
        <thead>
          <tr>
            <th>Quote ID</th>
            <th>Tourist</th>
            <th>Destination</th>
            <th>Duration</th>
            <th>Budget</th>
            <th>Responses</th>
            <th>Posted</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="quote in paginatedQuotes" :key="quote._id" class="quote-row">
            <td class="quote-id-cell">{{ quote._id.slice(-8) }}</td>
            <td class="tourist-cell">{{ quote.tourist_name }}</td>
            <td class="destination-cell">
              <div class="locations">
                <span v-if="quote.from_location" class="location">📍 {{ quote.from_location }}</span>
                <span class="separator">→</span>
                <span v-if="quote.to_location" class="location">📍 {{ quote.to_location }}</span>
              </div>
            </td>
            <td class="duration-cell">{{ quote.duration }} days</td>
            <td class="budget-cell">₹{{ formatBudget(quote.min_budget) }} - ₹{{ formatBudget(quote.max_budget) }}</td>
            <td class="responses-cell">
              <span class="badge responses">{{ quote.total_responses || 0 }}</span>
            </td>
            <td class="posted-cell">{{ formatDate(quote.created_at) }}</td>
            <td class="status-cell">
              <span :class="['status-badge', quote.is_closed ? 'closed' : 'open']">
                {{ quote.is_closed ? '✓ Closed' : '📂 Open' }}
              </span>
            </td>
            <td class="actions-cell">
              <button
                @click="viewQuote(quote)"
                class="action-btn view"
                title="View Details"
              >
                👁️
              </button>
              <button
                @click="viewResponses(quote)"
                class="action-btn responses"
                title="View Responses"
              >
                💬
              </button>
              <button
                v-if="!quote.is_closed"
                @click="closeQuote(quote)"
                class="action-btn close"
                title="Close Quote"
              >
                ✓
              </button>
              <button
                @click="deleteQuote(quote)"
                class="action-btn delete"
                title="Delete"
              >
                🗑️
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalQuotes > 0" class="pagination">
      <button
        @click="previousPage"
        :disabled="currentPage === 1"
        class="pagination-btn"
      >
        ← Previous
      </button>

      <div class="page-numbers">
        <button
          v-for="page in visiblePages"
          :key="page"
          @click="goToPage(page)"
          :class="['page-number', { active: currentPage === page }]"
        >
          {{ page }}
        </button>
      </div>

      <button
        @click="nextPage"
        :disabled="currentPage >= totalPages"
        class="pagination-btn"
      >
        Next →
      </button>
    </div>

    <!-- Quote Details Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Quote Details</h2>
          <button @click="closeModal" class="close-btn">✕</button>
        </div>

        <div v-if="selectedQuote" class="modal-body">
          <!-- Tourist Info -->
          <div class="info-section">
            <h3>Tourist Information</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Name:</span>
                <span class="value">{{ selectedQuote.tourist_name }}</span>
              </div>
              <div class="info-item">
                <span class="label">Email:</span>
                <span class="value email">{{ selectedQuote.tourist_email }}</span>
              </div>
              <div class="info-item">
                <span class="label">Phone:</span>
                <span class="value">{{ selectedQuote.tourist_phone || 'N/A' }}</span>
              </div>
              <div class="info-item">
                <span class="label">Status:</span>
                <span :class="['value', selectedQuote.is_closed ? 'closed' : 'open']">
                  {{ selectedQuote.is_closed ? 'Closed' : 'Open' }}
                </span>
              </div>
            </div>
          </div>

          <!-- Trip Details -->
          <div class="info-section">
            <h3>Trip Details</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">From Location:</span>
                <span class="value">{{ selectedQuote.from_location }}</span>
              </div>
              <div class="info-item">
                <span class="label">To Location:</span>
                <span class="value">{{ selectedQuote.to_location }}</span>
              </div>
              <div class="info-item">
                <span class="label">Duration:</span>
                <span class="value">{{ selectedQuote.duration }} days</span>
              </div>
              <div class="info-item">
                <span class="label">Budget:</span>
                <span class="value">₹{{ formatBudget(selectedQuote.min_budget) }} - ₹{{ formatBudget(selectedQuote.max_budget) }}</span>
              </div>
              <div class="info-item">
                <span class="label">Travelers:</span>
                <span class="value">{{ selectedQuote.number_of_travelers || 'N/A' }}</span>
              </div>
              <div class="info-item">
                <span class="label">Posted:</span>
                <span class="value">{{ formatDate(selectedQuote.created_at) }}</span>
              </div>
            </div>
          </div>

          <!-- Description -->
          <div v-if="selectedQuote.description" class="info-section">
            <h3>Description</h3>
            <p class="description">{{ selectedQuote.description }}</p>
          </div>

          <!-- Preferences -->
          <div v-if="selectedQuote.preferences && selectedQuote.preferences.length" class="info-section">
            <h3>Preferences</h3>
            <div class="preferences">
              <span v-for="pref in selectedQuote.preferences" :key="pref" class="pref-tag">
                {{ pref }}
              </span>
            </div>
          </div>

          <!-- Activity Info -->
          <div class="info-section">
            <h3>Activity</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Total Responses:</span>
                <span class="value">{{ selectedQuote.total_responses || 0 }}</span>
              </div>
              <div class="info-item">
                <span class="label">Last Response:</span>
                <span class="value">{{ selectedQuote.last_response_at ? formatDate(selectedQuote.last_response_at) : 'No responses yet' }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>

    <!-- Responses Modal -->
    <div v-if="showResponsesModal" class="modal-overlay" @click.self="closeResponsesModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Responses ({{ responsesData.length }})</h2>
          <button @click="closeResponsesModal" class="close-btn">✕</button>
        </div>

        <div class="modal-body">
          <div v-if="responsesData.length === 0" class="empty-responses">
            <p>No responses yet</p>
          </div>

          <div v-else class="responses-list">
            <div v-for="response in responsesData" :key="response._id" class="response-item">
              <div class="response-header">
                <div>
                  <h4>{{ response.operator_name }}</h4>
                  <p class="operator-business">{{ response.operator_business_name || 'N/A' }}</p>
                </div>
                <span class="response-rating">⭐ {{ response.operator_rating || '0.0' }}</span>
              </div>
              <div class="response-details">
                <p><strong>Quote Amount:</strong> ₹{{ formatBudget(response.quote_price) }}</p>
                <p><strong>Respond Date:</strong> {{ formatDate(response.created_at) }}</p>
                <p><strong>Message:</strong></p>
                <p class="message">{{ response.message || 'No message provided' }}</p>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeResponsesModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>

    <!-- Confirmation Dialog -->
    <div v-if="showConfirmDialog" class="confirm-overlay" @click.self="cancelAction">
      <div class="confirm-dialog">
        <p>{{ confirmMessage }}</p>
        <div class="confirm-actions">
          <button @click="cancelAction" class="btn btn-secondary">Cancel</button>
          <button @click="confirmAction" :class="['btn', confirmDanger ? 'btn-danger' : 'btn-primary']">
            {{ confirmButtonText }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'

const loading = ref(true)
const quotes = ref([])
const searchQuery = ref('')
const statusFilter = ref('')
const responseFilter = ref('')
const currentPage = ref(1)
const pageSize = 10
const selectedQuote = ref(null)
const showModal = ref(false)
const showResponsesModal = ref(false)
const responsesData = ref([])
const showConfirmDialog = ref(false)
const confirmMessage = ref('')
const confirmButtonText = ref('')
const confirmDanger = ref(false)
let confirmCallback = null

const totalQuotes = computed(() => quotes.value.length)
const totalPages = computed(() => Math.ceil(filteredQuotes.value.length / pageSize))

const filteredQuotes = computed(() => {
  let filtered = quotes.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(q =>
      q.tourist_name.toLowerCase().includes(query) ||
      (q.from_location || '').toLowerCase().includes(query) ||
      (q.to_location || '').toLowerCase().includes(query) ||
      q.tourist_email.toLowerCase().includes(query)
    )
  }

  if (statusFilter.value) {
    filtered = filtered.filter(q =>
      statusFilter.value === 'open' ? !q.is_closed : q.is_closed
    )
  }

  if (responseFilter.value === '0') {
    filtered = filtered.filter(q => (q.total_responses || 0) === 0)
  } else if (responseFilter.value === '1plus') {
    filtered = filtered.filter(q => (q.total_responses || 0) >= 1)
  } else if (responseFilter.value === '5plus') {
    filtered = filtered.filter(q => (q.total_responses || 0) >= 5)
  }

  return filtered
})

const paginatedQuotes = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return filteredQuotes.value.slice(start, end)
})

const visiblePages = computed(() => {
  const pages = []
  const maxPages = 5
  let startPage = Math.max(1, currentPage.value - Math.floor(maxPages / 2))
  let endPage = Math.min(totalPages.value, startPage + maxPages - 1)

  if (endPage - startPage + 1 < maxPages) {
    startPage = Math.max(1, endPage - maxPages + 1)
  }

  for (let i = startPage; i <= endPage; i++) {
    pages.push(i)
  }
  return pages
})

const formatBudget = (value) => {
  return new Intl.NumberFormat('en-IN').format(value || 0)
}

const formatDate = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString('en-IN')
}

const fetchQuotes = async () => {
  try {
    loading.value = true
    const token = localStorage.getItem('adminToken')
    const response = await api.get('/admin/quotes?skip=0&limit=1000', {
      headers: { Authorization: `Bearer ${token}` }
    })
    quotes.value = response.data.quotes || []
  } catch (error) {
    console.error('Error fetching quotes:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
}

const viewQuote = (quote) => {
  selectedQuote.value = quote
  showModal.value = true
}

const viewResponses = async (quote) => {
  try {
    const token = localStorage.getItem('adminToken')
    const response = await api.get(`/admin/quotes/${quote._id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    responsesData.value = response.data.quote?.responses || []
    showResponsesModal.value = true
  } catch (error) {
    console.error('Error fetching responses:', error)
  }
}

const closeQuote = (quote) => {
  confirmMessage.value = `Are you sure you want to close this quote from ${quote.tourist_name}?`
  confirmButtonText.value = 'Close Quote'
  confirmDanger.value = false
  confirmCallback = async () => {
    try {
      const token = localStorage.getItem('adminToken')
      // This would need a backend endpoint to close quotes
      // await api.post(`/admin/quotes/${quote._id}/close`, {}, {
      //   headers: { Authorization: `Bearer ${token}` }
      // })
      quote.is_closed = true
      showConfirmDialog.value = false
    } catch (error) {
      console.error('Error closing quote:', error)
    }
  }
  showConfirmDialog.value = true
}

const deleteQuote = (quote) => {
  confirmMessage.value = `Are you sure you want to delete this quote? This action cannot be undone.`
  confirmButtonText.value = 'Delete Quote'
  confirmDanger.value = true
  confirmCallback = async () => {
    try {
      const token = localStorage.getItem('adminToken')
      await api.delete(`/admin/quotes/${quote._id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
      const index = quotes.value.findIndex(q => q._id === quote._id)
      if (index > -1) {
        quotes.value.splice(index, 1)
      }
      showConfirmDialog.value = false
    } catch (error) {
      console.error('Error deleting quote:', error)
    }
  }
  showConfirmDialog.value = true
}

const confirmAction = () => {
  if (confirmCallback) {
    confirmCallback()
  }
}

const cancelAction = () => {
  showConfirmDialog.value = false
  confirmCallback = null
}

const closeModal = () => {
  showModal.value = false
  selectedQuote.value = null
}

const closeResponsesModal = () => {
  showResponsesModal.value = false
  responsesData.value = []
}

const previousPage = () => {
  if (currentPage.value > 1) currentPage.value--
}

const nextPage = () => {
  if (currentPage.value < totalPages.value) currentPage.value++
}

const goToPage = (page) => {
  currentPage.value = page
}

onMounted(() => {
  fetchQuotes()
})
</script>

<style scoped>
.admin-quotes {
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

/* Toolbar */
.toolbar {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  align-items: center;
}

.search-box {
  flex: 1;
  min-width: 250px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 2.5rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  transition: all 0.2s;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  font-size: 1rem;
  color: #a0aec0;
}

.filter-controls {
  display: flex;
  gap: 0.75rem;
}

.filter-select {
  padding: 0.75rem 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  background: white;
  cursor: pointer;
  transition: all 0.2s;
}

.filter-select:focus {
  outline: none;
  border-color: #667eea;
}

.pagination-info {
  font-size: 0.9rem;
  color: #718096;
  white-space: nowrap;
}

/* Loading & Empty States */
.loading-state,
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
}

.spinner {
  width: 3rem;
  height: 3rem;
  border: 4px solid #e2e8f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.empty-state p {
  font-size: 1.2rem;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
}

.hint {
  color: #a0aec0;
  font-size: 0.9rem;
}

/* Table */
.table-container {
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
  margin-bottom: 2rem;
}

.quotes-table {
  width: 100%;
  border-collapse: collapse;
}

.quotes-table thead {
  background: #f7fafc;
  border-bottom: 2px solid #e2e8f0;
}

.quotes-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #2d3748;
  font-size: 0.9rem;
}

.quotes-table tbody tr {
  border-bottom: 1px solid #e2e8f0;
  transition: background 0.2s;
}

.quotes-table tbody tr:hover {
  background: #f7fafc;
}

.quotes-table td {
  padding: 1rem;
  font-size: 0.9rem;
  color: #2d3748;
}

.quote-id-cell {
  font-family: monospace;
  font-weight: 600;
  color: #667eea;
}

.tourist-cell {
  font-weight: 500;
}

.destination-cell {
  font-size: 0.85rem;
}

.locations {
  display: flex;
  align-items: center;
  gap: 0.25rem;
  flex-wrap: wrap;
}

.location {
  color: #666;
}

.separator {
  color: #cbd5e0;
  margin: 0 0.25rem;
}

.duration-cell {
  text-align: center;
  color: #667eea;
  font-weight: 500;
}

.budget-cell {
  font-weight: 600;
  color: #f59e0b;
}

.responses-cell {
  text-align: center;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
}

.badge.responses {
  background: #dbeafe;
  color: #0284c7;
}

.posted-cell {
  color: #a0aec0;
  font-size: 0.9rem;
}

.status-cell {
  text-align: center;
}

.status-badge {
  display: inline-block;
  padding: 0.5rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.status-badge.open {
  background: #dbeafe;
  color: #0284c7;
}

.status-badge.closed {
  background: #dcfce7;
  color: #166534;
}

.actions-cell {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 6px;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.2s;
  display: flex;
  align-items: center;
  justify-content: center;
}

.action-btn.view {
  background: #dbeafe;
  color: #0284c7;
}

.action-btn.view:hover {
  background: #bfdbfe;
}

.action-btn.responses {
  background: #fce7f3;
  color: #be185d;
}

.action-btn.responses:hover {
  background: #fbcfe8;
}

.action-btn.close {
  background: #dcfce7;
  color: #166534;
}

.action-btn.close:hover {
  background: #bbf7d0;
}

.action-btn.delete {
  background: #fee2e2;
  color: #991b1b;
}

.action-btn.delete:hover {
  background: #fecaca;
}

/* Pagination */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  margin-top: 2rem;
}

.pagination-btn {
  padding: 0.75rem 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  background: white;
  color: #2d3748;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  border-color: #667eea;
  color: #667eea;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-numbers {
  display: flex;
  gap: 0.5rem;
}

.page-number {
  width: 2.5rem;
  height: 2.5rem;
  border: 2px solid #e2e8f0;
  border-radius: 6px;
  background: white;
  cursor: pointer;
  font-weight: 600;
  color: #2d3748;
  transition: all 0.2s;
}

.page-number:hover {
  border-color: #667eea;
  color: #667eea;
}

.page-number.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: white;
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

.info-section {
  margin-bottom: 2rem;
}

.info-section h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e2e8f0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
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

.info-item .value.email {
  color: #667eea;
}

.info-item .value.open {
  color: #0284c7;
}

.info-item .value.closed {
  color: #166534;
}

.description {
  color: #4b5563;
  line-height: 1.6;
  margin: 0;
  padding: 1rem;
  background: #f7fafc;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.preferences {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.pref-tag {
  display: inline-block;
  padding: 0.5rem 0.75rem;
  background: #dbeafe;
  color: #0284c7;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
}

/* Responses */
.empty-responses {
  text-align: center;
  padding: 2rem;
  color: #718096;
}

.responses-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.response-item {
  padding: 1.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  background: #f7fafc;
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.response-header h4 {
  margin: 0;
  color: #1a202c;
  font-size: 1rem;
  font-weight: 600;
}

.operator-business {
  margin: 0.25rem 0 0 0;
  color: #718096;
  font-size: 0.9rem;
}

.response-rating {
  color: #f59e0b;
  font-weight: 600;
  font-size: 0.95rem;
}

.response-details {
  font-size: 0.9rem;
  line-height: 1.6;
}

.response-details p {
  margin: 0.5rem 0;
  color: #4b5563;
}

.response-details strong {
  color: #2d3748;
}

.message {
  padding: 0.75rem;
  background: white;
  border-radius: 6px;
  border-left: 3px solid #667eea;
  margin: 0.5rem 0;
}

.modal-footer {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  background: #f7fafc;
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

.btn-secondary {
  background: #e2e8f0;
  color: #2d3748;
}

.btn-secondary:hover {
  background: #cbd5e0;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5a67d8;
}

.btn-danger {
  background: #f87171;
  color: white;
}

.btn-danger:hover {
  background: #ef4444;
}

/* Confirm Dialog */
.confirm-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1001;
}

.confirm-dialog {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  max-width: 400px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
}

.confirm-dialog p {
  margin: 0 0 1.5rem 0;
  color: #2d3748;
  font-size: 1rem;
  line-height: 1.5;
}

.confirm-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

/* Responsive */
@media (max-width: 768px) {
  .toolbar {
    flex-direction: column;
  }

  .search-box {
    width: 100%;
    min-width: unset;
  }

  .filter-controls {
    width: 100%;
    flex-wrap: wrap;
  }

  .filter-select {
    flex: 1;
    min-width: 150px;
  }

  .pagination-info {
    display: none;
  }

  .quotes-table {
    font-size: 0.85rem;
  }

  .quotes-table th,
  .quotes-table td {
    padding: 0.75rem;
  }

  .destination-cell {
    font-size: 0.8rem;
  }

  .actions-cell {
    flex-wrap: wrap;
  }

  .action-btn {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.9rem;
  }

  .pagination {
    flex-direction: column;
    width: 100%;
  }

  .page-numbers {
    flex-wrap: wrap;
    justify-content: center;
  }
}
</style>
