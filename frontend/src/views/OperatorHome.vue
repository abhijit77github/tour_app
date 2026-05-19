<template>
  <div class="operator-home">
    <!-- Hero/Welcome Section -->
    <section class="hero-section">
      <div class="hero-content">
        <div class="hero-text">
          <p class="greeting">Welcome back,</p>
          <h1>{{ operatorName }}</h1>
          <p class="subheading">Manage your tours and respond to booking requests</p>
        </div>
        <div class="hero-stats">
          <div class="stat-card">
            <span class="stat-icon">📋</span>
            <div>
              <p class="stat-value">{{ quotesCount }}</p>
              <p class="stat-label">Quote Requests</p>
            </div>
          </div>
          <div class="stat-card">
            <span class="stat-icon">📍</span>
            <div>
              <p class="stat-value">{{ servingAreasCount }}</p>
              <p class="stat-label">Serving Areas</p>
            </div>
          </div>
          <div class="stat-card">
            <span class="stat-icon">⭐</span>
            <div>
              <p class="stat-value">{{ rating.toFixed(1) }}</p>
              <p class="stat-label">Rating</p>
            </div>
          </div>
          <div class="stat-card">
            <span class="stat-icon">✅</span>
            <div>
              <p class="stat-value">{{ bookingsCount }}</p>
              <p class="stat-label">Bookings</p>
            </div>
          </div>
        </div>
      </div>
    </section>

    <!-- Main Content Grid -->
    <div class="main-content">
      <!-- Left Column: Quotes and Quick Links -->
      <main class="content-left">
        <!-- Quick Navigation -->
        <section class="quick-nav-section">
          <h2>Quick Actions</h2>
          <div class="quick-nav-grid">
            <router-link to="/operator/dashboard" class="nav-card dashboard-card">
              <div class="nav-icon">📊</div>
              <div>
                <h3>Dashboard</h3>
                <p>Manage everything</p>
              </div>
              <span class="arrow">→</span>
            </router-link>

            <router-link to="/operator/dashboard" class="nav-card profile-card">
              <div class="nav-icon">👤</div>
              <div>
                <h3>My Profile</h3>
                <p>Update business info</p>
              </div>
              <span class="arrow">→</span>
            </router-link>

            <router-link to="/operator/dashboard" class="nav-card areas-card">
              <div class="nav-icon">🗺️</div>
              <div>
                <h3>Serving Areas</h3>
                <p>Manage locations</p>
              </div>
              <span class="arrow">→</span>
            </router-link>

            <router-link to="/operator/dashboard" class="nav-card bookings-card">
              <div class="nav-icon">📅</div>
              <div>
                <h3>My Bookings</h3>
                <p>View all bookings</p>
              </div>
              <span class="arrow">→</span>
            </router-link>
          </div>
        </section>

        <!-- Recent Quote Requests -->
        <section class="quotes-section">
          <div class="section-header">
            <div>
              <h2>Recent Quote Requests</h2>
              <p>Respond to tourist requests for your serving areas</p>
            </div>
            <router-link to="/operator/quotes" class="btn btn-text">View All →</router-link>
          </div>

          <div v-if="loading" class="loading-state">
            <div class="spinner"></div>
            <p>Loading quote requests...</p>
          </div>

          <div v-else-if="quoteRequests.length === 0" class="empty-state">
            <div class="empty-icon">📬</div>
            <h3>No quote requests yet</h3>
            <p>When tourists request quotes for your areas, they'll appear here.</p>
          </div>

          <div v-else class="quotes-list">
            <div
              v-for="quote in quoteRequests.slice(0, 5)"
              :key="quote._id"
              class="quote-card"
              :class="getQuoteStatus(quote)"
            >
              <!-- Card Header -->
              <div class="quote-header">
                <div class="quote-meta">
                  <h3>{{ quote.locations.length }} Location{{ quote.locations.length > 1 ? 's' : '' }}</h3>
                  <span class="quote-badge" :class="getStatusClass(quote.status)">
                    {{ quote.status }}
                  </span>
                </div>
                <p class="quote-time">{{ formatTime(quote.created_at) }}</p>
              </div>

              <!-- Locations Matched -->
              <div class="locations-matched">
                <p class="matched-label">Your serving areas:</p>
                <div class="location-tags">
                  <span
                    v-for="loc in getMatchingLocations(quote.locations)"
                    :key="loc.name"
                    class="location-tag"
                  >
                    📍 {{ loc.name }}
                  </span>
                </div>
              </div>

              <!-- Tourist Info -->
              <div class="tourist-info">
                <div class="info-item">
                  <span class="info-label">Tourist:</span>
                  <span class="info-value">{{ quote.tourist_name }}</span>
                </div>
                <div v-if="quote.travel_window" class="info-item">
                  <span class="info-label">When:</span>
                  <span class="info-value">{{ quote.travel_window }}</span>
                </div>
                <div v-if="quote.travelers" class="info-item">
                  <span class="info-label">Travelers:</span>
                  <span class="info-value">{{ quote.travelers }} people</span>
                </div>
                <div v-if="quote.budget" class="info-item">
                  <span class="info-label">Budget:</span>
                  <span class="info-value">${{ quote.budget }}</span>
                </div>
              </div>

              <!-- Notes -->
              <div v-if="quote.notes" class="quote-notes">
                <p class="notes-label">Notes:</p>
                <p class="notes-text">{{ quote.notes }}</p>
              </div>

              <!-- Responses -->
              <div v-if="quote.responses && quote.responses.length" class="responses-info">
                <p class="responses-label">
                  <span class="response-count">{{ quote.responses.length }}</span>
                  Response{{ quote.responses.length > 1 ? 's' : '' }} from operators
                </p>
              </div>

              <!-- Actions -->
              <div class="quote-actions">
                <router-link
                  :to="getQuoteRoute(quote._id)"
                  class="btn btn-primary btn-small"
                >
                  Respond with Quote
                </router-link>
                <button class="btn btn-secondary btn-small" @click="markAsRead(quote._id)">
                  Details
                </button>
              </div>
            </div>
          </div>
        </section>
      </main>

      <!-- Right Column: Ads and Featured Content -->
      <aside class="content-right">
        <!-- Featured Section -->
        <section class="featured-section">
          <h3>Featured for Operators</h3>
          <div class="featured-item">
            <div class="featured-icon">🌟</div>
            <h4>Premium Listing</h4>
            <p>Boost your visibility and attract more tourists</p>
            <router-link to="/operator/dashboard" class="btn btn-text-small">Learn More →</router-link>
          </div>
        </section>

        <!-- Tips & Best Practices -->
        <section class="tips-section">
          <h3>📚 Pro Tips</h3>
          <div class="tips-list">
            <div class="tip-item">
              <span class="tip-number">1</span>
              <div>
                <h4>Respond Quickly</h4>
                <p>Reply to quotes within 24 hours</p>
              </div>
            </div>
            <div class="tip-item">
              <span class="tip-number">2</span>
              <div>
                <h4>Be Competitive</h4>
                <p>Check market rates for your area</p>
              </div>
            </div>
            <div class="tip-item">
              <span class="tip-number">3</span>
              <div>
                <h4>Build Reviews</h4>
                <p>Encourage tourists to leave ratings</p>
              </div>
            </div>
            <div class="tip-item">
              <span class="tip-number">4</span>
              <div>
                <h4>Update Areas</h4>
                <p>Keep your serving areas current</p>
              </div>
            </div>
          </div>
        </section>

        <!-- Performance Stats -->
        <section class="stats-sidebar">
          <h3>Your Performance</h3>
          <div class="stat-row">
            <div class="stat-label">Response Rate</div>
            <div class="stat-value">{{ responseRate }}%</div>
          </div>
          <div class="stat-row">
            <div class="stat-label">Avg Response Time</div>
            <div class="stat-value">{{ avgResponseTime }}</div>
          </div>
          <div class="stat-row">
            <div class="stat-label">Completion Rate</div>
            <div class="stat-value">{{ completionRate }}%</div>
          </div>
        </section>

        <!-- CTA Banner -->
        <section class="cta-banner">
          <div class="banner-content">
            <h3>Ready to Grow?</h3>
            <p>Complete your profile to unlock premium features</p>
            <router-link to="/operator/dashboard" class="btn btn-primary btn-block">
              Go to Dashboard
            </router-link>
          </div>
        </section>
      </aside>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import api from '../services/api'

