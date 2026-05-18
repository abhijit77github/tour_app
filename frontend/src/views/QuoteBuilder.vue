<template>
  <div class="quote-builder">
    <div class="container">
      <header class="page-header">
        <div>
          <p class="eyebrow">Custom trip planner</p>
          <h1>Search places, build a bucket, get operator quotes</h1>
          <p class="lede">Add any place you like (even if no operator serves it yet), publish it, and operators will respond with quotes you can chat about.</p>
        </div>
        <div class="stats">
          <div class="stat-card">
            <span class="label">Locations</span>
            <span class="value">{{ quoteStore.bucketCount }}</span>
          </div>
          <div class="stat-card">
            <span class="label">Requests sent</span>
            <span class="value">{{ quoteStore.recentQuotes.length }}</span>
          </div>
        </div>
      </header>

      <div class="grid">
        <section class="card search-card">
          <div class="section-head">
            <div>
              <h2>Find locations</h2>
              <p>Search worldwide and drop them into your bucket. Use the map to add custom pins.</p>
            </div>
            <div class="search-container">
              <div class="search-bar-wrapper">
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Search any place (city, landmark, beach...)"
                  @keyup="handleSearchInput"
                  @keyup.enter="handleSearch"
                  @focus="showSuggestions = true"
                  @blur="setTimeout(() => showSuggestions = false, 200)"
                  class="search-input"
                />
                <button class="btn btn-primary" @click="handleSearch" :disabled="quoteStore.searching">
                  {{ quoteStore.searching ? 'Searching...' : 'Search' }}
                </button>
              </div>

              <!-- Autocomplete Suggestions Dropdown -->
              <div v-if="showSuggestions && searchQuery.length >= 2" class="suggestions-dropdown">
                <!-- Operator Locations Section -->
                <div v-if="suggestedLocations.from_operators.length > 0" class="suggestions-section">
                  <div class="section-label">
                    <span class="badge operator-badge">Featured from Operators</span>
                  </div>
                  <div
                    v-for="result in suggestedLocations.from_operators.slice(0, 5)"
                    :key="result.id"
                    class="suggestion-item operator-item"
                    @click="selectSuggestion(result)"
                  >
                    <div class="suggestion-content">
                      <div class="suggestion-title">{{ result.name }}</div>
                      <div class="suggestion-meta">
                        <span v-if="result.state">{{ result.state }}</span>
                        <span v-if="result.country">{{ result.country }}</span>
                        <span class="operator-info">by {{ result.operator_name }}</span>
                      </div>
                    </div>
                    <div class="suggestion-icon">✈️</div>
                  </div>
                </div>

                <!-- Global Locations Section -->
                <div v-if="suggestedLocations.global.length > 0" class="suggestions-section">
                  <div class="section-label">
                    <span class="badge global-badge">Locations Worldwide</span>
                  </div>
                  <div
                    v-for="result in suggestedLocations.global.slice(0, 5)"
                    :key="result.id"
                    class="suggestion-item global-item"
                    @click="selectSuggestion(result)"
                  >
                    <div class="suggestion-content">
                      <div class="suggestion-title">{{ result.name.split(',')[0] }}</div>
                      <div class="suggestion-meta">
                        <span v-if="result.state">{{ result.state }}</span>
                        <span v-if="result.country">{{ result.country }}</span>
                      </div>
                    </div>
                    <div class="suggestion-icon">🌍</div>
                  </div>
                </div>

                <div v-if="suggestedLocations.from_operators.length === 0 && suggestedLocations.global.length === 0" class="no-suggestions">
                  No locations found
                </div>
              </div>
            </div>
          </div>

          <div v-if="searchError" class="error">{{ searchError }}</div>

          <div v-if="searchResults.length" class="results">
            <!-- Operator Locations Results -->
            <div v-if="searchResults.from_operators && searchResults.from_operators.length > 0" class="results-section">
              <h3 class="results-section-title">
                <span class="badge operator-badge">Featured from Operators</span>
              </h3>
              <div v-for="result in searchResults.from_operators" :key="result.id" class="result-item operator-result">
                <div class="result-content">
                  <h4>{{ result.name }}</h4>
                  <p class="muted">{{ result.state }} {{ result.state && result.country ? '•' : '' }} {{ result.country }}</p>
                  <p class="operator-badge-text">✈️ Offered by {{ result.operator_name }}</p>
                  <p v-if="result.sub_locations && result.sub_locations.length" class="sub-locations">
                    Includes: {{ result.sub_locations.join(', ') }}
                  </p>
                  <p class="coords">📍 {{ result.lat?.toFixed(4) }}, {{ result.lng?.toFixed(4) }}</p>
                </div>
                <button class="btn btn-secondary" @click="addSearchResult(result)">Add to bucket</button>
              </div>
            </div>

            <!-- Global Locations Results -->
            <div v-if="searchResults.global && searchResults.global.length > 0" class="results-section">
              <h3 class="results-section-title">
                <span class="badge global-badge">Worldwide Locations</span>
              </h3>
              <div v-for="result in searchResults.global" :key="result.id" class="result-item global-result">
                <div class="result-content">
                  <h4>{{ result.name }}</h4>
                  <p class="muted">{{ result.state }} {{ result.state && result.country ? '•' : '' }} {{ result.country }}</p>
                  <p class="coords">📍 {{ result.lat.toFixed(4) }}, {{ result.lng.toFixed(4) }}</p>
                </div>
                <button class="btn btn-secondary" @click="addSearchResult(result)">Add to bucket</button>
              </div>
            </div>
          </div>

          <div class="manual-add card-sub">
            <div>
              <h3>Or drop a custom pin</h3>
              <p class="muted">Click the map, give it a name, and add.</p>
            </div>
            <MapView
              v-model="manualLocation.coordinates"
              :allow-selection="true"
              :show-coordinates="true"
              height="250px"
            />
            <div class="manual-form">
              <input v-model="manualLocation.name" type="text" placeholder="Location name" />
              <input v-model="manualLocation.state" type="text" placeholder="State/Region" />
              <input v-model="manualLocation.country" type="text" placeholder="Country" />
              <input v-model="manualLocation.notes" type="text" placeholder="Notes (optional)" />
              <button class="btn btn-primary" @click="addManualLocation">Add pin</button>
            </div>
            <div v-if="manualError" class="error">{{ manualError }}</div>
          </div>
        </section>

        <section class="card bucket-card">
          <div class="section-head">
            <div>
              <h2>Bucket ({{ quoteStore.bucketCount }})</h2>
              <p>Preview everything you will publish for operators.</p>
            </div>
            <button v-if="quoteStore.bucketCount" class="btn btn-ghost" @click="clearBucket">Clear</button>
          </div>

          <MapView
            :locations="quoteStore.mapLocations"
            :center="defaultCenter"
            :zoom="quoteStore.mapLocations.length ? 6 : 3"
            height="260px"
            :show-coordinates="false"
          />

          <div v-if="!quoteStore.bucketCount" class="empty">Start with a search or drop a pin.</div>

          <div v-else class="bucket-list">
            <div v-for="(item, idx) in quoteStore.bucket" :key="idx" class="bucket-item">
              <div>
                <h4>{{ item.name }}</h4>
                <p class="muted">{{ item.state }} {{ item.state && item.country ? '•' : '' }} {{ item.country }}</p>
                <p class="coords">📍 {{ item.coordinates.latitude.toFixed(4) }}, {{ item.coordinates.longitude.toFixed(4) }}</p>
                <input
                  v-model="item.notes"
                  class="note-input"
                  type="text"
                  placeholder="Add note for operators"
                  @blur="quoteStore.persist"
                />
              </div>
              <button class="btn btn-danger" @click="removeLocation(idx)">Remove</button>
            </div>
          </div>
        </section>
      </div>

      <section class="card publish-card">
        <div class="section-head">
          <div>
            <h2>Publish and get a quote</h2>
            <p>Share timing, budget, and anything else operators should know.</p>
          </div>
          <button class="btn btn-primary" @click="publishQuote" :disabled="quoteStore.loading || !quoteStore.bucketCount">
            {{ quoteStore.loading ? 'Publishing...' : 'Get a quote' }}
          </button>
        </div>

        <div class="form-grid">
          <div class="form-group">
            <label>Travel window</label>
            <input v-model="form.travel_window" type="text" placeholder="e.g., 15-22 March or Flexible in April" />
          </div>
          <div class="form-group">
            <label>Travelers</label>
            <input v-model.number="form.travelers" type="number" min="1" placeholder="2" />
          </div>
          <div class="form-group">
            <label>Budget (optional)</label>
            <input v-model="form.budget" type="number" min="0" step="50" placeholder="1000" />
          </div>
        </div>

        <div class="form-group">
          <label>Notes to operators</label>
          <textarea v-model="form.notes" rows="3" placeholder="Interests, constraints, must-do experiences..."></textarea>
        </div>

        <div class="status-row">
          <div v-if="successMessage" class="success">{{ successMessage }}</div>
          <div v-if="quoteStore.error" class="error">{{ quoteStore.error }}</div>
        </div>
      </section>

      <section class="card" v-if="quoteStore.recentQuotes.length">
        <div class="section-head">
          <h2>My quote requests</h2>
          <p class="muted">Track responses from operators and open chats.</p>
        </div>
        <div class="quotes-list">
          <div v-for="quote in quoteStore.recentQuotes" :key="quote._id" class="quote-card">
            <div class="quote-meta">
              <h4>{{ quote.locations.length }} location(s) • Status: <span class="badge">{{ quote.status }}</span></h4>
              <p class="muted">{{ new Date(quote.created_at).toLocaleString() }}</p>
              <p v-if="quote.notes" class="muted">Note: {{ quote.notes }}</p>
              <p v-if="quote.travel_window" class="muted">When: {{ quote.travel_window }}</p>
              <p v-if="quote.budget" class="muted">Budget: ${{ quote.budget }}</p>
            </div>
            <ul class="location-list">
              <li v-for="(loc, idx) in quote.locations" :key="idx">
                {{ loc.name }} — {{ loc.state || 'State N/A' }}, {{ loc.country || 'Country N/A' }}
              </li>
            </ul>
            <div v-if="quote.responses && quote.responses.length" class="responses">
              <h5>Responses</h5>
              <div v-for="(resp, ridx) in quote.responses" :key="ridx" class="response-item">
                <p><strong>{{ resp.operator_name || 'Operator' }}</strong> quoted <span v-if="resp.amount">${{ resp.amount }}</span></p>
                <p class="muted">{{ resp.message || 'No message' }}</p>
                <p class="muted">{{ new Date(resp.created_at).toLocaleString() }}</p>
              </div>
            </div>
            <div v-else class="muted">No responses yet.</div>
            <div class="quote-actions">
              <button 
                v-if="quote.status !== 'closed'"
                @click="removeQuote(quote._id)"
                class="btn btn-danger"
              >
                Remove Request
              </button>
              <span v-else class="status-closed-label">Closed</span>
            </div>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import MapView from '../components/MapView.vue'
