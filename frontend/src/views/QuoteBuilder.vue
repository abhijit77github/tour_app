<template>
  <div class="qb-page">

    <!-- Page header -->
    <div class="qb-hero">
      <div class="qb-hero-inner">
        <span class="eyebrow">Trip Quote Builder</span>
        <h1>Build your bucket, get custom quotes</h1>
        <p>Add destinations, drop custom pins, then publish — operators will respond with tailored offers.</p>
        <div class="hero-stats">
          <div class="hstat">
            <strong>{{ quoteStore.bucketCount }}</strong>
            <span>Locations</span>
          </div>
          <div class="hstat-div"></div>
          <div class="hstat">
            <strong>{{ quoteStore.recentQuotes.length }}</strong>
            <span>Requests sent</span>
          </div>
        </div>
      </div>
    </div>

    <div class="qb-container">
      <StepGuidePanel
        class="flow-guide"
        variant="quote"
        eyebrow="Quick Path"
        title="Use the platform in the same order operators expect"
        description="Search or pin destinations first, attach a saved itinerary only when it adds context, then publish one request that operators can quote against clearly."
        :steps="quoteSteps"
      />

      <!-- Main 2-column layout -->
      <div class="qb-grid">

        <!-- LEFT: Search + manual pin -->
        <div class="qb-col">

          <!-- Search card -->
          <div class="qb-card">
            <div class="card-label">Search destinations</div>
            <h2 class="card-title">Find a place to add</h2>
            <p class="card-sub">Type any city, landmark, or beach — we'll show operator-featured and worldwide results.</p>

            <div class="search-wrap">
              <div class="search-bar">
                <svg class="search-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Manali, Santorini, Angkor Wat…"
                  @keyup="handleSearchInput"
                  @keyup.enter="handleSearch"
                  @focus="showSuggestions = true"
                  @blur="setTimeout(() => showSuggestions = false, 200)"
                />
                <button class="btn-search" @click="handleSearch" :disabled="quoteStore.searching">
                  {{ quoteStore.searching ? '…' : 'Search' }}
                </button>
              </div>

              <!-- Autocomplete -->
              <div v-if="showSuggestions && searchQuery.length >= 2" class="suggestions">
                <div v-if="suggestedLocations.from_operators.length" class="sug-group">
                  <div class="sug-label"><span class="sug-badge op-badge">✈️ Featured</span></div>
                  <div
                    v-for="r in suggestedLocations.from_operators.slice(0, 5)"
                    :key="r.id"
                    class="sug-item op-item"
                    @click="selectSuggestion(r)"
                  >
                    <div>
                      <div class="sug-name">{{ r.name }}</div>
                      <div class="sug-meta">{{ [r.state, r.country].filter(Boolean).join(', ') }} · {{ r.operator_name }}</div>
                    </div>
                  </div>
                </div>
                <div v-if="suggestedLocations.global.length" class="sug-group">
                  <div class="sug-label"><span class="sug-badge gl-badge">🌍 Worldwide</span></div>
                  <div
                    v-for="r in suggestedLocations.global.slice(0, 5)"
                    :key="r.id"
                    class="sug-item gl-item"
                    @click="selectSuggestion(r)"
                  >
                    <div>
                      <div class="sug-name">{{ r.name.split(',')[0] }}</div>
                      <div class="sug-meta">{{ [r.state, r.country].filter(Boolean).join(', ') }}</div>
                    </div>
                  </div>
                </div>
                <div v-if="!suggestedLocations.from_operators.length && !suggestedLocations.global.length" class="sug-empty">
                  No results yet…
                </div>
              </div>
            </div>

            <div v-if="searchError" class="msg-error">{{ searchError }}</div>

            <!-- Search results list -->
            <div v-if="searchResults.from_operators?.length || searchResults.global?.length" class="results-list">

              <div v-if="searchResults.from_operators?.length">
                <div class="res-group-label"><span class="sug-badge op-badge">✈️ Operator featured</span></div>
                <div v-for="r in searchResults.from_operators" :key="r.id" class="res-item op-res">
                  <div class="res-left">
                    <div class="res-name">{{ r.name }}</div>
                    <div class="res-meta">{{ [r.state, r.country].filter(Boolean).join(' · ') }}</div>
                    <div class="res-op">by {{ r.operator_name }}</div>
                    <div v-if="r.sub_locations?.length" class="res-subs">Includes: {{ r.sub_locations.join(', ') }}</div>
                  </div>
                  <button class="btn-add" @click="addSearchResult(r)">+ Add</button>
                </div>
              </div>

              <div v-if="searchResults.global?.length" class="mt-12">
                <div class="res-group-label"><span class="sug-badge gl-badge">🌍 Worldwide</span></div>
                <div v-for="r in searchResults.global" :key="r.id" class="res-item gl-res">
                  <div class="res-left">
                    <div class="res-name">{{ r.name }}</div>
                    <div class="res-meta">{{ [r.state, r.country].filter(Boolean).join(' · ') }}</div>
                    <div class="res-coords">{{ r.lat?.toFixed(4) }}, {{ r.lng?.toFixed(4) }}</div>
                  </div>
                  <button class="btn-add" @click="addSearchResult(r)">+ Add</button>
                </div>
              </div>

            </div>
          </div>

          <!-- Manual pin card -->
          <div class="qb-card mt-14">
            <div class="card-label">Custom pin</div>
            <h2 class="card-title">Drop a pin manually</h2>
            <p class="card-sub">Click the map to pick coordinates, then fill in the name.</p>

            <MapView
              v-model="manualLocation.coordinates"
              :allow-selection="true"
              :show-coordinates="true"
              height="220px"
            />

            <div class="pin-form">
              <input v-model="manualLocation.name" type="text" placeholder="Location name *" />
              <input v-model="manualLocation.state" type="text" placeholder="State / Region" />
              <input v-model="manualLocation.country" type="text" placeholder="Country" />
              <input v-model="manualLocation.notes" type="text" placeholder="Notes (optional)" />
              <button class="btn-pin" @click="addManualLocation">📍 Add pin to bucket</button>
            </div>
            <div v-if="manualError" class="msg-error mt-8">{{ manualError }}</div>
          </div>

        </div><!-- /left col -->

        <!-- RIGHT: Bucket + map -->
        <div class="qb-col">
          <div class="qb-card bucket-card">
            <div class="bucket-head">
              <div>
                <div class="card-label">Your bucket</div>
                <h2 class="card-title">{{ quoteStore.bucketCount }} location{{ quoteStore.bucketCount !== 1 ? 's' : '' }}</h2>
              </div>
              <button v-if="quoteStore.bucketCount" class="btn-clear" @click="clearBucket">Clear all</button>
            </div>

            <MapView
              :locations="quoteStore.mapLocations"
              :center="defaultCenter"
              :zoom="quoteStore.mapLocations.length ? 6 : 3"
              height="240px"
              :show-coordinates="false"
            />

            <div v-if="!quoteStore.bucketCount" class="bucket-empty">
              <span>🗺️</span>
              <p>Search or drop a pin to start building.</p>
            </div>

            <div v-else class="bucket-items">
              <div v-for="(item, idx) in quoteStore.bucket" :key="idx" class="bucket-row">
                <div class="bucket-row-left">
                  <div class="bucket-num">{{ idx + 1 }}</div>
                  <div class="bucket-info">
                    <div class="bucket-name">{{ item.name }}</div>
                    <div class="bucket-loc">{{ [item.state, item.country].filter(Boolean).join(', ') }}</div>
                    <input
                      v-model="item.notes"
                      class="bucket-note"
                      type="text"
                      placeholder="Note for operators…"
                      @blur="quoteStore.persist"
                    />
                  </div>
                </div>
                <button class="btn-remove" @click="removeLocation(idx)" title="Remove">✕</button>
              </div>
            </div>
          </div>
        </div>

      </div><!-- /qb-grid -->

      <!-- Publish section -->
      <div class="qb-card publish-card">
        <div class="publish-head">
          <div>
            <div class="card-label">Step 2 — publish</div>
            <h2 class="card-title">Request quotes from operators</h2>
            <p class="card-sub">Fill in your travel details and operators will reply with tailored offers.</p>
          </div>
          <button
            class="btn-publish"
            @click="publishQuote"
            :disabled="quoteStore.loading || !quoteStore.bucketCount"
          >
            <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
            {{ quoteStore.loading ? 'Publishing…' : 'Get quotes' }}
          </button>
        </div>

        <div class="pub-form-grid">
          <div class="pub-field">
            <label>📅 Travel window</label>
            <input v-model="form.travel_window" type="text" placeholder="e.g., 15-22 March or Flexible in April" />
          </div>
          <div class="pub-field">
            <label>👥 Travelers</label>
            <input v-model.number="form.travelers" type="number" min="1" placeholder="2" />
          </div>
          <div class="pub-field">
            <label>💰 Budget (optional)</label>
            <input v-model="form.budget" type="number" min="0" step="50" placeholder="1000" />
          </div>
        </div>
        <div class="pub-field mt-12">
          <label>📝 Notes to operators</label>
          <textarea v-model="form.notes" rows="3" placeholder="Interests, special requirements, must-do experiences…"></textarea>
        </div>

        <div class="itinerary-share mt-12">
          <div class="itinerary-share-head">
            <div>
              <label>🗓️ Attach saved itinerary</label>
              <p>Optional. Share a saved itinerary so operators understand your preferred route and pacing.</p>
            </div>
            <router-link to="/itineraries" class="btn-manage-itineraries">Manage itineraries</router-link>
          </div>
          <select v-model="selectedItineraryId" class="itinerary-select" :disabled="itineraryLoading">
            <option value="">No itinerary attached</option>
            <option v-for="item in savedItineraries" :key="item._id" :value="item._id">
              {{ item.title }} · {{ item.duration_days }} days
            </option>
          </select>
          <div v-if="selectedItinerary" class="itinerary-preview">
            <strong>{{ selectedItinerary.title }}</strong>
            <span>{{ selectedItinerary.primary_location?.area_name || 'Custom trip' }} · {{ selectedItinerary.duration_days }} days</span>
            <p>{{ selectedItinerary.summary || 'This itinerary will be snapshot into the quote request.' }}</p>
          </div>
        </div>

        <div v-if="successMessage" class="msg-success mt-12">✅ {{ successMessage }}</div>
        <div v-if="quoteStore.error" class="msg-error mt-12">{{ quoteStore.error }}</div>
      </div>

      <!-- My Requests -->
      <div v-if="quoteStore.recentQuotes.length" class="qb-card mt-14">
        <div class="card-label">Sent requests</div>
        <h2 class="card-title">My quote requests</h2>
        <p class="card-sub">Track operator responses and open chats.</p>

        <div class="quotes-grid">
          <div v-for="quote in quoteStore.recentQuotes" :key="quote._id" class="quote-row">

            <div class="quote-top">
              <div class="quote-meta-left">
                <span class="qbadge" :class="quote.status === 'closed' ? 'closed' : 'open'">{{ quote.status }}</span>
                <span class="q-locs">{{ quote.locations.length }} location{{ quote.locations.length !== 1 ? 's' : '' }}</span>
              </div>
              <span class="q-date">{{ new Date(quote.created_at).toLocaleDateString() }}</span>
            </div>

            <ul class="q-loc-list">
              <li v-for="(loc, i) in quote.locations" :key="i">📍 {{ loc.name }} — {{ loc.state || 'N/A' }}, {{ loc.country || 'N/A' }}</li>
            </ul>

            <div class="q-details">
              <span v-if="quote.travel_window">📅 {{ quote.travel_window }}</span>
              <span v-if="quote.budget">💰 ${{ quote.budget }}</span>
              <span v-if="quote.travelers">👥 {{ quote.travelers }}</span>
            </div>

            <div v-if="quote.attached_itinerary_snapshot" class="q-itinerary">
              <strong>Attached itinerary:</strong>
              <span>{{ quote.attached_itinerary_snapshot.title }}</span>
            </div>

            <div v-if="quote.notes" class="q-note">{{ quote.notes }}</div>

            <div v-if="quote.responses?.length" class="q-responses">
              <div class="q-resp-label">Responses ({{ quote.responses.length }})</div>
              <div v-for="(resp, ri) in quote.responses" :key="ri" class="q-resp-item">
                <div class="q-resp-name">{{ resp.operator_name || 'Operator' }}</div>
                <div v-if="resp.amount" class="q-resp-amt">${{ resp.amount }}</div>
                <div v-if="resp.message" class="q-resp-msg">{{ resp.message }}</div>
                <div v-if="resp.proposed_itinerary_snapshot" class="q-resp-itinerary">
                  <strong>{{ resp.proposed_itinerary_snapshot.title }}</strong>
                  <span>
                    {{ resp.proposed_itinerary_snapshot.duration_days }} days ·
                    {{ resp.proposed_itinerary_snapshot.primary_location?.area_name || 'Custom route' }}
                  </span>
                  <p>{{ resp.proposed_itinerary_snapshot.summary || 'Operator shared an itinerary proposal for this quote.' }}</p>
                  <button
                    class="btn-save-proposal"
                    :disabled="savingProposalKey === `${quote._id}-${ri}`"
                    @click="saveProposalToItineraries(quote._id, ri)"
                  >
                    {{ savingProposalKey === `${quote._id}-${ri}` ? 'Saving…' : 'Save to my itineraries' }}
                  </button>
                </div>
              </div>
            </div>
            <div v-else class="q-no-resp">No responses yet — operators are reviewing your request.</div>

            <div class="q-actions">
              <button v-if="quote.status !== 'closed'" class="btn-remove-quote" @click="removeQuote(quote._id)">Remove request</button>
              <span v-else class="q-closed-tag">Closed</span>
            </div>
          </div>
        </div>
      </div>

    </div><!-- /qb-container -->
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import MapView from '../components/MapView.vue'
import StepGuidePanel from '../components/StepGuidePanel.vue'
import api from '../services/api'
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
const savingProposalKey = ref('')
const savedItineraries = ref([])
const itineraryLoading = ref(false)
const selectedItineraryId = ref('')
const quoteSteps = [
  { title: 'Collect destinations', detail: 'Search featured places or drop custom pins so your request reflects the exact shortlist you care about.' },
  { title: 'Attach itinerary context', detail: 'If you already built an itinerary, attach it to show your preferred route and pacing without rewriting everything in notes.' },
  { title: 'Publish and compare', detail: 'Send one structured request and then save the best operator-proposed itinerary back into My Itineraries when it is worth keeping.' }
]

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
const selectedItinerary = computed(() => savedItineraries.value.find(item => item._id === selectedItineraryId.value) || null)

