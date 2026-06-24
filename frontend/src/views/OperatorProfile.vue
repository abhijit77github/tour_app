<template>
  <div class="operator-profile-page">
    <div v-if="loading" class="loading-container">
      <p>Loading operator profile...</p>
    </div>

    <div v-else-if="error" class="error-container">
      <p>{{ error }}</p>
      <router-link to="/search" class="btn btn-primary">Back to Search</router-link>
    </div>

    <div v-else-if="operator" class="profile-content">
      <!-- Hero Section -->
      <div class="hero-section" :style="operator.profile_image ? { backgroundImage: `url(${getImageUrl(operator.profile_image)})` } : {}">
        <div class="hero-overlay">
          <div class="container">
            <h1>{{ operator.business_name }}</h1>
            <div class="rating">
              ⭐ {{ operator.average_rating.toFixed(1) }} ({{ operator.total_reviews }} reviews)
            </div>
          </div>
        </div>
      </div>

      <div class="container">
        <!-- About Section -->
        <section class="about-section card">
          <h2>About</h2>
          <p>{{ operator.description || 'No description available' }}</p>
          
          <div class="operator-details">
            <div class="detail-item">
              <strong>📞 Contact:</strong>
              <span>{{ operator.contact_number }}</span>
            </div>
            <div class="detail-item" v-if="operator.years_of_experience">
              <strong>📅 Experience:</strong>
              <span>{{ operator.years_of_experience }} years</span>
            </div>
            <div class="detail-item" v-if="operator.specializations.length > 0">
              <strong>🎯 Specializations:</strong>
              <div class="tags">
                <span v-for="spec in operator.specializations" :key="spec" class="tag">{{ spec }}</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Serving Areas Section -->
        <section v-if="operator.serving_areas && operator.serving_areas.length > 0" class="serving-areas-section">
          <h2>Serving Areas</h2>
          
          <!-- Map with all locations -->
          <div class="map-card card">
            <h3>All Locations on Map</h3>
            <MapView 
              :locations="allLocations"
              :zoom="8"
              height="450px"
            />
          </div>

          <div class="areas-grid">
            <div v-for="(area, idx) in operator.serving_areas" :key="idx" class="area-card card">
              <h3>{{ area.area_name }}, {{ area.state }}</h3>
              <p v-if="area.description">{{ area.description }}</p>

              <!-- Area Images -->
              <div v-if="area.images && area.images.length > 0" class="area-gallery">
                <img 
                  v-for="(img, imgIdx) in area.images.slice(0, 3)" 
                  :key="imgIdx"
                  :src="getImageUrl(img)" 
                  :alt="`${area.area_name} ${imgIdx + 1}`"
                  class="gallery-image"
                />
              </div>

              <!-- Sub-locations -->
              <div v-if="area.sub_locations && area.sub_locations.length > 0" class="sub-locations">
                <h4>Attractions</h4>
                <div class="sub-locations-list">
                  <div 
                    v-for="(sub, subIdx) in area.sub_locations" 
                    :key="subIdx"
                    :class="['sub-location-item', { 'has-image': sub.images && sub.images.length > 0 }]"
                  >
                    <div class="sub-location-images" v-if="sub.images && sub.images.length > 0">
                      <img :src="getImageUrl(sub.images[0])" :alt="sub.name" />
                    </div>
                    <div v-else class="sub-location-placeholder" aria-hidden="true">
                      <span class="placeholder-icon">📍</span>
                      <span class="placeholder-text">No image</span>
                    </div>
                    <div class="sub-location-info">
                      <div class="sub-location-header">
                        <h5>{{ sub.name }}</h5>
                        <span v-if="sub.popular" class="popular-badge">⭐ Popular</span>
                      </div>
                      <p v-if="sub.description">{{ sub.description }}</p>
                      <div v-if="sub.coordinates" class="location-coords">
                        📍 {{ sub.coordinates.latitude.toFixed(4) }}, {{ sub.coordinates.longitude.toFixed(4) }}
                      </div>
                    </div>
                    <div class="sub-location-actions">
                      <button
                        v-if="sub.coordinates"
                        @click="viewOnMap(area, sub)"
                        class="btn btn-secondary btn-sm"
                      >
                        View on Map
                      </button>
                      <button 
                        @click="addToCart(area, sub)" 
                        class="btn btn-primary btn-sm"
                        :disabled="isInCart(area, sub)"
                      >
                        {{ isInCart(area, sub) ? 'In Cart' : '+ Add to Cart' }}
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </section>

        <!-- Reviews Section -->
        <section class="reviews-section card">
          <h2>Reviews & Ratings</h2>
          
          <div v-if="reviews && reviews.length > 0" class="reviews-list">
            <div v-for="review in reviews" :key="review._id" class="review-item">
              <div class="review-header">
                <div>
                  <h4>{{ review.tourist_name || 'Anonymous' }}</h4>
                  <div class="rating">⭐ {{ review.rating }} / 5</div>
                </div>
                <span class="review-date">{{ new Date(review.created_at).toLocaleDateString() }}</span>
              </div>
              <p v-if="review.review" class="review-text">{{ review.review }}</p>
            </div>
          </div>

          <div v-else class="empty-state">
            <p>No reviews yet</p>
          </div>
        </section>

        <!-- Contact Section -->
        <section class="contact-section card">
          <h2>Ready to Book?</h2>
          <p>Add your desired locations to the cart and send a booking request to this operator.</p>
          <div class="action-buttons">
            <button v-if="isAuthenticated && isTourist" @click="startChat" class="btn btn-success btn-lg">
              💬 Chat with Operator
            </button>
            <router-link to="/cart" class="btn btn-primary btn-lg">View Cart</router-link>
            <button @click="scrollToTop" class="btn btn-secondary btn-lg">Back to Top</button>
          </div>
        </section>

        <div v-if="showMapModal" class="map-modal">
          <div class="map-modal-content card">
            <div class="modal-header">
              <h4>{{ selectedLocation?.title }}</h4>
              <button class="close-btn" @click="closeMapModal">X</button>
            </div>
            <MapView
              v-if="selectedLocation"
              :locations="[selectedLocation]"
              :center="{ lat: selectedLocation.lat, lng: selectedLocation.lng }"
              :zoom="12"
              height="320px"
              :show-coordinates="false"
            />
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, computed } from 'vue';
import { useRoute } from 'vue-router';
import { useCartStore } from '../stores/cart';
import { useAuthStore } from '../stores/auth';
import { useChatStore } from '../stores/chat';
import api from '../services/api';
import MapView from '../components/MapView.vue';