const authStore = useAuthStore()
const router = useRouter()
const quoteRequests = ref([])
const bookings = ref([])
const loading = ref(true)
const profile = ref(null)

const operatorName = computed(() => profile.value?.business_name || 'Operator')
const quotesCount = computed(() => quoteRequests.value.length)
const servingAreasCount = computed(() => profile.value?.serving_areas?.length || 0)
const rating = computed(() => profile.value?.average_rating || 0)
const bookingsCount = computed(() => bookings.value.length)
const responseRate = computed(() => {
  const totalQuotes = quoteRequests.value.length
  if (!totalQuotes) return 0

  const myResponses = quoteRequests.value.filter((quote) =>
    (quote.responses || []).some((resp) => resp.operator_id === profile.value?._id)
  ).length

  return Math.round((myResponses / totalQuotes) * 100)
})

const avgResponseTime = computed(() => {
  if (!profile.value?._id) return 'N/A'

  const responseHours = quoteRequests.value
    .map((quote) => {
      const myResponse = (quote.responses || [])
        .filter((resp) => resp.operator_id === profile.value._id)
        .sort((a, b) => new Date(a.created_at) - new Date(b.created_at))[0]

      if (!myResponse || !quote.created_at) return null

      const createdAt = new Date(quote.created_at)
      const respondedAt = new Date(myResponse.created_at)
      const diffMs = respondedAt - createdAt

      if (Number.isNaN(diffMs) || diffMs < 0) return null
      return diffMs / (1000 * 60 * 60)
    })
    .filter((v) => v !== null)

  if (!responseHours.length) return 'N/A'

  const avgHours = responseHours.reduce((sum, h) => sum + h, 0) / responseHours.length
  if (avgHours < 1) return '<1 hr'
  if (avgHours < 24) return `${Math.round(avgHours)} hrs`
  return `${Math.round(avgHours / 24)} days`
})

