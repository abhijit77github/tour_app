<template>
  <div class="operator-quotes">
    <!-- Header -->
    <div class="quotes-header">
      <div>
        <h1>Quote Requests</h1>
        <p>Respond to booking requests from tourists</p>
      </div>
      <div class="header-stats">
        <div class="stat">
          <span class="stat-number">{{ totalQuotes }}</span>
          <span class="stat-label">Total Requests</span>
        </div>
        <div class="stat">
          <span class="stat-number">{{ newQuotes }}</span>
          <span class="stat-label">New</span>
        </div>
        <div class="stat">
          <span class="stat-number">{{ respondedQuotes }}</span>
          <span class="stat-label">Responded</span>
        </div>
      </div>
    </div>

    <!-- Filters -->
    <div class="filters-bar">
      <div class="filter-group">
        <button 
          @click="selectedFilter = 'all'" 
          :class="['filter-btn', { active: selectedFilter === 'all' }]"
        >
          All
        </button>
        <button 
          @click="selectedFilter = 'new'" 
          :class="['filter-btn', { active: selectedFilter === 'new' }]"
        >
          New
        </button>
        <button 
          @click="selectedFilter = 'responded'" 
          :class="['filter-btn', { active: selectedFilter === 'responded' }]"
        >
          Responded
        </button>
      </div>
      <input 
        v-model="searchQuery" 
        type="text" 
        placeholder="Search locations or tourist name..."
        class="search-input"
      />
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading quote requests...</p>
    </div>

    <!-- Empty State -->
    <div v-else-if="filteredQuotes.length === 0" class="empty-state">
      <div class="empty-icon">📬</div>
      <h3>No quote requests found</h3>
      <p v-if="selectedFilter === 'all' && searchQuery">
        Try adjusting your search filters
      </p>
      <p v-else>
        When tourists request quotes for your areas, they'll appear here
      </p>
    </div>

    <!-- Quotes List -->
    <div v-else class="quotes-container">
      <div
        v-for="quote in filteredQuotes"
        :key="quote._id"
        class="quote-card"
        :class="getQuoteClass(quote)"
      >
        <div class="quote-card-header">
          <div class="quote-info">
            <h3>{{ quote.locations.length }} Location{{ quote.locations.length > 1 ? 's' : '' }}</h3>
            <span class="quote-status" :class="getStatusClass(quote)">
              {{ getStatusLabel(quote) }}
            </span>
          </div>
          <p class="quote-date">{{ formatDate(quote.created_at) }}</p>
        </div>

        <!-- Locations -->
        <div class="locations-section">
          <p class="section-label">Locations Requested:</p>
          <div class="location-list">
            <div 
              v-for="loc in quote.locations" 
              :key="loc.name"
              class="location-item"
            >
              <span class="location-icon">📍</span>
              <span class="location-name">{{ loc.name }}</span>
              <span v-if="isMatchingLocation(loc)" class="location-match">✓ Your Area</span>
            </div>
          </div>
        </div>

        <!-- Tourist Info -->
        <div class="tourist-section">
          <div class="tourist-header">
            <h4>Tourist Details</h4>
          </div>
          <div class="tourist-grid">
            <div class="tourist-item">
              <span class="item-label">Name:</span>
              <span class="item-value">{{ quote.tourist_name }}</span>
            </div>
            <div class="tourist-item">
              <span class="item-label">Travel Window:</span>
              <span class="item-value">{{ formatTravelWindow(quote.travel_window) }}</span>
            </div>
            <div class="tourist-item">
              <span class="item-label">Travelers:</span>
              <span class="item-value">{{ quote.travelers }} People</span>
            </div>
            <div class="tourist-item">
              <span class="item-label">Budget:</span>
              <span class="item-value">{{ quote.budget }}</span>
            </div>
          </div>
          <div v-if="quote.preferences" class="preferences">
            <span class="pref-label">Preferences:</span>
            <p class="pref-text">{{ quote.preferences }}</p>
          </div>
        </div>

        <!-- Responses -->
        <div v-if="quote.responses && quote.responses.length > 0" class="responses-section">
          <p class="section-label">Your Responses:</p>
          <div 
            v-for="(resp, idx) in quote.responses" 
            :key="idx"
            class="response-item"
          >
            <div class="response-header">
              <span class="response-operator">{{ resp.operator_name }}</span>
              <span class="response-date">{{ formatDate(resp.created_at) }}</span>
            </div>
            <p class="response-message">{{ resp.message }}</p>
            <p class="response-amount">Amount: <strong>{{ resp.amount }}</strong></p>
          </div>
        </div>

        <!-- Action Buttons -->
        <div class="card-actions">
          <button 
            v-if="!quote.responded_by_me"
            @click="openResponseForm(quote)"
            class="btn btn-primary"
          >
            Send Quote
          </button>
          <button 
            v-else
            class="btn btn-secondary"
            disabled
          >
            ✓ Responded
          </button>
          <a :href="getMapLink(quote)" target="_blank" class="btn btn-secondary">
            View Map
          </a>
        </div>
      </div>
    </div>

    <!-- Response Form Modal -->
    <div v-if="showResponseForm" class="modal-overlay" @click.self="closeResponseForm">
      <div class="modal">
        <div class="modal-header">
          <h2>Send Quote</h2>
          <button @click="closeResponseForm" class="close-btn">✕</button>
        </div>
        <div class="modal-content">
          <div class="form-group">
            <label>Quote Amount</label>
            <input 
              v-model="responseForm.amount"
              type="text"
              placeholder="e.g., $2500 per person"
              class="form-input"
            />
          </div>
          <div class="form-group">
            <label>Message</label>
            <textarea 
              v-model="responseForm.message"
              placeholder="Include details about your package, what's included, availability, etc."
              class="form-textarea"
              rows="6"
            ></textarea>
          </div>
          <div class="modal-actions">
            <button @click="closeResponseForm" class="btn btn-secondary">Cancel</button>
            <button @click="submitResponse" class="btn btn-primary" :disabled="!responseForm.amount || !responseForm.message">
              Send Quote
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'

