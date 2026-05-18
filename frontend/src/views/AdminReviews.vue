<template>
  <div class="admin-reviews">
    <div class="page-header">
      <h1>Ratings & Reviews Management</h1>
      <p class="subtitle">Manage platform reviews, respond to feedback, and monitor ratings</p>
    </div>

    <!-- Search and Filter Bar -->
    <div class="toolbar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="Search by tourist name, operator name, or review content..."
          @input="handleSearch"
          class="search-input"
        />
        <span class="search-icon">🔍</span>
      </div>

      <div class="filter-controls">
        <select v-model="ratingFilter" class="filter-select">
          <option value="">All Ratings</option>
          <option value="5">⭐⭐⭐⭐⭐ 5 Stars</option>
          <option value="4">⭐⭐⭐⭐ 4 Stars</option>
          <option value="3">⭐⭐⭐ 3 Stars</option>
          <option value="2">⭐⭐ 2 Stars</option>
          <option value="1">⭐ 1 Star</option>
        </select>

        <select v-model="statusFilter" class="filter-select">
          <option value="">All Status</option>
          <option value="flagged">🚩 Flagged</option>
          <option value="responded">✓ Responded</option>
          <option value="pending">⏳ Pending Response</option>
        </select>
      </div>

      <div class="pagination-info">
        Showing {{ currentPage * pageSize - pageSize + 1 }} to {{ Math.min(currentPage * pageSize, totalReviews) }} of {{ totalReviews }}
      </div>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading reviews...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredReviews.length === 0" class="empty-state">
      <p>📭 No reviews found</p>
      <span v-if="searchQuery" class="hint">Try adjusting your search criteria</span>
    </div>

    <!-- Reviews List -->
    <div v-else class="reviews-container">
      <div v-for="review in paginatedReviews" :key="review._id" class="review-card">
        <!-- Review Header -->
        <div class="review-header">
          <div class="review-left">
            <div class="reviewer-info">
              <h3>{{ review.tourist_name }}</h3>
              <p class="operator-name">→ {{ review.operator_name }}</p>
            </div>
            <div class="rating-display">
              <span class="stars">{{ '⭐'.repeat(review.rating) }}</span>
              <span class="rating-value">{{ review.rating }}/5</span>
            </div>
          </div>

          <div class="review-meta">
            <span class="date">{{ formatDate(review.created_at) }}</span>
            <div class="status-flags">
              <span v-if="review.is_flagged" class="flag-badge">🚩 Flagged</span>
              <span v-if="review.is_responded" class="responded-badge">✓ Responded</span>
            </div>
          </div>
        </div>

        <!-- Review Content -->
        <div class="review-content">
          <p class="review-text">{{ review.review_text }}</p>
          
          <!-- Admin Response -->
          <div v-if="review.is_responded" class="admin-response">
            <div class="response-header">
              <span class="response-label">Admin Response:</span>
              <span class="response-date">{{ formatDate(review.responded_at) }}</span>
            </div>
            <p class="response-text">{{ review.admin_response }}</p>
          </div>
        </div>

        <!-- Review Actions -->
        <div class="review-actions">
          <button
            v-if="!review.is_responded"
            @click="openResponseForm(review)"
            class="action-btn respond"
            title="Respond to Review"
          >
            💬 Respond
          </button>
          <button
            v-else
            @click="viewResponse(review)"
            class="action-btn view-response"
            title="View Response"
          >
            👁️ View Response
          </button>
          <button
            v-if="!review.is_flagged"
            @click="flagReview(review)"
            class="action-btn flag"
            title="Flag Review"
          >
            🚩 Flag
          </button>
          <button
            v-else
            @click="unflagReview(review)"
            class="action-btn unflag"
            title="Unflag Review"
          >
            ✓ Unflag
          </button>
          <button
            @click="deleteReview(review)"
            class="action-btn delete"
            title="Delete Review"
          >
            🗑️ Delete
          </button>
        </div>
      </div>
    </div>

    <!-- Pagination -->
    <div v-if="totalReviews > 0" class="pagination">
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

    <!-- Response Modal -->
    <div v-if="showResponseModal" class="modal-overlay" @click.self="closeResponseModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Respond to Review</h2>
          <button @click="closeResponseModal" class="close-btn">✕</button>
        </div>

        <div v-if="selectedReview" class="modal-body">
          <div class="review-context">
            <h4>{{ selectedReview.tourist_name }} → {{ selectedReview.operator_name }}</h4>
            <p class="original-review">{{ selectedReview.review_text }}</p>
            <div class="rating-context">
              <span class="stars">{{ '⭐'.repeat(selectedReview.rating) }}</span>
            </div>
          </div>

          <form @submit.prevent="submitResponse" class="response-form">
            <div class="form-group">
              <label for="response-text">Your Response</label>
              <textarea
                id="response-text"
                v-model="responseForm.text"
                placeholder="Provide a professional and courteous response..."
                class="textarea"
                rows="5"
              ></textarea>
              <span class="char-count">{{ responseForm.text.length }}/500</span>
            </div>

            <div v-if="responseError" class="error-message">{{ responseError }}</div>

            <div class="form-actions">
              <button type="button" @click="closeResponseModal" class="btn btn-secondary">
                Cancel
              </button>
              <button type="submit" :disabled="responseLoading" class="btn btn-primary">
                {{ responseLoading ? 'Posting...' : 'Post Response' }}
              </button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- View Response Modal -->
    <div v-if="showViewResponseModal" class="modal-overlay" @click.self="closeViewResponseModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Admin Response</h2>
          <button @click="closeViewResponseModal" class="close-btn">✕</button>
        </div>

        <div v-if="selectedReview" class="modal-body">
          <div class="review-context">
            <h4>{{ selectedReview.tourist_name }} → {{ selectedReview.operator_name }}</h4>
            <p class="original-review">{{ selectedReview.review_text }}</p>
          </div>

          <div class="admin-response-view">
            <div class="response-header">
              <span class="response-label">Admin Response</span>
              <span class="response-date">{{ formatDate(selectedReview.responded_at) }}</span>
            </div>
            <p class="response-text">{{ selectedReview.admin_response }}</p>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeViewResponseModal" class="btn btn-secondary">Close</button>
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
const reviews = ref([])
const searchQuery = ref('')
const ratingFilter = ref('')
const statusFilter = ref('')
const currentPage = ref(1)
const pageSize = 10
const selectedReview = ref(null)
const showResponseModal = ref(false)
const showViewResponseModal = ref(false)
const showConfirmDialog = ref(false)
const responseLoading = ref(false)
const responseError = ref('')
const confirmMessage = ref('')
const confirmButtonText = ref('')
const confirmDanger = ref(false)
let confirmCallback = null