const completionRate = computed(() => {
  const totalBookings = bookings.value.length
  if (!totalBookings) return 0

  const completed = bookings.value.filter(
    (booking) => booking.booking_status?.status === 'completed'
  ).length

  return Math.round((completed / totalBookings) * 100)
})

const getQuoteStatus = (quote) => {
  if (quote.responses?.some(r => r.operator_id === authStore.user._id)) {
    return 'has-response'
  }
  return 'new-quote'
}

const getStatusClass = (status) => {
  return {
    'open': 'status-open',
    'closed': 'status-closed'
  }[status] || 'status-open'
}

const getMatchingLocations = (locations) => {
  if (!profile.value?.serving_areas) return locations.slice(0, 2)
  return locations.filter(loc => 
    profile.value.serving_areas.some(area => 
      area.area_name.toLowerCase().includes(loc.name.toLowerCase()) ||
      loc.name.toLowerCase().includes(area.area_name.toLowerCase())
    )
  ).slice(0, 3)
}

const formatTime = (dateString) => {
  const date = new Date(dateString)
  const now = new Date()
  const diff = now - date
  
  if (diff < 60000) return 'Just now'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}m ago`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}h ago`
  if (diff < 604800000) return `${Math.floor(diff / 86400000)}d ago`
  
  return date.toLocaleDateString()
}

const markAsRead = async (quoteId) => {
  await router.push({
    name: 'OperatorQuoteRequests',
    query: { quoteId }
  })
}

const getQuoteRoute = (quoteId) => ({
  name: 'OperatorQuoteRequests',
  query: { quoteId }
})

