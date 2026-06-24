<template>
  <div class="admin-tourists">
    <div class="page-header">
      <h1>Manage Tourists</h1>
      <p class="subtitle">View and manage all tourist users on the platform</p>
    </div>

    <!-- Search and Filter Bar -->
    <div class="toolbar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by name, email, or phone..."
          @input="handleSearch"
          class="search-input"
        />
        <span class="search-icon">🔍</span>
      </div>

      <div class="filter-controls">
          <select v-model="statusFilter" @change="handleFilterChange" class="filter-select">
          <option value="">All Status</option>
          <option value="active">Active</option>
          <option value="inactive">Inactive</option>
        </select>
      </div>

      <div class="pagination-info">
          Showing {{ pageStart }} to {{ pageEnd }} of {{ totalTourists }}
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading tourists...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="tourists.length === 0" class="empty-state">
      <p>📭 No tourists found</p>
      <span v-if="searchQuery" class="hint">Try adjusting your search criteria</span>
    </div>

    <!-- Tourists Table -->
    <div v-else class="table-container">
      <table class="tourists-table">
        <thead>
          <tr>
            <th>Name</th>
            <th>Email</th>
            <th>Phone</th>
            <th>Joined</th>
            <th>Quotes Posted</th>
            <th>Status</th>
            <th>Last Login</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="tourist in tourists" :key="tourist._id" class="tourist-row">
            <td class="name-cell">{{ tourist.full_name }}</td>
            <td class="email-cell">{{ tourist.email }}</td>
            <td class="phone-cell">{{ tourist.phone || 'N/A' }}</td>
            <td class="date-cell">{{ formatDate(tourist.created_at) }}</td>
            <td class="quotes-cell">
              <span class="badge quotes">{{ tourist.quotes_posted || 0 }}</span>
            </td>
            <td class="status-cell">
              <span :class="['status-badge', tourist.is_active ? 'active' : 'inactive']">
                {{ tourist.is_active ? '🟢 Active' : '🔴 Inactive' }}
              </span>
            </td>
            <td class="login-cell">{{ formatDate(tourist.last_login) || 'Never' }}</td>
            <td class="actions-cell">
              <button
                @click="viewTourist(tourist)"
                class="action-btn view"
                title="View Details"
              >
                👁️
              </button>
              <button
                v-if="tourist.is_active"
                @click="suspendTourist(tourist)"
                class="action-btn suspend"
                title="Suspend"
              >
                ⏸️
              </button>
              <button
                v-else
                @click="activateTourist(tourist)"
                class="action-btn activate"
                title="Activate"
              >
                ▶️
              </button>
              <button
                @click="deleteTourist(tourist)"
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
    <div v-if="totalTourists > 0" class="pagination">
      <button
        @click="previousPage"
        :disabled="currentPage === 1 || loading"
        class="pagination-btn"
      >
        ← Previous
      </button>

      <div class="page-numbers">
        <span :class="['page-number', 'active']">{{ currentPage }}</span>
      </div>

      <button
        @click="nextPage"
        :disabled="!pagination.hasMore || loading"
        class="pagination-btn"
      >
        Next →
      </button>
    </div>

    <!-- Tourist Details Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Tourist Details</h2>
          <button @click="closeModal" class="close-btn">✕</button>
        </div>

        <div v-if="selectedTourist" class="modal-body">
          <!-- Personal Info -->
          <div class="info-section">
            <h3>Personal Information</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Name:</span>
                <span class="value">{{ selectedTourist.full_name }}</span>
              </div>
              <div class="info-item">
                <span class="label">Email:</span>
                <span class="value">{{ selectedTourist.email }}</span>
              </div>
              <div class="info-item">
                <span class="label">Phone:</span>
                <span class="value">{{ selectedTourist.phone || 'N/A' }}</span>
              </div>
              <div class="info-item">
                <span class="label">User Type:</span>
                <span class="value">{{ selectedTourist.user_type }}</span>
              </div>
              <div class="info-item">
                <span class="label">Status:</span>
                <span :class="['value', selectedTourist.is_active ? 'active' : 'inactive']">
                  {{ selectedTourist.is_active ? 'Active' : 'Inactive' }}
                </span>
              </div>
              <div class="info-item">
                <span class="label">Joined:</span>
                <span class="value">{{ formatDate(selectedTourist.created_at) }}</span>
              </div>
            </div>
          </div>

          <!-- Quote Activity -->
          <div class="info-section">
            <h3>Quote Activity</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Total Quotes Posted:</span>
                <span class="value">{{ selectedTourist.quotes_posted || 0 }}</span>
              </div>
              <div class="info-item">
                <span class="label">Last Login:</span>
                <span class="value">{{ formatDate(selectedTourist.last_login) || 'Never' }}</span>
              </div>
            </div>
          </div>

          <!-- Recent Quotes -->
          <div v-if="selectedTourist.quotes && selectedTourist.quotes.length > 0" class="info-section">
            <h3>Recent Quotes</h3>
            <div class="quotes-list">
              <div v-for="quote in selectedTourist.quotes.slice(0, 3)" :key="quote._id" class="quote-item">
                <div class="quote-header">
                  <span class="quote-id">ID: {{ quote._id.substring(0, 8) }}</span>
                  <span :class="['quote-status', quote.status]">{{ quote.status }}</span>
                </div>
                <div class="quote-locations">
                  <span v-for="(loc, idx) in quote.locations.slice(0, 2)" :key="idx" class="location">
                    📍 {{ loc.name }}, {{ loc.state }}
                  </span>
                  <span v-if="quote.locations.length > 2" class="more-locations">
                    +{{ quote.locations.length - 2 }} more
                  </span>
                </div>
                <div class="quote-meta">
                  <span>{{ quote.responses?.length || 0 }} responses</span>
                  <span>{{ formatDate(quote.created_at) }}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button @click="closeModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>

    <!-- Confirmation Dialog -->
    <div v-if="showConfirmDialog" class="confirm-overlay" @click.self="cancelAction">
      <div class="confirm-dialog">
        <p>{{ confirmMessage }}</p>
        <div class="confirm-actions">
          <button @click="cancelAction" class="btn btn-secondary">Cancel</button>
          <button @click="confirmAction" class="btn btn-danger">{{ confirmButtonText }}</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'

