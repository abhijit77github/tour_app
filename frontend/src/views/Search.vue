<template>
  <div class="search-page">

    <!-- Hero -->
    <section class="hero">
      <div class="hero-bg"></div>
      <div class="hero-inner">
        <span class="hero-eyebrow">Discover &amp; Book</span>
        <h1>Find the right operator<br><span class="hero-accent">for your journey</span></h1>
        <p class="hero-sub">Search by operator name, destination, state, or country — then filter by tour or car service.</p>
      </div>
    </section>

    <!-- Search card (overlaps hero) -->
    <div class="container">
      <div class="search-card">

        <div class="search-row">
          <div class="search-field">
            <span class="field-icon">🏢</span>
            <div class="field-body">
              <label>Operator</label>
              <input
                type="text"
                v-model="searchParams.operator_name"
                placeholder="Himalayan Trails Co…"
              />
            </div>
          </div>

          <div class="field-sep"></div>

          <div class="search-field">
            <span class="field-icon">📍</span>
            <div class="field-body">
              <label>Destination</label>
              <input
                type="text"
                v-model="searchParams.area_name"
                @input="handleLocationInput"
                @focus="showLocationSuggestions = true"
                @blur="setTimeout(() => showLocationSuggestions = false, 200)"
                placeholder="Manali, Goa, Kerala…"
              />
              <div v-if="showLocationSuggestions && locationSuggestions.length" class="dropdown">
                <div v-for="s in locationSuggestions" :key="s" @click="selectLocation(s)" class="drop-item">{{ s }}</div>
              </div>
            </div>
          </div>

          <div class="field-sep"></div>

          <div class="search-field">
            <span class="field-icon">🏘️</span>
            <div class="field-body">
              <label>State</label>
              <input
                type="text"
                v-model="searchParams.state"
                @input="handleStateInput"
                @focus="showStateSuggestions = true"
                @blur="setTimeout(() => showStateSuggestions = false, 200)"
                placeholder="Himachal Pradesh…"
              />
              <div v-if="showStateSuggestions && stateSuggestions.length" class="dropdown">
                <div v-for="s in stateSuggestions" :key="s" @click="selectState(s)" class="drop-item">{{ s }}</div>
              </div>
            </div>
          </div>

          <div class="field-sep"></div>

          <div class="search-field">
            <span class="field-icon">🌍</span>
            <div class="field-body">
              <label>Country</label>
              <input
                type="text"
                v-model="searchParams.country"
                @input="handleCountryInput"
                @focus="showCountrySuggestions = true"
                @blur="setTimeout(() => showCountrySuggestions = false, 200)"
                placeholder="India…"
              />
              <div v-if="showCountrySuggestions && countrySuggestions.length" class="dropdown">
                <div v-for="s in countrySuggestions" :key="s" @click="selectCountry(s)" class="drop-item">{{ s }}</div>
              </div>
            </div>
          </div>

          <button class="btn-search" @click="handleSearch">
            <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
            Search
          </button>
        </div>

        <!-- Service type filter -->
        <div class="filter-bar">
          <div class="svc-toggle">
            <button :class="['svc-btn', { active: serviceFilter === 'all' }]" @click="setServiceFilter('all')">All</button>
            <button :class="['svc-btn', 'tour', { active: serviceFilter === 'tour' }]" @click="setServiceFilter('tour')">🗺️ Tours</button>
            <button :class="['svc-btn', 'car', { active: serviceFilter === 'car' }]" @click="setServiceFilter('car')">🚗 Car Services</button>
          </div>
          <div class="popular-row">
            <span class="pop-label">Popular:</span>
            <button v-for="dest in popularDestinations" :key="dest" class="pop-chip" @click="selectQuickFilter(dest)">{{ dest }}</button>
          </div>
        </div>

      </div><!-- /search-card -->

      <!-- Loading -->
      <div v-if="loading" class="state-box">
        <div class="loader-ring"></div>
        <p>Searching operators…</p>
      </div>

      <!-- Results -->
      <section v-else-if="operators.length" class="results">
        <div class="results-meta">
          <div class="results-count">
            <strong>{{ operators.length }}</strong> {{ operators.length === 1 ? 'operator' : 'operators' }} found
            <span v-if="searchMeta.promoted_count" class="promoted-count-badge">
              {{ searchMeta.promoted_count }} promoted
            </span>
            <span v-if="serviceFilter !== 'all'" class="active-filter-badge">
              {{ serviceFilter === 'car' ? '🚗 Car only' : '🗺️ Tours only' }}
              <button class="clear-filter" @click="setServiceFilter('all')">✕</button>
            </span>
          </div>
          <button v-if="searched" class="btn-clear" @click="resetSearch">Clear search</button>
        </div>

        <div class="cards-grid">
          <div v-for="op in operators" :key="op._id" :class="['op-card', { promoted: op.is_promoted }]">

            <div class="op-card-top">
              <div class="op-avatar">{{ (op.business_name || '?').charAt(0).toUpperCase() }}</div>
              <div class="op-head-info">
                <h3 class="op-name">{{ op.business_name }}</h3>
                <div v-if="op.is_promoted" class="promoted-inline-badge">
                  {{ op.promotion_context?.label || 'Promoted' }}
                </div>
                <div class="op-meta-row">
                  <span class="stars">★ {{ Number(op.average_rating || 0).toFixed(1) }}</span>
                  <span class="rev-count">{{ op.total_reviews || 0 }} reviews</span>
                  <span class="exp-pill" v-if="op.years_of_experience">{{ op.years_of_experience }}y exp</span>
                </div>
              </div>
              <div class="svc-badges">
                <span v-if="(op.service_types || ['tour']).includes('car')" class="sbadge car-b">🚗 Car</span>
                <span v-if="(op.service_types || ['tour']).includes('tour')" class="sbadge tour-b">🗺️ Tour</span>
              </div>
            </div>

            <p class="op-desc">{{ op.description || 'Professional operator with local expertise.' }}</p>
            <p v-if="op.is_promoted" class="promoted-caption">Featured for this searched location</p>

            <div class="op-specs">
              <div class="spec-row" v-if="(op.specializations || []).length">
                <span class="spec-label">Specializes in</span>
                <div class="spec-chips">
                  <span v-for="(s, i) in (op.specializations || []).slice(0, 3)" :key="i" class="spec-chip">{{ s }}</span>
                </div>
              </div>
              <div class="spec-row">
                <span class="spec-label">Serves</span>
                <div class="spec-chips">
                  <span v-for="(a, i) in (op.serving_areas || []).slice(0, 3)" :key="i" class="area-chip">
                    📍 {{ a.area_name }}<span v-if="a.state">, {{ a.state }}</span>
                  </span>
                  <span v-if="(op.serving_areas || []).length > 3" class="more-chip">+{{ op.serving_areas.length - 3 }}</span>
                </div>
              </div>
            </div>

            <div v-if="(op.service_types || []).includes('car') && (op.car_services || []).length" class="car-preview">
              <span class="car-preview-label">Vehicles</span>
              <div class="car-tags">
                <span v-for="(c, ci) in (op.car_services || []).slice(0, 3)" :key="ci" class="car-tag">
                  {{ c.vehicle_type }} · {{ c.seats }} seats
                  <span v-if="c.base_fare"> · ₹{{ c.base_fare }}</span>
                </span>
              </div>
            </div>

            <router-link :to="`/operator/${op._id}`" class="btn-view" @click.prevent="viewOperatorProfile(op)">View Profile →</router-link>

          </div>
        </div>
      </section>

      <!-- No results -->
      <div v-else-if="searched" class="state-box">
        <div class="state-icon">🔍</div>
        <h3>No operators found</h3>
        <p>Try a broader search, another operator name, or a different service type.</p>
        <button class="btn-ghost" @click="resetSearch">Clear &amp; try again</button>
      </div>

      <!-- Initial state -->
      <div v-else class="state-box initial">
        <div class="state-icon">✈️</div>
        <h3>Ready to explore?</h3>
        <p>Search by operator name or location to find the right match.</p>
      </div>

    </div><!-- /container -->
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'

