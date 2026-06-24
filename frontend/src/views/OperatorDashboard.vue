<template>
  <div class="operator-dashboard">
    <div class="container">
      <h1>Operator Dashboard</h1>

      <section v-if="canReadBilling" class="billing-summary-card">
        <div class="billing-summary-head">
          <div>
            <p class="billing-kicker">Billing pulse</p>
            <h2>Recent credit movement</h2>
          </div>
          <router-link to="/operator/billing-analytics" class="billing-link">Open full analytics</router-link>
        </div>

        <div class="billing-summary-grid">
          <article class="billing-metric">
            <span>Credits remaining</span>
            <strong>{{ billingCurrentCredits }}</strong>
            <p>{{ billingCurrentPlan }}</p>
          </article>
          <article class="billing-metric">
            <span>7 day spend</span>
            <strong>₹{{ formatBillingMoney(billingTotals.spend_amount) }}</strong>
            <p>{{ billingTotals.billable_events }} billable events</p>
          </article>
          <article class="billing-metric">
            <span>Credits used</span>
            <strong>{{ billingTotals.credits_consumed }}</strong>
            <p>{{ billingTotals.non_billable_events }} tracked non-billable</p>
          </article>
        </div>

        <div class="billing-mini-row">
          <div v-if="billingMiniBars.length" class="billing-mini-chart" aria-label="Compact billing spend chart">
            <div v-for="point in billingMiniBars" :key="point.date" class="billing-mini-bar-wrap">
              <div class="billing-mini-bar-track">
                <div class="billing-mini-bar-fill" :style="{ height: `${point.height}%` }"></div>
              </div>
              <span>{{ point.label }}</span>
            </div>
          </div>
          <div v-else class="billing-empty">No recent billable spend yet.</div>

          <div class="billing-surfaces">
            <article v-for="row in billingTopSurfaces" :key="row.surface" class="billing-surface-chip">
              <strong>{{ humanizeBilling(row.surface) }}</strong>
              <span>₹{{ formatBillingMoney(row.spend_amount) }} · {{ row.credits_consumed }} credits</span>
            </article>
            <div v-if="!billingTopSurfaces.length" class="billing-empty compact">No billing surface data yet.</div>
          </div>
        </div>
      </section>

      <!-- Navigation Tabs -->
      <div class="dashboard-tabs">
        <button
          v-for="tab in tabs"
          :key="tab"
          type="button"
          @click="switchTab(tab)"
          :class="['tab-btn', { active: activeTab === tab }]"
        >
          {{ tab }}
        </button>
      </div>

      <!-- Profile Management -->
      <section v-if="activeTab === 'Profile'" class="tab-content">
        <div class="card">
          <h2>My Profile</h2>
          
          <div v-if="!editingProfile" class="profile-view">
            <div v-if="profile" class="profile-info">
              <div class="info-group">
                <label>Business Name:</label>
                <p>{{ profile.business_name }}</p>
              </div>
              <div class="info-group">
                <label>Description:</label>
                <p>{{ profile.description || 'No description' }}</p>
              </div>
              <div class="info-group">
                <label>Contact:</label>
                <p>{{ profile.contact_number }}</p>
              </div>
              <div class="info-group">
                <label>Years of Experience:</label>
                <p>{{ profile.years_of_experience || 'N/A' }}</p>
              </div>
              <div class="info-group">
                <label>Specializations:</label>
                <div class="tags">
                  <span v-for="spec in profile.specializations" :key="spec" class="tag">
                    {{ spec }}
                  </span>
                </div>
              </div>
              <div class="info-group">
                <label>Rating:</label>
                <p>⭐ {{ profile.average_rating.toFixed(1) }} ({{ profile.total_reviews }} reviews)</p>
              </div>
            </div>
            <button v-if="canUpdateProfile" type="button" @click="editingProfile = true" class="btn btn-primary">Edit Profile</button>
          </div>

          <form v-else @submit.prevent="updateProfile" class="profile-form">
            <div class="form-group">
              <label>Profile Image</label>
              <ImageUpload 
                v-model="profileForm.profile_image" 
                :multiple="false"
                upload-endpoint="/upload/profile-image"
              />
            </div>
            
            <div class="form-group">
              <label>Business Name</label>
              <input v-model="profileForm.business_name" type="text" required />
            </div>
            <div class="form-group">
              <label>Description</label>
              <textarea v-model="profileForm.description"></textarea>
            </div>
            <div class="form-group">
              <label>Contact Number</label>
              <input v-model="profileForm.contact_number" type="tel" required />
            </div>
            <div class="form-group">
              <label>Years of Experience</label>
              <input v-model.number="profileForm.years_of_experience" type="number" />
            </div>
            <div class="form-group">
              <label>Specializations (comma separated)</label>
              <input 
                v-model="specializationsInput" 
                type="text" 
                placeholder="Adventure, Family Tours, Budget Travel"
              />
            </div>
            <div v-if="profileError" class="error">{{ profileError }}</div>
            <div class="button-group">
              <button type="submit" class="btn btn-primary">Save Changes</button>
              <button type="button" @click="editingProfile = false" class="btn btn-secondary">Cancel</button>
            </div>
          </form>
        </div>
      </section>

      <!-- Serving Areas -->
      <section v-if="activeTab === 'Serving Areas'" class="tab-content">
        <div class="card">
          <h2>My Serving Areas</h2>
          
          <button type="button" @click="showAddServingArea = true" class="btn btn-primary mb-2">
            + Add Serving Area
          </button>

          <!-- Add/Edit Serving Area Form -->
          <form v-if="showAddServingArea" @submit.prevent="addServingArea" class="serving-area-form">
            <h3>{{ editingAreaIndex !== null ? 'Edit Serving Area' : 'Add New Serving Area' }}</h3>
            <div class="form-row">
              <div class="form-group">
                <label>Area Name</label>
                <input v-model="newServingArea.area_name" type="text" required />
              </div>
              <div class="form-group">
                <label>State</label>
                <input v-model="newServingArea.state" type="text" required />
              </div>
              <div class="form-group">
                <label>Country</label>
                <input v-model="newServingArea.country" type="text" required />
              </div>
            </div>
            
            <div class="form-group">
              <label>Description</label>
              <textarea v-model="newServingArea.description"></textarea>
            </div>

            <div class="form-group">
              <label>Area Images</label>
              <ImageUpload 
                v-model="newServingArea.images" 
                :multiple="true"
                upload-endpoint="/upload/location-images"
              />
            </div>

            <div class="form-group">
              <label>Location Coordinates (click on map to select)</label>
              <MapView 
                v-model="newServingArea.coordinates"
                :allow-selection="true"
                :show-coordinates="true"
                height="300px"
              />
            </div>

            <!-- Sub-locations -->
            <div class="sub-locations-section">
              <h4>Sub-locations</h4>
              <div 
                v-for="(sub, idx) in newServingArea.sub_locations" 
                :key="idx" 
                class="sub-location-item"
              >
                <input v-model="sub.name" placeholder="Location name" type="text" />
                <textarea v-model="sub.description" placeholder="Description"></textarea>
                
                <div class="sub-location-extras">
                  <div class="form-group-inline">
                    <label>
                      <input type="checkbox" v-model="sub.popular" />
                      Mark as Popular
                    </label>
                  </div>
                  
                  <div class="form-group">
                    <label>Images for this location</label>
                    <ImageUpload 
                      v-model="sub.images" 
                      :multiple="true"
                      upload-endpoint="/upload/location-images"
                    />
                  </div>

                  <div class="form-group">
                    <label>Coordinates (click on map)</label>
                    <MapView 
                      v-model="sub.coordinates"
                      :allow-selection="true"
                      :show-coordinates="true"
                      height="200px"
                    />
                  </div>
                </div>
                
                <button type="button" @click="newServingArea.sub_locations.splice(idx, 1)" class="btn btn-danger btn-sm">
                  Remove Sub-location
                </button>
              </div>
              <button 
                type="button" 
                @click="newServingArea.sub_locations.push({name: '', description: '', images: [], coordinates: null, popular: false})"
                class="btn btn-secondary btn-sm"
              >
                + Add Sub-location
              </button>
            </div>

            <div v-if="servingAreaError" class="error">{{ servingAreaError }}</div>
            
            <div class="form-actions">
              <button type="submit" class="btn btn-primary">
                {{ editingAreaIndex !== null ? 'Save Changes' : 'Add Serving Area' }}
              </button>
              <button type="button" @click="cancelEditServingArea" class="btn btn-secondary">
                Cancel
              </button>
            </div>
          </form>

          <!-- List of Serving Areas -->
          <div v-if="!showAddServingArea" class="serving-areas-list">
            <div v-if="profile && profile.serving_areas.length > 0">
              <div v-for="(area, idx) in profile.serving_areas" :key="idx" class="serving-area-card">
                <div class="card-header">
                  <div>
                    <h3>{{ area.area_name }}, {{ area.state }}</h3>
                    <p>{{ area.description }}</p>
                  </div>
                  <div class="card-actions">
                    <button type="button" @click="editServingArea(idx)" class="btn btn-sm btn-primary">Edit</button>
                    <button type="button" @click="deleteServingArea(idx)" class="btn btn-sm btn-danger">Delete</button>
                  </div>
                </div>
                <div class="sub-locations">
                  <strong>Locations:</strong>
                  <ul>
                    <li v-for="(sub, sidx) in area.sub_locations" :key="sidx">
                      {{ sub.name }} {{ sub.popular ? '(Popular)' : '' }}
                    </li>
                  </ul>
                </div>
              </div>
            </div>
            <div v-else class="empty-state">
              <p>No serving areas added yet. Create one to get started!</p>
            </div>
          </div>
        </div>
      </section>

      <!-- Quote Requests -->
      <section v-if="activeTab === 'Quote Requests'" class="tab-content">
        <div class="card">
          <h2>Quote Requests</h2>
          <p class="muted section-intro">Use this tab to preview incoming demand, then open the request in the main inbox to respond.</p>

          <div v-if="quoteLoading" class="loading-container">
            <p>Loading quote requests...</p>
          </div>

          <div v-else-if="quoteError" class="error">{{ quoteError }}</div>

          <div v-else-if="quoteRequests && quoteRequests.length" class="quotes-grid">
            <div v-for="quote in quoteRequests" :key="quote._id" class="quote-card">
              <div class="quote-header">
                <div>
                  <h3>{{ quote.tourist_name }}</h3>
                  <p class="muted">{{ formatQuoteAge(quote.created_at) }}</p>
                </div>
                <span :class="['status-badge', getQuoteStatusClass(quote)]">{{ getQuoteStatusLabel(quote) }}</span>
              </div>

              <div class="quote-body">
                <MapView
                  v-if="getQuoteLocations(quote).length"
                  :locations="getQuoteLocations(quote)"
                  :zoom="6"
                  height="200px"
                  :show-coordinates="false"
                />

                <ul class="location-list">
                  <li v-for="(loc, idx) in quote.locations" :key="idx">
                    {{ loc.name }} — {{ loc.state || 'State N/A' }}, {{ loc.country || 'Country N/A' }}
                  </li>
                </ul>

                <div class="quote-meta">
                  <p v-if="quote.travel_window"><strong>Travel window:</strong> {{ formatQuoteTravelWindow(quote.travel_window) }}</p>
                  <p v-if="quote.travelers"><strong>Travelers:</strong> {{ formatQuoteTravelers(quote.travelers) }}</p>
                  <p v-if="quote.budget"><strong>Budget:</strong> {{ formatQuoteBudget(quote.budget) }}</p>
                  <p v-if="quote.notes"><strong>Notes:</strong> {{ quote.notes }}</p>
                </div>

                <div v-if="quote.responses && quote.responses.length" class="responses">
                  <h4>Responses</h4>
                  <div v-for="(resp, ridx) in quote.responses" :key="ridx" class="response-item">
                    <p><strong>{{ resp.operator_name || 'Operator' }}</strong> quoted <span v-if="resp.amount">{{ formatQuoteBudget(resp.amount) }}</span></p>
                    <p class="muted">{{ resp.message || 'No message' }}</p>
                    <p class="muted">{{ formatQuoteAge(resp.created_at) }}</p>
                  </div>
                </div>

                <div class="quote-actions">
                  <button class="btn btn-primary btn-sm" @click="openQuoteInInbox(quote._id)">Open in inbox</button>
                  <button class="btn btn-secondary btn-sm" @click="startQuoteChat(quote)">Chat with tourist</button>
                </div>

                <div class="muted">{{ quote.responded_by_me ? 'You already responded to this request in the main inbox.' : 'Respond from the main inbox to keep the workflow consistent.' }}</div>
              </div>
            </div>
          </div>

          <div v-if="quoteRequests && quoteRequests.length" class="pager-row dashboard-pager">
            <span>{{ quoteRangeLabel }}</span>
            <div class="pager-controls">
              <button class="btn btn-secondary btn-sm" type="button" @click="previousQuotePage" :disabled="quotePage <= 1 || quoteLoading">Prev</button>
              <span>Page {{ quotePage }} / {{ quoteTotalPages }}</span>
              <button class="btn btn-secondary btn-sm" type="button" @click="nextQuotePage" :disabled="!quotePagination.hasMore || quoteLoading">Next</button>
            </div>
          </div>

          <div v-else class="empty-state">
            <p>No quote requests yet</p>
          </div>
        </div>
      </section>

      <!-- Bookings/Requests -->
      <section v-if="activeTab === 'Bookings'" class="tab-content">
        <div class="card">
          <h2>Booking Requests</h2>
          
          <div v-if="loading" class="loading-container">
            <p>Loading bookings...</p>
          </div>

          <div v-else-if="bookings && bookings.length > 0">
            <!-- Filter Section -->
            <div class="filter-section">
              <button 
                v-for="status in bookingStatuses" 
                :key="status"
                :class="['filter-btn', { active: bookingFilter === status }]"
                @click="bookingFilter = status"
              >
                {{ formatStatus(status) }}
                <span class="count">{{ getBookingCountByStatus(status) }}</span>
              </button>
            </div>

            <!-- Bookings List -->
            <div class="bookings-list">
              <div v-for="booking in filteredBookings" :key="booking._id" class="booking-card">
                <div class="booking-header">
                  <h3>Booking Request</h3>
                  <span :class="['status-badge', 'status-' + booking.booking_status.status]">
                    {{ booking.booking_status.status }}
                  </span>
                </div>
                
                <div class="booking-details">
                  <div class="info-group">
                    <label>Location:</label>
                    <p>{{ booking.cart.area_name }}, {{ booking.cart.state }}</p>
                  </div>
                  
                  <div class="info-group">
                    <label>Selected Items:</label>
                    <ul class="items-list">
                      <li v-for="(item, idx) in booking.cart.items" :key="idx">
                        {{ item.sub_location_name }} - 
                        <span :class="{ 'text-green': item.selected, 'text-red': !item.selected }">
                          {{ item.selected ? 'Selected' : 'Excluded' }}
                        </span>
                      </li>
                    </ul>
                  </div>

                  <div v-if="booking.estimated_cost" class="info-group">
                    <label>Estimated Cost:</label>
                    <p>${{ booking.estimated_cost }}</p>
                  </div>

                  <div class="info-group">
                    <label>Requested:</label>
                    <p>{{ new Date(booking.created_at).toLocaleDateString() }}</p>
                  </div>
                </div>

                <div class="booking-actions">
                  <button 
                    v-if="booking.booking_status.status === 'pending'"
                    @click="updateBookingStatus(booking._id, 'confirmed')"
                    :disabled="bookingUpdating[booking._id]"
                    class="btn btn-success btn-sm"
                  >
                    {{ bookingUpdating[booking._id] ? '...' : 'Confirm' }}
                  </button>
                  <button 
                    v-if="booking.booking_status.status === 'confirmed'"
                    @click="updateBookingStatus(booking._id, 'completed')"
                    :disabled="bookingUpdating[booking._id]"
                    class="btn btn-info btn-sm"
                  >
                    {{ bookingUpdating[booking._id] ? '...' : 'Mark Completed' }}
                  </button>
                  <button 
                    v-if="['pending', 'confirmed'].includes(booking.booking_status.status)"
                    @click="cancelBookingRequest(booking._id)"
                    :disabled="bookingUpdating[booking._id]"
                    class="btn btn-danger btn-sm"
                  >
                    {{ bookingUpdating[booking._id] ? '...' : 'Cancel' }}
                  </button>
                  <button @click="startChat(booking.tourist_id)" class="btn btn-warning btn-sm">
                    💬 Chat
                  </button>
                </div>
              </div>
            </div>
            <div class="pager-row dashboard-pager">
              <span>{{ bookingRangeLabel }}</span>
              <div class="pager-controls">
                <button class="btn btn-secondary btn-sm" type="button" @click="previousBookingPage" :disabled="bookingPage <= 1 || loading">Prev</button>
                <span>Page {{ bookingPage }} / {{ bookingTotalPages }}</span>
                <button class="btn btn-secondary btn-sm" type="button" @click="nextBookingPage" :disabled="!bookingPagination.hasMore || loading">Next</button>
              </div>
            </div>
          </div>

          <div v-else class="empty-state">
            <p>No booking requests yet</p>
          </div>
        </div>
      </section>

      <!-- Reviews & Ratings -->
      <section v-if="activeTab === 'Reviews'" class="tab-content">
        <div class="card">
          <h2>Your Reviews</h2>
          
          <div v-if="reviews && reviews.length > 0" class="reviews-list">
            <div v-for="review in reviews" :key="review._id" class="review-card">
              <div class="review-header">
                <div>
                  <h4>{{ review.tourist_name }}</h4>
                  <span class="rating">⭐ {{ review.rating }} / 5</span>
                </div>
                <p class="date">{{ new Date(review.created_at).toLocaleDateString() }}</p>
              </div>
              
              <p class="review-text">{{ review.review || 'No comment' }}</p>
              
              <div v-if="review.categories" class="categories">
                <div v-for="(value, cat) in review.categories" :key="cat" class="category">
                  <span>{{ cat }}:</span>
                  <span class="cat-rating">⭐ {{ value }}/5</span>
                </div>
              </div>
            </div>
          </div>

          <div v-if="reviews && reviews.length > 0" class="pager-row dashboard-pager">
            <span>{{ reviewRangeLabel }}</span>
            <div class="pager-controls">
              <button class="btn btn-secondary btn-sm" type="button" @click="previousReviewPage" :disabled="reviewPage <= 1 || loading">Prev</button>
              <span>Page {{ reviewPage }} / {{ reviewTotalPages }}</span>
              <button class="btn btn-secondary btn-sm" type="button" @click="nextReviewPage" :disabled="!reviewPagination.hasMore || loading">Next</button>
            </div>
          </div>

          <div v-else class="empty-state">
            <p>No reviews yet</p>
          </div>
        </div>
      </section>

      <!-- Statistics -->
      <section v-if="activeTab === 'Statistics'" class="tab-content">
        <div class="stats-grid">
          <div class="stat-card">
            <h3>Total Bookings</h3>
            <p class="stat-number">{{ bookingPagination.totalItems || 0 }}</p>
          </div>
          
          <div class="stat-card">
            <h3>Average Rating</h3>
            <p class="stat-number">{{ profile ? profile.average_rating.toFixed(1) : '0' }} ⭐</p>
          </div>
          
          <div class="stat-card">
            <h3>Total Reviews</h3>
            <p class="stat-number">{{ profile ? profile.total_reviews : 0 }}</p>
          </div>
          
          <div class="stat-card">
            <h3>Serving Areas</h3>
            <p class="stat-number">{{ profile ? profile.serving_areas.length : 0 }}</p>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed, watch } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useChatStore } from '../stores/chat'