const responseForm = ref({
  text: ''
})

const totalReviews = computed(() => reviews.value.length)
const totalPages = computed(() => Math.ceil(filteredReviews.value.length / pageSize))

const filteredReviews = computed(() => {
  let filtered = reviews.value

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(r =>
      r.tourist_name.toLowerCase().includes(query) ||
      r.operator_name.toLowerCase().includes(query) ||
      (r.review_text || '').toLowerCase().includes(query)
    )
  }

  if (ratingFilter.value) {
    filtered = filtered.filter(r => r.rating === parseInt(ratingFilter.value))
  }

  if (statusFilter.value === 'flagged') {
    filtered = filtered.filter(r => r.is_flagged)
  } else if (statusFilter.value === 'responded') {
    filtered = filtered.filter(r => r.is_responded)
  } else if (statusFilter.value === 'pending') {
    filtered = filtered.filter(r => !r.is_responded)
  }

  return filtered
})

const paginatedReviews = computed(() => {
  const start = (currentPage.value - 1) * pageSize
  const end = start + pageSize
  return filteredReviews.value.slice(start, end)
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

const formatDate = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString('en-IN')
}

const fetchReviews = async () => {
  try {
    loading.value = true
    const token = localStorage.getItem('adminToken')
    // Mock data for now - replace with actual API call
    reviews.value = [
      {
        _id: '1',
        tourist_name: 'John Doe',
        operator_name: 'Adventure Tours',
        rating: 5,
        review_text: 'Amazing experience! The guide was knowledgeable and friendly. Highly recommended!',
        created_at: new Date('2024-01-15'),
        is_flagged: false,
        is_responded: true,
        admin_response: 'Thank you for the wonderful review! We appreciate your feedback.',
        responded_at: new Date('2024-01-16')
      },
      {
        _id: '2',
        tourist_name: 'Jane Smith',
        operator_name: 'Mountain Trails',
        rating: 2,
        review_text: 'Poor service, late arrival, and the itinerary was not followed.',
        created_at: new Date('2024-01-20'),
        is_flagged: true,
        is_responded: false,
        admin_response: null,
        responded_at: null
      },
      {
        _id: '3',
        tourist_name: 'Mike Johnson',
        operator_name: 'Beach Resorts',
        rating: 4,
        review_text: 'Good experience overall. Only minor issues with accommodation.',
        created_at: new Date('2024-01-22'),
        is_flagged: false,
        is_responded: false,
        admin_response: null,
        responded_at: null
      }
    ]
  } catch (error) {
    console.error('Error fetching reviews:', error)
  } finally {
    loading.value = false
  }
}

const handleSearch = () => {
  currentPage.value = 1
}

const openResponseForm = (review) => {
  selectedReview.value = review
  responseForm.value.text = ''
  responseError.value = ''
  showResponseModal.value = true
}

const submitResponse = async () => {
  responseError.value = ''

  if (!responseForm.value.text.trim()) {
    responseError.value = 'Response text cannot be empty'
    return
  }

  if (responseForm.value.text.length > 500) {
    responseError.value = 'Response cannot exceed 500 characters'
    return
  }

  try {
    responseLoading.value = true
    const token = localStorage.getItem('adminToken')
    
    // Mock API call
    selectedReview.value.admin_response = responseForm.value.text
    selectedReview.value.is_responded = true
    selectedReview.value.responded_at = new Date()
    
    showResponseModal.value = false
    responseForm.value.text = ''
  } catch (error) {
    responseError.value = error.response?.data?.detail || 'Failed to post response'
  } finally {
    responseLoading.value = false
  }
}

const viewResponse = (review) => {
  selectedReview.value = review
  showViewResponseModal.value = true
}

const closeResponseModal = () => {
  showResponseModal.value = false
  selectedReview.value = null
  responseForm.value.text = ''
}

const closeViewResponseModal = () => {
  showViewResponseModal.value = false
  selectedReview.value = null
}

const flagReview = (review) => {
  confirmMessage.value = 'Flag this review for inappropriate content?'
  confirmButtonText.value = 'Flag'
  confirmDanger.value = false
  confirmCallback = () => {
    review.is_flagged = true
    showConfirmDialog.value = false
  }
  showConfirmDialog.value = true
}

const unflagReview = (review) => {
  confirmMessage.value = 'Remove flag from this review?'
  confirmButtonText.value = 'Unflag'
  confirmDanger.value = false
  confirmCallback = () => {
    review.is_flagged = false
    showConfirmDialog.value = false
  }
  showConfirmDialog.value = true
}

const deleteReview = (review) => {
  confirmMessage.value = 'Delete this review permanently? This action cannot be undone.'
  confirmButtonText.value = 'Delete'
  confirmDanger.value = true
  confirmCallback = () => {
    const index = reviews.value.findIndex(r => r._id === review._id)
    if (index > -1) {
      reviews.value.splice(index, 1)
    }
    showConfirmDialog.value = false
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
  fetchReviews()
})
</script>

<style scoped>
.admin-reviews {
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
  min-width: 300px;
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

/* Reviews Container */
.reviews-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.review-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.review-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.review-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.reviewer-info h3 {
  margin: 0;
  color: #1a202c;
  font-size: 1rem;
  font-weight: 600;
}

.reviewer-info p {
  margin: 0.25rem 0 0 0;
  color: #718096;
  font-size: 0.9rem;
}

.rating-display {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.stars {
  font-size: 1.2rem;
}

.rating-value {
  font-weight: 600;
  color: #f59e0b;
  font-size: 0.95rem;
}

.review-meta {
  text-align: right;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  align-items: flex-end;
}

.date {
  font-size: 0.85rem;
  color: #a0aec0;
}

.status-flags {
  display: flex;
  gap: 0.5rem;
}

.flag-badge,
.responded-badge {
  display: inline-block;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.75rem;
  font-weight: 600;
}

.flag-badge {
  background: #fee2e2;
  color: #991b1b;
}

.responded-badge {
  background: #dcfce7;
  color: #166534;
}

.review-content {
  margin-bottom: 1rem;
}

.review-text {
  color: #4b5563;
  line-height: 1.6;
  margin: 0 0 1rem 0;
}

.admin-response {
  padding: 1rem;
  background: #f0fdf4;
  border-left: 4px solid #22c55e;
  border-radius: 6px;
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
}

.response-label {
  font-weight: 600;
  color: #166534;
}

.response-date {
  color: #a0aec0;
}

.response-text {
  margin: 0;
  color: #4b5563;
  line-height: 1.5;
}

.review-actions {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.action-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn.respond {
  background: #dbeafe;
  color: #0284c7;
}

.action-btn.respond:hover {
  background: #bfdbfe;
}

.action-btn.view-response {
  background: #ddd6fe;
  color: #6d28d9;
}

.action-btn.view-response:hover {
  background: #c4b5fd;
}

.action-btn.flag {
  background: #fce7f3;
  color: #be185d;
}

.action-btn.flag:hover {
  background: #fbcfe8;
}

.action-btn.unflag {
  background: #dcfce7;
  color: #166534;
}

.action-btn.unflag:hover {
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

.review-context {
  background: #f7fafc;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.review-context h4 {
  margin: 0 0 0.5rem 0;
  color: #1a202c;
  font-size: 1rem;
}

.original-review {
  margin: 0.5rem 0;
  color: #4b5563;
  line-height: 1.5;
  font-style: italic;
}

.rating-context {
  margin-top: 0.5rem;
}

.response-form {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.form-group label {
  font-weight: 600;
  color: #2d3748;
  font-size: 0.95rem;
}

.textarea {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  font-family: inherit;
  resize: vertical;
  transition: all 0.2s;
}

.textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.char-count {
  font-size: 0.85rem;
  color: #a0aec0;
  text-align: right;
}

.error-message {
  padding: 0.75rem;
  background: #fee2e2;
  border-left: 3px solid #ef4444;
  color: #991b1b;
  border-radius: 6px;
  font-size: 0.9rem;
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

.btn-danger {
  background: #f87171;
  color: white;
}

.btn-danger:hover {
  background: #ef4444;
}

.modal-footer {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  background: #f7fafc;
}

.admin-response-view {
  padding: 1rem;
  background: #f0fdf4;
  border-left: 4px solid #22c55e;
  border-radius: 6px;
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

  .review-header {
    flex-direction: column;
    gap: 1rem;
  }

  .review-meta {
    text-align: left;
    align-items: flex-start;
  }

  .review-actions {
    justify-content: flex-start;
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