const router = useRouter()

const searchParams = ref({
  operator_name: '',
  area_name: '',
  state: '',
  country: ''
})

const operators = ref([])
const loading = ref(false)
const searched = ref(false)
const serviceFilter = ref('all')
const searchMeta = ref({ promoted_count: 0, organic_count: 0 })

// Suggestion states
const showLocationSuggestions = ref(false)
const showStateSuggestions = ref(false)
const showCountrySuggestions = ref(false)

const locationSuggestions = ref([])
const stateSuggestions = ref([])
const countrySuggestions = ref([])

// Available data for suggestions
const allLocations = ref([])
const allStates = ref([])
const allCountries = ref([])

const popularDestinations = [
  'Manali',
  'Goa',
  'Kerala',
  'Rajasthan',
  'Himalayas',
  'Mumbai'
]

// Initialize all available locations from operators
const initializeSuggestions = async () => {
  try {
    // Fetch serving areas from operators (primary source)
    const response = await api.get('/operators/serving-areas')
    
    if (response.data.areas && response.data.areas.length > 0) {
      allLocations.value = response.data.areas
    }
    
    // Extract states and countries
    if (response.data.states && response.data.states.length > 0) {
      allStates.value = response.data.states
    }
    
    if (response.data.countries && response.data.countries.length > 0) {
      allCountries.value = response.data.countries
    }
    
    // If still no data from operators, try destinations from quotes
    if (allLocations.value.length === 0) {
      const destResponse = await api.get('/quotes/destinations')
      if (destResponse.data.destinations) {
        allLocations.value = destResponse.data.destinations
      }
      
      const statesSet = new Set()
      const countriesSet = new Set()
      
      if (destResponse.data.destinations_with_details) {
        destResponse.data.destinations_with_details.forEach(dest => {
          if (dest.state) statesSet.add(dest.state)
          if (dest.country) countriesSet.add(dest.country)
        })
      }
      
      allStates.value = Array.from(statesSet).sort()
      allCountries.value = Array.from(countriesSet).sort()
    }
    
    // Fallback to common locations if no data is returned
    if (allLocations.value.length === 0) {
      allLocations.value = [
        'Manali', 'Goa', 'Kerala', 'Rajasthan', 'Himalayas', 'Mumbai',
        'Delhi', 'Jaipur', 'Agra', 'Spiti', 'Ladakh', 'Ooty',
        'Cochin', 'Munnar', 'Darjeeling', 'Shimla'
      ]
    }
    
    if (allStates.value.length === 0) {
      allStates.value = [
        'Himachal Pradesh', 'Goa', 'Kerala', 'Rajasthan', 'Delhi',
        'Karnataka', 'Tamil Nadu', 'Uttarakhand', 'Maharashtra',
        'Assam', 'West Bengal', 'Punjab'
      ]
    }
    
    if (allCountries.value.length === 0) {
      allCountries.value = [
        'India', 'Nepal', 'Bhutan', 'Thailand', 'Vietnam',
        'Indonesia', 'Sri Lanka', 'Myanmar', 'Malaysia'
      ]
    }
  } catch (error) {
    console.error('Error initializing suggestions:', error)
    // Use fallback locations
    allLocations.value = [
      'Manali', 'Goa', 'Kerala', 'Rajasthan', 'Himalayas', 'Mumbai',
      'Delhi', 'Jaipur', 'Agra', 'Spiti', 'Ladakh', 'Ooty',
      'Cochin', 'Munnar', 'Darjeeling', 'Shimla'
    ]
    
    allStates.value = [
      'Himachal Pradesh', 'Goa', 'Kerala', 'Rajasthan', 'Delhi',
      'Karnataka', 'Tamil Nadu', 'Uttarakhand', 'Maharashtra',
      'Assam', 'West Bengal', 'Punjab'
    ]
    
    allCountries.value = [
      'India', 'Nepal', 'Bhutan', 'Thailand', 'Vietnam',
      'Indonesia', 'Sri Lanka', 'Myanmar', 'Malaysia'
    ]
  }
}

