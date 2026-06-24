<template>
  <div class="container">
    <div class="my-bookings-page">
      <h1>My Bookings</h1>

      <div v-if="loading" class="loading-state">
        <p>Loading your bookings...</p>
      </div>

      <div v-else-if="bookings.length === 0" class="empty-state">
        <p>No bookings yet</p>
        <p class="hint">Start by exploring tour operators and sending booking requests</p>
        <router-link to="/search" class="btn btn-primary">
          Explore Tours
        </router-link>
      </div>

      <div v-else>
        <div class="filter-section">
          <button
            v-for="status in statuses"
            :key="status"
            :class="['filter-btn', { active: selectedFilter === status }]"
            @click="selectedFilter = status"
          >
            {{ formatStatus(status) }}
            <span class="count">{{ getCountByStatus(status) }}</span>
          </button>
        </div>

        <div class="bookings-grid">
          <div v-for="booking in filteredBookings" :key="booking._id" class="booking-card">
            <div class="booking-header">
              <div class="booking-title-block">
                <h3>Booking Request</h3>
                <p class="booking-subtitle">Requested {{ formatDate(booking.created_at) }}</p>
              </div>
              <span :class="['status-badge', 'status-' + booking.booking_status?.status]">
                {{ booking.booking_status?.status }}
              </span>
            </div>

            <div class="booking-details">
              <div class="detail-row">
                <label>Location:</label>
                <p>{{ booking.cart?.area_name }}, {{ booking.cart?.state }}</p>
              </div>

              <div class="detail-row">
                <label>Items:</label>
                <p>{{ booking.cart?.items?.length || 0 }} {{ booking.cart?.items?.length === 1 ? 'item' : 'items' }}</p>
              </div>
            </div>

            <div v-if="expandedBookings[booking._id]" class="booking-expanded">
              <div class="expanded-grid">
                <div class="detail-row detail-row-expanded">
                  <label>Booking ID:</label>
                  <p>{{ booking._id }}</p>
                </div>

                <div class="detail-row detail-row-expanded">
                  <label>Operator:</label>
                  <p>{{ booking.operator_name || 'Unknown Operator' }}</p>
                </div>

                <div class="detail-row detail-row-expanded">
                  <label>Cost:</label>
                  <p>{{ formatBookingCost(booking) }}</p>
                </div>

                <div class="detail-row detail-row-expanded detail-row-full">
                  <label>Requested Items:</label>
                  <ul class="items-list">
                    <li v-for="(item, idx) in booking.cart?.items" :key="idx">
                      {{ item.sub_location_name }}
                    </li>
                  </ul>
                </div>

                <div v-if="booking.notes" class="detail-row detail-row-expanded detail-row-full">
                  <label>Notes:</label>
                  <p>{{ booking.notes }}</p>
                </div>
              </div>
            </div>

            <div class="booking-actions">
              <button
                type="button"
                class="btn btn-secondary btn-sm"
                @click="toggleExpanded(booking._id)"
              >
                {{ expandedBookings[booking._id] ? 'Hide Details' : 'View Details' }}
              </button>
              <router-link
                v-if="booking.booking_status?.status === 'completed'"
                :to="`/booking/${booking._id}`"
                class="btn btn-primary btn-sm"
              >
                Leave Review
              </router-link>
              <button
                v-if="booking.booking_status?.status === 'pending'"
                @click="cancelBooking(booking._id)"
                :disabled="cancelling[booking._id]"
                class="btn btn-danger btn-sm"
              >
                {{ cancelling[booking._id] ? 'Cancelling...' : 'Cancel' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../services/api'

const bookings = ref([])
const loading = ref(true)
const selectedFilter = ref('all')
const cancelling = ref({})
const expandedBookings = ref({})

const statuses = ['all', 'pending', 'confirmed', 'completed', 'cancelled']

onMounted(async () => {
  await loadBookings()
})

const loadBookings = async () => {
  loading.value = true
  try {
    const response = await api.get('/bookings/my-bookings')
    bookings.value = response.data.bookings || []
  } catch (error) {
    console.error('Failed to load bookings:', error)
  } finally {
    loading.value = false
  }
}

const filteredBookings = computed(() => {
  if (selectedFilter.value === 'all') {
    return bookings.value
  }
  return bookings.value.filter((booking) => booking.booking_status?.status === selectedFilter.value)
})

const getCountByStatus = (status) => {
  if (status === 'all') {
    return bookings.value.length
  }
  return bookings.value.filter((booking) => booking.booking_status?.status === status).length
}

const formatStatus = (status) => status.charAt(0).toUpperCase() + status.slice(1)

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  })
}

const formatBookingCost = (booking) => {
  const amount = booking.final_cost ?? booking.estimated_cost
  if (amount === null || amount === undefined || amount === '') {
    return 'Pending quote'
  }

  const numericAmount = Number(amount)
  if (Number.isNaN(numericAmount)) {
    return String(amount)
  }

  return new Intl.NumberFormat('en-US', {
    style: 'currency',
    currency: 'USD',
    maximumFractionDigits: 0
  }).format(numericAmount)
}

const toggleExpanded = (bookingId) => {
  expandedBookings.value[bookingId] = !expandedBookings.value[bookingId]
}

