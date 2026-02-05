<template>
  <div class="container">
    <div class="booking-details">
      <h1>Booking Details</h1>
      
      <div v-if="loading" class="loading-container">
        <p>Loading booking details...</p>
      </div>
      
      <div v-else-if="booking" class="card">
        <div class="booking-info">
          <div class="info-group">
            <label>Booking ID:</label>
            <p>{{ booking._id }}</p>
          </div>
          
          <div class="info-group">
            <label>Status:</label>
            <p :class="'status-' + booking.booking_status?.status">
              {{ booking.booking_status?.status }}
            </p>
          </div>
          
          <div class="info-group">
            <label>Location:</label>
            <p>{{ booking.cart?.area_name }}, {{ booking.cart?.state }}</p>
          </div>
          
          <div class="info-group">
            <label>Items:</label>
            <ul>
              <li v-for="(item, idx) in booking.cart?.items" :key="idx">
                {{ item.sub_location_name }} - {{ item.selected ? 'Selected' : 'Not selected' }}
              </li>
            </ul>
          </div>
          
          <div v-if="booking.estimated_cost" class="info-group">
            <label>Estimated Cost:</label>
            <p>${{ booking.estimated_cost }}</p>
          </div>
          
          <div v-if="booking.final_cost" class="info-group">
            <label>Final Cost:</label>
            <p>${{ booking.final_cost }}</p>
          </div>
          
          <div class="info-group">
            <label>Created:</label>
            <p>{{ new Date(booking.created_at).toLocaleDateString() }}</p>
          </div>
        </div>
        
        <!-- Review Section -->
        <div v-if="booking.booking_status?.status === 'completed'" class="review-section">
          <div v-if="!hasReview" class="review-form-container">
            <h3>Leave a Review</h3>
            <p class="hint">Share your experience with this tour operator</p>
            
            <div class="form-group">
              <label>Rating *</label>
              <div class="star-rating">
                <span
                  v-for="n in 5"
                  :key="n"
                  :class="['star', { filled: reviewForm.rating >= n }]"
                  @click="reviewForm.rating = n"
                >
                  ⭐
                </span>
              </div>
              <small>{{ reviewForm.rating }}/5 selected</small>
            </div>
            
            <div class="form-group">
              <label>Your Review</label>
              <textarea
                v-model="reviewForm.review"
                placeholder="Tell us about your experience (optional)"
                rows="4"
              ></textarea>
            </div>
            
            <div class="categories-section">
              <label>Rate by Category (optional)</label>
              <div class="categories-grid">
                <div class="category-rating">
                  <label>Hospitality</label>
                  <div class="small-stars">
                    <span
                      v-for="n in 5"
                      :key="`h-${n}`"
                      :class="['small-star', { filled: (reviewForm.categories?.hospitality || 0) >= n }]"
                      @click="reviewForm.categories = reviewForm.categories || {}; reviewForm.categories.hospitality = n"
                    >
                      ⭐
                    </span>
                  </div>
                </div>
                
                <div class="category-rating">
                  <label>Value for Money</label>
                  <div class="small-stars">
                    <span
                      v-for="n in 5"
                      :key="`v-${n}`"
                      :class="['small-star', { filled: (reviewForm.categories?.value || 0) >= n }]"
                      @click="reviewForm.categories = reviewForm.categories || {}; reviewForm.categories.value = n"
                    >
                      ⭐
                    </span>
                  </div>
                </div>
                
                <div class="category-rating">
                  <label>Experience Quality</label>
                  <div class="small-stars">
                    <span
                      v-for="n in 5"
                      :key="`e-${n}`"
                      :class="['small-star', { filled: (reviewForm.categories?.experience || 0) >= n }]"
                      @click="reviewForm.categories = reviewForm.categories || {}; reviewForm.categories.experience = n"
                    >
                      ⭐
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            <div v-if="reviewError" class="error-message">{{ reviewError }}</div>
            
            <div class="button-group">
              <button
                @click="submitReview"
                :disabled="submitting || reviewForm.rating === 0"
                class="btn btn-primary"
              >
                {{ submitting ? 'Submitting...' : 'Submit Review' }}
              </button>
            </div>
          </div>
          
          <div v-else-if="editingReview" class="review-form-container">
            <h3>Edit Your Review</h3>
            
            <div class="form-group">
              <label>Rating *</label>
              <div class="star-rating">
                <span
                  v-for="n in 5"
                  :key="n"
                  :class="['star', { filled: reviewForm.rating >= n }]"
                  @click="reviewForm.rating = n"
                >
                  ⭐
                </span>
              </div>
              <small>{{ reviewForm.rating }}/5 selected</small>
            </div>
            
            <div class="form-group">
              <label>Your Review</label>
              <textarea
                v-model="reviewForm.review"
                placeholder="Tell us about your experience (optional)"
                rows="4"
              ></textarea>
            </div>
            
            <div class="categories-section">
              <label>Rate by Category (optional)</label>
              <div class="categories-grid">
                <div class="category-rating">
                  <label>Hospitality</label>
                  <div class="small-stars">
                    <span
                      v-for="n in 5"
                      :key="`h-${n}`"
                      :class="['small-star', { filled: (reviewForm.categories?.hospitality || 0) >= n }]"
                      @click="reviewForm.categories = reviewForm.categories || {}; reviewForm.categories.hospitality = n"
                    >
                      ⭐
                    </span>
                  </div>
                </div>
                
                <div class="category-rating">
                  <label>Value for Money</label>
                  <div class="small-stars">
                    <span
                      v-for="n in 5"
                      :key="`v-${n}`"
                      :class="['small-star', { filled: (reviewForm.categories?.value || 0) >= n }]"
                      @click="reviewForm.categories = reviewForm.categories || {}; reviewForm.categories.value = n"
                    >
                      ⭐
                    </span>
                  </div>
                </div>
                
                <div class="category-rating">
                  <label>Experience Quality</label>
                  <div class="small-stars">
                    <span
                      v-for="n in 5"
                      :key="`e-${n}`"
                      :class="['small-star', { filled: (reviewForm.categories?.experience || 0) >= n }]"
                      @click="reviewForm.categories = reviewForm.categories || {}; reviewForm.categories.experience = n"
                    >
                      ⭐
                    </span>
                  </div>
                </div>
              </div>
            </div>
            
            <div v-if="reviewError" class="error-message">{{ reviewError }}</div>
            
            <div class="button-group">
              <button
                @click="updateReview"
                :disabled="submitting || reviewForm.rating === 0"
                class="btn btn-primary"
              >
                {{ submitting ? 'Updating...' : 'Update Review' }}
              </button>
              <button
                @click="cancelEdit"
                :disabled="submitting"
                class="btn btn-secondary"
              >
                Cancel
              </button>
            </div>
          </div>
          
          <div v-else class="review-submitted">
            <div class="success-message">
              <p>✓ You have already reviewed this booking</p>
              <p class="rating-display">
                <strong>Your Rating:</strong> {{ existingReview.rating }}/5 ⭐
              </p>
              <p v-if="existingReview.review" class="review-text">
                <strong>Your Review:</strong> {{ existingReview.review }}
              </p>
              <button
                @click="startEdit"
                class="btn btn-primary btn-sm"
                style="margin-top: 1rem;"
              >
                Edit Review
              </button>
            </div>
          </div>
        </div>
        
        <button class="btn btn-secondary" @click="goBack">Back to Bookings</button>
      </div>
      
      <div v-else class="error-message">
        <p>Booking not found</p>
        <router-link to="/my-bookings" class="btn btn-primary">Back to Bookings</router-link>
      </div>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import api from '../services/api'