const handleLocationInput = () => {
  const query = searchParams.value.area_name.toLowerCase()
  if (query.length > 0) {
    locationSuggestions.value = allLocations.value.filter(loc =>
      loc.toLowerCase().includes(query)
    ).slice(0, 5)
    showLocationSuggestions.value = locationSuggestions.value.length > 0
  } else {
    locationSuggestions.value = []
    showLocationSuggestions.value = false
  }
}

const handleStateInput = () => {
  const query = searchParams.value.state.toLowerCase()
  if (query.length > 0) {
    stateSuggestions.value = allStates.value.filter(state =>
      state.toLowerCase().includes(query)
    ).slice(0, 5)
    showStateSuggestions.value = stateSuggestions.value.length > 0
  } else {
    stateSuggestions.value = []
    showStateSuggestions.value = false
  }
}

const handleCountryInput = () => {
  const query = searchParams.value.country.toLowerCase()
  if (query.length > 0) {
    countrySuggestions.value = allCountries.value.filter(country =>
      country.toLowerCase().includes(query)
    ).slice(0, 5)
    showCountrySuggestions.value = countrySuggestions.value.length > 0
  } else {
    countrySuggestions.value = []
    showCountrySuggestions.value = false
  }
}

const selectLocation = (location) => {
  searchParams.value.area_name = location
  showLocationSuggestions.value = false
  locationSuggestions.value = []
}