import { useQuoteStore } from '../stores/quotes'

const quoteStore = useQuoteStore()
const searchQuery = ref('')
const searchResults = ref({ global: [], from_operators: [] })
const suggestedLocations = ref({ global: [], from_operators: [] })
const showSuggestions = ref(false)
const searchError = ref(null)
const manualError = ref(null)
const searchTimeout = ref(null)
const successMessage = ref('')

const manualLocation = ref({
  name: '',
  state: '',
  country: '',
  notes: '',
  coordinates: null
})

const form = ref({
  travel_window: '',
  travelers: 2,
  budget: '',
  notes: ''
})

const defaultCenter = computed(() => ({ lat: 20.5937, lng: 78.9629 }))

onMounted(async () => {
  quoteStore.hydrate()
  await quoteStore.loadMyQuotes()
})

const handleSearch = async () => {
  searchError.value = null
  searchResults.value = { global: [], from_operators: [] }
  const results = await quoteStore.searchPlaces(searchQuery.value)
  searchResults.value = results
  
  const totalResults = (results.global?.length || 0) + (results.from_operators?.length || 0)
  if (totalResults === 0) {
    searchError.value = 'No places found. Try refining your query.'
  }
  showSuggestions.value = false
}

const handleSearchInput = async () => {
  searchError.value = null
  
  // Clear previous timeout
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  
  // Show suggestions if query is long enough
  if (searchQuery.value.length >= 2) {
    showSuggestions.value = true
    
    // Debounced search for suggestions
    searchTimeout.value = setTimeout(async () => {
      const results = await quoteStore.searchPlaces(searchQuery.value)
      suggestedLocations.value = results
    }, 300)
  } else {
    showSuggestions.value = false
  }
}