const authStore = useAuthStore()
const quoteRequests = ref([])
const loading = ref(true)
const selectedFilter = ref('all')
const searchQuery = ref('')
const profile = ref(null)

const showResponseForm = ref(false)
const currentQuoteId = ref(null)
const responseForm = ref({
  amount: '',
  message: ''
})

const totalQuotes = computed(() => quoteRequests.value.length)
const newQuotes = computed(() => 
  quoteRequests.value.filter(q => !q.responded_by_me).length
)
const respondedQuotes = computed(() => 
  quoteRequests.value.filter(q => q.responded_by_me).length
)

const filteredQuotes = computed(() => {
  let filtered = quoteRequests.value

  // Apply filter
  if (selectedFilter.value === 'new') {
    filtered = filtered.filter(q => !q.responded_by_me)
  } else if (selectedFilter.value === 'responded') {
    filtered = filtered.filter(q => q.responded_by_me)
  }

  // Apply search
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(q => 
      q.locations.some(loc => loc.name.toLowerCase().includes(query)) ||
      q.tourist_name.toLowerCase().includes(query)
    )
  }

  return filtered
})

const getQuoteClass = (quote) => {
  if (quote.responded_by_me) return 'responded'
  return 'new-quote'
}

const getStatusLabel = (quote) => {
  if (quote.responded_by_me) return 'Responded'
  return 'New'
}

const getStatusClass = (quote) => {
  return quote.responded_by_me ? 'status-responded' : 'status-new'
}

const isMatchingLocation = (location) => {
  if (!profile.value?.serving_areas) return false
  return profile.value.serving_areas.some(area =>
    area.area_name.toLowerCase().includes(location.name.toLowerCase()) ||
    location.name.toLowerCase().includes(area.area_name.toLowerCase())
  )
}

const formatDate = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    if (diffHours === 0) return 'Just now'
    return `${diffHours}h ago`
  } else if (diffDays === 1) {
    return 'Yesterday'
  } else if (diffDays < 7) {
    return `${diffDays}d ago`
  }
  
  return date.toLocaleDateString()
}