import { useAccessStore } from '../stores/access'
import api from '../services/api'
import ImageUpload from '../components/ImageUpload.vue'
import MapView from '../components/MapView.vue'
import {
  buildOperatorQuoteRoute,
  formatOperatorQuoteAge,
  formatOperatorQuoteBudget,
  formatOperatorQuoteTravelWindow,
  formatOperatorQuoteTravelers,
  getOperatorQuoteState,
} from '../utils/operatorQuotePresentation'

export default {
  name: 'OperatorDashboard',
  components: {
    ImageUpload,
    MapView
  },
  setup() {
    const authStore = useAuthStore()
    const chatStore = useChatStore()
    const accessStore = useAccessStore()
    const router = useRouter()
    
    const tabs = computed(() => {
      const availableTabs = ['Profile']
      if (accessStore.hasOperatorPermission('operator.serving_areas.manage')) {
        availableTabs.push('Serving Areas')
      }
      if (accessStore.hasOperatorPermission('operator.quotes.read')) {
        availableTabs.push('Quote Requests')
      }
      availableTabs.push('Bookings', 'Reviews')
      if (accessStore.hasOperatorPermission('operator.analytics.read')) {
        availableTabs.push('Statistics')
      }
      return availableTabs
    })
    const activeTab = ref('Profile')
    
    const profile = ref(null)
    const bookings = ref([])
    const reviews = ref([])
    const loading = ref(false)
    const billingPlanState = ref(null)
    const billingAnalytics = ref(null)
    const quoteRequests = ref([])
    const quoteLoading = ref(false)
    const quoteError = ref(null)
    const quotePage = ref(1)
    const quoteCursors = ref([null])
    const quotePagination = ref({ totalItems: 0, hasMore: false, nextCursor: null })
    const canReadBilling = computed(() => accessStore.hasOperatorPermission('operator.billing.read'))
    const canReadQuotes = computed(() => accessStore.hasOperatorPermission('operator.quotes.read'))
    const canUpdateProfile = computed(() => accessStore.hasOperatorPermission('operator.profile.update'))
    
    // Booking filter and management
    const bookingFilter = ref('all')
    const bookingStatuses = ['all', 'pending', 'confirmed', 'completed', 'cancelled']
    const bookingUpdating = ref({})
    const bookingStatusCounts = ref({ all: 0, pending: 0, confirmed: 0, completed: 0, cancelled: 0 })
    const bookingPage = ref(1)
    const bookingCursors = ref([null])
    const bookingPagination = ref({ totalItems: 0, hasMore: false, nextCursor: null })
    const reviewPage = ref(1)
    const reviewCursors = ref([null])
    const reviewPagination = ref({ totalItems: 0, hasMore: false, nextCursor: null })
    const PAGE_SIZE = 8
    
    // Profile editing
    const editingProfile = ref(false)
    const profileForm = ref({
      business_name: '',
      description: '',
      contact_number: '',
      years_of_experience: null,
      specializations: []
    })
    const specializationsInput = ref('')
    const profileError = ref(null)
    
    // Serving areas
    const showAddServingArea = ref(false)
    const editingAreaIndex = ref(null)
    const servingAreaError = ref(null)
    const newServingArea = ref({
      area_name: '',
      state: '',
      country: '',
      description: '',
      images: [],
      coordinates: null,
      sub_locations: []
    })
    
    const resetServingAreaForm = () => {
      newServingArea.value = {
        area_name: '',
        state: '',
        country: '',
        description: '',
        images: [],
        coordinates: null,
        sub_locations: []
      }
      editingAreaIndex.value = null
      servingAreaError.value = null
    }

    const switchTab = (tab) => {
      // Update active tab and reset any open forms to avoid unintended submits
      activeTab.value = tab
      // Close and reset serving area form state
      showAddServingArea.value = false
      resetServingAreaForm()
      // Close profile edit if open
      editingProfile.value = false
      profileError.value = null
    }

    const totalPagesFor = (pagination) => Math.max(1, Math.ceil((pagination?.totalItems || 0) / PAGE_SIZE))

    const rangeLabelFor = (pagination, page, currentCount) => {
      const totalItems = pagination?.totalItems || 0
      if (!totalItems || !currentCount) return '0-0 of 0'
      const start = (page - 1) * PAGE_SIZE + 1
      return `${start}-${start + currentCount - 1} of ${totalItems}`
    }

    const syncCursor = (cursorRef, page, nextCursor) => {
      if (cursorRef.value.length === page) {
        cursorRef.value.push(nextCursor)
      } else {
        cursorRef.value[page] = nextCursor
      }
      cursorRef.value = cursorRef.value.slice(0, page + 1)
    }

    const quoteTotalPages = computed(() => totalPagesFor(quotePagination.value))
    const bookingTotalPages = computed(() => totalPagesFor(bookingPagination.value))
    const reviewTotalPages = computed(() => totalPagesFor(reviewPagination.value))
    const quoteRangeLabel = computed(() => rangeLabelFor(quotePagination.value, quotePage.value, quoteRequests.value.length))
    const bookingRangeLabel = computed(() => rangeLabelFor(bookingPagination.value, bookingPage.value, bookings.value.length))
    const reviewRangeLabel = computed(() => rangeLabelFor(reviewPagination.value, reviewPage.value, reviews.value.length))

    const loadQuoteRequests = async () => {
      if (!canReadQuotes.value) {
        quoteRequests.value = []
        quoteError.value = null
        return
      }
      quoteLoading.value = true
      quoteError.value = null
      try {
        const res = await api.get('/quotes/inbox', { params: { page_size: PAGE_SIZE, cursor: quoteCursors.value[quotePage.value - 1] || undefined } })
        quoteRequests.value = res.data.quotes || []
        quotePagination.value = {
          totalItems: res.data.pagination?.total_items || quoteRequests.value.length,
          hasMore: Boolean(res.data.pagination?.has_more),
          nextCursor: res.data.pagination?.next_cursor || null,
        }
        syncCursor(quoteCursors, quotePage.value, quotePagination.value.nextCursor)
      } catch (error) {
        quoteError.value = error.response?.data?.detail || 'Failed to load quote requests'
      } finally {
        quoteLoading.value = false
      }
    }

    const loadOperatorData = async () => {
      loading.value = true
      try {
        const requests = [
          api.get('/operators/profile/me'),
          api.get('/bookings/my-bookings', { params: { page_size: PAGE_SIZE, cursor: bookingCursors.value[bookingPage.value - 1] || undefined } }),
        ]
        if (canReadBilling.value) {
          requests.push(api.get('/operator/billing/plan').catch(() => null))
          requests.push(api.get('/operator/billing/analytics?days=7').catch(() => null))
        }

        const responses = await Promise.all(requests)
        const profileRes = responses[0]
        const bookingsRes = responses[1]
        const billingPlanRes = canReadBilling.value ? responses[2] : null
        const billingAnalyticsRes = canReadBilling.value ? responses[3] : null

        profile.value = profileRes.data
        bookings.value = bookingsRes.data.bookings
        bookingStatusCounts.value = {
          all: bookingsRes.data.status_counts?.all || bookingsRes.data.pagination?.total_items || bookings.value.length,
          pending: bookingsRes.data.status_counts?.pending || 0,
          confirmed: bookingsRes.data.status_counts?.confirmed || 0,
          completed: bookingsRes.data.status_counts?.completed || 0,
          cancelled: bookingsRes.data.status_counts?.cancelled || 0,
        }
        bookingPagination.value = {
          totalItems: bookingsRes.data.pagination?.total_items || bookings.value.length,
          hasMore: Boolean(bookingsRes.data.pagination?.has_more),
          nextCursor: bookingsRes.data.pagination?.next_cursor || null,
        }
        syncCursor(bookingCursors, bookingPage.value, bookingPagination.value.nextCursor)
        billingPlanState.value = billingPlanRes?.data || null
        billingAnalytics.value = billingAnalyticsRes?.data || null

        // Load reviews
        const reviewsRes = await api.get(`/bookings/ratings/operator/${profileRes.data._id}`, { params: { page_size: PAGE_SIZE, cursor: reviewCursors.value[reviewPage.value - 1] || undefined } })
        reviews.value = reviewsRes.data.ratings
        reviewPagination.value = {
          totalItems: reviewsRes.data.pagination?.total_items || reviews.value.length,
          hasMore: Boolean(reviewsRes.data.pagination?.has_more),
          nextCursor: reviewsRes.data.pagination?.next_cursor || null,
        }
        syncCursor(reviewCursors, reviewPage.value, reviewPagination.value.nextCursor)

        await loadQuoteRequests()
      } catch (error) {
        console.error('Error loading data:', error)
      } finally {
        loading.value = false
      }
    }

    const updateProfile = async () => {
      profileError.value = null
      try {
        // Parse specializations
        const specializations = specializationsInput.value
          .split(',')
          .map(s => s.trim())
          .filter(s => s.length > 0)

        await api.put('/operators/profile/me', {
          ...profileForm.value,
          specializations
        })
        
        // Reload profile
        await loadOperatorData()
        editingProfile.value = false
      } catch (error) {
        profileError.value = error.response?.data?.detail || 'Failed to update profile'
      }
    }

    const getQuoteLocations = (quote) => {
      if (!quote?.locations) return []
      return quote.locations
        .filter(loc => loc.coordinates)
        .map(loc => ({
          lat: loc.coordinates.latitude,
          lng: loc.coordinates.longitude,
          title: loc.name,
          description: loc.state || loc.country || ''
        }))
    }

    const getQuoteStatusClass = (quote) => getOperatorQuoteState(quote, profile.value?._id).key === 'responded' ? 'status-responded' : 'status-new'

    const getQuoteStatusLabel = (quote) => getOperatorQuoteState(quote, profile.value?._id).label

    const formatQuoteAge = (value) => formatOperatorQuoteAge(value)

    const formatQuoteTravelWindow = (value) => formatOperatorQuoteTravelWindow(value)

    const formatQuoteTravelers = (value) => formatOperatorQuoteTravelers(value)

    const formatQuoteBudget = (value) => formatOperatorQuoteBudget(value)

    const openQuoteInInbox = async (quoteId) => {
      await router.push(buildOperatorQuoteRoute(quoteId))
    }

    const addServingArea = async () => {
      servingAreaError.value = null
      try {
        // Filter out empty sub-locations
        const filteredArea = {
          ...newServingArea.value,
          sub_locations: newServingArea.value.sub_locations.filter(s => s.name.trim())
        }

        const missingCoordinates = filteredArea.sub_locations.some(s => !s.coordinates)
        if (missingCoordinates) {
          servingAreaError.value = 'Please set coordinates for every sub-location.'
          console.error('Missing coordinates for sub-locations')
          return
        }

        const isEditing = editingAreaIndex.value !== null
        console.log('Saving serving area...', { isEditing, filteredArea })

        if (isEditing) {
          // Update existing area
          console.log(`Updating area at index ${editingAreaIndex.value}`)
          await api.put(`/operators/profile/serving-areas/${editingAreaIndex.value}`, filteredArea)
          console.log('Area updated successfully')
        } else {
          // Create new area
          console.log('Creating new area')
          await api.post('/operators/profile/serving-areas', filteredArea)
          console.log('Area created successfully')
        }
        
        // Reset form and reload
        resetServingAreaForm()
        showAddServingArea.value = false
        await loadOperatorData()
      } catch (error) {
        console.error('Error saving serving area:', error)
        servingAreaError.value = error.response?.data?.detail || 'Failed to save serving area'
      }
    }

    const editServingArea = (idx) => {
      try {
        // Copy the area data into the form
        if (!profile.value || !profile.value.serving_areas || !profile.value.serving_areas[idx]) {
          console.error('Serving area not found at index', idx)
          servingAreaError.value = 'Error: Serving area not found'
          return
        }
        
        const area = profile.value.serving_areas[idx]
        console.log('Editing area at index:', idx, area)
        
        // Deep clone and ensure all properties exist
        newServingArea.value = {
          area_name: area.area_name || '',
          state: area.state || '',
          country: area.country || '',
          description: area.description || '',
          images: area.images ? JSON.parse(JSON.stringify(area.images)) : [],
          coordinates: area.coordinates ? JSON.parse(JSON.stringify(area.coordinates)) : null,
          sub_locations: (area.sub_locations || []).map(sub => ({
            name: sub.name || '',
            description: sub.description || '',
            coordinates: sub.coordinates ? JSON.parse(JSON.stringify(sub.coordinates)) : null,
            images: sub.images ? JSON.parse(JSON.stringify(sub.images)) : [],
            estimated_duration: sub.estimated_duration || '',
            popular: sub.popular || false
          }))
        }
        
        editingAreaIndex.value = idx
        showAddServingArea.value = true
        
        // Scroll to form
        setTimeout(() => {
          const formElement = document.querySelector('.serving-area-form')
          if (formElement) {
            formElement.scrollIntoView({ behavior: 'smooth' })
          }
        }, 100)
      } catch (error) {
        console.error('Error in editServingArea:', error)
        servingAreaError.value = 'Error loading serving area: ' + error.message
      }
    }

    const cancelEditServingArea = () => {
      console.log('Canceling edit/add form')
      resetServingAreaForm()
      showAddServingArea.value = false
    }

    const deleteServingArea = async (idx) => {
      if (!confirm('Are you sure you want to delete this serving area? This action cannot be undone.')) {
        return
      }

      try {
        await api.delete(`/operators/profile/serving-areas/${idx}`)
        await loadOperatorData()
      } catch (error) {
        alert(error.response?.data?.detail || 'Failed to delete serving area')
      }
    }

    const updateBookingStatus = async (bookingId, newStatus) => {
      try {
        bookingUpdating.value[bookingId] = true
        await api.put(`/bookings/${bookingId}/status`, { status: newStatus })
        await loadOperatorData()
      } catch (error) {
        console.error('Error updating booking:', error)
        alert('Failed to update booking status')
      } finally {
        bookingUpdating.value[bookingId] = false
      }
    }

    const cancelBookingRequest = async (bookingId) => {
      if (confirm('Are you sure you want to cancel this booking?')) {
        await updateBookingStatus(bookingId, 'cancelled')
      }
    }

    const formatStatus = (status) => {
      if (status === 'all') return 'All'
      return status.charAt(0).toUpperCase() + status.slice(1)
    }

    const getBookingCountByStatus = (status) => {
      return bookingStatusCounts.value[status] ?? 0
    }

    const filteredBookings = computed(() => {
      if (bookingFilter.value === 'all') {
        return bookings.value
      }
      return bookings.value.filter(
        b => b.booking_status?.status === bookingFilter.value
      )
    })

    const billingTotals = computed(() => billingAnalytics.value?.totals || {
      billable_events: 0,
      non_billable_events: 0,
      credits_consumed: 0,
      spend_amount: 0,
    })

    const billingCurrentCredits = computed(() => Number(billingPlanState.value?.subscription?.credits_remaining || 0))
    const billingCurrentPlan = computed(() => billingPlanState.value?.plan?.name || 'Free')

    const billingMiniBars = computed(() => {
      const rows = billingAnalytics.value?.daily || []
      const aggregated = new Map()
      rows.forEach((row) => {
        const existing = aggregated.get(row.date) || { date: row.date, spend_amount: 0 }
        existing.spend_amount += Number(row.spend_amount || 0)
        aggregated.set(row.date, existing)
      })
      const values = Array.from(aggregated.values())
        .sort((left, right) => left.date.localeCompare(right.date))
        .slice(-7)
      const maxSpend = Math.max(...values.map((item) => item.spend_amount), 0)
      return values.map((item) => ({
        ...item,
        label: new Date(`${item.date}T00:00:00`).toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
        height: maxSpend > 0 ? Math.max(10, Math.round((item.spend_amount / maxSpend) * 100)) : 0,
      }))
    })

    const billingTopSurfaces = computed(() =>
      (billingAnalytics.value?.by_surface || [])
        .slice()
        .sort((left, right) => Number(right.spend_amount || 0) - Number(left.spend_amount || 0))
        .slice(0, 2)
    )

    const formatBillingMoney = (value) => Number(value || 0).toFixed(2)
    const humanizeBilling = (value) => String(value || 'none').replaceAll('_', ' ')

    watch(tabs, (availableTabs) => {
      if (!availableTabs.includes(activeTab.value)) {
        activeTab.value = availableTabs[0] || 'Profile'
      }
    }, { immediate: true })

    onMounted(async () => {
      await accessStore.loadOperatorContext().catch(() => null)
      // Initialize profile form with current profile data
      const profileRes = await api.get('/operators/profile/me').catch(() => null)
      
      if (profileRes?.data) {
        profile.value = profileRes.data
        profileForm.value = {
          business_name: profileRes.data.business_name,
          description: profileRes.data.description || '',
          contact_number: profileRes.data.contact_number,
          years_of_experience: profileRes.data.years_of_experience,
          specializations: profileRes.data.specializations || []
        }
        specializationsInput.value = (profileRes.data.specializations || []).join(', ')
      }

      await loadOperatorData()
    })
    
    const startChat = async (touristId) => {
      // Start or open chat with tourist
      try {
        await chatStore.openConversation(
          touristId,
          'Tourist',
          'tourist'
        )
      } catch (error) {
        console.error('Error starting chat:', error)
      }
    }

    const startQuoteChat = async (quote) => {
      if (!quote?.tourist_id) return
      try {
        await chatStore.openConversation(
          quote.tourist_id,
          quote.tourist_name || 'Tourist',
          'tourist'
        )
      } catch (error) {
        console.error('Error starting quote chat:', error)
      }
    }

    const previousQuotePage = async () => {
      if (quotePage.value === 1 || quoteLoading.value) return
      quotePage.value -= 1
      await loadQuoteRequests()
    }

    const nextQuotePage = async () => {
      if (!quotePagination.value.hasMore || quoteLoading.value) return
      quotePage.value += 1
      await loadQuoteRequests()
    }

    const previousBookingPage = async () => {
      if (bookingPage.value === 1 || loading.value) return
      bookingPage.value -= 1
      await loadOperatorData()
    }

    const nextBookingPage = async () => {
      if (!bookingPagination.value.hasMore || loading.value) return
      bookingPage.value += 1
      await loadOperatorData()
    }

    const previousReviewPage = async () => {
      if (reviewPage.value === 1 || loading.value) return
      reviewPage.value -= 1
      await loadOperatorData()
    }

    const nextReviewPage = async () => {
      if (!reviewPagination.value.hasMore || loading.value) return
      reviewPage.value += 1
      await loadOperatorData()
    }

    return {
      tabs,
      activeTab,
      profile,
      bookings,
      reviews,
      loading,
      quoteRequests,
      quoteLoading,
      quoteError,
      quotePage,
      quotePagination,
      quoteTotalPages,
      quoteRangeLabel,
      bookingFilter,
      bookingStatuses,
      bookingUpdating,
      bookingPage,
      bookingPagination,
      bookingTotalPages,
      bookingRangeLabel,
      reviewPage,
      reviewPagination,
      reviewTotalPages,
      reviewRangeLabel,
      filteredBookings,
      canReadBilling,
      canUpdateProfile,
      billingTotals,
      billingCurrentCredits,
      billingCurrentPlan,
      billingMiniBars,
      billingTopSurfaces,
      formatBillingMoney,
      humanizeBilling,
      editingProfile,
      profileForm,
      specializationsInput,
      profileError,
      showAddServingArea,
      editingAreaIndex,
      servingAreaError,
      newServingArea,
      updateProfile,
      addServingArea,
      editServingArea,
      cancelEditServingArea,
      deleteServingArea,
      resetServingAreaForm,
      loadQuoteRequests,
      getQuoteLocations,
      getQuoteStatusClass,
      getQuoteStatusLabel,
      formatQuoteAge,
      formatQuoteTravelWindow,
      formatQuoteTravelers,
      formatQuoteBudget,
      updateBookingStatus,
      cancelBookingRequest,
      formatStatus,
      getBookingCountByStatus,
      startChat,
      startQuoteChat,
      openQuoteInInbox,
      previousQuotePage,
      nextQuotePage,
      previousBookingPage,
      nextBookingPage,
      previousReviewPage,
      nextReviewPage,
      loadOperatorData,
      switchTab
    }
  }
}
</script>