const selectSuggestion = async (result) => {
  addSearchResult(result)
  searchQuery.value = ''
  showSuggestions.value = false
  suggestedLocations.value = { global: [], from_operators: [] }
}

const addSearchResult = (result) => {
  quoteStore.addLocation({
    name: result.name,
    state: result.state,
    country: result.country,
    coordinates: { latitude: result.lat, longitude: result.lng }
  })
}

const addManualLocation = () => {
  manualError.value = null
  if (!manualLocation.value.name.trim()) {
    manualError.value = 'Give this pin a name.'
    return
  }
  if (!manualLocation.value.coordinates) {
    manualError.value = 'Select coordinates on the map first.'
    return
  }
  quoteStore.addLocation(manualLocation.value)
  manualLocation.value = { name: '', state: '', country: '', notes: '', coordinates: null }
}

const removeLocation = (idx) => {
  quoteStore.removeLocation(idx)
}

const clearBucket = () => {
  quoteStore.clearBucket()
}

const publishQuote = async () => {
  successMessage.value = ''
  try {
    await quoteStore.publishQuote({
      travel_window: form.value.travel_window,
      travelers: form.value.travelers || null,
      budget: form.value.budget ? Number(form.value.budget) : null,
      notes: form.value.notes
    })
    successMessage.value = 'Quote request published. Operators will respond soon.'
  } catch (err) {
    console.error(err)
  }
}