const formatTravelWindow = (window) => {
  if (!window) return 'Not specified'
  if (window.start_date && window.end_date) {
    const start = new Date(window.start_date).toLocaleDateString()
    const end = new Date(window.end_date).toLocaleDateString()
    return `${start} to ${end}`
  }
  return window.start_date || 'Not specified'
}

const getMapLink = (quote) => {
  if (!quote.locations || quote.locations.length === 0) return '#'
  const loc = quote.locations[0]
  if (loc.coordinates?.lat && loc.coordinates?.lng) {
    return `https://maps.google.com/?q=${loc.coordinates.lat},${loc.coordinates.lng}`
  }
  return `https://maps.google.com/?q=${loc.name}`
}

const openResponseForm = (quote) => {
  currentQuoteId.value = quote._id
  showResponseForm.value = true
  responseForm.value = { amount: '', message: '' }
}

const closeResponseForm = () => {
  showResponseForm.value = false
  currentQuoteId.value = null
  responseForm.value = { amount: '', message: '' }
}

const submitResponse = async () => {
  if (!currentQuoteId.value || !responseForm.value.amount || !responseForm.value.message) return

  try {
    await api.post(`/quotes/${currentQuoteId.value}/respond`, {
      amount: responseForm.value.amount,
      message: responseForm.value.message
    })
    
    // Reload quotes
    await loadQuotes()
    closeResponseForm()
  } catch (error) {
    console.error('Failed to submit response:', error)
    alert('Failed to send quote. Please try again.')
  }
}

const loadQuotes = async () => {
  try {
    const profileRes = await api.get('/operators/profile/me')
    profile.value = profileRes.data

    const quotesRes = await api.get('/quotes/inbox')
    quoteRequests.value = quotesRes.data.quotes || []
  } catch (error) {
    console.error('Failed to load quotes:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadQuotes()
})
</script>

<style scoped>
.operator-quotes {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #e0f2fe 100%);
  min-height: 100vh;
  padding: 2rem;
}

.quotes-header {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #334155 100%);
  color: white;
  padding: 2.5rem;
  border-radius: 15px;
  margin-bottom: 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
}

.quotes-header h1 {
  font-size: 2.2rem;
  margin: 0 0 0.5rem 0;
  font-weight: 800;
}

.quotes-header p {
  margin: 0;
  opacity: 0.9;
}

.header-stats {
  display: flex;
  gap: 2rem;
}

.stat {
  text-align: center;
}

.stat-number {
  display: block;
  font-size: 1.8rem;
  font-weight: 700;
}

.stat-label {
  display: block;
  font-size: 0.85rem;
  opacity: 0.8;
  margin-top: 0.3rem;
}

.filters-bar {
  display: flex;
  gap: 1.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
  align-items: center;
}

.filter-group {
  display: flex;
  gap: 0.5rem;
  background: white;
  padding: 0.5rem;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
}

.filter-btn {
  padding: 0.6rem 1.2rem;
  border: none;
  background: transparent;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 500;
  transition: all 0.3s;
  color: #666;
}

.filter-btn:hover {
  background: #f1f5f9;
}

.filter-btn.active {
  background: #3b82f6;
  color: white;
}

.search-input {
  flex: 1;
  min-width: 250px;
  padding: 0.8rem 1.2rem;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.95rem;
  transition: border-color 0.3s;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
}

.loading-state, .empty-state {
  text-align: center;
  padding: 4rem 2rem;
  background: white;
  border-radius: 15px;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  font-size: 1.3rem;
  color: #333;
  margin-bottom: 0.5rem;
}

.empty-state p {
  color: #999;
}

.quotes-container {
  display: grid;
  gap: 1.5rem;
}

.quote-card {
  background: white;
  border-radius: 15px;
  padding: 2rem;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  transition: all 0.3s;
  border-left: 5px solid #3b82f6;
}

.quote-card:hover {
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12);
  transform: translateY(-2px);
}

.quote-card.responded {
  border-left-color: #10b981;
  opacity: 0.95;
}

.quote-card.new-quote {
  border-left-color: #f59e0b;
}

