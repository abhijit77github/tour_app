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
      <div class="filters-cluster">
        <label class="sort-group">
          <span>Sort</span>
          <select v-model="selectedSort" class="sort-select">
            <option v-for="option in sortOptions" :key="option.value" :value="option.value">
              {{ option.label }}
            </option>
          </select>
        </label>
        <label class="filter-select-group">
          <span>Location</span>
          <select v-model="selectedLocation" class="filter-select" :disabled="loadingFilterOptions">
            <option value="">All locations</option>
            <option v-for="option in filterOptions.locations" :key="option.value" :value="option.value">
              {{ option.label }}<template v-if="option.count"> ({{ option.count }})</template>
            </option>
          </select>
        </label>
        <label class="filter-select-group">
          <span>Budget</span>
          <select v-model="selectedBudgetBand" class="filter-select" :disabled="loadingFilterOptions">
            <option value="">All budgets</option>
            <option v-for="option in filterOptions.budgetBands" :key="option.value" :value="option.value">
              {{ option.label }}<template v-if="option.count"> ({{ option.count }})</template>
            </option>
          </select>
        </label>
        <label class="filter-select-group">
          <span>Travel window</span>
          <select v-model="selectedTravelWindow" class="filter-select" :disabled="loadingFilterOptions">
            <option value="">Any window</option>
            <option v-for="option in filterOptions.travelWindows" :key="option.value" :value="option.value">
              {{ option.label }}<template v-if="option.count"> ({{ option.count }})</template>
            </option>
          </select>
        </label>
        <button v-if="hasSecondaryFilters" type="button" class="filter-clear-btn" @click="clearSecondaryFilters">
          Clear filters
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
    <div v-else-if="visibleQuotes.length === 0" class="empty-state">
      <div class="empty-icon">📬</div>
      <h3>No quote requests found</h3>
      <p v-if="selectedFilter === 'all' && searchQuery">
        Try adjusting your search filters
      </p>
      <p v-else>
        When tourists request quotes for your areas, they'll appear here
      </p>
    </div>

    <!-- Quotes Workspace -->
    <div v-else class="quotes-workspace">
      <section :class="['queue-panel', `queue-panel-${queueDensity}`]">
        <div class="panel-head">
          <div>
            <p class="panel-kicker">Queue</p>
            <h2>Operator inbox</h2>
            <p class="panel-subcopy">{{ quoteRangeLabel }} · {{ visibleQuotes.length }} on this page</p>
          </div>
          <div class="density-toggle" role="group" aria-label="Queue density">
            <button
              type="button"
              :class="['density-option', { active: queueDensity === 'comfortable' }]"
              @click="setQueueDensity('comfortable')"
            >
              Comfortable
            </button>
            <button
              type="button"
              :class="['density-option', { active: queueDensity === 'compact' }]"
              @click="setQueueDensity('compact')"
            >
              Compact
            </button>
          </div>
        </div>

        <div class="queue-list">
          <article
            v-for="quote in visibleQuotes"
            :key="quote._id"
            :id="`quote-card-${quote._id}`"
            :class="[
              'queue-card',
              getQuoteClass(quote),
              {
                active: selectedQuote?._id === quote._id,
                'quote-card-focused': quote._id === focusedQuoteId,
              },
            ]"
            @click="selectQuote(quote)"
          >
            <div class="queue-card-top">
              <div class="queue-title-stack">
                <h3>{{ quote.tourist_name }}</h3>
                <p>{{ formatDate(quote.created_at) }}</p>
              </div>
              <div class="queue-chip-row">
                <span class="quote-status" :class="getStatusClass(quote)">{{ getStatusLabel(quote) }}</span>
                <span v-if="getUrgencyLabel(quote)" class="quote-urgency" :class="getUrgencyClass(quote)">{{ getUrgencyLabel(quote) }}</span>
              </div>
            </div>

            <div class="queue-meta-row">
              <span>{{ quote.locations.length }} stop{{ quote.locations.length > 1 ? 's' : '' }}</span>
              <span>{{ formatTravelers(quote.travelers) }}</span>
              <span>{{ formatBudget(quote.budget) }}</span>
            </div>

            <div class="queue-meta-row queue-meta-row-strong">
              <span>{{ quote.locations[0]?.name || 'Location pending' }}</span>
              <span>{{ formatTravelWindow(quote.travel_window) }}</span>
            </div>

            <p v-if="quote.notes" class="queue-preview">{{ quote.notes }}</p>

            <div class="queue-footer-row">
              <span v-if="quote.attached_itinerary_snapshot" class="mini-tag">Itinerary shared</span>
              <span v-if="quote.responses?.length" class="mini-tag mini-tag-info">{{ quote.responses.length }} response{{ quote.responses.length > 1 ? 's' : '' }}</span>
              <span v-if="quote._id === focusedQuoteId" class="mini-tag mini-tag-focus">Preview handoff</span>
            </div>
          </article>
        </div>

        <div class="pager-row">
          <span class="pager-copy">{{ quoteRangeLabel }}</span>
          <div class="pager-controls">
            <button class="btn btn-secondary" type="button" @click="previousPage" :disabled="currentPage === 1 || loading">Prev</button>
            <span>Page {{ currentPage }} / {{ totalPages }}</span>
            <button class="btn btn-secondary" type="button" @click="nextPage" :disabled="!quotePagination.hasMore || loading">Next</button>
          </div>
        </div>
      </section>

      <section v-if="selectedQuote" class="detail-panel">
        <div v-if="focusedQuoteId" class="focus-banner detail-focus-banner">
          <div>
            <strong>Focused request</strong>
            <p v-if="focusedQuote">This request was opened from a preview surface so it stays pinned while you review and respond.</p>
            <p v-else>Loading the selected request.</p>
          </div>
          <button type="button" class="btn btn-secondary" @click="clearFocusedQuote">Clear focus</button>
        </div>

        <div class="detail-head">
          <div class="detail-title-stack">
            <p class="panel-kicker">Details</p>
            <h2>{{ selectedQuote.tourist_name }}</h2>
            <div class="detail-chip-row">
              <span class="quote-status" :class="getStatusClass(selectedQuote)">{{ getStatusLabel(selectedQuote) }}</span>
              <span v-if="getUrgencyLabel(selectedQuote)" class="quote-urgency" :class="getUrgencyClass(selectedQuote)">{{ getUrgencyLabel(selectedQuote) }}</span>
            </div>
          </div>
          <p class="quote-date">{{ formatDate(selectedQuote.created_at) }}</p>
        </div>

        <div class="detail-grid">
          <section class="detail-section">
            <p class="section-label">Trip snapshot</p>
            <div class="tourist-grid compact-tourist-grid">
              <div class="tourist-item compact-pill">
                <span class="item-label">Travelers</span>
                <span class="item-value">{{ formatTravelers(selectedQuote.travelers) }}</span>
              </div>
              <div class="tourist-item compact-pill">
                <span class="item-label">Budget</span>
                <span class="item-value">{{ formatBudget(selectedQuote.budget) }}</span>
              </div>
              <div class="tourist-item compact-pill wide-pill">
                <span class="item-label">Window</span>
                <span class="item-value">{{ formatTravelWindow(selectedQuote.travel_window) }}</span>
              </div>
            </div>
          </section>

          <section class="detail-section">
            <p class="section-label">Locations</p>
            <div class="location-list compact-location-list">
              <div v-for="loc in selectedQuote.locations" :key="loc.name" class="location-item">
                <span class="location-icon">📍</span>
                <span class="location-name">{{ loc.name }}</span>
                <span v-if="isMatchingLocation(loc)" class="location-match">✓ Your Area</span>
              </div>
            </div>
          </section>

          <section v-if="selectedQuote.notes" class="detail-section preferences compact-note">
            <span class="pref-label">Request</span>
            <p class="pref-text">{{ selectedQuote.notes }}</p>
          </section>

          <section v-if="selectedQuote.preferences" class="detail-section preferences compact-note">
            <span class="pref-label">Preferences</span>
            <p class="pref-text">{{ selectedQuote.preferences }}</p>
          </section>

          <section v-if="selectedQuote.attached_itinerary_snapshot" class="detail-section preferences compact-note itinerary-note">
            <span class="pref-label">Shared itinerary</span>
            <p class="pref-text">
              {{ selectedQuote.attached_itinerary_snapshot.title }} ·
              {{ selectedQuote.attached_itinerary_snapshot.duration_days }} days ·
              {{ selectedQuote.attached_itinerary_snapshot.primary_location?.area_name || 'Custom route' }}
            </p>
          </section>

          <section v-if="selectedQuote.responses && selectedQuote.responses.length > 0" class="detail-section responses-section compact-section">
            <p class="section-label">Your Responses</p>
            <div v-for="(resp, idx) in selectedQuote.responses" :key="idx" class="response-item">
              <div class="response-header">
                <span class="response-operator">{{ resp.operator_name }}</span>
                <span class="response-date">{{ formatDate(resp.created_at) }}</span>
              </div>
              <p class="response-message">{{ resp.message }}</p>
              <div v-if="resp.proposed_itinerary_snapshot" class="response-itinerary">
                <strong>{{ resp.proposed_itinerary_snapshot.title }}</strong>
                <p>
                  {{ resp.proposed_itinerary_snapshot.duration_days }} days ·
                  {{ resp.proposed_itinerary_snapshot.primary_location?.area_name || 'Custom route' }}
                </p>
              </div>
              <p class="response-amount">Amount: <strong>{{ formatBudget(resp.amount) }}</strong></p>
            </div>
          </section>
        </div>

        <div class="card-actions detail-actions">
          <button v-if="!selectedQuote.responded_by_me" @click="openResponseForm(selectedQuote)" class="btn btn-primary">
            Send Quote
          </button>
          <button v-else class="btn btn-secondary" disabled>
            ✓ Responded
          </button>
          <a :href="getMapLink(selectedQuote)" target="_blank" class="btn btn-secondary">
            View Map
          </a>
        </div>
      </section>
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
          <div class="form-group itinerary-group">
            <label>Optional itinerary proposal</label>
            <select v-model="responseForm.selectedTemplateId" class="form-input">
              <option value="">No itinerary attached</option>
              <option v-for="item in operatorTemplates" :key="item._id" :value="item._id">
                {{ item.title }} · {{ item.duration_days }} days
              </option>
            </select>
            <p class="field-help">Choose one of your saved templates to share as-is or lightly customize for this tourist.</p>
          </div>
          <div v-if="selectedTemplate" class="proposal-editor">
            <div class="form-group">
              <label>Proposal title</label>
              <input v-model="responseForm.proposalTitle" type="text" class="form-input" />
            </div>
            <div class="form-group">
              <label>Proposal summary</label>
              <textarea v-model="responseForm.proposalSummary" class="form-textarea" rows="3"></textarea>
            </div>
            <div class="form-group">
              <label>Proposal notes</label>
              <textarea v-model="responseForm.proposalNotes" class="form-textarea" rows="3" placeholder="Optional custom note for this tourist"></textarea>
            </div>
            <div class="proposal-preview">
              <strong>{{ selectedTemplate.title }}</strong>
              <span>{{ selectedTemplate.primary_location?.area_name || 'Custom route' }} · {{ selectedTemplate.duration_days }} days</span>
              <p>{{ selectedTemplate.summary || 'Template summary not provided.' }}</p>
            </div>
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
import { ref, computed, onMounted, watch, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'
import {
  formatOperatorQuoteAge,
  formatOperatorQuoteBudget,
  formatOperatorQuoteTravelWindow,
  formatOperatorQuoteTravelers,
  getOperatorQuoteState,
  getOperatorQuoteUrgency,
} from '../utils/operatorQuotePresentation'

const route = useRoute()
const router = useRouter()
const QUEUE_DENSITY_STORAGE_KEY = 'operatorQuoteQueueDensity'
const quoteRequests = ref([])
const loading = ref(true)
const selectedFilter = ref('all')
const selectedSort = ref('newest')
const selectedLocation = ref('')
const selectedBudgetBand = ref('')
const selectedTravelWindow = ref('')
const searchQuery = ref('')
const debouncedSearchQuery = ref('')
const profile = ref(null)
const operatorTemplates = ref([])
const filterOptions = ref({ locations: [], budgetBands: [], travelWindows: [] })
const loadingFilterOptions = ref(false)
const selectedQuoteId = ref('')
const queueDensity = ref('comfortable')
const currentPage = ref(1)
const pageCursors = ref([null])
const PAGE_SIZE = 10
const quotePagination = ref({ totalItems: 0, hasMore: false, nextCursor: null })
const quoteSummary = ref({ totalItems: 0, newItems: 0, respondedItems: 0 })
const focusedQuoteId = ref(null)
const focusedQuote = ref(null)

const showResponseForm = ref(false)
const currentQuoteId = ref(null)
const responseForm = ref({
  amount: '',
  message: '',
  selectedTemplateId: '',
  proposalTitle: '',
  proposalSummary: '',
  proposalNotes: ''
})

const selectedTemplate = computed(() =>
  operatorTemplates.value.find((item) => item._id === responseForm.value.selectedTemplateId) || null
)

const hasSecondaryFilters = computed(() =>
  Boolean(selectedLocation.value || selectedBudgetBand.value || selectedTravelWindow.value)
)

const selectedQuote = computed(() => {
  if (selectedQuoteId.value) {
    const queuedQuote = visibleQuotes.value.find((quote) => quote._id === selectedQuoteId.value)
    if (queuedQuote) return queuedQuote
    if (focusedQuote.value?._id === selectedQuoteId.value) return focusedQuote.value
  }
  if (focusedQuote.value && visibleQuotes.value.some((quote) => quote._id === focusedQuote.value._id)) {
    return focusedQuote.value
  }
  return visibleQuotes.value[0] || focusedQuote.value || null
})

const sortOptions = [
  { value: 'newest', label: 'Newest first' },
  { value: 'unresponded_first', label: 'Unresponded first' },
  { value: 'highest_budget', label: 'Highest budget' },
  { value: 'travel_soonest', label: 'Travel soonest' },
]

const totalQuotes = computed(() => quoteSummary.value.totalItems || quotePagination.value.totalItems || quoteRequests.value.length)
const newQuotes = computed(() => 
  quoteSummary.value.newItems || (quoteSummary.value.totalItems === 0 ? quoteRequests.value.filter(q => !q.responded_by_me).length : 0)
)
const respondedQuotes = computed(() => 
  quoteSummary.value.respondedItems || (quoteSummary.value.totalItems === 0 ? quoteRequests.value.filter(q => q.responded_by_me).length : 0)
)

const visibleQuotes = computed(() => {
  if (!focusedQuote.value) return quoteRequests.value
  const remainingQuotes = quoteRequests.value.filter((quote) => quote._id !== focusedQuote.value._id)
  return [focusedQuote.value, ...remainingQuotes]
})

const totalPages = computed(() => Math.max(1, Math.ceil((quotePagination.value.totalItems || 0) / PAGE_SIZE)))
const quoteRangeLabel = computed(() => {
  const totalItems = quotePagination.value.totalItems || 0
  if (!totalItems || !quoteRequests.value.length) return '0-0 of 0'
  const start = (currentPage.value - 1) * PAGE_SIZE + 1
  const end = start + quoteRequests.value.length - 1
  return `${start}-${end} of ${totalItems}`
})

const getQuoteClass = (quote) => {
  if (getOperatorQuoteState(quote, profile.value?._id).key === 'responded') return 'responded'
  return 'new-quote'
}

const getStatusLabel = (quote) => getOperatorQuoteState(quote, profile.value?._id).label

const getStatusClass = (quote) => getOperatorQuoteState(quote, profile.value?._id).key === 'responded' ? 'status-responded' : 'status-new'

const getUrgency = (quote) => getOperatorQuoteUrgency(quote, profile.value?._id)

const getUrgencyLabel = (quote) => getUrgency(quote)?.label || null

const getUrgencyClass = (quote) => {
  const urgencyKey = getUrgency(quote)?.key
  if (urgencyKey === 'travel-soon') return 'urgency-travel-soon'
  if (urgencyKey === 'stale') return 'urgency-stale'
  if (urgencyKey === 'responded-recently') return 'urgency-responded-recently'
  if (urgencyKey === 'new') return 'urgency-new'
  return ''
}

const isMatchingLocation = (location) => {
  if (!profile.value?.serving_areas) return false
  return profile.value.serving_areas.some(area =>
    area.area_name.toLowerCase().includes(location.name.toLowerCase()) ||
    location.name.toLowerCase().includes(area.area_name.toLowerCase())
  )
}

const formatDate = (dateString) => formatOperatorQuoteAge(dateString)

const formatTravelWindow = (window) => formatOperatorQuoteTravelWindow(window)

const formatTravelers = (value) => formatOperatorQuoteTravelers(value)

const formatBudget = (value) => formatOperatorQuoteBudget(value)

const scrollSelectedQuoteIntoView = async () => {
  if (!selectedQuoteId.value) return
  await nextTick()
  const element = document.getElementById(`quote-card-${selectedQuoteId.value}`)
  element?.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

const syncSelectedQuote = async () => {
  const visibleIds = new Set(visibleQuotes.value.map((quote) => quote._id))
  const preferredId = focusedQuoteId.value || selectedQuoteId.value

  if (preferredId && (visibleIds.has(preferredId) || focusedQuote.value?._id === preferredId)) {
    selectedQuoteId.value = preferredId
    return
  }

  selectedQuoteId.value = visibleQuotes.value[0]?._id || focusedQuote.value?._id || ''
}

const selectQuote = async (quote) => {
  selectedQuoteId.value = quote._id
  await scrollSelectedQuoteIntoView()
}

const hydrateFocusedQuote = async () => {
  const quoteId = route.query.quoteId
  if (!quoteId || Array.isArray(quoteId)) {
    focusedQuoteId.value = null
    focusedQuote.value = null
    return
  }

  focusedQuoteId.value = quoteId
  selectedQuoteId.value = quoteId
  selectedFilter.value = 'all'
  selectedLocation.value = ''
  selectedBudgetBand.value = ''
  selectedTravelWindow.value = ''
  searchQuery.value = ''

  const currentPageQuote = quoteRequests.value.find((quote) => quote._id === quoteId)
  if (currentPageQuote) {
    focusedQuote.value = currentPageQuote
    await scrollSelectedQuoteIntoView()
    return
  }

  try {
    const response = await api.get(`/quotes/${quoteId}`)
    focusedQuote.value = response.data.quote
    await syncSelectedQuote()
    await scrollSelectedQuoteIntoView()
  } catch (error) {
    console.error('Failed to load focused quote:', error)
    focusedQuote.value = null
  }
}

const clearFocusedQuote = async () => {
  focusedQuoteId.value = null
  focusedQuote.value = null
  await syncSelectedQuote()
  const nextQuery = { ...route.query }
  delete nextQuery.quoteId
  await router.replace({ query: nextQuery })
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
  responseForm.value = {
    amount: '',
    message: '',
    selectedTemplateId: '',
    proposalTitle: '',
    proposalSummary: '',
    proposalNotes: ''
  }
}

const closeResponseForm = () => {
  showResponseForm.value = false
  currentQuoteId.value = null
  responseForm.value = {
    amount: '',
    message: '',
    selectedTemplateId: '',
    proposalTitle: '',
    proposalSummary: '',
    proposalNotes: ''
  }
}

const buildProposedItinerarySnapshot = () => {
  if (!selectedTemplate.value) return null
  return {
    title: responseForm.value.proposalTitle || selectedTemplate.value.title,
    summary: responseForm.value.proposalSummary || selectedTemplate.value.summary || null,
    primary_location: selectedTemplate.value.primary_location || null,
    route_locations: selectedTemplate.value.route_locations || [],
    duration_days: selectedTemplate.value.duration_days,
    trip_styles: selectedTemplate.value.trip_styles || [],
    travelers: null,
    budget_band: selectedTemplate.value.budget_band || null,
    notes: responseForm.value.proposalNotes || selectedTemplate.value.notes_for_planner || null,
    days: selectedTemplate.value.days || [],
    source_template_id: selectedTemplate.value._id,
    source_template_title: selectedTemplate.value.title
  }
}

const submitResponse = async () => {
  if (!currentQuoteId.value || !responseForm.value.amount || !responseForm.value.message) return

  try {
    await api.post(`/quotes/${currentQuoteId.value}/respond`, {
      amount: responseForm.value.amount,
      message: responseForm.value.message,
      proposed_itinerary_snapshot: buildProposedItinerarySnapshot()
    })
    
    // Reload quotes
    await loadQuotes(currentPage.value)
    closeResponseForm()
  } catch (error) {
    console.error('Failed to submit response:', error)
    alert('Failed to send quote. Please try again.')
  }
}

const resetPagination = () => {
  currentPage.value = 1
  pageCursors.value = [null]
}

const reloadQuotesFromFirstPage = async () => {
  resetPagination()
  await loadQuotes(1)
}

const buildQuoteParams = (page = currentPage.value) => {
  const quoteParams = {
    page_size: PAGE_SIZE,
    status_filter: selectedFilter.value,
    sort_mode: selectedSort.value,
  }
  if (selectedLocation.value) quoteParams.location = selectedLocation.value
  if (selectedBudgetBand.value) quoteParams.budget_band = selectedBudgetBand.value
  if (selectedTravelWindow.value) quoteParams.travel_window = selectedTravelWindow.value
  if (debouncedSearchQuery.value.trim()) {
    quoteParams.search = debouncedSearchQuery.value.trim()
  }
  const currentCursor = pageCursors.value[page - 1]
  if (currentCursor) quoteParams.cursor = currentCursor
  return quoteParams
}

const loadFilterOptions = async () => {
  loadingFilterOptions.value = true
  try {
    const params = { status_filter: selectedFilter.value }
    if (debouncedSearchQuery.value.trim()) params.search = debouncedSearchQuery.value.trim()
    const response = await api.get('/quotes/inbox/filter-options', { params })
    filterOptions.value = {
      locations: response.data.filters?.locations || [],
      budgetBands: response.data.filters?.budget_bands || [],
      travelWindows: response.data.filters?.travel_windows || [],
    }
  } catch (error) {
    console.error('Failed to load quote filter options:', error)
    filterOptions.value = { locations: [], budgetBands: [], travelWindows: [] }
  } finally {
    loadingFilterOptions.value = false
  }
}

let suppressSecondaryFilterReload = false

const clearSecondaryFilters = async () => {
  suppressSecondaryFilterReload = true
  selectedLocation.value = ''
  selectedBudgetBand.value = ''
  selectedTravelWindow.value = ''
  suppressSecondaryFilterReload = false
  await reloadQuotesFromFirstPage()
}

const setQueueDensity = (nextDensity) => {
  queueDensity.value = nextDensity === 'compact' ? 'compact' : 'comfortable'
}

const loadQuotes = async (page = currentPage.value) => {
  loading.value = true
  try {
    const [profileRes, quotesRes, templatesRes] = await Promise.all([
      api.get('/operators/profile/me'),
      api.get('/quotes/inbox', { params: buildQuoteParams(page) }),
      api.get('/itineraries/operator/templates', { params: { page_size: 50 } })
    ])
    profile.value = profileRes.data
    quoteRequests.value = quotesRes.data.quotes || []
    quoteSummary.value = {
      totalItems: quotesRes.data.summary?.total_items || quotesRes.data.pagination?.total_items || quoteRequests.value.length,
      newItems: quotesRes.data.summary?.new_items || 0,
      respondedItems: quotesRes.data.summary?.responded_items || 0,
    }
    quotePagination.value = {
      totalItems: quotesRes.data.pagination?.total_items || quoteRequests.value.length,
      hasMore: Boolean(quotesRes.data.pagination?.has_more),
      nextCursor: quotesRes.data.pagination?.next_cursor || null,
    }
    if (pageCursors.value.length === page) {
      pageCursors.value.push(quotePagination.value.nextCursor)
    } else {
      pageCursors.value[page] = quotePagination.value.nextCursor
    }
    pageCursors.value = pageCursors.value.slice(0, page + 1)
    currentPage.value = page
    operatorTemplates.value = (templatesRes.data.templates || []).filter((item) => item.status === 'published')
    await hydrateFocusedQuote()
    await syncSelectedQuote()
  } catch (error) {
    console.error('Failed to load quotes:', error)
  } finally {
    loading.value = false
  }
}

const previousPage = async () => {
  if (currentPage.value === 1 || loading.value) return
  await loadQuotes(currentPage.value - 1)
}

const nextPage = async () => {
  if (!quotePagination.value.hasMore || loading.value) return
  await loadQuotes(currentPage.value + 1)
}

onMounted(() => {
  try {
    const savedDensity = localStorage.getItem(QUEUE_DENSITY_STORAGE_KEY)
    if (savedDensity === 'compact' || savedDensity === 'comfortable') {
      queueDensity.value = savedDensity
    }
  } catch (error) {
    console.error('Failed to restore queue density preference:', error)
  }
  resetPagination()
  loadQuotes(1)
  loadFilterOptions()
})

watch(queueDensity, (value) => {
  try {
    localStorage.setItem(QUEUE_DENSITY_STORAGE_KEY, value)
  } catch (error) {
    console.error('Failed to persist queue density preference:', error)
  }
})

watch(() => route.query.quoteId, async () => {
  await hydrateFocusedQuote()
})

let searchDebounceTimer = null

watch(searchQuery, (value) => {
  if (searchDebounceTimer) {
    clearTimeout(searchDebounceTimer)
  }
  searchDebounceTimer = setTimeout(() => {
    debouncedSearchQuery.value = value
  }, 250)
})

watch(selectedFilter, async () => {
  await Promise.all([reloadQuotesFromFirstPage(), loadFilterOptions()])
})

watch(selectedSort, async () => {
  await reloadQuotesFromFirstPage()
})

watch([selectedLocation, selectedBudgetBand, selectedTravelWindow], async () => {
  if (suppressSecondaryFilterReload) return
  await reloadQuotesFromFirstPage()
})

watch(debouncedSearchQuery, async (value, oldValue) => {
  if (value === oldValue) return
  await Promise.all([reloadQuotesFromFirstPage(), loadFilterOptions()])
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

.filters-cluster {
  display: flex;
  gap: 0.9rem;
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

.sort-group {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  background: white;
  padding: 0.5rem 0.9rem;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  color: #475569;
  font-size: 0.9rem;
  font-weight: 600;
}

.filter-select-group {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  background: white;
  padding: 0.5rem 0.9rem;
  border-radius: 10px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  color: #475569;
  font-size: 0.9rem;
  font-weight: 600;
}

.sort-select {
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  padding: 0.55rem 0.8rem;
  background: #fff;
  color: #0f172a;
  font-size: 0.92rem;
}

.sort-select:focus {
  outline: none;
  border-color: #3b82f6;
}

.filter-select {
  border: 1px solid #dbe4ee;
  border-radius: 8px;
  padding: 0.55rem 0.8rem;
  background: #fff;
  color: #0f172a;
  font-size: 0.92rem;
  min-width: 170px;
}

.filter-select:focus {
  outline: none;
  border-color: #3b82f6;
}

.filter-clear-btn {
  border: 1px solid #cbd5e1;
  background: white;
  color: #334155;
  border-radius: 10px;
  padding: 0.72rem 1rem;
  font-weight: 600;
  cursor: pointer;
}

.filter-clear-btn:hover {
  background: #f8fafc;
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

.quotes-workspace {
  display: grid;
  grid-template-columns: minmax(320px, 0.92fr) minmax(0, 1.35fr);
  gap: 1rem;
  align-items: start;
}

.queue-panel,
.detail-panel {
  background: rgba(255, 255, 255, 0.9);
  border: 1px solid rgba(219, 228, 238, 0.9);
  border-radius: 20px;
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.07);
  backdrop-filter: blur(10px);
}

.queue-panel {
  padding: 1rem;
}

.detail-panel {
  padding: 1.1rem;
  position: sticky;
  top: 1rem;
  padding-right: 6.5rem;
  padding-bottom: 5.5rem;
}

.panel-head,
.detail-head,
.queue-card-top,
.card-actions {
  display: flex;
  justify-content: space-between;
  gap: 0.9rem;
}

.panel-kicker {
  margin: 0 0 0.35rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.75rem;
  font-weight: 700;
}

.panel-head h2,
.detail-head h2 {
  margin: 0;
  color: #0f172a;
}

.detail-head {
  align-items: flex-start;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.detail-title-stack {
  min-width: 0;
  flex: 1 1 320px;
}

.detail-title-stack h2 {
  overflow-wrap: anywhere;
}

.density-toggle {
  display: inline-flex;
  align-items: center;
  gap: 0;
  background: #f8fafc;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  padding: 0.1rem;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}

.density-option {
  border: none;
  background: transparent;
  color: #475569;
  font-size: 0.82rem;
  font-weight: 700;
  border-radius: 8px;
  padding: 0.38rem 0.78rem;
  min-width: 104px;
  cursor: pointer;
  transition: background 0.2s ease, color 0.2s ease, box-shadow 0.2s ease;
}

.density-option:hover {
  color: #0f172a;
  background: rgba(148, 163, 184, 0.08);
}

.density-option:focus-visible {
  outline: 2px solid #93c5fd;
  outline-offset: 1px;
}

.density-option.active {
  background: #1d4ed8;
  color: #ffffff;
  box-shadow: 0 4px 10px rgba(59, 130, 246, 0.2);
}

.panel-subcopy {
  margin: 0.35rem 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.queue-list,
.detail-grid {
  display: grid;
  gap: 0.85rem;
}

.queue-list {
  margin-top: 1rem;
}

.queue-panel-compact .queue-list {
  gap: 0.55rem;
}

.queue-card {
  border-radius: 16px;
  padding: 1rem;
  border: 1px solid #dbe4ee;
  border-left: 5px solid #3b82f6;
  background: white;
  cursor: pointer;
  transition: all 0.25s ease;
}

.queue-card:hover {
  transform: translateY(-1px);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
}

.queue-panel-compact .queue-card {
  padding: 0.72rem 0.78rem;
  border-radius: 14px;
}

.queue-card.active {
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.12), 0 12px 24px rgba(15, 23, 42, 0.08);
}

.queue-card.responded {
  border-left-color: #10b981;
}

.queue-card.new-quote {
  border-left-color: #f59e0b;
}

.queue-title-stack h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
}

.queue-panel-compact .queue-title-stack h3 {
  font-size: 0.92rem;
}

.queue-title-stack p {
  margin: 0.3rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
}

.queue-panel-compact .queue-title-stack p {
  margin-top: 0.15rem;
  font-size: 0.78rem;
}

.queue-chip-row,
.detail-chip-row,
.queue-meta-row,
.queue-footer-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.queue-meta-row {
  margin-top: 0.75rem;
  color: #64748b;
  font-size: 0.88rem;
}

.detail-chip-row {
  margin-top: 0.75rem;
}

.queue-panel-compact .queue-meta-row {
  margin-top: 0.45rem;
  gap: 0.45rem 0.65rem;
  font-size: 0.8rem;
}

.queue-meta-row-strong {
  color: #334155;
  font-weight: 600;
}

.queue-preview {
  margin: 0.8rem 0 0;
  color: #475569;
  line-height: 1.45;
  font-size: 0.9rem;
}

.queue-panel-compact .queue-preview {
  display: none;
}

.queue-footer-row {
  margin-top: 0.85rem;
}

.queue-panel-compact .queue-footer-row {
  margin-top: 0.55rem;
}

.mini-tag {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.25rem 0.55rem;
  background: #eef2ff;
  color: #3730a3;
  font-size: 0.74rem;
  font-weight: 700;
}

.queue-panel-compact .mini-tag {
  font-size: 0.68rem;
  padding: 0.22rem 0.48rem;
}

.mini-tag-info {
  background: #ecfeff;
  color: #155e75;
}

.mini-tag-focus {
  background: #fff7ed;
  color: #c2410c;
}

.detail-section {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 0.95rem;
}

.detail-focus-banner {
  margin-bottom: 1rem;
}

.quotes-container {
  display: grid;
  gap: 1rem;
}

.focus-banner {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  background: #fff7ed;
  border: 1px solid #fdba74;
  color: #9a3412;
  border-radius: 15px;
  padding: 1rem 1.2rem;
}

.focus-banner p {
  margin: 0.3rem 0 0;
}

.pager-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.pager-copy {
  color: #64748b;
  font-size: 0.9rem;
}

.pager-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.quote-card {
  background: white;
  border-radius: 15px;
  padding: 1.1rem 1.2rem;
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

.quote-card-focused {
  border-color: #ea580c;
  box-shadow: 0 0 0 3px rgba(234, 88, 12, 0.15), 0 8px 24px rgba(0, 0, 0, 0.12);
}

.quote-card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 0.9rem;
  padding-bottom: 0.9rem;
  border-bottom: 1px solid #f1f5f9;
}

.quote-info {
  display: flex;
  align-items: flex-start;
  gap: 0.65rem;
}

.quote-info-stack {
  flex: 1;
  flex-direction: column;
}

.quote-title-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.quote-subline {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
  color: #64748b;
  font-size: 0.88rem;
}

.quote-info h3 {
  margin: 0;
  font-size: 1rem;
  color: #333;
}

.quote-status {
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.quote-urgency {
  padding: 0.35rem 0.75rem;
  border-radius: 999px;
  font-size: 0.78rem;
  font-weight: 700;
  letter-spacing: 0.01em;
}

.status-new {
  background: #fef3c7;
  color: #92400e;
}

.status-responded {
  background: #d1fae5;
  color: #065f46;
}

.urgency-new {
  background: #dbeafe;
  color: #1d4ed8;
}

.urgency-travel-soon {
  background: #ffedd5;
  color: #c2410c;
}

.urgency-stale {
  background: #fee2e2;
  color: #b91c1c;
}

.urgency-responded-recently {
  background: #ede9fe;
  color: #6d28d9;
}

.quote-date {
  color: #999;
  font-size: 0.9rem;
  margin: 0;
  flex: 0 0 auto;
  text-align: right;
}

.quote-card-body {
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(0, 1fr);
  gap: 1rem;
  align-items: start;
}

.compact-section {
  margin-bottom: 0;
}

.section-label {
  font-weight: 600;
  color: #333;
  margin-bottom: 0.55rem;
  font-size: 0.82rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
}

.location-list {
  display: flex;
  flex-direction: row;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.location-item {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.55rem 0.7rem;
  background: #f8fafc;
  border-radius: 999px;
  font-size: 0.88rem;
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
  padding: 0.2rem 0.45rem;
  border-radius: 999px;
  font-size: 0.72rem;
  font-weight: 600;
}

.tourist-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.65rem;
  margin-bottom: 0.75rem;
}

.tourist-item {
  display: flex;
  gap: 0.35rem;
}

.compact-pill {
  flex-direction: column;
  padding: 0.65rem 0.75rem;
  background: #f8fafc;
  border-radius: 10px;
  border: 1px solid #e2e8f0;
}

.wide-pill {
  grid-column: 1 / -1;
}

.item-label {
  font-weight: 600;
  color: #666;
  min-width: 0;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.item-value {
  color: #333;
  font-size: 0.92rem;
}

.preferences {
  background: #f8fafc;
  padding: 0.75rem 0.85rem;
  border-radius: 8px;
  margin-top: 0.55rem;
}

.pref-label {
  font-weight: 600;
  color: #333;
}

.pref-text {
  margin: 0.35rem 0 0 0;
  color: #666;
  line-height: 1.4;
  font-size: 0.9rem;
}

.response-item {
  background: #f0f9ff;
  padding: 0.8rem 0.9rem;
  border-radius: 8px;
  margin-bottom: 0.55rem;
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
  margin: 0.4rem 0;
  line-height: 1.4;
  font-size: 0.9rem;
}

.response-amount {
  color: #0284c7;
  font-weight: 600;
  margin: 0.6rem 0 0 0;
}

.response-itinerary {
  background: #ecfeff;
  border: 1px solid #a5f3fc;
  border-radius: 8px;
  padding: 0.75rem;
  margin: 0.75rem 0;
}

.response-itinerary p {
  margin: 0.35rem 0 0;
  color: #155e75;
}

.card-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #f1f5f9;
}

.btn {
  flex: 0 0 auto;
  padding: 0.65rem 1rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.3s;
  font-size: 0.88rem;
  text-align: center;
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

.field-help {
  margin: 0.4rem 0 0;
  color: #64748b;
  font-size: 0.85rem;
}

.proposal-editor {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem;
  margin-bottom: 1rem;
}

.proposal-preview {
  background: white;
  border-radius: 8px;
  padding: 0.85rem;
  border: 1px solid #dbeafe;
}

.proposal-preview span {
  display: block;
  color: #475569;
  margin-top: 0.2rem;
}

.proposal-preview p {
  margin: 0.5rem 0 0;
  color: #64748b;
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
  .operator-quotes {
    padding: 1rem;
  }

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

  .quotes-workspace {
    grid-template-columns: 1fr;
  }

  .detail-panel {
    position: static;
  }

  .search-input {
    width: 100%;
  }

  .sort-group,
  .filter-select-group {
    width: 100%;
  }

  .tourist-grid {
    grid-template-columns: 1fr;
  }

  .quote-card-body {
    grid-template-columns: 1fr;
  }

  .quote-card {
    padding: 1.5rem;
  }

  .queue-card-top,
  .panel-head,
  .detail-head,
  .pager-row,
  .focus-banner {
    flex-direction: column;
    align-items: flex-start;
  }

  .density-toggle {
    width: 100%;
    justify-content: space-between;
  }

  .detail-panel {
    padding-right: 1.1rem;
    padding-bottom: 6.5rem;
  }

  .quote-date {
    text-align: left;
  }

  .card-actions {
    flex-direction: column;
  }
}
</style>