const route = useRoute();
const cartStore = useCartStore();
const authStore = useAuthStore();
const chatStore = useChatStore();

const operator = ref(null);
const reviews = ref([]);
const loading = ref(true);
const error = ref(null);
const showMapModal = ref(false);
const selectedLocation = ref(null);

const isAuthenticated = computed(() => authStore.isAuthenticated);
const isTourist = computed(() => authStore.isTourist);

onMounted(async () => {
  await loadOperatorProfile();
  cartStore.initCart();
});

const loadOperatorProfile = async () => {
  const operatorId = route.params.id;
  
  try {
    // Load operator profile
    const response = await api.get(`/operators/${operatorId}`);
    operator.value = response.data;

    // Load reviews
    try {
      const reviewsResponse = await api.get(`/bookings/ratings/operator/${operatorId}`);
      reviews.value = reviewsResponse.data.ratings || [];
    } catch (err) {
      console.error('Failed to load reviews:', err);
      reviews.value = [];
    }
  } catch (err) {
    error.value = err.response?.data?.detail || 'Failed to load operator profile';
  } finally {
    loading.value = false;
  }
};

const allLocations = computed(() => {
  if (!operator.value || !operator.value.serving_areas) return [];
  
  const locations = [];
  operator.value.serving_areas.forEach(area => {
    if (area.sub_locations) {
      area.sub_locations.forEach(sub => {
        if (sub.coordinates) {
          locations.push({
            lat: sub.coordinates.latitude,
            lng: sub.coordinates.longitude,
            title: sub.name,
            description: sub.description || area.area_name
          });
        }
      });
    }
  });
  return locations;
});

