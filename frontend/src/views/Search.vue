<template>
  <div class="search-page">
    <!-- Hero Section -->
    <section class="hero-section">
      <div class="hero-content">
        <h1>Find Your Perfect Tour Operator</h1>
        <p>Discover amazing destinations and experienced guides</p>
      </div>
    </section>

    <!-- Search Section -->
    <div class="container">
      <section class="search-section">
        <div class="search-card">
          <h2>Search Operators by Location</h2>
          
          <div class="search-form">
            <!-- Location Input -->
            <div class="form-group">
              <label>📍 Destination</label>
              <div class="search-input-wrapper">
                <input
                  type="text"
                  v-model="searchParams.area_name"
                  @input="handleLocationInput"
                  @focus="showLocationSuggestions = true"
                  @blur="setTimeout(() => showLocationSuggestions = false, 200)"
                  placeholder="Search destinations..."
                  class="search-input"
                />
                <div v-if="showLocationSuggestions && locationSuggestions.length > 0" class="suggestions-dropdown">
                  <div
                    v-for="suggestion in locationSuggestions"
                    :key="suggestion"
                    @click="selectLocation(suggestion)"
                    class="suggestion-item"
                  >
                    📍 {{ suggestion }}
                  </div>
                </div>
              </div>
            </div>

            <!-- State Input -->
            <div class="form-group">
              <label>🏘️ State/Province</label>
              <div class="search-input-wrapper">
                <input
                  type="text"
                  v-model="searchParams.state"
                  @input="handleStateInput"
                  @focus="showStateSuggestions = true"
                  @blur="setTimeout(() => showStateSuggestions = false, 200)"
                  placeholder="Search state..."
                  class="search-input"
                />
                <div v-if="showStateSuggestions && stateSuggestions.length > 0" class="suggestions-dropdown">
                  <div
                    v-for="suggestion in stateSuggestions"
                    :key="suggestion"
                    @click="selectState(suggestion)"
                    class="suggestion-item"
                  >
                    🏘️ {{ suggestion }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Country Input -->
            <div class="form-group">
              <label>🌍 Country</label>
              <div class="search-input-wrapper">
                <input
                  type="text"
                  v-model="searchParams.country"
                  @input="handleCountryInput"
                  @focus="showCountrySuggestions = true"
                  @blur="setTimeout(() => showCountrySuggestions = false, 200)"
                  placeholder="Search country..."
                  class="search-input"
                />
                <div v-if="showCountrySuggestions && countrySuggestions.length > 0" class="suggestions-dropdown">
                  <div
                    v-for="suggestion in countrySuggestions"
                    :key="suggestion"
                    @click="selectCountry(suggestion)"
                    class="suggestion-item"
                  >
                    🌍 {{ suggestion }}
                  </div>
                </div>
              </div>
            </div>

            <!-- Search Button -->
            <button @click="handleSearch" class="btn btn-search">
              <span>🔍 Search Operators</span>
            </button>
          </div>

          <!-- Quick Filters -->
          <div class="quick-filters">
            <p class="filter-label">Popular Destinations:</p>
            <div class="filter-chips">
              <button
                v-for="dest in popularDestinations"
                :key="dest"
                @click="selectQuickFilter(dest)"
                class="chip"
              >
                {{ dest }}
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Loading State -->
      <div v-if="loading" class="loading-container">
        <div class="spinner"></div>
        <p>Finding the perfect operators...</p>
      </div>

      <!-- Results Section -->
      <section v-else-if="operators.length > 0" class="results-section">
        <div class="results-header">
          <h2>Found {{ operators.length }} Operator{{ operators.length !== 1 ? 's' : '' }}</h2>
          <p class="results-subtitle">Choose from these amazing tour operators</p>
        </div>

        <div class="operator-grid">
          <div v-for="operator in operators" :key="operator._id" class="operator-card">
            <!-- Card Header -->
            <div class="card-header">
              <div class="operator-badge">
                <span class="rating-badge">⭐ {{ operator.average_rating.toFixed(1) }}</span>
                <span class="reviews-count">({{ operator.total_reviews }} reviews)</span>
              </div>
            </div>

            <!-- Card Content -->
            <div class="card-content">
              <h3 class="operator-name">{{ operator.business_name }}</h3>
              
              <p class="operator-description">{{ operator.description || 'Professional tour operator with years of experience' }}</p>

              <div class="operator-details">
                <div class="detail-item">
                  <span class="detail-label">Experience:</span>
                  <span class="detail-value">{{ operator.years_of_experience || 'N/A' }} years</span>
                </div>
                <div class="detail-item">
                  <span class="detail-label">Specializations:</span>
                  <div class="specializations">
                    <span
                      v-for="(spec, idx) in (operator.specializations || []).slice(0, 3)"
                      :key="idx"
                      class="spec-tag"
                    >
                      {{ spec }}
                    </span>
                  </div>
                </div>
              </div>

              <!-- Serving Areas -->
              <div class="serving-areas">
                <p class="areas-label">📍 Serving Areas:</p>
                <div class="area-chips">
                  <span
                    v-for="(area, idx) in operator.serving_areas.slice(0, 3)"
                    :key="idx"
                    class="area-chip"
                  >
                    {{ area.area_name }}, {{ area.state }}
                  </span>
                  <span v-if="operator.serving_areas.length > 3" class="area-chip more">
                    +{{ operator.serving_areas.length - 3 }} more
                  </span>
                </div>
              </div>

              <!-- Action Button -->
              <router-link :to="`/operator/${operator._id}`" class="btn btn-operator-view">
                View Full Profile →
              </router-link>
            </div>
          </div>
        </div>
      </section>

      <!-- No Results State -->
      <section v-else-if="searched" class="empty-state">
        <div class="empty-icon">🔍</div>
        <h3>No Operators Found</h3>
        <p>Try adjusting your search criteria or explore popular destinations</p>
        <button @click="resetSearch" class="btn btn-secondary">
          Clear Search & Try Again
        </button>
      </section>

      <!-- Initial State -->
      <section v-else class="initial-state">
        <div class="state-icon">✈️</div>
        <h3>Ready to explore?</h3>
        <p>Search for tour operators or browse popular destinations</p>
      </section>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'
import api from '../services/api'

const searchParams = ref({
  area_name: '',
  state: '',
  country: ''
})

const operators = ref([])
const loading = ref(false)
const searched = ref(false)

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

const selectQuickFilter = (destination) => {
  searchParams.value.area_name = destination
  searchParams.value.state = ''
  searchParams.value.country = ''
  handleSearch()
}

const handleSearch = async () => {
  const params = {}
  if (searchParams.value.area_name) params.area_name = searchParams.value.area_name
  if (searchParams.value.state) params.state = searchParams.value.state
  if (searchParams.value.country) params.country = searchParams.value.country

  if (Object.keys(params).length === 0) {
    alert('Please enter at least one search criteria')
    return
  }

  loading.value = true
  searched.value = true

  try {
    const response = await api.get('/operators/search/location', { params })
    operators.value = response.data.operators
  } catch (error) {
    console.error('Search failed:', error)
    alert('Search failed. Please try again.')
  } finally {
    loading.value = false
  }
}

const resetSearch = () => {
  searchParams.value = { area_name: '', state: '', country: '' }
  operators.value = []
  searched.value = false
  locationSuggestions.value = []
  stateSuggestions.value = []
  countrySuggestions.value = []
}

// Initialize on mount
initializeSuggestions()
</script>

<style scoped>
.search-page {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #e0f2fe 100%);
  min-height: 100vh;
  padding-bottom: 4rem;
}

/* Hero Section */
.hero-section {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #334155 100%);
  color: white;
  padding: 4rem 2rem;
  text-align: center;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.hero-content h1 {
  font-size: 2.8rem;
  font-weight: 800;
  margin: 0 0 1rem 0;
  line-height: 1.1;
}

.hero-content p {
  font-size: 1.3rem;
  opacity: 0.9;
  margin: 0;
  max-width: 600px;
  margin: 0 auto;
}

/* Container */
.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 2rem;
}

/* Search Section */
.search-section {
  margin: -3rem 2rem 3rem 2rem;
  position: relative;
  z-index: 10;
}

.search-card {
  background: white;
  border-radius: 20px;
  padding: 2.5rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
}

.search-card h2 {
  font-size: 1.8rem;
  color: #1f2d3d;
  margin: 0 0 2rem 0;
  font-weight: 700;
}

.search-form {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 1.5rem;
  align-items: end;
  margin-bottom: 2rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 600;
  color: #2d3748;
  margin-bottom: 0.6rem;
  font-size: 0.95rem;
}

.search-input-wrapper {
  position: relative;
}

.search-input {
  width: 100%;
  padding: 0.9rem 1.2rem;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  font-size: 0.95rem;
  transition: all 0.3s ease;
  font-family: inherit;
}

.search-input:focus {
  outline: none;
  border-color: #3b82f6;
  box-shadow: 0 0 0 3px rgba(59, 130, 246, 0.1);
}

.suggestions-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: white;
  border: 2px solid #e2e8f0;
  border-top: none;
  border-radius: 0 0 12px 12px;
  max-height: 200px;
  overflow-y: auto;
  z-index: 100;
}