const loading = ref(true)
const tourists = ref([])
const searchQuery = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = 10
const totalTourists = ref(0)
const pagination = ref({ totalPages: 1, hasMore: false })
const pageCursors = ref([null])
const selectedTourist = ref(null)
const showModal = ref(false)
const showConfirmDialog = ref(false)
const confirmMessage = ref('')
const confirmButtonText = ref('')
let confirmCallback = null

const totalPages = computed(() => Math.max(1, Math.ceil(totalTourists.value / pageSize)))
const pageStart = computed(() => (totalTourists.value === 0 ? 0 : (currentPage.value - 1) * pageSize + 1))
const pageEnd = computed(() => (totalTourists.value === 0 ? 0 : Math.min(currentPage.value * pageSize, totalTourists.value)))

const formatDate = (date) => {
  if (!date) return ''
  try {
    return new Date(date).toLocaleDateString('en-US', {
      year: 'numeric',
      month: 'short',
      day: 'numeric'
    })
  } catch {
    return ''
  }
}

const fetchTourists = async () => {
  try {
    loading.value = true
    const token = localStorage.getItem('adminToken')
    const currentCursor = pageCursors.value[currentPage.value - 1]
    const response = await api.get('/admin/tourists', {
      params: {
        limit: pageSize,
        cursor: currentCursor || undefined,
        search: searchQuery.value.trim(),
        status_filter: statusFilter.value || undefined
      },
      headers: { Authorization: `Bearer ${token}` }
    })
    tourists.value = response.data.tourists || []
    totalTourists.value = response.data.pagination?.total_items || 0
    pagination.value = {
      totalPages: response.data.pagination?.total_pages || 1,
      hasMore: Boolean(response.data.pagination?.has_more)
    }
    if (pageCursors.value.length === currentPage.value) {
      pageCursors.value.push(response.data.pagination?.next_cursor || null)
    } else {
      pageCursors.value[currentPage.value] = response.data.pagination?.next_cursor || null
    }
    pageCursors.value = pageCursors.value.slice(0, currentPage.value + 1)
  } catch (error) {
    console.error('Error fetching tourists:', error)
  } finally {
    loading.value = false
  }
}

const resetPagination = () => {
  currentPage.value = 1
  pageCursors.value = [null]
}

const handleSearch = () => {
  resetPagination()
  fetchTourists()
}

const handleFilterChange = () => {
  resetPagination()
  fetchTourists()
}