export default {
  name: 'BookingDetails',
  setup() {
    const router = useRouter()
    const route = useRoute()
    
    const booking = ref(null)
    const loading = ref(true)
    const submitting = ref(false)
    const reviewError = ref(null)
    const hasReview = ref(false)
    const editingReview = ref(false)
    const existingReview = ref(null)
    
    const reviewForm = ref({
      rating: 0,
      review: '',
      categories: {
        hospitality: 0,
        value: 0,
        experience: 0
      }
    })
    
    onMounted(async () => {
      try {
        const bookingId = route.params.id
        const response = await api.get(`/bookings/${bookingId}`)
        booking.value = response.data
        
        // Check if already reviewed
        await checkIfReviewed(bookingId)
      } catch (error) {
        console.error('Failed to load booking:', error)
      } finally {
        loading.value = false
      }
    })
    
    const checkIfReviewed = async (bookingId) => {
      try {
        // Check if a rating exists for this booking
        const ratingResponse = await api.get(`/bookings/ratings/booking/${bookingId}`)
        if (ratingResponse.data) {
          hasReview.value = true
          existingReview.value = ratingResponse.data
        }
      } catch (error) {
        // No review found, that's ok
        hasReview.value = false
      }
    }
    
    const startEdit = () => {
      if (existingReview.value) {
        reviewForm.value = {
          rating: existingReview.value.rating,
          review: existingReview.value.review || '',
          categories: existingReview.value.categories || {
            hospitality: 0,
            value: 0,
            experience: 0
          }
        }
        editingReview.value = true
      }
    }
    
    const cancelEdit = () => {
      editingReview.value = false
      reviewForm.value = {
        rating: 0,
        review: '',
        categories: { hospitality: 0, value: 0, experience: 0 }
      }
    }
    
    const submitReview = async () => {
      reviewError.value = null
      
      if (reviewForm.value.rating === 0) {
        reviewError.value = 'Please select a rating'
        return
      }
      
      submitting.value = true
      try {
        await api.post('/bookings/ratings', {
          booking_id: booking.value._id,
          operator_id: booking.value.operator_id,
          rating: reviewForm.value.rating,
          review: reviewForm.value.review || null,
          categories: reviewForm.value.categories
        })
        
        hasReview.value = true
        existingReview.value = {
          rating: reviewForm.value.rating,
          review: reviewForm.value.review,
          categories: reviewForm.value.categories
        }
        reviewForm.value = {
          rating: 0,
          review: '',
          categories: { hospitality: 0, value: 0, experience: 0 }
        }
      } catch (error) {
        reviewError.value = error.response?.data?.detail || 'Failed to submit review'
        console.error('Error submitting review:', error)
      } finally {
        submitting.value = false
      }
    }
    
    const updateReview = async () => {
      reviewError.value = null
      
      if (reviewForm.value.rating === 0) {
        reviewError.value = 'Please select a rating'
        return
      }
      
      submitting.value = true
      try {
        await api.put(`/bookings/ratings/${existingReview.value._id}`, {
          booking_id: booking.value._id,
          operator_id: booking.value.operator_id,
          rating: reviewForm.value.rating,
          review: reviewForm.value.review || null,
          categories: reviewForm.value.categories
        })
        
        // Update existing review
        existingReview.value = {
          ...existingReview.value,
          rating: reviewForm.value.rating,
          review: reviewForm.value.review,
          categories: reviewForm.value.categories
        }
        
        editingReview.value = false
        reviewForm.value = {
          rating: 0,
          review: '',
          categories: { hospitality: 0, value: 0, experience: 0 }
        }
      } catch (error) {
        reviewError.value = error.response?.data?.detail || 'Failed to update review'
        console.error('Error updating review:', error)
      } finally {
        submitting.value = false
      }
    }
    
    const goBack = () => {
      router.back()
    }
    
    return {
      booking,
      loading,
      submitting,
      reviewError,
      hasReview,
      editingReview,
      existingReview,
      reviewForm,
      submitReview,
      updateReview,
      startEdit,
      cancelEdit,
      goBack
    }
  }
}
</script>

