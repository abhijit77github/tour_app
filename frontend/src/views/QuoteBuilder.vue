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
            <div class="search-bar">
              <input
                v-model="searchQuery"
                type="text"
                placeholder="Search any place (city, landmark, beach...)"
                @keyup.enter="handleSearch"
              />
              <button class="btn btn-primary" @click="handleSearch" :disabled="quoteStore.searching">
                {{ quoteStore.searching ? 'Searching...' : 'Search' }}
              </button>
            </div>
          </div>

          <div v-if="searchError" class="error">{{ searchError }}</div>

          <div v-if="searchResults.length" class="results">
            <div v-for="result in searchResults" :key="result.id" class="result-item">
              <div>
                <h4>{{ result.name }}</h4>
                <p class="muted">{{ result.state }} {{ result.state && result.country ? '•' : '' }} {{ result.country }}</p>
                <p class="coords">📍 {{ result.lat.toFixed(4) }}, {{ result.lng.toFixed(4) }}</p>
              </div>
              <button class="btn btn-secondary" @click="addSearchResult(result)">Add to bucket</button>
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
const searchResults = ref([])
const searchError = ref(null)
const manualError = ref(null)
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
  searchResults.value = []
  const results = await quoteStore.searchPlaces(searchQuery.value)
  searchResults.value = results
  if (!results.length) {
    searchError.value = 'No places found. Try refining your query.'
  }
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

@media (max-width: 900px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .page-header {
    flex-direction: column;
  }
}
</style>