.quote-card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.5rem;
  padding-bottom: 1.5rem;
  border-bottom: 1px solid #f1f5f9;
}

.quote-info {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.quote-info h3 {
  margin: 0;
  font-size: 1.1rem;
  color: #333;
}

.quote-status {
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.status-new {
  background: #fef3c7;
  color: #92400e;
}

.status-responded {
  background: #d1fae5;
  color: #065f46;
}

.quote-date {
  color: #999;
  font-size: 0.9rem;
  margin: 0;
}

.locations-section, .tourist-section, .responses-section {
  margin-bottom: 1.5rem;
}

.section-label {
  font-weight: 600;
  color: #333;
  margin-bottom: 0.8rem;
  font-size: 0.95rem;
}

.location-list {
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
}

.location-item {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  padding: 0.8rem;
  background: #f8fafc;
  border-radius: 8px;
  font-size: 0.95rem;
}

.location-icon {
  font-size: 1.2rem;
}

.location-name {
  flex: 1;
  color: #333;
}

.location-match {
  background: #d1fae5;
  color: #065f46;
  padding: 0.3rem 0.6rem;
  border-radius: 4px;
  font-size: 0.8rem;
  font-weight: 600;
}

.tourist-header {
  margin-bottom: 1rem;
}

.tourist-header h4 {
  margin: 0;
  color: #333;
}

.tourist-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
  margin-bottom: 1rem;
}

.tourist-item {
  display: flex;
  gap: 0.5rem;
}

.item-label {
  font-weight: 600;
  color: #666;
  min-width: 100px;
}

.item-value {
  color: #333;
}

.preferences {
  background: #f8fafc;
  padding: 1rem;
  border-radius: 8px;
  margin-top: 1rem;
}

.pref-label {
  font-weight: 600;
  color: #333;
}

.pref-text {
  margin: 0.5rem 0 0 0;
  color: #666;
  line-height: 1.5;
}

.response-item {
  background: #f0f9ff;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 0.8rem;
  border-left: 3px solid #0284c7;
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.6rem;
}

.response-operator {
  font-weight: 600;
  color: #333;
}

.response-date {
  color: #999;
  font-size: 0.85rem;
}

.response-message {
  color: #555;
  margin: 0.6rem 0;
  line-height: 1.5;
}

.response-amount {
  color: #0284c7;
  font-weight: 600;
  margin: 0.6rem 0 0 0;
}

.card-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
  padding-top: 1.5rem;
  border-top: 1px solid #f1f5f9;
}

.btn {
  flex: 1;
  padding: 0.8rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 0.95rem;
}

.btn-primary {
  background: #3b82f6;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2563eb;
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(59, 130, 246, 0.4);
}

.btn-secondary {
  background: #e2e8f0;
  color: #333;
}

.btn-secondary:hover:not(:disabled) {
  background: #cbd5e1;
}

.btn:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

/* Modal Styles */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 1000;
}

.modal {
  background: white;
  border-radius: 15px;
  width: 90%;
  max-width: 500px;
  max-height: 90vh;
  overflow-y: auto;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 2rem;
  border-bottom: 1px solid #f1f5f9;
}

.modal-header h2 {
  margin: 0;
  color: #333;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #999;
}

.modal-content {
  padding: 2rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 600;
  color: #333;
}

.form-input, .form-textarea {
  width: 100%;
  padding: 0.8rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-family: inherit;
  font-size: 0.95rem;
  transition: border-color 0.3s;
}

.form-input:focus, .form-textarea:focus {
  outline: none;
  border-color: #3b82f6;
}

.form-textarea {
  resize: vertical;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #f1f5f9;
}

.modal-actions .btn {
  flex: 1;
}

@media (max-width: 768px) {
  .quotes-header {
    flex-direction: column;
    text-align: center;
  }

  .header-stats {
    margin-top: 1.5rem;
  }

  .filters-bar {
    flex-direction: column;
  }

  .search-input {
    width: 100%;
  }

  .tourist-grid {
    grid-template-columns: 1fr;
  }

  .quote-card {
    padding: 1.5rem;
  }

  .card-actions {
    flex-direction: column;
  }
}
</style>