<style scoped>
.operator-dashboard {
  padding: 2rem 0;
}

.billing-summary-card {
  margin-bottom: 2rem;
  padding: 1.6rem;
  border-radius: 18px;
  background: linear-gradient(135deg, #10201f 0%, #155e75 52%, #1d4ed8 100%);
  box-shadow: 0 16px 40px rgba(15, 23, 42, 0.14);
  color: #fff;
}

.dashboard-pager {
  margin-top: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}

.pager-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.billing-summary-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.billing-kicker {
  margin: 0 0 0.2rem;
  color: rgba(255,255,255,0.66);
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-size: 0.74rem;
  font-weight: 700;
}

.billing-summary-head h2 {
  margin: 0;
  font-size: 1.35rem;
  color: #fff;
}

.billing-link {
  display: inline-flex;
  align-items: center;
  padding: 0.7rem 0.95rem;
  border-radius: 999px;
  background: rgba(255,255,255,0.12);
  border: 1px solid rgba(255,255,255,0.2);
  color: #fff;
  text-decoration: none;
  font-weight: 700;
}

.billing-summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.9rem;
  margin-top: 1rem;
}

.billing-metric {
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.14);
  border-radius: 16px;
  padding: 1rem;
}

.billing-metric span {
  display: block;
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  color: rgba(255,255,255,0.68);
}