const removeQuote = async (quoteId) => {
  if (confirm('Are you sure you want to remove this quote request?')) {
    try {
      const api = await import('../services/api').then(m => m.default)
      await api.post(`/quotes/${quoteId}/close`)
      // Reload quotes after deletion
      await quoteStore.loadMyQuotes()
      successMessage.value = 'Quote request removed successfully.'
    } catch (err) {
      console.error('Failed to remove quote:', err)
      alert('Failed to remove quote request. Please try again.')
    }
  }
}
</script>

<style scoped>
.quote-builder {
  background: #f5f7fb;
  min-height: 100vh;
  padding: 20px 0 60px;
}

.container {
  max-width: 1180px;
  margin: 0 auto;
  padding: 0 18px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 20px;
  margin-bottom: 24px;
  align-items: flex-start;
}

.eyebrow {
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #5b6b8a;
  font-size: 0.8rem;
  margin: 0 0 6px;
}

h1 {
  margin: 0 0 8px;
  color: #1f2d3d;
}

.lede {
  color: #4f5d75;
  margin: 0;
}

.stats {
  display: flex;
  gap: 12px;
}

.stat-card {
  background: white;
  border-radius: 12px;
  padding: 14px 18px;
  box-shadow: 0 4px 18px rgba(0,0,0,0.06);
  min-width: 120px;
}

.stat-card .label {
  display: block;
  color: #6b7a99;
  font-size: 0.85rem;
}

.stat-card .value {
  font-size: 1.6rem;
  color: #1f2d3d;
  font-weight: 700;
}

.grid {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 18px;
  margin-bottom: 18px;
}

.card {
  background: white;
  border-radius: 14px;
  padding: 18px;
  box-shadow: 0 8px 20px rgba(0,0,0,0.06);
}

.card-sub {
  background: #f8f9fc;
  border: 1px solid #e6e9f2;
  border-radius: 12px;
  padding: 12px;
  margin-top: 16px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 16px;
  margin-bottom: 12px;
}

.section-head h2 {
  margin: 0;
  color: #1f2d3d;
}