<style scoped>
.booking-details h1 {
  margin-bottom: 2rem;
  color: #2c3e50;
}

.booking-info {
  margin-bottom: 2rem;
}

.info-group {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #eee;
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

.status-pending {
  color: #f39c12;
  font-weight: bold;
}

.status-confirmed {
  color: #27ae60;
  font-weight: bold;
}

.status-completed {
  color: #3498db;
  font-weight: bold;
}

.status-cancelled {
  color: #e74c3c;
  font-weight: bold;
}

.info-group ul {
  margin: 0;
  padding-left: 1.5rem;
}

.info-group li {
  color: #666;
  margin: 0.25rem 0;
}

.review-section {
  margin-top: 2rem;
  padding-top: 2rem;
  border-top: 2px solid #ecf0f1;
}

.review-form-container {
  background: #f8f9fa;
  padding: 1.5rem;
  border-radius: 8px;
}

.review-form-container h3 {
  margin-top: 0;
  color: #2c3e50;
}

.hint {
  color: #7f8c8d;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 1.5rem;
}

.form-group label {
  display: block;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 0.75rem;
}

.form-group textarea {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #ddd;
  border-radius: 5px;
  font-family: inherit;
  font-size: 0.95rem;
  resize: vertical;
}

.star-rating {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.5rem;
}

.star {
  font-size: 1.5rem;
  cursor: pointer;
  opacity: 0.3;
  transition: opacity 0.2s;
}

.star.filled {
  opacity: 1;
}

.star:hover {
  opacity: 0.7;
}

.categories-section {
  background: white;
  padding: 1rem;
  border-radius: 5px;
  margin-bottom: 1.5rem;
}

.categories-section label {
  display: block;
  font-weight: 600;
  color: #2c3e50;
  margin-bottom: 1rem;
}

.categories-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.category-rating {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.category-rating label {
  font-size: 0.9rem;
  margin: 0;
  font-weight: 500;
}

.small-stars {
  display: flex;
  gap: 0.25rem;
}

.small-star {
  font-size: 1rem;
  cursor: pointer;
  opacity: 0.3;
  transition: opacity 0.2s;
}

.small-star.filled {
  opacity: 1;
}

.small-star:hover {
  opacity: 0.7;
}

.button-group {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.error-message {
  background: #ffe5e5;
  color: #e74c3c;
  padding: 0.75rem;
  border-radius: 5px;
  margin-bottom: 1rem;
}

.success-message {
  background: #e8f5e9;
  color: #27ae60;
  padding: 1rem;
  border-radius: 5px;
  text-align: center;
}

.success-message p {
  margin: 0 0 0.5rem 0;
  font-weight: 500;
}

.rating-display {
  color: #27ae60;
  font-size: 1.1rem;
  margin: 0.75rem 0 !important;
}

.review-text {
  color: #555;
  margin-top: 1rem !important;
  padding: 1rem;
  background: #f8f9fa;
  border-radius: 5px;
  border-left: 4px solid #27ae60;
}

.btn-sm {
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
}

.review-submitted {
  margin-top: 1rem;
}

.loading-container {
  text-align: center;
  padding: 3rem;
  color: #7f8c8d;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.3s ease;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: #3498db;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #2980b9;
}

.btn-primary:disabled {
  background: #95a5a6;
  cursor: not-allowed;
}

.btn-secondary {
  background: #95a5a6;
  color: white;
}

.btn-secondary:hover {
  background: #7f8c8d;
}

.card {
  background: white;
  border-radius: 8px;
  padding: 2rem;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  margin-bottom: 2rem;
}
</style>