.billing-metric strong {
  display: block;
  margin-top: 0.35rem;
  font-size: 1.45rem;
}

.billing-metric p {
  margin: 0.45rem 0 0;
  color: rgba(255,255,255,0.82);
}

.billing-mini-row {
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 1rem;
  margin-top: 1rem;
}

.billing-mini-chart {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 0.55rem;
  align-items: end;
  min-height: 140px;
}

.billing-mini-bar-wrap {
  display: grid;
  justify-items: center;
  gap: 0.35rem;
}

.billing-mini-bar-track {
  width: 100%;
  height: 96px;
  border-radius: 999px;
  background: rgba(255,255,255,0.12);
  position: relative;
  overflow: hidden;
}

.billing-mini-bar-fill {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  min-height: 4px;
  border-radius: inherit;
  background: linear-gradient(180deg, #f59e0b, #ea580c);
}

.billing-mini-bar-wrap span {
  font-size: 0.7rem;
  color: rgba(255,255,255,0.72);
}

.billing-surfaces {
  display: flex;
  flex-direction: column;
  gap: 0.65rem;
}

.billing-surface-chip {
  display: grid;
  gap: 0.25rem;
  padding: 0.9rem 1rem;
  border-radius: 16px;
  background: rgba(255,255,255,0.1);
  border: 1px solid rgba(255,255,255,0.14);
}

.billing-surface-chip strong {
  color: #fff;
}

.billing-surface-chip span,
.billing-empty {
  color: rgba(255,255,255,0.74);
}

.billing-empty.compact {
  min-height: 0;
  padding: 0.2rem 0;
}

h1 {
  margin-bottom: 2rem;
  color: #2c3e50;
}

.dashboard-tabs {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  border-bottom: 2px solid #ecf0f1;
  flex-wrap: wrap;
}

@media (max-width: 900px) {
  .billing-summary-grid,
  .billing-mini-row {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 720px) {
  .billing-summary-head {
    flex-direction: column;
  }
}

.tab-btn {
  padding: 0.75rem 1.5rem;
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1rem;
  color: #666;
  border-bottom: 3px solid transparent;
  transition: all 0.3s ease;
}

.tab-btn.active {
  color: #3498db;
  border-bottom-color: #3498db;
}

.tab-btn:hover {
  color: #3498db;
}

.tab-content {
  animation: fadeIn 0.3s ease;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

.card {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
}

.profile-view {
  margin-bottom: 2rem;
}

.profile-info {
  margin-bottom: 2rem;
}

.info-group {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #ecf0f1;
}

.info-group label {
  font-weight: bold;
  color: #2c3e50;
  display: block;
  margin-bottom: 0.5rem;
}

.info-group p {
  color: #666;
  margin: 0;
}

.tags {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.tag {
  display: inline-block;
  background: #3498db;
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 20px;
  font-size: 0.9rem;
}

.profile-form,
.serving-area-form {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 5px;
  margin-bottom: 1.5rem;
}

.form-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
  flex-wrap: wrap;
}

.form-actions .btn {
  min-width: 120px;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  margin-bottom: 0.5rem;
  font-weight: 500;
  color: #2c3e50;
}

.form-group input,
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-size: 1rem;
  font-family: inherit;
}

.form-group textarea {
  resize: vertical;
  min-height: 80px;
}

.form-row {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.sub-locations-section {
  margin: 1.5rem 0;
  padding: 1rem;
  background: white;
  border-radius: 5px;
}

.sub-locations-section h4 {
  margin-bottom: 1rem;
}

.sub-location-item {
  display: grid;
  grid-template-columns: 1fr 1fr auto;
  gap: 1rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 5px;
  align-items: start;
}

.sub-location-item input,
.sub-location-item textarea {
  padding: 0.5rem;
  border: 1px solid #ddd;
  border-radius: 3px;
  font-size: 0.9rem;
}

.button-group {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.serving-areas-list {
  margin-top: 2rem;
}

.serving-area-card {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 5px;
  margin-bottom: 1rem;
  border-left: 4px solid #3498db;
}

.serving-area-card .card-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.serving-area-card .card-header > div:first-child {
  flex: 1;
}

.serving-area-card .card-header h3 {
  color: #2c3e50;
  margin: 0 0 0.5rem 0;
}

.serving-area-card .card-header p {
  margin: 0;
  color: #666;
  font-size: 0.9rem;
}

.card-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: flex-end;
  min-width: fit-content;
}

.sub-locations {
  margin-top: 1rem;
}

.sub-locations ul {
  margin-top: 0.5rem;
  padding-left: 1.5rem;
}

.quotes-grid {
  display: grid;
  gap: 1rem;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
}

.quote-card {
  border: 1px solid #ecf0f1;
  border-radius: 6px;
  padding: 1rem;
  background: #fafbff;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.quote-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.quote-body .location-list {
  margin: 0.5rem 0;
  padding-left: 1.5rem;
}

.quote-meta p {
  margin: 0.25rem 0;
  color: #555;
}

.response-form {
  margin-top: 0.75rem;
  border-top: 1px dashed #e0e6ef;
  padding-top: 0.75rem;
}

.response-form .form-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}

.quote-actions {
  margin: 0.5rem 0;
}

.bookings-list {
  display: grid;
  gap: 1.5rem;
}

.booking-card {
  border: 1px solid #ecf0f1;
  border-radius: 5px;
  padding: 1.5rem;
  background: white;
}

.booking-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #ecf0f1;
}

.booking-header h3 {
  margin: 0;
  color: #2c3e50;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: bold;
  text-transform: uppercase;
}

.status-pending {
  background: #f39c12;
  color: white;
}

.status-confirmed {
  background: #27ae60;
  color: white;
}

.status-completed {
  background: #3498db;
  color: white;
}

.status-cancelled {
  background: #e74c3c;
  color: white;
}

.items-list {
  margin-top: 0.5rem;
  padding-left: 1.5rem;
}

.items-list li {
  margin: 0.25rem 0;
  color: #666;
}

.text-green {
  color: #27ae60;
  font-weight: bold;
}

.text-red {
  color: #e74c3c;
  font-weight: bold;
}

.booking-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #ecf0f1;
}