const getImageUrl = (url) => {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  return `http://localhost:8808${url}`;
};

const addToCart = (area, subLocation) => {
  cartStore.addToCart({
    operator_id: operator.value._id,
    operator_name: operator.value.business_name,
    area_name: area.area_name,
    state: area.state,
    country: area.country,
    sub_location_name: subLocation.name,
    description: subLocation.description,
    coordinates: subLocation.coordinates,
    images: subLocation.images || []
  });
};

const isInCart = (area, subLocation) => {
  return cartStore.cartItems.some(
    item => item.operator_id === operator.value._id && 
           item.sub_location_name === subLocation.name
  );
};

const viewOnMap = (area, subLocation) => {
  if (!subLocation.coordinates) return;
  selectedLocation.value = {
    lat: subLocation.coordinates.latitude,
    lng: subLocation.coordinates.longitude,
    title: `${subLocation.name} (${area.area_name})`,
    description: subLocation.description || ''
  };
  showMapModal.value = true;
};

const closeMapModal = () => {
  showMapModal.value = false;
};

const startChat = async () => {
  if (!operator.value) return;
  
  await chatStore.openConversation(
    operator.value.user_id,
    operator.value.business_name,
    'operator'
  );
};

const scrollToTop = () => {
  window.scrollTo({ top: 0, behavior: 'smooth' });
};
</script>

<style scoped>
.operator-profile-page {
  min-height: 100vh;
  background: #f5f5f5;
}

.loading-container, .error-container {
  padding: 100px 20px;
  text-align: center;
}

.hero-section {
  height: 400px;
  background-size: cover;
  background-position: center;
  background-color: #667eea;
  position: relative;
}

.hero-overlay {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  color: white;
  text-align: center;
}

.hero-section h1 {
  font-size: 3em;
  margin: 0 0 15px;
}

.hero-section .rating {
  font-size: 1.5em;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

.profile-content {
  padding-bottom: 50px;
}

section {
  margin: 30px 0;
}

.card {
  background: white;
  padding: 30px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
}

h2 {
  margin: 0 0 20px;
  color: #333;
  font-size: 2em;
}

h3 {
  margin: 0 0 15px;
  color: #444;
}

.operator-details {
  margin-top: 25px;
  display: flex;
  flex-direction: column;
  gap: 15px;
}

.detail-item {
  display: flex;
  align-items: center;
  gap: 10px;
}

.detail-item strong {
  min-width: 150px;
  color: #555;
}

.tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.tag {
  padding: 5px 12px;
  background: #e3f2fd;
  color: #1976d2;
  border-radius: 15px;
  font-size: 0.9em;
}

.map-card {
  margin-bottom: 30px;
}

.areas-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
  gap: 25px;
  margin-top: 25px;
}

.area-card {
  height: fit-content;
}

.area-gallery {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 10px;
  margin: 15px 0;
}

.gallery-image {
  width: 100%;
  height: 120px;
  object-fit: cover;
  border-radius: 8px;
}

.sub-locations {
  margin-top: 20px;
}

.sub-locations h4 {
  margin-bottom: 15px;
  color: #555;
}

.sub-locations-list {
  display: grid;
  gap: 15px;
}

.sub-location-item {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 148px;
  gap: 16px;
  padding: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  border-radius: 14px;
  border: 1px solid #dfe8f3;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  align-items: start;
}

.sub-location-item.has-image {
  grid-template-columns: 108px minmax(0, 1fr) 148px;
}