.suggestion-item {
  padding: 0.8rem 1.2rem;
  cursor: pointer;
  border-bottom: 1px solid #f1f5f9;
  transition: all 0.2s ease;
  color: #2d3748;
}

.suggestion-item:hover {
  background: #f0f9ff;
  color: #0284c7;
  padding-left: 1.5rem;
}

.suggestion-item:last-child {
  border-bottom: none;
}

.btn-search {
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  border: none;
  padding: 0.9rem 2rem;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
  font-size: 0.95rem;
  white-space: nowrap;
}

.btn-search:hover {
  transform: translateY(-2px);
  box-shadow: 0 10px 20px rgba(59, 130, 246, 0.3);
}

.btn-search:active {
  transform: translateY(0);
}

/* Quick Filters */
.quick-filters {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 1px solid #e2e8f0;
}

.filter-label {
  margin: 0 0 1rem 0;
  color: #5b6b8a;
  font-weight: 600;
  font-size: 0.9rem;
}

.filter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.8rem;
}

.chip {
  background: linear-gradient(135deg, #f0f9ff, #f8fbfe);
  border: 2px solid #0284c7;
  color: #0284c7;
  padding: 0.6rem 1.2rem;
  border-radius: 999px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s ease;
  font-size: 0.85rem;
}

.chip:hover {
  background: #0284c7;
  color: white;
  transform: translateY(-2px);
}

/* Results Section */
.results-section {
  margin: 3rem 0;
}

.results-header {
  margin-bottom: 2.5rem;
  text-align: center;
}

.results-header h2 {
  font-size: 2rem;
  color: #1f2d3d;
  margin: 0 0 0.5rem 0;
}

.results-subtitle {
  color: #5b6b8a;
  margin: 0;
  font-size: 1.05rem;
}

.operator-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 2rem;
}

