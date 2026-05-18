<template>
  <div class="admin-operators">
    <div class="page-header">
      <h1>Manage Operators</h1>
      <p class="subtitle">View and manage all tour operators on the platform</p>
    </div>

    <!-- Search and Filter Bar -->
    <div class="toolbar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by business name or owner name..."
          @input="handleSearch"
          class="search-input"
        />
        <span class="search-icon">🔍</span>
      </div>

      <div class="filter-controls">
        <select v-model="ratingFilter" class="filter-select">
          <option value="">All Ratings</option>
          <option value="4">⭐ 4.0+</option>
          <option value="3">⭐ 3.0+</option>
          <option value="below3">⭐ Below 3.0</option>
        </select>
      </div>

      <div class="pagination-info">
        Showing {{ currentPage * pageSize - pageSize + 1 }} to {{ Math.min(currentPage * pageSize, totalOperators) }} of {{ totalOperators }}
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading operators...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredOperators.length === 0" class="empty-state">
      <p>📭 No operators found</p>
      <span v-if="searchQuery" class="hint">Try adjusting your search criteria</span>
    </div>

    <!-- Operators Table -->
    <div v-else class="table-container">
      <table class="operators-table">
        <thead>
          <tr>
            <th>Business Name</th>
            <th>Owner</th>
            <th>Serving Areas</th>
            <th>Rating</th>
            <th>Responses</th>
            <th>Experience</th>
            <th>Status</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="operator in paginatedOperators" :key="operator._id" class="operator-row">
            <td class="business-cell">{{ operator.profile?.business_name || 'N/A' }}</td>
            <td class="owner-cell">{{ operator.full_name }}</td>
            <td class="areas-cell">
              <span class="badge areas">{{ operator.serving_areas_count || 0 }}</span>
            </td>
            <td class="rating-cell">
              <span class="rating">
                ⭐ {{ operator.avg_rating?.toFixed(1) || '0.0' }}
              </span>
            </td>
            <td class="responses-cell">{{ operator.quotes_responded || 0 }}</td>
            <td class="experience-cell">{{ operator.profile?.years_of_experience || 0 }} yrs</td>
            <td class="status-cell">
              <span :class="['status-badge', operator.is_active ? 'active' : 'inactive']">
                {{ operator.is_active ? '🟢 Active' : '🔴 Inactive' }}
              </span>
            </td>
            <td class="actions-cell">
              <button
                @click="viewOperator(operator)"
                class="action-btn view"
                title="View Profile"
              >
                👁️
              </button>
              <button
                @click="viewPerformance(operator)"
                class="action-btn performance"
                title="View Performance"
              >
                📈
              </button>
              <button
                v-if="operator.is_active"
                @click="suspendOperator(operator)"
                class="action-btn suspend"
                title="Suspend"
              >
                ⏸️
              </button>
              <button
                v-else
                @click="activateOperator(operator)"
                class="action-btn activate"
                title="Activate"
              >
                ▶️
              </button>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <!-- Pagination -->
    <div v-if="totalOperators > 0" class="pagination">
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

    <!-- Operator Details Modal -->
    <div v-if="showModal" class="modal-overlay" @click.self="closeModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Operator Profile</h2>
          <button @click="closeModal" class="close-btn">✕</button>
        </div>

        <div v-if="selectedOperator" class="modal-body">
          <!-- Business Info -->
          <div class="info-section">
            <h3>Business Information</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Business Name:</span>
                <span class="value">{{ selectedOperator.profile?.business_name || 'N/A' }}</span>
              </div>
              <div class="info-item">
                <span class="label">Owner Name:</span>
                <span class="value">{{ selectedOperator.full_name }}</span>
              </div>
              <div class="info-item">
                <span class="label">Email:</span>
                <span class="value email">{{ selectedOperator.email }}</span>
              </div>
              <div class="info-item">
                <span class="label">Phone:</span>
                <span class="value">{{ selectedOperator.phone || 'N/A' }}</span>
              </div>
              <div class="info-item">
                <span class="label">Experience:</span>
                <span class="value">{{ selectedOperator.profile?.years_of_experience || 0 }} years</span>
              </div>
              <div class="info-item">
                <span class="label">Status:</span>
                <span :class="['value', selectedOperator.is_active ? 'active' : 'inactive']">
                  {{ selectedOperator.is_active ? 'Active' : 'Inactive' }}
                </span>
              </div>
            </div>
          </div>

          <!-- Rating Info -->
          <div class="info-section">
            <h3>Ratings & Reviews</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Average Rating:</span>
                <span class="value">⭐ {{ selectedOperator.profile?.average_rating?.toFixed(1) || '0.0' }} / 5.0</span>
              </div>
              <div class="info-item">
                <span class="label">Total Reviews:</span>
                <span class="value">{{ selectedOperator.profile?.total_reviews || 0 }}</span>
              </div>
              <div class="info-item">
                <span class="label">Total Responses:</span>
                <span class="value">{{ selectedOperator.quotes_responded || 0 }}</span>
              </div>
              <div class="info-item">
                <span class="label">Serving Areas:</span>
                <span class="value">{{ selectedOperator.serving_areas_count || 0 }}</span>
              </div>
            </div>
          </div>

          <!-- Description -->
          <div v-if="selectedOperator.profile?.description" class="info-section">
            <h3>Description</h3>
            <p class="description">{{ selectedOperator.profile.description }}</p>
          </div>

          <!-- Specializations -->
          <div v-if="selectedOperator.profile?.specializations?.length" class="info-section">
            <h3>Specializations</h3>
            <div class="specializations">
              <span v-for="spec in selectedOperator.profile.specializations" :key="spec" class="spec-tag">
                {{ spec }}
              </span>
            </div>
          </div>
        </div>

        <!-- Modal Footer -->
        <div class="modal-footer">
          <button @click="closeModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>

    <!-- Performance Modal -->
    <div v-if="showPerformanceModal" class="modal-overlay" @click.self="closePerformanceModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Performance Analytics</h2>
          <button @click="closePerformanceModal" class="close-btn">✕</button>
        </div>

        <div v-if="performanceData" class="modal-body">
          <div class="info-section">
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Total Responses:</span>
                <span class="value">{{ performanceData.total_responses }}</span>
              </div>
              <div class="info-item">
                <span class="label">Avg Response Time:</span>
                <span class="value">{{ performanceData.average_response_time_hours }}h</span>
              </div>
              <div class="info-item">
                <span class="label">Average Rating:</span>
                <span class="value">{{ performanceData.average_rating }}</span>
              </div>
              <div class="info-item">
                <span class="label">Serving Areas:</span>
                <span class="value">{{ performanceData.serving_areas_count }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closePerformanceModal" class="btn btn-secondary">Close</button>
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
const operators = ref([])
const searchQuery = ref('')
const ratingFilter = ref('')
const currentPage = ref(1)
const pageSize = 10
const selectedOperator = ref(null)
const showModal = ref(false)
const showPerformanceModal = ref(false)
const performanceData = ref(null)
const showConfirmDialog = ref(false)
const confirmMessage = ref('')
const confirmButtonText = ref('')
let confirmCallback = null

const totalOperators = computed(() => operators.value.length)
const totalPages = computed(() => Math.ceil(filteredOperators.value.length / pageSize))

const filteredOperators = computed(() => {
  let filtered = operators.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(o =>
      (o.profile?.business_name || '').toLowerCase().includes(query) ||
      o.full_name.toLowerCase().includes(query) ||
      o.email.toLowerCase().includes(query)
    )
  }

  if (ratingFilter.value === '4') {
    filtered = filtered.filter(o => (o.avg_rating || 0) >= 4)
  } else if (ratingFilter.value === '3') {
    filtered = filtered.filter(o => (o.avg_rating || 0) >= 3 && (o.avg_rating || 0) < 4)
  } else if (ratingFilter.value === 'below3') {
    filtered = filtered.filter(o => (o.avg_rating || 0) < 3)
  }

  return filtered
})

