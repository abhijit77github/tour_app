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
        <!-- Filter Buttons -->
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
        
        <!-- Filtered Bookings -->
        <div class="bookings-grid">
          <div v-for="booking in filteredBookings" :key="booking._id" class="booking-card">
            <div class="booking-header">
              <h3>Booking Request</h3>
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
                <ul class="items-list">
                  <li v-for="(item, idx) in booking.cart?.items" :key="idx">
                    {{ item.sub_location_name }}
                  </li>
                </ul>
              </div>
              
              <div v-if="booking.estimated_cost" class="detail-row">
                <label>Estimated Cost:</label>
                <p>${{ booking.estimated_cost }}</p>
              </div>
              
              <div class="detail-row">
                <label>Created:</label>
                <p>{{ formatDate(booking.created_at) }}</p>
              </div>
              
              <div v-if="booking.notes" class="detail-row">
                <label>Notes:</label>
                <p>{{ booking.notes }}</p>
              </div>
            </div>
            
            <div class="booking-actions">
              <router-link :to="`/booking/${booking._id}`" class="btn btn-secondary btn-sm">
                View Details
              </router-link>
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
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'

const bookings = ref([])
const loading = ref(true)
const selectedFilter = ref('all')
const cancelling = ref({})

const statuses = ['all', 'pending', 'confirmed', 'completed', 'cancelled']

onMounted(async () => {
  await loadBookings()
})

const loadBookings = async () => {
  loading.value = true
  try {
    const response = await api.get('/bookings/my-bookings')
    bookings.value = response.data.bookings || []
    console.log('Loaded bookings:', bookings.value)
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
  return bookings.value.filter(b => b.booking_status?.status === selectedFilter.value)
})

const getCountByStatus = (status) => {
  if (status === 'all') {
    return bookings.value.length
  }
  return bookings.value.filter(b => b.booking_status?.status === status).length
}

const formatStatus = (status) => {
  return status.charAt(0).toUpperCase() + status.slice(1)
}

const formatDate = (dateString) => {
  if (!dateString) return ''
  const date = new Date(dateString)
  return date.toLocaleDateString('en-US', { 
    year: 'numeric', 
    month: 'long', 
    day: 'numeric' 
  })
}

const cancelBooking = async (bookingId) => {
  if (!confirm('Are you sure you want to cancel this booking?')) {
    return
  }
  
  cancelling.value[bookingId] = true
  try {
    // Try to cancel via backend - update status to cancelled
    await api.put(`/bookings/${bookingId}/status`, { status: 'cancelled' })
    
    // Reload bookings
    await loadBookings()
    console.log('Booking cancelled successfully')
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
  padding: 2rem 0;
}

.my-bookings-page h1 {
  margin-bottom: 2rem;
  color: #2c3e50;
}

.loading-state,
.empty-state {
  padding: 3rem 2rem;
  text-align: center;
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.empty-state .hint {
  color: #999;
  margin-bottom: 2rem;
}

/* Filter Section */
.filter-section {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.75rem 1.5rem;
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
  background: rgba(0,0,0,0.1);
  padding: 0.2rem 0.6rem;
  border-radius: 12px;
  font-size: 0.85rem;
  font-weight: 600;
}

.filter-btn.active .count {
  background: rgba(255,255,255,0.3);
}

.bookings-grid {
  display: grid;
  gap: 1.5rem;
}

.booking-card {
  background: white;
  border-radius: 8px;
  box-shadow: 0 2px 8px rgba(0,0,0,0.1);
  overflow: hidden;
  transition: transform 0.3s, box-shadow 0.3s;
}

.booking-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0,0,0,0.15);
}

.booking-header {
  padding: 1.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.booking-header h3 {
  margin: 0;
  font-size: 1.25rem;
}

.status-badge {
  padding: 0.5rem 1rem;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  background: rgba(255,255,255,0.2);
  color: white;
}

.status-badge.status-pending {
  background: #ff9800;
  color: white;
}

.status-badge.status-confirmed {
  background: #4CAF50;
  color: white;
}

.status-badge.status-completed {
  background: #2196F3;
  color: white;
}

.status-badge.status-cancelled {
  background: #f44336;
  color: white;
}

.booking-details {
  padding: 1.5rem;
}

.detail-row {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #eee;
}

.detail-row:last-child {
  border-bottom: none;
  margin-bottom: 0;
  padding-bottom: 0;
}

.detail-row label {
  font-weight: 600;
  color: #2c3e50;
  display: block;
  margin-bottom: 0.5rem;
}

.detail-row p {
  margin: 0;
  color: #555;
}

.items-list {
  margin: 0;
  padding-left: 1.5rem;
}

.items-list li {
  color: #555;
}

.booking-actions {
  padding: 1rem 1.5rem;
  background: #f9f9f9;
  border-top: 1px solid #eee;
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
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
  padding: 0.4rem 0.8rem;
  font-size: 0.85rem;
}
</style>