.sub-location-images {
  width: 108px;
  height: 108px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
}

.sub-location-placeholder {
  width: 108px;
  height: 108px;
  border-radius: 8px;
  border: 1px dashed #cdd8e6;
  background: linear-gradient(135deg, #eef5ff 0%, #f8fbff 100%);
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 0.35rem;
  text-align: center;
  padding: 0.75rem;
}

.placeholder-icon {
  font-size: 1.35rem;
}

.placeholder-text {
  font-size: 0.78rem;
  font-weight: 600;
  color: #5a6a7d;
  line-height: 1.3;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.sub-location-images img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.sub-location-info {
  flex: 1;
  min-width: 0;
}

.sub-location-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
  flex-wrap: wrap;
  gap: 0.65rem;
  margin-bottom: 0.5rem;
}

.sub-location-info h5 {
  margin: 0;
  color: #333;
  font-size: 1.02rem;
  line-height: 1.3;
  flex: 0 1 auto;
  min-width: 0;
}

.popular-badge {
  font-size: 0.8em;
  padding: 0.18rem 0.55rem;
  background: #ffc107;
  color: white;
  border-radius: 999px;
  font-weight: 600;
  flex-shrink: 0;
  white-space: nowrap;
}

.sub-location-info p {
  margin: 0 0 10px;
  color: #58606e;
  font-size: 0.94em;
  line-height: 1.55;
}

.location-coords {
  display: inline-flex;
  align-items: center;
  padding: 0.32rem 0.65rem;
  border-radius: 999px;
  background: #eef4fb;
  color: #516070;
  font-size: 0.82em;
  font-weight: 500;
}

.sub-location-actions {
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
  justify-content: center;
  align-self: stretch;
}

.sub-location-actions .btn {
  width: 100%;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.reviews-list {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.review-item {
  padding: 20px;
  background: #f9f9f9;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.review-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 10px;
}

.review-header h4 {
  margin: 0 0 5px;
  color: #333;
}

.review-date {
  color: #888;
  font-size: 0.9em;
}

.review-text {
  margin: 0;
  color: #555;
  line-height: 1.6;
}

.contact-section {
  text-align: center;
}

.contact-section p {
  margin-bottom: 25px;
  font-size: 1.1em;
  color: #666;
}

.action-buttons {
  display: flex;
  gap: 15px;
  justify-content: center;
  flex-wrap: wrap;
}

.map-modal {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 20;
}

.map-modal-content {
  width: min(720px, 90vw);
  border-radius: 12px;
  position: relative;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 10px;
}

.close-btn {
  background: transparent;
  border: none;
  font-size: 1.1rem;
  cursor: pointer;
}

.btn {
  padding: 10px 20px;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1em;
  transition: all 0.3s;
  text-decoration: none;
  display: inline-block;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 0.9em;
}

.btn-lg {
  padding: 15px 35px;
  font-size: 1.1em;
}

.btn-primary {
  background: #4CAF50;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #45a049;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-secondary {
  background: #757575;
  color: white;
}

.btn-secondary:hover {
  background: #616161;
}

.empty-state {
  padding: 40px;
  text-align: center;
  color: #888;
}

@media (max-width: 768px) {
  .hero-section h1 {
    font-size: 2em;
  }

  .areas-grid {
    grid-template-columns: 1fr;
  }

  .sub-location-item {
    grid-template-columns: 1fr;
    padding: 16px;
  }

  .sub-location-item.has-image {
    grid-template-columns: 1fr;
  }

  .sub-location-images {
    width: 100%;
    height: 200px;
  }

  .sub-location-placeholder {
    width: 100%;
    height: 140px;
  }

  .sub-location-header {
    align-items: flex-start;
    gap: 0.45rem;
  }

  .sub-location-info h5 {
    font-size: 0.98rem;
  }

  .popular-badge {
    font-size: 0.75em;
  }

  .sub-location-actions {
    width: 100%;
  }
}
</style>