const cancelBooking = async (bookingId) => {
  if (!confirm('Are you sure you want to cancel this booking?')) {
    return
  }

  cancelling.value[bookingId] = true
  try {
    await api.put(`/bookings/${bookingId}/status`, { status: 'cancelled' })
    await loadBookings()
  } catch (error) {
    console.error('Failed to cancel booking:', error)
    alert('Failed to cancel booking. Please try again.')
  } finally {
    cancelling.value[bookingId] = false
  }
}
</script>

<style scoped>
.my-bookings-page {
  padding: 1.5rem 0 2rem;
}

.my-bookings-page h1 {
  margin-bottom: 1.35rem;
  color: #2c3e50;
  font-size: clamp(2rem, 4vw, 2.5rem);
}

.loading-state,
.empty-state {
  padding: 3rem 2rem;
  text-align: center;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.empty-state .hint {
  color: #999;
  margin-bottom: 2rem;
}

.filter-section {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1.3rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.68rem 1.2rem;
  background: white;
  border: 2px solid #ddd;
  border-radius: 25px;
  cursor: pointer;
  font-size: 0.95rem;
  font-weight: 500;
  color: #666;
  transition: all 0.3s;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.filter-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

.filter-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: white;
}

.filter-btn .count {
  background: rgba(0, 0, 0, 0.1);
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
}

.filter-btn.active .count {
  background: rgba(255, 255, 255, 0.3);
}

.bookings-grid {
  display: grid;
  gap: 1rem;
}

.booking-card {
  background: white;
  border-radius: 18px;
  border: 1px solid #e6edf5;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.08);
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
}

.booking-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
}

.booking-header {
  padding: 0.9rem 1.1rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.booking-title-block {
  min-width: 0;
}

.booking-header h3 {
  margin: 0;
  font-size: 1rem;
}

.booking-subtitle {
  margin: 0.22rem 0 0;
  font-size: 0.8rem;
  color: rgba(255, 255, 255, 0.82);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.status-badge {
  padding: 0.35rem 0.78rem;
  border-radius: 20px;
  font-size: 0.7rem;
  font-weight: 600;
  text-transform: uppercase;
  background: rgba(255, 255, 255, 0.2);
  color: white;
  letter-spacing: 0.04em;
  flex-shrink: 0;
}

.status-badge.status-pending {
  background: #ff9800;
}

.status-badge.status-confirmed {
  background: #4caf50;
}

.status-badge.status-completed {
  background: #2196f3;
}

.status-badge.status-cancelled {
  background: #f44336;
}

.booking-details {
  padding: 0.95rem 1.1rem 0.15rem;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.7rem 1rem;
}

.detail-row {
  margin-bottom: 0;
  padding-bottom: 0.7rem;
  border-bottom: 1px solid #edf2f7;
  min-width: 0;
}

.detail-row:last-child,
.detail-row:nth-last-child(2):nth-child(odd) {
  border-bottom: none;
  padding-bottom: 0;
}

.detail-row label {
  font-weight: 600;
  color: #2c3e50;
  display: block;
  margin-bottom: 0.22rem;
  font-size: 0.78rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.detail-row p {
  margin: 0;
  color: #555;
  line-height: 1.45;
}

.booking-expanded {
  padding: 0 1.1rem 0.35rem;
  background: #ffffff;
}

.expanded-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.7rem 1rem;
  border-top: 1px dashed #e2e8f0;
  padding-top: 0.85rem;
}

.detail-row-expanded {
  border-bottom: 0;
  padding-bottom: 0;
}

.detail-row-full {
  grid-column: 1 / -1;
}

.items-list {
  margin: 0;
  padding-left: 1rem;
}

.items-list li {
  color: #555;
  line-height: 1.45;
}

.booking-actions {
  padding: 0.7rem 1.1rem 0.9rem;
  background: #fbfdff;
  border-top: 1px solid #edf2f7;
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 4px;
  text-decoration: none;
  display: inline-block;
  font-size: 0.9rem;
  cursor: pointer;
  border: none;
  transition: background 0.3s;
}

.btn-primary {
  background: #667eea;
  color: white;
}

.btn-primary:hover {
  background: #5568d3;
}

.btn-secondary {
  background: #666;
  color: white;
}

.btn-secondary:hover {
  background: #555;
}

.btn-danger {
  background: #f44336;
  color: white;
}

.btn-danger:hover:not(:disabled) {
  background: #da190b;
}

.btn-danger:disabled {
  background: #ffb3b0;
  cursor: not-allowed;
}

.btn-sm {
  padding: 0.36rem 0.72rem;
  font-size: 0.8rem;
}

@media (max-width: 760px) {
  .booking-header {
    align-items: stretch;
    flex-direction: column;
  }

  .booking-details,
  .expanded-grid {
    grid-template-columns: 1fr;
    gap: 0.75rem;
  }

  .detail-row:nth-last-child(2):nth-child(odd) {
    border-bottom: 1px solid #edf2f7;
    padding-bottom: 0.85rem;
  }

  .booking-actions {
    justify-content: stretch;
  }

  .booking-actions .btn {
    flex: 1 1 100%;
    text-align: center;
  }
}
</style>