const selectState = (state) => {
  searchParams.value.state = state
  showStateSuggestions.value = false
  stateSuggestions.value = []
}

const selectCountry = (country) => {
  searchParams.value.country = country
  showCountrySuggestions.value = false
  countrySuggestions.value = []
}

const setServiceFilter = (type) => {
  serviceFilter.value = type
  if (searched.value) handleSearch()
}

const selectQuickFilter = (destination) => {
  searchParams.value.operator_name = ''
  searchParams.value.area_name = destination
  searchParams.value.state = ''
  searchParams.value.country = ''
  handleSearch()
}

const getPromotionSessionId = () => {
  const storageKey = 'promotionTrackingSessionId'
  let sessionId = localStorage.getItem(storageKey)
  if (!sessionId) {
    sessionId = window.crypto?.randomUUID?.() || `promo-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`
    localStorage.setItem(storageKey, sessionId)
  }
  return sessionId
}

const createTrackingRequestId = () => window.crypto?.randomUUID?.() || `req-${Date.now()}-${Math.random().toString(36).slice(2, 10)}`

const viewOperatorProfile = async (operator) => {
  if (operator?.is_promoted && operator?.promotion_context?.promotion_id) {
    try {
      await api.post(`/operators/promotions/${operator.promotion_context.promotion_id}/click`, {
        source: 'search',
        area_name: searchParams.value.area_name || null,
        state: searchParams.value.state || null,
        country: searchParams.value.country || null,
        service_type: serviceFilter.value === 'all' ? null : serviceFilter.value,
        session_id: getPromotionSessionId(),
        request_id: createTrackingRequestId()
      })
    } catch (error) {
      console.error('Failed to track promotion click:', error)
    }
  }

  router.push(`/operator/${operator._id}`)
}

const handleSearch = async () => {
  const params = {}
  if (searchParams.value.operator_name) params.operator_name = searchParams.value.operator_name
  if (searchParams.value.area_name) params.area_name = searchParams.value.area_name
  if (searchParams.value.state) params.state = searchParams.value.state
  if (searchParams.value.country) params.country = searchParams.value.country
  if (serviceFilter.value !== 'all') params.service_type = serviceFilter.value

  if (Object.keys(params).length === 0) {
    alert('Please enter at least one search criteria')
    return
  }

  loading.value = true
  searched.value = true

  try {
    const response = await api.get('/operators/search/location', { params })
    operators.value = response.data.operators
    searchMeta.value = {
      promoted_count: response.data.promoted_count || 0,
      organic_count: response.data.organic_count || 0
    }
  } catch (error) {
    console.error('Search failed:', error)
    alert('Search failed. Please try again.')
  } finally {
    loading.value = false
  }
}

const resetSearch = () => {
  searchParams.value = { operator_name: '', area_name: '', state: '', country: '' }
  operators.value = []
  searched.value = false
  serviceFilter.value = 'all'
  searchMeta.value = { promoted_count: 0, organic_count: 0 }
  locationSuggestions.value = []
  stateSuggestions.value = []
  countrySuggestions.value = []
}