.filter-section {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.5rem 1.5rem;
  border: 2px solid #ecf0f1;
  border-radius: 25px;
  background: white;
  color: #666;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-btn:hover {
  border-color: #3498db;
  color: #3498db;
}

.filter-btn.active {
  background: #3498db;
  color: white;
  border-color: #3498db;
}

.filter-btn .count {
  background: rgba(255, 255, 255, 0.3);
  padding: 0.1rem 0.5rem;
  border-radius: 10px;
  font-size: 0.8rem;
  font-weight: bold;
}

.filter-btn.active .count {
  background: rgba(0, 0, 0, 0.2);
}

.btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 0.9rem;
  transition: all 0.3s ease;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover {
  background: #2980b9;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn-success {
  background: #27ae60;
  color: white;
}

.btn-success:hover {
  background: #229954;
}

.btn-info {
  background: #3498db;
  color: white;
}

.btn-warning {
  background: #f39c12;
  color: white;
}

.btn-danger {
  background: #e74c3c;
  color: white;
}

.btn-sm {
  padding: 0.25rem 0.75rem;
  font-size: 0.85rem;
}

.mb-2 {
  margin-bottom: 1rem;
}

.reviews-list {
  display: grid;
  gap: 1.5rem;
}

.review-card {
  border: 1px solid #ecf0f1;
  border-radius: 5px;
  padding: 1.5rem;
  background: #f8f9fa;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #ecf0f1;
}