const paginatedOperators = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return filteredOperators.value.slice(start, end)
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

const fetchOperators = async () => {
  try {
    loading.value = true
    const token = localStorage.getItem('adminToken')
    const response = await api.get('/admin/operators?skip=0&limit=1000', {
      headers: { Authorization: `Bearer ${token}` }
    })
    operators.value = response.data.operators || []
  } catch (error) {
    console.error('Error fetching operators:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
}

const viewOperator = (operator) => {
  selectedOperator.value = operator
  showModal.value = true
}

const viewPerformance = async (operator) => {
  try {
    const token = localStorage.getItem('adminToken')
    const response = await api.get(`/admin/operators/${operator.profile?._id}/performance`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    performanceData.value = response.data.performance
    showPerformanceModal.value = true
  } catch (error) {
    console.error('Error fetching performance:', error)
  }
}

const suspendOperator = (operator) => {
  confirmMessage.value = `Are you sure you want to suspend ${operator.profile?.business_name}?`
  confirmButtonText.value = 'Suspend'
  confirmCallback = async () => {
    try {
      const token = localStorage.getItem('adminToken')
      await api.post(`/admin/users/${operator._id}/suspend`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      operator.is_active = false
      showConfirmDialog.value = false
    } catch (error) {
      console.error('Error suspending operator:', error)
    }
  }
  showConfirmDialog.value = true
}

const activateOperator = (operator) => {
  confirmMessage.value = `Are you sure you want to activate ${operator.profile?.business_name}?`
  confirmButtonText.value = 'Activate'
  confirmCallback = async () => {
    try {
      const token = localStorage.getItem('adminToken')
      await api.post(`/admin/users/${operator._id}/activate`, {}, {
        headers: { Authorization: `Bearer ${token}` }
      })
      operator.is_active = true
      showConfirmDialog.value = false
    } catch (error) {
      console.error('Error activating operator:', error)
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
  selectedOperator.value = null
}

const closePerformanceModal = () => {
  showPerformanceModal.value = false
  performanceData.value = null
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
  fetchOperators()
})
</script>

<style scoped>
.admin-operators {
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

.operators-table {
  width: 100%;
  border-collapse: collapse;
}

.operators-table thead {
  background: #f7fafc;
  border-bottom: 2px solid #e2e8f0;
}

.operators-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #2d3748;
  font-size: 0.9rem;
}

.operators-table tbody tr {
  border-bottom: 1px solid #e2e8f0;
  transition: background 0.2s;
}

.operators-table tbody tr:hover {
  background: #f7fafc;
}

.operators-table td {
  padding: 1rem;
  font-size: 0.9rem;
  color: #2d3748;
}

.business-cell {
  font-weight: 600;
}

.owner-cell {
  color: #667eea;
}

.areas-cell,
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

.badge.areas {
  background: #dbeafe;
  color: #0284c7;
}

.rating {
  font-weight: 600;
  color: #f59e0b;
}

.experience-cell {
  color: #a0aec0;
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

.action-btn.performance {
  background: #fef3c7;
  color: #b45309;
}

.action-btn.performance:hover {
  background: #fde68a;
}

.action-btn.suspend,
.action-btn.activate {
  background: #ddd6fe;
  color: #6d28d9;
}

.action-btn.suspend:hover,
.action-btn.activate:hover {
  background: #c4b5fd;
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

.info-item .value.active {
  color: #166534;
  font-weight: 600;
}

.info-item .value.inactive {
  color: #991b1b;
  font-weight: 600;
}

.description {
  color: #4b5563;
  line-height: 1.6;
  margin: 0;
}

.specializations {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.spec-tag {
  display: inline-block;
  padding: 0.5rem 0.75rem;
  background: #f0fdf4;
  color: #166534;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
  border: 1px solid #bbf7d0;
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

  .operators-table {
    font-size: 0.85rem;
  }

  .operators-table th,
  .operators-table td {
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