onMounted(async () => {
  try {
    // Fetch operator profile
    const profileRes = await api.get('/operators/profile/me')
    profile.value = profileRes.data

    // Fetch quote inbox
    const quotesRes = await api.get('/quotes/inbox')
    quoteRequests.value = quotesRes.data.quotes || []

    // Fetch booking requests for summary cards
    const bookingsRes = await api.get('/bookings/my-bookings')
    bookings.value = bookingsRes.data.bookings || []
  } catch (error) {
    console.error('Failed to load operator home data:', error)
    if (error.response) {
      console.error('Error status:', error.response.status)
      console.error('Error data:', error.response.data)
    }
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.operator-home {
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #e0f2fe 100%);
  min-height: 100vh;
  padding-bottom: 4rem;
}

/* Hero Section */
.hero-section {
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #334155 100%);
  color: white;
  padding: 3rem 2rem;
  border-radius: 20px;
  margin: 2rem;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
}

.hero-content {
  max-width: 1400px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1fr 1.2fr;
  gap: 2rem;
  align-items: center;
}

.hero-text h1 {
  font-size: 2.8rem;
  font-weight: 800;
  margin: 0.5rem 0 0;
  line-height: 1.1;
}

.greeting {
  font-size: 1rem;
  opacity: 0.9;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.15em;
  font-weight: 700;
}

.subheading {
  font-size: 1.1rem;
  opacity: 0.85;
  margin: 0.5rem 0 0;
  line-height: 1.5;
}

.hero-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
}

.stat-card {
  background: rgba(255, 255, 255, 0.1);
  backdrop-filter: blur(20px);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  padding: 1.5rem;
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: all 0.3s ease;
}

.stat-card:hover {
  background: rgba(255, 255, 255, 0.15);
  border-color: rgba(255, 255, 255, 0.4);
  transform: translateY(-2px);
}

.stat-icon {
  font-size: 2rem;
}

.stat-value {
  font-size: 1.8rem;
  font-weight: 800;
  margin: 0;
}

.stat-label {
  font-size: 0.85rem;
  opacity: 0.9;
  margin: 0.2rem 0 0;
}

/* Main Content Grid */
.main-content {
  display: grid;
  grid-template-columns: 1fr 360px;
  gap: 2rem;
  max-width: 1400px;
  margin: 2rem auto;
  padding: 0 2rem;
}

/* Content Left */
.content-left {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

/* Quick Navigation */
.quick-nav-section h2,
.quotes-section h2 {
  font-size: 1.5rem;
  font-weight: 800;
  margin: 0 0 1.5rem 0;
  color: #0f172a;
}

.quick-nav-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.nav-card {
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 16px;
  padding: 1.5rem;
  text-decoration: none;
  color: inherit;
  display: flex;
  align-items: center;
  gap: 1rem;
  transition: all 0.3s ease;
  position: relative;
  overflow: hidden;
}

.nav-card::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.1), transparent);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.nav-card:hover {
  border-color: #2563eb;
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(37, 99, 235, 0.15);
}

.nav-card:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.35);
  outline-offset: 2px;
  border-color: #2563eb;
}

.nav-card:hover::before {
  opacity: 1;
}

.nav-icon {
  font-size: 2rem;
  min-width: 48px;
  text-align: center;
}

.nav-card h3 {
  margin: 0;
  font-weight: 700;
  color: #1f2d3d;
  font-size: 1rem;
}

.nav-card p {
  margin: 0.3rem 0 0;
  font-size: 0.85rem;
  color: #6b7a99;
}

.arrow {
  margin-left: auto;
  font-size: 1.2rem;
  opacity: 0;
  transition: all 0.3s ease;
}

.nav-card:hover .arrow {
  opacity: 1;
  transform: translateX(4px);
}