// Initialize on mount
initializeSuggestions()
</script>

<style scoped>
/* ── Page shell ──────────────────────────────────────────────────────────── */
.search-page {
  min-height: 100vh;
  background: #f0f4f8;
  padding-bottom: 5rem;
  font-family: inherit;
}

/* ── Hero ────────────────────────────────────────────────────────────────── */
.hero {
  position: relative;
  background: linear-gradient(135deg, #0f172a 0%, #1a2d4a 55%, #0f4c75 100%);
  padding: 5rem 2rem 8rem;
  text-align: center;
  overflow: hidden;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 20% 50%, rgba(56,189,248,0.08), transparent 60%),
    radial-gradient(ellipse at 80% 20%, rgba(99,102,241,0.1), transparent 50%);
  pointer-events: none;
}

.hero-inner { position: relative; z-index: 1; }

.hero-eyebrow {
  display: inline-block;
  background: rgba(56,189,248,0.15);
  color: #7dd3fc;
  border: 1px solid rgba(56,189,248,0.25);
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  padding: 0.35rem 1rem;
  margin-bottom: 1.2rem;
}

.hero h1 {
  font-size: 3rem;
  font-weight: 800;
  color: #fff;
  line-height: 1.15;
  margin: 0 0 1rem;
}

.hero-accent { color: #38bdf8; }

.hero-sub {
  color: rgba(255,255,255,0.6);
  font-size: 1.05rem;
  max-width: 480px;
  margin: 0 auto;
}

/* ── Container ───────────────────────────────────────────────────────────── */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 1.5rem;
}

/* ── Search card (overlaps hero) ─────────────────────────────────────────── */
.search-card {
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 24px 64px rgba(15,23,42,0.14);
  padding: 1.6rem 2rem;
  margin-top: -4.5rem;
  position: relative;
  z-index: 10;
}

/* ── Search row ──────────────────────────────────────────────────────────── */
.search-row {
  display: flex;
  align-items: stretch;
  gap: 0;
  border: 1.5px solid #e2e8f0;
  border-radius: 14px;
  overflow: visible;
  background: #f8fafc;
}

.search-field {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex: 1;
  padding: 0.7rem 1rem;
  position: relative;
}

.field-sep {
  width: 1px;
  background: #e2e8f0;
  align-self: stretch;
  margin: 0.6rem 0;
}

.field-icon {
  font-size: 1.1rem;
  flex-shrink: 0;
}

.field-body {
  flex: 1;
  min-width: 0;
}

.field-body label {
  display: block;
  font-size: 0.68rem;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  margin-bottom: 0.15rem;
}

.field-body input {
  width: 100%;
  border: none;
  background: transparent;
  font-size: 0.93rem;
  color: #0f172a;
  outline: none;
  font-family: inherit;
}