.search-bar {
  display: flex;
  gap: 10px;
}

.search-bar input {
  flex: 1;
  padding: 10px 12px;
  border: 1px solid #d8deeb;
  border-radius: 10px;
}

.results {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 12px;
}

.result-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 10px 12px;
  border: 1px solid #e6e9f2;
  border-radius: 10px;
}

.manual-add {
  margin-top: 14px;
}

.manual-form {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 10px;
  margin-top: 10px;
}

.bucket-card .map-view-container {
  margin-bottom: 12px;
}

.bucket-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.bucket-item {
  display: flex;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid #e6e9f2;
  border-radius: 10px;
  padding: 12px;
}

.note-input {
  width: 100%;
  margin-top: 8px;
  padding: 8px;
  border: 1px solid #d8deeb;
  border-radius: 8px;
}

.publish-card .form-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.form-group input,
.form-group textarea {
  padding: 10px;
  border: 1px solid #d8deeb;
  border-radius: 8px;
}

.status-row {
  margin-top: 12px;
  display: flex;
  gap: 10px;
  align-items: center;
}

.quotes-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 14px;
}

.quote-card {
  border: 1px solid #e6e9f2;
  border-radius: 10px;
  padding: 12px;
  background: #fafbfe;
}

.quote-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #e6e9f2;
}

.quote-actions .btn {
  flex: 1;
  padding: 8px 12px;
  font-size: 0.9rem;
}

.status-closed-label {
  display: inline-block;
  background: #e6e9f2;
  color: #6b7a99;
  padding: 6px 12px;
  border-radius: 6px;
  font-size: 0.9rem;
  font-weight: 600;
}

.location-list {
  margin: 8px 0;
  padding-left: 16px;
  color: #4f5d75;
}

.responses {
  margin-top: 8px;
  border-top: 1px dashed #d8deeb;
  padding-top: 8px;
}

.response-item {
  margin-bottom: 6px;
}

.badge {
  background: #e9f5ef;
  color: #1b8a5a;
  padding: 3px 8px;
  border-radius: 999px;
  font-size: 0.9rem;
}

.btn {
  border: none;
  border-radius: 10px;
  padding: 10px 14px;
  cursor: pointer;
  font-weight: 600;
  transition: transform 0.1s ease, box-shadow 0.2s ease;
}

.btn:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 6px 14px rgba(0,0,0,0.08);
}

.btn-primary {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  color: white;
}

.btn-secondary {
  background: #eef2ff;
  color: #1d4ed8;
}

.btn-danger {
  background: #ffe7e7;
  color: #c24141;
}

.btn-ghost {
  background: transparent;
  color: #1f2d3d;
}

.muted {
  color: #6b7a99;
}

.coords {
  color: #4f5d75;
  font-size: 0.9rem;
}

.error {
  color: #c24141;
  margin-top: 8px;
}

.success {
  color: #1b8a5a;
}

.empty {
  text-align: center;
  color: #6b7a99;
  padding: 10px 0;
}

/* Search Container & Autocomplete Styles */
.search-container {
  position: relative;
  width: 100%;
}

.search-bar-wrapper {
  display: flex;
  gap: 8px;
  position: relative;
}

.search-input {
  flex: 1;
  padding: 12px 14px;
  border: 2px solid #d8deeb;
  border-radius: 10px;
  font-size: 1rem;
  transition: border-color 0.3s ease, box-shadow 0.3s ease;
}

.search-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.1);
}

/* Autocomplete Dropdown */
.suggestions-dropdown {
  position: absolute;
  top: calc(100% + 8px);
  left: 0;
  right: 100px;
  background: white;
  border: 1px solid #d8deeb;
  border-radius: 12px;
  box-shadow: 0 10px 32px rgba(0, 0, 0, 0.12);
  max-height: 400px;
  overflow-y: auto;
  z-index: 100;
}

.suggestions-section {
  padding: 12px 0;
  border-bottom: 1px solid #f0f2f7;
}

.suggestions-section:last-child {
  border-bottom: none;
}