onMounted(async () => {
  quoteStore.hydrate()
  await Promise.all([quoteStore.loadMyQuotes(), loadSavedItineraries()])
})

const loadSavedItineraries = async () => {
  itineraryLoading.value = true
  try {
    const res = await api.get('/itineraries/my')
    savedItineraries.value = (res.data.itineraries || []).filter(item => item.shareable_to_quote !== false)
  } catch (err) {
    console.error('Failed to load saved itineraries', err)
  } finally {
    itineraryLoading.value = false
  }
}

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
      notes: form.value.notes,
      attached_itinerary_id: selectedItineraryId.value || null
    })
    successMessage.value = 'Quote request published. Operators will respond soon.'
    selectedItineraryId.value = ''
  } catch (err) {
    console.error(err)
  }
}

const removeQuote = async (quoteId) => {
  if (confirm('Are you sure you want to remove this quote request?')) {
    try {
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

const saveProposalToItineraries = async (quoteId, responseIndex) => {
  savingProposalKey.value = `${quoteId}-${responseIndex}`
  try {
    await api.post(`/quotes/${quoteId}/responses/${responseIndex}/save-itinerary`)
    successMessage.value = 'Itinerary saved to My Itineraries.'
    await loadSavedItineraries()
  } catch (err) {
    console.error('Failed to save proposed itinerary', err)
    quoteStore.error = err.response?.data?.detail || 'Failed to save itinerary proposal'
  } finally {
    savingProposalKey.value = ''
  }
}
</script>

<style scoped>
/* ── Page ────────────────────────────────────────────────────────────────── */
.qb-page {
  min-height: 100vh;
  background: #f0f4f8;
  padding-bottom: 5rem;
}

/* ── Hero ────────────────────────────────────────────────────────────────── */
.qb-hero {
  background: linear-gradient(135deg, #0f172a 0%, #1a2d4a 55%, #0c4a6e 100%);
  padding: 4rem 2rem 6.5rem;
  position: relative;
  overflow: hidden;
}

.qb-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 15% 60%, rgba(56,189,248,0.09), transparent 55%),
    radial-gradient(ellipse at 85% 30%, rgba(99,102,241,0.09), transparent 50%);
  pointer-events: none;
}

.qb-hero-inner {
  position: relative;
  z-index: 1;
  max-width: 760px;
  margin: 0 auto;
  text-align: center;
}

.eyebrow {
  display: inline-block;
  background: rgba(56,189,248,0.15);
  color: #7dd3fc;
  border: 1px solid rgba(56,189,248,0.25);
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.3rem 1rem;
  margin-bottom: 1rem;
}

.qb-hero-inner h1 {
  font-size: 2.5rem;
  font-weight: 800;
  color: #fff;
  line-height: 1.15;
  margin: 0 0 0.8rem;
}

.qb-hero-inner p {
  color: rgba(255,255,255,0.6);
  font-size: 1rem;
  margin: 0 0 1.8rem;
}

.hero-stats {
  display: inline-flex;
  align-items: center;
  gap: 1.2rem;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 16px;
  padding: 0.75rem 1.8rem;
}

.hstat {
  text-align: center;
}

.hstat strong {
  display: block;
  font-size: 1.6rem;
  font-weight: 800;
  color: #fff;
  line-height: 1;
}

.hstat span {
  font-size: 0.75rem;
  color: rgba(255,255,255,0.55);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.hstat-div {
  width: 1px;
  height: 36px;
  background: rgba(255,255,255,0.15);
}

/* ── Container ───────────────────────────────────────────────────────────── */
.qb-container {
  max-width: 1200px;
  margin: -3.5rem auto 0;
  padding: 0 1.5rem;
  position: relative;
  z-index: 10;
}
.flow-guide {
  margin-bottom: 1.4rem;
}

/* ── Cards ───────────────────────────────────────────────────────────────── */
.qb-card {
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(15,23,42,0.09);
  border: 1px solid #f1f5f9;
  padding: 1.8rem;
}

.mt-14 { margin-top: 1.4rem; }
.mt-12 { margin-top: 1.2rem; }
.mt-8  { margin-top: 0.8rem; }

.card-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #94a3b8;
  margin-bottom: 0.35rem;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.35rem;
}

.card-sub {
  font-size: 0.875rem;
  color: #64748b;
  margin: 0 0 1.2rem;
  line-height: 1.5;
}

/* ── 2-col grid ──────────────────────────────────────────────────────────── */
.qb-grid {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 1.4rem;
  margin-bottom: 1.4rem;
}

.qb-col {
  display: flex;
  flex-direction: column;
}

/* ── Search bar ──────────────────────────────────────────────────────────── */
.search-wrap { position: relative; }

.search-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.5rem 0.5rem 0.5rem 1rem;
}

.search-ico {
  width: 16px;
  height: 16px;
  color: #94a3b8;
  flex-shrink: 0;
}

.search-bar input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 0.9rem;
  color: #0f172a;
  outline: none;
  font-family: inherit;
}