.dashboard-card { border-top: 3px solid #2563eb; }
.profile-card { border-top: 3px solid #8b5cf6; }
.areas-card { border-top: 3px solid #ec4899; }
.bookings-card { border-top: 3px solid #f59e0b; }

/* Quotes Section */
.section-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.section-header h2 {
  font-size: 1.5rem;
  font-weight: 800;
  margin: 0;
  color: #0f172a;
}

.section-header p {
  margin: 0.5rem 0 0;
  color: #6b7a99;
  font-size: 0.95rem;
}

.quotes-list {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.quote-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1.5rem;
  transition: all 0.3s ease;
}

.quote-card:hover {
  border-color: #2563eb;
  box-shadow: 0 12px 32px rgba(37, 99, 235, 0.1);
  transform: translateY(-2px);
}

.quote-card.has-response {
  border-left: 4px solid #10b981;
  background: linear-gradient(135deg, rgba(16, 185, 129, 0.02) 0%, white 100%);
}

.quote-card.new-quote {
  border-left: 4px solid #f59e0b;
  background: linear-gradient(135deg, rgba(245, 158, 11, 0.02) 0%, white 100%);
}

.quote-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.quote-meta {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.quote-meta h3 {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 700;
  color: #1f2d3d;
}

.quote-badge {
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  font-size: 0.8rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.status-open {
  background: #fef3c7;
  color: #b45309;
}

.status-closed {
  background: #dbeafe;
  color: #0369a1;
}

.quote-time {
  font-size: 0.85rem;
  color: #6b7a99;
  margin: 0;
}

.locations-matched {
  margin-bottom: 1rem;
}

.matched-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #6b7a99;
  margin: 0 0 0.5rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.location-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
}

.location-tag {
  display: inline-block;
  background: #f0f9ff;
  color: #0369a1;
  padding: 0.4rem 0.8rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 600;
  border: 1px solid #bae6fd;
}

.tourist-info {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin: 1rem 0;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 12px;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.info-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: #6b7a99;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-value {
  font-size: 0.95rem;
  font-weight: 600;
  color: #1f2d3d;
}

.quote-notes {
  margin: 1rem 0;
  padding: 1rem;
  background: #fef3c7;
  border-radius: 10px;
  border-left: 3px solid #f59e0b;
}

.notes-label {
  font-size: 0.8rem;
  font-weight: 700;
  color: #b45309;
  margin: 0 0 0.5rem;
}

.notes-text {
  margin: 0;
  color: #92400e;
  font-size: 0.95rem;
}

.responses-info {
  margin: 1rem 0;
  padding: 0.75rem 1rem;
  background: #dbeafe;
  border-radius: 8px;
  border-left: 3px solid #0284c7;
}

.responses-label {
  font-size: 0.9rem;
  color: #0369a1;
  margin: 0;
  font-weight: 600;
}

.response-count {
  font-weight: 800;
  color: #0284c7;
}

.quote-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.btn {
  border: none;
  border-radius: 10px;
  padding: 0.75rem 1.5rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.3s ease;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3);
}

.btn:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.35);
  outline-offset: 2px;
}

.btn-secondary {
  background: #f0f4f8;
  color: #1f2d3d;
  border: 1px solid #d8deeb;
}

.btn-secondary:hover {
  background: #e2e8f0;
}

.btn-small {
  padding: 0.6rem 1.2rem;
  font-size: 0.9rem;
}

.btn-text {
  background: transparent;
  color: #2563eb;
  padding: 0.5rem 1rem;
  font-weight: 600;
}

.btn-text:hover {
  color: #1e40af;
  text-decoration: underline;
}

.btn-text-small {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
}

/* Empty State */
.empty-state,
.loading-state {
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  border-radius: 16px;
  border: 2px dashed #e2e8f0;
}

.empty-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.empty-state h3 {
  margin: 0;
  color: #1f2d3d;
  font-size: 1.3rem;
}

.empty-state p,
.loading-state p {
  margin: 0.5rem 0 0;
  color: #6b7a99;
}

.spinner {
  width: 40px;
  height: 40px;
  border: 4px solid #e2e8f0;
  border-top-color: #2563eb;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin: 0 auto 1rem;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Content Right (Sidebar) */
.content-right {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.featured-section,
.tips-section,
.stats-sidebar,
.cta-banner {
  background: white;
  border-radius: 16px;
  padding: 1.5rem;
  border: 1px solid #e2e8f0;
}

.featured-section h3,
.tips-section h3,
.stats-sidebar h3 {
  margin: 0 0 1.5rem;
  font-size: 1.1rem;
  font-weight: 800;
  color: #1f2d3d;
}

.featured-item {
  text-align: center;
  padding: 1rem;
}

.featured-icon {
  font-size: 2rem;
  margin-bottom: 0.5rem;
}

.featured-item h4 {
  margin: 0 0 0.5rem;
  color: #1f2d3d;
  font-weight: 700;
}

.featured-item p {
  margin: 0 0 1rem;
  color: #6b7a99;
  font-size: 0.9rem;
}

.btn-text-small {
  background: transparent;
  color: #2563eb;
  padding: 0.3rem 0.6rem;
  font-size: 0.85rem;
  font-weight: 600;
}

.tips-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.tip-item {
  display: flex;
  gap: 1rem;
  padding: 1rem;
  background: #f8fafc;
  border-radius: 10px;
  border-left: 3px solid #2563eb;
}

.tip-number {
  min-width: 30px;
  height: 30px;
  background: #2563eb;
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 800;
  font-size: 0.9rem;
}

.tip-item h4 {
  margin: 0 0 0.2rem;
  font-size: 0.9rem;
  color: #1f2d3d;
}

.tip-item p {
  margin: 0;
  font-size: 0.8rem;
  color: #6b7a99;
}

.stat-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem 0;
  border-bottom: 1px solid #f0f4f8;
}

.stat-row:last-child {
  border-bottom: none;
}

.stat-label {
  font-size: 0.9rem;
  color: #6b7a99;
  font-weight: 600;
}

.stat-value {
  font-size: 1.3rem;
  font-weight: 800;
  color: #2563eb;
}

.cta-banner {
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  color: white;
  text-align: center;
  border: none;
}

.cta-banner h3 {
  color: white;
  margin-bottom: 0.5rem;
}

.cta-banner p {
  margin: 0 0 1.5rem;
  opacity: 0.9;
  font-size: 0.9rem;
}

.btn-block {
  width: 100%;
  display: block;
}

/* Responsive */
@media (max-width: 1024px) {
  .main-content {
    grid-template-columns: 1fr;
  }

  .content-right {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 1.5rem;
  }

  .hero-content {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero-section {
    padding: 2rem 1rem;
    margin: 1rem;
    border-radius: 16px;
  }

  .hero-text h1 {
    font-size: 2rem;
  }

  .hero-stats {
    grid-template-columns: 1fr;
  }

  .quick-nav-grid {
    grid-template-columns: 1fr;
  }

  .tourist-info {
    grid-template-columns: 1fr;
  }

  .quote-actions {
    flex-direction: column;
  }

  .quote-actions .btn {
    width: 100%;
  }

  .main-content {
    padding: 0 1rem;
  }

  .content-right {
    grid-template-columns: 1fr;
  }

  .section-header {
    flex-direction: column;
    gap: 1rem;
  }
}

@media (max-width: 480px) {
  .hero-section {
    padding: 1.5rem;
    margin: 1rem 0.5rem;
  }

  .hero-text h1 {
    font-size: 1.5rem;
  }

  .stat-card {
    flex-direction: column;
    text-align: center;
    gap: 0.5rem;
  }

  .quick-nav-section h2,
  .section-header h2 {
    font-size: 1.2rem;
  }

  .quote-meta {
    flex-direction: column;
    align-items: flex-start;
  }

  .main-content {
    gap: 1rem;
    padding: 0 0.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .nav-card,
  .quote-card,
  .btn,
  .stat-card,
  .arrow {
    transition: none !important;
  }

  .spinner {
    animation-duration: 1.6s;
  }
}
</style>