.operator-card {
  background: white;
  border-radius: 15px;
  overflow: hidden;
  box-shadow: 0 4px 15px rgba(0, 0, 0, 0.08);
  transition: all 0.3s ease;
  border-left: 5px solid #0284c7;
}

.operator-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 15px 40px rgba(0, 0, 0, 0.12);
}

.card-header {
  background: linear-gradient(135deg, #0f172a, #1e293b);
  color: white;
  padding: 1.2rem;
}

.operator-badge {
  display: flex;
  align-items: center;
  gap: 0.8rem;
}

.rating-badge {
  font-size: 1.2rem;
  font-weight: 700;
}

.reviews-count {
  font-size: 0.9rem;
  opacity: 0.9;
}

.card-content {
  padding: 1.8rem;
}

.operator-name {
  font-size: 1.4rem;
  color: #1f2d3d;
  margin: 0 0 0.8rem 0;
  font-weight: 700;
}

.operator-description {
  color: #5b6b8a;
  margin: 0 0 1.5rem 0;
  line-height: 1.6;
  font-size: 0.95rem;
}

.operator-details {
  background: #f8fafc;
  padding: 1rem;
  border-radius: 10px;
  margin-bottom: 1.5rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.8rem;
}

.detail-item:last-child {
  margin-bottom: 0;
}

.detail-label {
  font-weight: 600;
  color: #5b6b8a;
  font-size: 0.9rem;
}

.detail-value {
  color: #1f2d3d;
  font-weight: 600;
}

.specializations {
  display: flex;
  flex-wrap: wrap;
  gap: 0.4rem;
}

.spec-tag {
  background: #dbeafe;
  color: #0284c7;
  padding: 0.3rem 0.8rem;
  border-radius: 6px;
  font-size: 0.75rem;
  font-weight: 600;
}

.serving-areas {
  margin: 1.5rem 0;
}

.areas-label {
  color: #2d3748;
  font-weight: 600;
  margin: 0 0 0.8rem 0;
  font-size: 0.9rem;
}

.area-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.area-chip {
  background: #f0f9ff;
  color: #0284c7;
  padding: 0.5rem 0.9rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  border: 1px solid #0284c7;
}

.area-chip.more {
  background: #e0e7ff;
  color: #4f46e5;
  border-color: #4f46e5;
}

.btn-operator-view {
  display: block;
  width: 100%;
  background: linear-gradient(135deg, #3b82f6, #2563eb);
  color: white;
  text-decoration: none;
  padding: 0.9rem 1.5rem;
  border-radius: 10px;
  text-align: center;
  font-weight: 600;
  transition: all 0.3s ease;
  border: none;
  cursor: pointer;
}

.btn-operator-view:hover {
  background: linear-gradient(135deg, #2563eb, #1d4ed8);
  transform: translateY(-2px);
  box-shadow: 0 6px 15px rgba(37, 99, 235, 0.3);
}

/* Loading State */
.loading-container {
  text-align: center;
  padding: 4rem 2rem;
}

.spinner {
  width: 50px;
  height: 50px;
  border: 4px solid #e2e8f0;
  border-top-color: #3b82f6;
  border-radius: 50%;
  animation: spin 1s linear infinite;
  margin: 0 auto 1.5rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.loading-container p {
  color: #5b6b8a;
  font-size: 1.1rem;
}

/* Empty and Initial States */
.empty-state,
.initial-state {
  text-align: center;
  padding: 4rem 2rem;
}

.empty-icon,
.state-icon {
  font-size: 4rem;
  margin-bottom: 1.5rem;
}

.empty-state h3,
.initial-state h3 {
  font-size: 1.8rem;
  color: #1f2d3d;
  margin: 0 0 0.8rem 0;
  font-weight: 700;
}

.empty-state p,
.initial-state p {
  color: #5b6b8a;
  margin: 0 0 2rem 0;
  font-size: 1.05rem;
}

.btn-secondary {
  background: #e2e8f0;
  color: #1f2d3d;
  border: none;
  padding: 0.9rem 2rem;
  border-radius: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s ease;
}

.btn-secondary:hover {
  background: #cbd5e1;
  transform: translateY(-2px);
}

/* Responsive */
@media (max-width: 1024px) {
  .search-form {
    grid-template-columns: 1fr 1fr;
  }

  .btn-search {
    grid-column: 1 / -1;
  }

  .operator-grid {
    grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  }
}

@media (max-width: 768px) {
  .hero-content h1 {
    font-size: 2rem;
  }

  .search-card {
    padding: 1.5rem;
    margin: -2rem 0 2rem 0;
  }

  .search-form {
    grid-template-columns: 1fr;
    gap: 1rem;
  }

  .operator-grid {
    grid-template-columns: 1fr;
  }

  .filter-chips {
    justify-content: center;
  }

  .form-group label {
    font-size: 0.85rem;
  }
}
</style>