.search-bar input::placeholder { color: #cbd5e1; }

.btn-search {
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: #fff;
  border: none;
  border-radius: 9px;
  font-size: 0.85rem;
  font-weight: 700;
  padding: 0.55rem 1.2rem;
  cursor: pointer;
  white-space: nowrap;
  transition: opacity 0.2s;
}

.btn-search:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-search:not(:disabled):hover { opacity: 0.88; }

/* Autocomplete */
.suggestions {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 16px 40px rgba(15,23,42,0.12);
  z-index: 200;
  overflow: hidden;
}

.sug-group { padding: 0.6rem 0; border-bottom: 1px solid #f1f5f9; }
.sug-group:last-child { border-bottom: none; }

.sug-label { padding: 0.4rem 1rem 0.2rem; }

.sug-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
}

.op-badge { background: #faf5ff; color: #7c3aed; border: 1px solid #ede9fe; }
.gl-badge { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }

.sug-item {
  padding: 0.65rem 1rem;
  cursor: pointer;
  transition: background 0.15s;
}

.sug-item:hover { background: #f8fafc; }
.op-item { border-left: 3px solid #8b5cf6; }
.gl-item { border-left: 3px solid #0ea5e9; }

.sug-name { font-size: 0.88rem; font-weight: 600; color: #0f172a; }
.sug-meta { font-size: 0.78rem; color: #94a3b8; margin-top: 0.1rem; }
.sug-empty { padding: 1rem; text-align: center; color: #94a3b8; font-size: 0.85rem; }

/* ── Results list ────────────────────────────────────────────────────────── */
.results-list { margin-top: 1.2rem; display: flex; flex-direction: column; gap: 0.7rem; }

.res-group-label { margin-bottom: 0.5rem; }

.res-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  background: #fafafa;
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  padding: 0.9rem 1rem;
  transition: box-shadow 0.2s, transform 0.15s;
}

.res-item:hover { box-shadow: 0 4px 16px rgba(15,23,42,0.08); transform: translateY(-1px); }
.op-res { border-left: 3px solid #8b5cf6; }
.gl-res { border-left: 3px solid #0ea5e9; }

.res-name { font-size: 0.95rem; font-weight: 700; color: #0f172a; }
.res-meta { font-size: 0.8rem; color: #64748b; margin-top: 0.15rem; }
.res-op   { font-size: 0.78rem; color: #7c3aed; font-weight: 600; margin-top: 0.15rem; }
.res-subs { font-size: 0.75rem; color: #94a3b8; font-style: italic; margin-top: 0.1rem; }
.res-coords { font-size: 0.75rem; color: #94a3b8; margin-top: 0.1rem; }

.btn-add {
  border: 1.5px solid #0ea5e9;
  background: #eff9ff;
  color: #0369a1;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.4rem 0.85rem;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.18s;
}

.btn-add:hover { background: #0ea5e9; color: #fff; border-color: #0ea5e9; }

/* ── Manual pin form ─────────────────────────────────────────────────────── */
.pin-form {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0.65rem;
  margin-top: 1rem;
}

.pin-form input {
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 9px;
  padding: 0.6rem 0.8rem;
  font-size: 0.88rem;
  font-family: inherit;
  color: #0f172a;
  outline: none;
  transition: border-color 0.2s;
}

.pin-form input:focus { border-color: #0ea5e9; background: #fff; }

.btn-pin {
  grid-column: 1 / -1;
  background: #0f172a;
  color: #fff;
  border: none;
  border-radius: 10px;
  font-size: 0.88rem;
  font-weight: 700;
  padding: 0.7rem;
  cursor: pointer;
  transition: background 0.2s;
}

.btn-pin:hover { background: #1e293b; }

/* ── Bucket card ─────────────────────────────────────────────────────────── */
.bucket-card { flex: 1; }

.bucket-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.btn-clear {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.35rem 0.8rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.18s;
}

.btn-clear:hover { background: #dc2626; color: #fff; border-color: #dc2626; }

.bucket-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem 1rem;
  color: #94a3b8;
  font-size: 0.9rem;
  text-align: center;
}

.bucket-empty span { font-size: 2rem; }

.bucket-items { margin-top: 1rem; display: flex; flex-direction: column; gap: 0.65rem; }

.bucket-row {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  padding: 0.8rem 0.9rem;
}

.bucket-row-left { display: flex; gap: 0.7rem; flex: 1; min-width: 0; }

.bucket-num {
  width: 24px;
  height: 24px;
  background: #0f172a;
  color: #fff;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.bucket-info { flex: 1; min-width: 0; }
.bucket-name { font-size: 0.9rem; font-weight: 700; color: #0f172a; }
.bucket-loc  { font-size: 0.78rem; color: #64748b; margin-top: 0.1rem; }

.bucket-note {
  width: 100%;
  margin-top: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  padding: 0.4rem 0.65rem;
  font-size: 0.8rem;
  font-family: inherit;
  color: #475569;
  background: #fff;
  outline: none;
}

.bucket-note:focus { border-color: #0ea5e9; }

.btn-remove {
  background: none;
  border: 1px solid #e2e8f0;
  color: #94a3b8;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  cursor: pointer;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.18s;
}

.btn-remove:hover { background: #fef2f2; border-color: #fecaca; color: #dc2626; }

/* ── Publish card ────────────────────────────────────────────────────────── */
.publish-card { margin-bottom: 1.4rem; }

.publish-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.btn-publish {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: 700;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: opacity 0.2s, transform 0.15s;
}

.btn-publish:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-publish:not(:disabled):hover { opacity: 0.9; transform: translateY(-1px); }

.pub-form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.pub-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.pub-field label {
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
}

.pub-field input,
.pub-field textarea {
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.65rem 0.85rem;
  font-size: 0.9rem;
  font-family: inherit;
  color: #0f172a;
  outline: none;
  transition: border-color 0.2s;
  resize: vertical;
}

.pub-field input:focus,
.pub-field textarea:focus { border-color: #0ea5e9; background: #fff; }

.itinerary-share {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 14px;
  padding: 1rem;
}

.itinerary-share-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.itinerary-share-head label {
  display: block;
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
}

.itinerary-share-head p {
  margin: 0.25rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
}

.btn-manage-itineraries {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  background: #fff;
  border: 1px solid #cbd5e1;
  color: #334155;
  border-radius: 10px;
  padding: 0.6rem 0.9rem;
  font-size: 0.82rem;
  font-weight: 700;
}

.itinerary-select {
  width: 100%;
  background: #fff;
  border: 1.5px solid #dbe4ee;
  border-radius: 10px;
  padding: 0.7rem 0.8rem;
  font: inherit;
}

.itinerary-preview {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.itinerary-preview strong {
  color: #0f172a;
}

.itinerary-preview span {
  font-size: 0.82rem;
  color: #0369a1;
  font-weight: 700;
}

.itinerary-preview p {
  margin: 0.2rem 0 0;
  font-size: 0.84rem;
  color: #64748b;
}

/* ── Messages ────────────────────────────────────────────────────────────── */
.msg-error   { color: #b91c1c; font-size: 0.85rem; }
.msg-success { color: #059669; font-size: 0.9rem; font-weight: 600; }

/* ── Quotes grid ─────────────────────────────────────────────────────────── */
.quotes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.2rem; margin-top: 1.2rem; }

.quote-row {
  border: 1px solid #f1f5f9;
  border-radius: 16px;
  padding: 1.2rem;
  background: #fafbfe;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

.quote-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quote-meta-left { display: flex; align-items: center; gap: 0.6rem; }

.qbadge {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  text-transform: capitalize;
}

.qbadge.open   { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.qbadge.closed { background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; }

.q-locs { font-size: 0.82rem; font-weight: 600; color: #334155; }
.q-date { font-size: 0.75rem; color: #94a3b8; }

.q-loc-list {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.82rem;
  color: #475569;
  line-height: 1.7;
}

.q-details {
  display: flex;
  gap: 0.8rem;
  flex-wrap: wrap;
}

.q-details span {
  font-size: 0.78rem;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 0.2rem 0.55rem;
}

.q-note {
  font-size: 0.82rem;
  color: #64748b;
  font-style: italic;
  background: #f8fafc;
  border-left: 3px solid #e2e8f0;
  padding: 0.5rem 0.7rem;
  border-radius: 0 8px 8px 0;
}

.q-itinerary {
  display: flex;
  gap: 0.45rem;
  flex-wrap: wrap;
  align-items: center;
  font-size: 0.82rem;
  color: #334155;
}

.q-itinerary strong {
  color: #0369a1;
}

.q-responses { border-top: 1px solid #f1f5f9; padding-top: 0.7rem; }

.q-resp-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: #94a3b8; margin-bottom: 0.5rem; }

.q-resp-item {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  padding: 0.65rem 0.85rem;
  margin-bottom: 0.5rem;
}

.q-resp-name { font-size: 0.85rem; font-weight: 700; color: #0f172a; }
.q-resp-amt  { font-size: 0.85rem; color: #059669; font-weight: 700; margin-top: 0.15rem; }
.q-resp-msg  { font-size: 0.8rem; color: #64748b; margin-top: 0.2rem; }
.q-resp-itinerary {
  margin-top: 0.55rem;
  padding: 0.7rem 0.8rem;
  border-radius: 10px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}
.q-resp-itinerary span {
  display: block;
  margin-top: 0.2rem;
  font-size: 0.8rem;
  color: #166534;
}
.q-resp-itinerary p {
  margin: 0.35rem 0 0;
  font-size: 0.82rem;
  color: #166534;
}
.btn-save-proposal {
  margin-top: 0.55rem;
  border: none;
  background: #166534;
  color: #fff;
  border-radius: 999px;
  padding: 0.45rem 0.8rem;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-save-proposal:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.q-no-resp { font-size: 0.82rem; color: #94a3b8; font-style: italic; }

.q-actions { border-top: 1px solid #f1f5f9; padding-top: 0.7rem; }

.btn-remove-quote {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  font-size: 0.82rem;
  font-weight: 600;
  padding: 0.45rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.18s;
}

.btn-remove-quote:hover { background: #dc2626; color: #fff; border-color: #dc2626; }

.q-closed-tag {
  font-size: 0.8rem;
  color: #64748b;
  background: #f1f5f9;
  padding: 0.3rem 0.8rem;
  border-radius: 8px;
  font-weight: 600;
}

/* ── Responsive ──────────────────────────────────────────────────────────── */
@media (max-width: 900px) {
  .qb-hero-inner h1 { font-size: 1.8rem; }
  .qb-grid { grid-template-columns: 1fr; }
  .pub-form-grid { grid-template-columns: 1fr 1fr; }
  .qb-container { margin-top: -2.5rem; }
}

@media (max-width: 600px) {
  .qb-hero { padding: 3rem 1.2rem 5.5rem; }
  .qb-hero-inner h1 { font-size: 1.5rem; }
  .qb-container { padding: 0 1rem; }
  .qb-card { padding: 1.2rem; }
  .pub-form-grid { grid-template-columns: 1fr; }
  .pin-form { grid-template-columns: 1fr; }
  .publish-head,
  .itinerary-share-head { flex-direction: column; }
  .btn-publish { width: 100%; justify-content: center; }
}
</style>