.review-header h4 {
  margin: 0 0 0.5rem 0;
  color: #2c3e50;
}

.rating {
  color: #f39c12;
  font-weight: bold;
}

.date {
  color: #95a5a6;
  font-size: 0.9rem;
  margin: 0;
}

.review-text {
  color: #666;
  margin: 0 0 1rem 0;
  line-height: 1.6;
}

.categories {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #ecf0f1;
}

.category {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.category span:first-child {
  font-weight: 500;
  color: #2c3e50;
}

.cat-rating {
  color: #f39c12;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.stat-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 2rem;
  border-radius: 8px;
  text-align: center;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
}

.stat-card h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  opacity: 0.9;
}

.stat-number {
  margin: 0;
  font-size: 2.5rem;
  font-weight: bold;
}

.empty-state {
  text-align: center;
  padding: 3rem;
  color: #95a5a6;
}

.error {
  background: #ffe5e5;
  color: #e74c3c;
  padding: 1rem;
  border-radius: 5px;
  margin-bottom: 1rem;
}

.loading-container {
  text-align: center;
  padding: 3rem;
  color: #95a5a6;
}

@media (max-width: 768px) {
  .booking-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .booking-actions {
    flex-direction: column;
  }

  .sub-location-item {
    grid-template-columns: 1fr;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
