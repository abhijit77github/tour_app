<template>
  <div class="cart-view">
    <div class="container">
      <h1>My Cart</h1>

      <div v-if="cartStore.hasItems" class="cart-content">
        <!-- Cart Statistics -->
        <div class="cart-summary">
          <div class="summary-card">
            <h3>{{ cartStore.cartCount }} Locations Selected</h3>
            <p>{{ Object.keys(cartByOperator).length }} Operator(s)</p>
          </div>
        </div>

        <!-- Map View -->
        <div class="map-section card">
          <h2>View Locations on Map</h2>
          <MapView 
            :locations="cartStore.cartLocations"
            :zoom="10"
            height="400px"
          />
        </div>

        <!-- Cart Items by Operator -->
        <div v-for="(operatorGroup, operatorId) in cartByOperator" :key="operatorId" class="operator-group card">
          <div class="operator-header">
            <h2>{{ operatorGroup.operatorName || 'Operator' }}</h2>
            <router-link :to="`/operator/${operatorId}`" class="view-profile-btn">View Profile</router-link>
          </div>

          <div v-for="(areaGroup, idx) in operatorGroup.areas" :key="idx" class="area-group">
            <h3>{{ areaGroup.area_name }}, {{ areaGroup.state }}</h3>

            <div class="cart-items">
              <div 
                v-for="(item, itemIdx) in areaGroup.items" 
                :key="itemIdx" 
                class="cart-item"
                :class="{ 'item-excluded': !item.selected }"
              >
                <div class="item-image" v-if="item.images && item.images.length > 0">
                  <img :src="getImageUrl(item.images[0])" :alt="item.sub_location_name" />
                </div>
                <div class="item-image placeholder" v-else>
                  <span>📷</span>
                </div>

                <div class="item-details">
                  <h4>{{ item.sub_location_name }}</h4>
                  <p>{{ item.description }}</p>
                  <div v-if="item.coordinates" class="coordinates">
                    📍 {{ item.coordinates.latitude.toFixed(4) }}, {{ item.coordinates.longitude.toFixed(4) }}
                  </div>
                </div>

                <div class="item-actions">
                  <button 
                    @click="cartStore.toggleItemSelection(getItemIndex(item))" 
                    :class="['btn', item.selected ? 'btn-warning' : 'btn-success']"
                  >
                    {{ item.selected ? 'Exclude' : 'Include' }}
                  </button>
                  <button 
                    @click="cartStore.removeFromCart(getItemIndex(item))" 
                    class="btn btn-danger"
                  >
                    Remove
                  </button>
                </div>
              </div>
            </div>

            <div class="area-actions">
              <button 
                @click="sendBookingRequest(operatorId)" 
                class="btn btn-primary btn-lg"
                :disabled="cartStore.loading"
              >
                {{ cartStore.loading ? 'Sending...' : 'Send Booking Request' }}
              </button>
            </div>
          </div>
        </div>
      </div>

      <div v-else class="empty-cart">
        <div class="empty-state">
          <h2>Your cart is empty</h2>
          <p>Browse operators and add locations to your cart</p>
          <router-link to="/search" class="btn btn-primary">Search Operators</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useRouter } from 'vue-router';
import { useCartStore } from '../stores/cart';
import MapView from '../components/MapView.vue';

const router = useRouter();
const cartStore = useCartStore();

onMounted(() => {
  cartStore.initCart();
});

const cartByOperator = computed(() => {
  const grouped = {};
  
  cartStore.cartItems.forEach(item => {
    if (!grouped[item.operator_id]) {
      grouped[item.operator_id] = {
        operatorName: item.operator_name || 'Unknown Operator',
        areas: []
      };
    }

    // Group by area within operator
    let areaGroup = grouped[item.operator_id].areas.find(
      a => a.area_name === item.area_name && a.state === item.state
    );

    if (!areaGroup) {
      areaGroup = {
        area_name: item.area_name,
        state: item.state,
        country: item.country,
        items: []
      };
      grouped[item.operator_id].areas.push(areaGroup);
    }

    areaGroup.items.push(item);
  });

  return grouped;
});