const viewTourist = async (tourist) => {
  try {
    const token = localStorage.getItem('adminToken')
    const response = await api.get(`/admin/users/${tourist._id}`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    selectedTourist.value = response.data
    showModal.value = true
  } catch (error) {
    console.error('Error fetching tourist details:', error)
  }
}

const suspendTourist = (tourist) => {
  confirmMessage.value = `Are you sure you want to suspend ${tourist.full_name}?`
  confirmButtonText.value = 'Suspend'
  confirmCallback = async () => {
    try {
      const token = localStorage.getItem('adminToken')
      await api.post(`/admin/users/${tourist._id}/suspend`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
        await fetchTourists()
      showConfirmDialog.value = false
    } catch (error) {
      console.error('Error suspending tourist:', error)
    }
  }
  showConfirmDialog.value = true
}

const activateTourist = (tourist) => {
  confirmMessage.value = `Are you sure you want to activate ${tourist.full_name}?`
  confirmButtonText.value = 'Activate'
  confirmCallback = async () => {
    try {
      const token = localStorage.getItem('adminToken')
      await api.post(`/admin/users/${tourist._id}/activate`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
        await fetchTourists()
      showConfirmDialog.value = false
    } catch (error) {
      console.error('Error activating tourist:', error)
    }
  }
  showConfirmDialog.value = true
}

const deleteTourist = (tourist) => {
  confirmMessage.value = `Are you sure you want to permanently delete ${tourist.full_name}? This action cannot be undone.`
  confirmButtonText.value = 'Delete'
  confirmCallback = async () => {
    try {
      const token = localStorage.getItem('adminToken')
      await api.delete(`/admin/users/${tourist._id}`, {
        headers: { Authorization: `Bearer ${token}` }
      })
        if (tourists.value.length === 1 && currentPage.value > 1) {
          currentPage.value -= 1
          pageCursors.value = pageCursors.value.slice(0, currentPage.value + 1)
        }
        await fetchTourists()
      showConfirmDialog.value = false
    } catch (error) {
      console.error('Error deleting tourist:', error)
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
  selectedTourist.value = null
}

const previousPage = () => {
  if (currentPage.value > 1) {
    currentPage.value--
    fetchTourists()
  }
}

const nextPage = () => {
  if (pagination.value.hasMore) {
    currentPage.value++
    fetchTourists()
  }
}

onMounted(() => {
  fetchTourists()
})
</script>

<style scoped>
.admin-tourists {
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

.tourists-table {
  width: 100%;
  border-collapse: collapse;
}

.tourists-table thead {
  background: #f7fafc;
  border-bottom: 2px solid #e2e8f0;
}

.tourists-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #2d3748;
  font-size: 0.9rem;
}

.tourists-table tbody tr {
  border-bottom: 1px solid #e2e8f0;
  transition: background 0.2s;
}

.tourists-table tbody tr:hover {
  background: #f7fafc;
}

.tourists-table td {
  padding: 1rem;
  font-size: 0.9rem;
  color: #2d3748;
}

.name-cell {
  font-weight: 600;
}

.email-cell {
  color: #667eea;
}

.phone-cell {
  color: #718096;
}

.date-cell {
  color: #a0aec0;
}

.quotes-cell {
  text-align: center;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
}

.badge.quotes {
  background: #dbeafe;
  color: #0284c7;
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

.status-badge.active {
  background: #dcfce7;
  color: #166534;
}

.status-badge.inactive {
  background: #fee2e2;
  color: #991b1b;
}

.login-cell {
  color: #a0aec0;
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

.action-btn.suspend,
.action-btn.activate {
  background: #fef3c7;
  color: #b45309;
}

.action-btn.suspend:hover,
.action-btn.activate:hover {
  background: #fde68a;
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

.info-item .value.active {
  color: #166534;
  font-weight: 600;
}

.info-item .value.inactive {
  color: #991b1b;
  font-weight: 600;
}

.quotes-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.quote-item {
  background: #f7fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1rem;
}

.quote-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.quote-id {
  font-size: 0.85rem;
  color: #718096;
  font-family: monospace;
}

.quote-status {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 600;
}

.quote-status.open {
  background: #dbeafe;
  color: #0284c7;
}

.quote-status.closed {
  background: #ddd6fe;
  color: #6d28d9;
}

.quote-locations {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.location {
  font-size: 0.9rem;
  color: #2d3748;
}

.more-locations {
  font-size: 0.9rem;
  color: #667eea;
  font-weight: 600;
}

.quote-meta {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #a0aec0;
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
  }

  .filter-select {
    flex: 1;
  }

  .pagination-info {
    display: none;
  }

  .tourists-table {
    font-size: 0.85rem;
  }

  .tourists-table th,
  .tourists-table td {
    padding: 0.75rem;
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