.section-label {
  padding: 8px 14px 4px;
  display: flex;
  align-items: center;
}

.section-label .badge {
  font-size: 0.75rem;
  padding: 2px 6px;
}

.suggestion-item {
  padding: 12px 14px;
  cursor: pointer;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  transition: background-color 0.2s ease;
}

.suggestion-item:hover {
  background-color: #f8fafc;
}

.suggestion-item.operator-item {
  border-left: 3px solid #8b5cf6;
  background-color: rgba(139, 92, 246, 0.04);
}

.suggestion-item.operator-item:hover {
  background-color: rgba(139, 92, 246, 0.08);
}

.suggestion-item.global-item {
  border-left: 3px solid #0284c7;
}

.suggestion-item.global-item:hover {
  background-color: #f0f9ff;
}

.suggestion-content {
  flex: 1;
  min-width: 0;
}

.suggestion-title {
  font-weight: 600;
  color: #1f2d3d;
  font-size: 0.95rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.suggestion-meta {
  font-size: 0.85rem;
  color: #6b7a99;
  display: flex;
  gap: 6px;
  margin-top: 2px;
  flex-wrap: wrap;
}

.suggestion-meta span {
  white-space: nowrap;
}

.operator-info {
  color: #8b5cf6;
  font-weight: 600;
}

.suggestion-icon {
  font-size: 1.2rem;
  flex-shrink: 0;
}

.no-suggestions {
  padding: 16px 14px;
  text-align: center;
  color: #6b7a99;
  font-size: 0.9rem;
}

/* Results Sections */
.results {
  margin-top: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.results-section {
  padding: 16px;
  background: #fafbfe;
  border-radius: 12px;
  border-left: 4px solid #d8deeb;
}

.results-section:has(.operator-result) {
  border-left-color: #8b5cf6;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.04) 0%, rgba(139, 92, 246, 0.02) 100%);
}

.results-section:has(.global-result) {
  border-left-color: #0284c7;
  background: linear-gradient(135deg, rgba(2, 132, 199, 0.04) 0%, rgba(2, 132, 199, 0.02) 100%);
}

.results-section-title {
  display: flex;
  align-items: center;
  gap: 8px;
  margin: 0 0 12px 0;
  font-size: 0.95rem;
  text-transform: uppercase;
  letter-spacing: 0.5px;
  color: #4f5d75;
}

.result-item {
  padding: 14px;
  background: white;
  border-radius: 10px;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 12px;
  margin-bottom: 10px;
  border: 1px solid #e6e9f2;
  transition: all 0.2s ease;
}

.result-item:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
  transform: translateY(-2px);
}

.result-item.operator-result {
  border-left: 3px solid #8b5cf6;
  background: linear-gradient(135deg, rgba(139, 92, 246, 0.02) 0%, rgba(139, 92, 246, 0.01) 100%);
}

.result-item.global-result {
  border-left: 3px solid #0284c7;
  background: linear-gradient(135deg, rgba(2, 132, 199, 0.02) 0%, rgba(2, 132, 199, 0.01) 100%);
}

.result-content {
  flex: 1;
  min-width: 0;
}

.result-content h4 {
  margin: 0 0 4px 0;
  color: #1f2d3d;
  font-size: 1.05rem;
}

.operator-badge-text {
  font-size: 0.85rem;
  color: #8b5cf6;
  font-weight: 600;
  margin: 4px 0 2px 0;
}

.sub-locations {
  font-size: 0.85rem;
  color: #6b7a99;
  margin: 2px 0;
  font-style: italic;
}

.badge.operator-badge {
  background: linear-gradient(135deg, #f3e8ff 0%, #ede9fe 100%);
  color: #7c3aed;
  border: 1px solid #ddd6fe;
}

.badge.global-badge {
  background: linear-gradient(135deg, #e0f2fe 0%, #cffafe 100%);
  color: #0369a1;
  border: 1px solid #bae6fd;
}

@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }

  .suggestions-dropdown {
    right: auto;
  }

  .search-bar-wrapper {
    flex-direction: column;
  }

  .search-bar-wrapper .btn {
    width: 100%;
  }
}
</style>