const getItemIndex = (item) => {
  return cartStore.cartItems.findIndex(
    i => i.operator_id === item.operator_id && 
        i.sub_location_name === item.sub_location_name
  );
};

const getImageUrl = (url) => {
  if (url.startsWith('http')) return url;
  return `http://localhost:8808${url}`;
};

const sendBookingRequest = async (operatorId) => {
  try {
    await cartStore.sendBookingRequest(operatorId);
    alert('Booking request sent successfully!');
    // Optionally navigate to bookings page
    // router.push('/my-bookings');
  } catch (error) {
    alert(error.message || 'Failed to send booking request');
  }
};
</script>

<style scoped>
.cart-view {
  padding: 20px 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 20px;
}

h1 {
  margin-bottom: 30px;
  color: #333;
}

.cart-summary {
  margin-bottom: 30px;
}

.summary-card {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 30px;
  border-radius: 12px;
  text-align: center;
}

.summary-card h3 {
  margin: 0 0 10px;
  font-size: 2em;
}

.summary-card p {
  margin: 0;
  font-size: 1.2em;
  opacity: 0.9;
}

.map-section {
  margin-bottom: 30px;
}

.map-section h2 {
  margin-bottom: 15px;
}

.operator-group {
  margin-bottom: 30px;
}

.operator-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 15px;
  border-bottom: 2px solid #eee;
}

.operator-header h2 {
  margin: 0;
  color: #333;
}

.view-profile-btn {
  padding: 8px 16px;
  background: #667eea;
  color: white;
  text-decoration: none;
  border-radius: 5px;
  transition: background 0.3s;
}

.view-profile-btn:hover {
  background: #5568d3;
}

.area-group {
  margin-bottom: 30px;
}

.area-group h3 {
  margin-bottom: 15px;
  color: #555;
}

.cart-items {
  display: flex;
  flex-direction: column;
  gap: 15px;
  margin-bottom: 20px;
}

.cart-item {
  display: flex;
  gap: 15px;
  padding: 15px;
  background: white;
  border: 2px solid #e0e0e0;
  border-radius: 8px;
  transition: all 0.3s;
}

.cart-item.item-excluded {
  opacity: 0.6;
  background: #f5f5f5;
}

.item-image {
  width: 120px;
  height: 120px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
}

.item-image.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  font-size: 3em;
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-details {
  flex: 1;
}

.item-details h4 {
  margin: 0 0 8px;
  color: #333;
}

.item-details p {
  margin: 0 0 8px;
  color: #666;
  font-size: 0.9em;
}

.coordinates {
  font-size: 0.85em;
  color: #888;
}

.item-actions {
  display: flex;
  flex-direction: column;
  gap: 8px;
  justify-content: center;
}

.item-actions .btn {
  white-space: nowrap;
  padding: 8px 16px;
  font-size: 0.9em;
}

.area-actions {
  text-align: center;
  padding-top: 20px;
  border-top: 1px solid #eee;
}

.btn-lg {
  padding: 12px 30px;
  font-size: 1.1em;
}

.empty-cart {
  padding: 80px 20px;
}

.empty-state {
  text-align: center;
  max-width: 500px;
  margin: 0 auto;
}

.empty-state h2 {
  margin-bottom: 15px;
  color: #666;
}

.empty-state p {
  margin-bottom: 25px;
  color: #888;
  font-size: 1.1em;
}

.card {
  background: white;
  padding: 25px;
  border-radius: 12px;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
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

.btn-success {
  background: #4CAF50;
  color: white;
}

.btn-success:hover {
  background: #45a049;
}

.btn-warning {
  background: #ff9800;
  color: white;
}

.btn-warning:hover {
  background: #e68900;
}

.btn-danger {
  background: #f44336;
  color: white;
}

.btn-danger:hover {
  background: #da190b;
}
</style>