.field-body input::placeholder { color: #cbd5e1; }

.btn-search {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: #fff;
  font-size: 0.9rem;
  font-weight: 700;
  border: none;
  border-radius: 11px;
  padding: 0 1.5rem;
  margin: 0.4rem;
  cursor: pointer;
  transition: opacity 0.2s, transform 0.15s;
  white-space: nowrap;
}

.btn-search:hover { opacity: 0.9; transform: translateY(-1px); }
.btn-search:active { transform: translateY(0); }

/* dropdown */
.dropdown {
  position: absolute;
  top: calc(100% + 4px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  box-shadow: 0 12px 32px rgba(15,23,42,0.1);
  z-index: 200;
  overflow: hidden;
}

.drop-item {
  padding: 0.75rem 1rem;
  font-size: 0.88rem;
  color: #334155;
  cursor: pointer;
  transition: background 0.15s;
}

.drop-item:hover { background: #f0f9ff; color: #0284c7; }

/* ── Filter bar ──────────────────────────────────────────────────────────── */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 1.2rem;
  margin-top: 1.1rem;
  flex-wrap: wrap;
}

.svc-toggle {
  display: inline-flex;
  background: #f1f5f9;
  border-radius: 10px;
  padding: 0.2rem;
  gap: 0.2rem;
}

.svc-btn {
  border: none;
  background: transparent;
  color: #64748b;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.4rem 0.9rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
}

.svc-btn.active { background: #fff; color: #0f172a; box-shadow: 0 1px 4px rgba(0,0,0,0.1); }
.svc-btn.tour.active { color: #047857; }
.svc-btn.car.active { color: #b91c1c; }

.popular-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.pop-label {
  font-size: 0.78rem;
  font-weight: 600;
  color: #94a3b8;
  white-space: nowrap;
}

.pop-chip {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  color: #475569;
  font-size: 0.78rem;
  font-weight: 600;
  padding: 0.28rem 0.75rem;
  border-radius: 999px;
  cursor: pointer;
  transition: all 0.18s;
}

.pop-chip:hover {
  border-color: #0284c7;
  color: #0284c7;
  background: #f0f9ff;
}

/* ── Results meta bar ────────────────────────────────────────────────────── */
.results {
  margin-top: 2.5rem;
}

.results-meta {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.4rem;
  gap: 1rem;
  flex-wrap: wrap;
}

.results-count {
  font-size: 0.95rem;
  color: #475569;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.6rem;
}

.results-count strong {
  font-size: 1.4rem;
  color: #0f172a;
}

.active-filter-badge {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  background: #eff6ff;
  border: 1px solid #bfdbfe;
  color: #1d4ed8;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.25rem 0.6rem 0.25rem 0.75rem;
  border-radius: 999px;
}

.promoted-count-badge {
  display: inline-flex;
  align-items: center;
  background: #fff7ed;
  border: 1px solid #fdba74;
  color: #c2410c;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.25rem 0.7rem;
  border-radius: 999px;
}

.clear-filter {
  border: none;
  background: none;
  color: #93c5fd;
  cursor: pointer;
  font-size: 0.8rem;
  padding: 0;
  line-height: 1;
  font-weight: 700;
}

.btn-clear {
  font-size: 0.82rem;
  font-weight: 600;
  color: #64748b;
  background: none;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 0.4rem 0.9rem;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-clear:hover { border-color: #94a3b8; color: #334155; }

/* ── Cards grid ──────────────────────────────────────────────────────────── */
.cards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: 1.4rem;
}

.op-card {
  background: #fff;
  border-radius: 18px;
  padding: 1.5rem;
  box-shadow: 0 2px 12px rgba(15,23,42,0.07);
  border: 1px solid #f1f5f9;
  display: flex;
  flex-direction: column;
  gap: 0.9rem;
  transition: box-shadow 0.25s, transform 0.2s;
}

.op-card.promoted {
  border-color: #fdba74;
  box-shadow: 0 10px 30px rgba(249, 115, 22, 0.12);
}

.op-card:hover {
  box-shadow: 0 12px 36px rgba(15,23,42,0.12);
  transform: translateY(-3px);
}

/* card top row */
.op-card-top {
  display: flex;
  align-items: flex-start;
  gap: 0.9rem;
}

.op-avatar {
  width: 46px;
  height: 46px;
  border-radius: 12px;
  background: linear-gradient(135deg, #0ea5e9, #6366f1);
  color: #fff;
  font-size: 1.4rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.op-head-info { flex: 1; min-width: 0; }

.op-name {
  font-size: 1.05rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.3rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.promoted-inline-badge {
  display: inline-flex;
  align-items: center;
  width: fit-content;
  background: #fff7ed;
  border: 1px solid #fdba74;
  color: #c2410c;
  font-size: 0.68rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  padding: 0.18rem 0.5rem;
  border-radius: 999px;
  margin: 0 0 0.45rem;
}

.op-meta-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.stars { color: #f59e0b; font-weight: 700; font-size: 0.85rem; }
.rev-count { font-size: 0.78rem; color: #94a3b8; }

.exp-pill {
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #bbf7d0;
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.15rem 0.55rem;
  border-radius: 999px;
}

/* service badges */
.svc-badges { display: flex; flex-direction: column; gap: 0.3rem; align-items: flex-end; flex-shrink: 0; }

.sbadge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.18rem 0.5rem;
  border-radius: 999px;
}

.car-b { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.tour-b { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }

/* description */
.op-desc {
  font-size: 0.87rem;
  color: #64748b;
  line-height: 1.55;
  margin: 0;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.promoted-caption {
  margin: -0.2rem 0 0;
  color: #c2410c;
  font-size: 0.76rem;
  font-weight: 700;
}

/* specs */
.op-specs { display: flex; flex-direction: column; gap: 0.6rem; }

.spec-row {
  display: flex;
  align-items: flex-start;
  gap: 0.6rem;
}

.spec-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: #94a3b8;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  white-space: nowrap;
  padding-top: 0.2rem;
  min-width: 70px;
}

.spec-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }

.spec-chip {
  background: #f0f9ff;
  color: #0369a1;
  border: 1px solid #bae6fd;
  font-size: 0.73rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
}

.area-chip {
  background: #fafafa;
  color: #475569;
  border: 1px solid #e2e8f0;
  font-size: 0.73rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
}

.more-chip {
  background: #f1f5f9;
  color: #64748b;
  border: 1px solid #e2e8f0;
  font-size: 0.73rem;
  font-weight: 600;
  padding: 0.2rem 0.6rem;
  border-radius: 6px;
}

/* car preview */
.car-preview {
  background: #fef7f7;
  border: 1px solid #fecaca;
  border-radius: 10px;
  padding: 0.65rem 0.85rem;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.car-preview-label {
  font-size: 0.72rem;
  font-weight: 700;
  color: #b91c1c;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  white-space: nowrap;
}

.car-tags { display: flex; flex-wrap: wrap; gap: 0.35rem; }

.car-tag {
  background: #fff;
  border: 1px solid #fecaca;
  color: #991b1b;
  font-size: 0.75rem;
  font-weight: 600;
  padding: 0.18rem 0.6rem;
  border-radius: 6px;
}

/* view button */
.btn-view {
  display: block;
  text-align: center;
  background: #0f172a;
  color: #fff;
  text-decoration: none;
  font-size: 0.85rem;
  font-weight: 700;
  padding: 0.7rem 1rem;
  border-radius: 10px;
  margin-top: auto;
  transition: background 0.2s, transform 0.15s;
}

.btn-view:hover { background: #1e293b; transform: translateY(-1px); }

/* ── State boxes ─────────────────────────────────────────────────────────── */
.state-box {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  text-align: center;
  padding: 5rem 2rem;
  gap: 0.8rem;
}

.state-box h3 {
  font-size: 1.4rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.state-box p {
  color: #64748b;
  font-size: 0.95rem;
  margin: 0;
}

.state-icon { font-size: 3.5rem; }

.loader-ring {
  width: 48px;
  height: 48px;
  border: 4px solid #e2e8f0;
  border-top-color: #0ea5e9;
  border-radius: 50%;
  animation: spin 0.9s linear infinite;
}

@keyframes spin { to { transform: rotate(360deg); } }

.btn-ghost {
  background: none;
  border: 1.5px solid #cbd5e1;
  color: #475569;
  font-size: 0.88rem;
  font-weight: 600;
  padding: 0.6rem 1.4rem;
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.2s;
  margin-top: 0.4rem;
}

.btn-ghost:hover { border-color: #94a3b8; color: #0f172a; }

.state-box.initial .state-icon { opacity: 0.6; }

/* ── Responsive ──────────────────────────────────────────────────────────── */
@media (max-width: 900px) {
  .hero h1 { font-size: 2.2rem; }
  .search-row { flex-direction: column; border: none; background: transparent; gap: 0.6rem; }
  .search-field { background: #f8fafc; border: 1.5px solid #e2e8f0; border-radius: 12px; }
  .field-sep { display: none; }
  .btn-search { margin: 0; width: 100%; justify-content: center; padding: 0.85rem; border-radius: 12px; }
  .filter-bar { flex-direction: column; align-items: flex-start; }
  .cards-grid { grid-template-columns: 1fr; }
}

@media (max-width: 600px) {
  .hero { padding: 3.5rem 1.2rem 6.5rem; }
  .hero h1 { font-size: 1.8rem; }
  .search-card { padding: 1.2rem; }
  .results-meta { flex-direction: column; align-items: flex-start; }
}
</style>
