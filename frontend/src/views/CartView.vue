<template>
  <div class="cart-view">
    <div class="container">
      <section class="cart-hero card">
        <div>
          <p class="hero-kicker">Trip cart</p>
          <h1>Review locations before sending requests</h1>
          <p class="hero-sub">Keep only the places you want, then send each operator a clean booking request.</p>
        </div>
        <div v-if="cartStore.hasItems" class="hero-metrics">
          <div>
            <strong>{{ cartStore.cartCount }}</strong>
            <span>Locations</span>
          </div>
          <div>
            <strong>{{ selectedCount }}</strong>
            <span>Included</span>
          </div>
          <div>
            <strong>{{ operatorCount }}</strong>
            <span>Operators</span>
          </div>
        </div>
      </section>

      <div v-if="cartStore.hasItems" class="cart-content">
        <div class="map-section card">
          <div class="section-head">
            <h2>Map Preview</h2>
            <span class="muted">Visual check before booking</span>
          </div>
          <MapView 
            :locations="cartStore.cartLocations"
            :zoom="10"
            height="400px"
          />
        </div>

        <div v-for="(operatorGroup, operatorId) in cartByOperator" :key="operatorId" class="operator-group card">
          <div class="operator-header">
            <div>
              <h2>{{ operatorGroup.operatorName || 'Operator' }}</h2>
              <p class="operator-meta">{{ operatorGroup.areas.length }} area group(s) • {{ selectedItemsForOperator(operatorId) }} item(s) included</p>
            </div>
            <div class="operator-actions">
              <router-link :to="`/operator/${operatorId}`" class="view-profile-btn">View Profile</router-link>
              <button 
                @click="sendBookingRequest(operatorId)" 
                class="btn btn-primary"
                :disabled="cartStore.loading"
              >
                {{ cartStore.loading ? 'Sending...' : 'Send Request' }}
              </button>
            </div>
          </div>

          <div v-for="(areaGroup, idx) in operatorGroup.areas" :key="idx" class="area-group">
            <div class="area-header">
              <h3>{{ areaGroup.area_name }}, {{ areaGroup.state }}</h3>
              <span class="area-count">{{ areaGroup.items.length }} item(s)</span>
            </div>

            <div class="cart-items">
              <div 
                v-for="(item, itemIdx) in areaGroup.items" 
                :key="itemIdx" 
                class="cart-item"
                :class="{ 'item-excluded': !item.selected }"
              >
                <div class="item-main">
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
                </div>

                <div class="item-actions">
                  <button 
                    @click="cartStore.toggleItemSelection(getItemIndex(item))" 
                    :class="['btn', item.selected ? 'btn-ghost' : 'btn-success']"
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
          </div>
        </div>
      </div>

      <div v-else class="empty-cart">
        <div class="empty-state card">
          <h2>Your cart is empty</h2>
          <p>Add locations from search or tour planner recommendations to build your request shortlist.</p>
          <router-link to="/search" class="btn btn-primary">Search Operators</router-link>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted } from 'vue';
import { useCartStore } from '../stores/cart';
import MapView from '../components/MapView.vue';

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

const operatorCount = computed(() => Object.keys(cartByOperator.value).length);

const selectedCount = computed(() => {
  return cartStore.cartItems.filter(item => item.selected).length;
});

const selectedItemsForOperator = (operatorId) => {
  return cartStore.cartItems.filter(item => item.operator_id === operatorId && item.selected).length;
};

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
  padding: 16px 0 28px;
}

.container {
  max-width: 1240px;
  margin: 0 auto;
  padding: 0 20px;
}

.cart-hero {
  margin-bottom: 18px;
  display: flex;
  align-items: end;
  justify-content: space-between;
  gap: 16px;
}

.hero-kicker {
  margin: 0;
  font-size: 0.78rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #0f766e;
}

h1 {
  margin: 6px 0 8px;
  color: #0f172a;
  font-size: clamp(1.55rem, 2.2vw, 2rem);
  line-height: 1.2;
}

.hero-sub {
  margin: 0;
  color: #475569;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 10px;
  min-width: 280px;
}

.hero-metrics div {
  background: rgba(15, 118, 110, 0.08);
  border: 1px solid rgba(15, 118, 110, 0.16);
  border-radius: 10px;
  padding: 10px;
}

.hero-metrics strong {
  display: block;
  color: #0f172a;
  font-size: 1.1rem;
}

.hero-metrics span {
  color: #64748b;
  font-size: 0.78rem;
}

.cart-content {
  display: grid;
  gap: 16px;
}

.section-head {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 12px;
}

.section-head h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.1rem;
}

.muted {
  color: #64748b;
  font-size: 0.82rem;
}

.map-section {
  padding-bottom: 12px;
}

.operator-group {
  margin-bottom: 2px;
}

.operator-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 14px;
  padding-bottom: 12px;
  border-bottom: 1px solid #e2e8f0;
  gap: 14px;
}

.operator-header h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.15rem;
}

.operator-meta {
  margin: 4px 0 0;
  color: #64748b;
  font-size: 0.84rem;
}

.operator-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.view-profile-btn {
  padding: 8px 16px;
  background: #334155;
  color: white;
  text-decoration: none;
  border-radius: 8px;
  transition: background 0.3s;
  font-size: 0.88rem;
  font-weight: 700;
}

.view-profile-btn:hover {
  background: #1e293b;
}

.area-group {
  margin-bottom: 18px;
}

.area-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
  margin-bottom: 10px;
}

.area-group h3 {
  margin: 0;
  color: #334155;
  font-size: 1rem;
}

.area-count {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.2rem 0.55rem;
  border-radius: 999px;
  background: #eef2ff;
  color: #4338ca;
  font-size: 0.74rem;
  font-weight: 700;
}

.cart-items {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.cart-item {
  display: flex;
  justify-content: space-between;
  gap: 14px;
  padding: 12px;
  background: white;
  border: 1px solid #dbe4ee;
  border-radius: 12px;
  transition: all 0.3s;
}

.cart-item.item-excluded {
  opacity: 0.58;
  background: #f8fafc;
}

.item-main {
  display: flex;
  gap: 12px;
  min-width: 0;
  flex: 1;
}

.item-image {
  width: 92px;
  height: 92px;
  border-radius: 8px;
  overflow: hidden;
  flex-shrink: 0;
}

.item-image.placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  font-size: 2em;
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.item-details {
  flex: 1;
  min-width: 0;
}

.item-details h4 {
  margin: 0 0 8px;
  color: #0f172a;
  font-size: 0.98rem;
}

.item-details p {
  margin: 0 0 6px;
  color: #475569;
  font-size: 0.86rem;
  line-height: 1.45;
}

.coordinates {
  font-size: 0.78rem;
  color: #64748b;
}

.item-actions {
  display: flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
  justify-content: flex-end;
  flex-wrap: wrap;
  min-width: 170px;
}

.item-actions .btn {
  white-space: nowrap;
  padding: 8px 12px;
  font-size: 0.82rem;
}

.empty-cart {
  padding: 14px 0;
}

.empty-state {
  text-align: center;
  max-width: 560px;
  margin: 0 auto;
  padding: 34px 24px;
}

.empty-state h2 {
  margin-bottom: 15px;
  color: #666;
}

.empty-state p {
  margin-bottom: 25px;
  color: #64748b;
  font-size: 1rem;
}

.card {
  background: white;
  padding: 18px;
  border-radius: 12px;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}

.btn {
  padding: 10px 16px;
  border: none;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.9rem;
  font-weight: 700;
  transition: all 0.3s;
  text-decoration: none;
  display: inline-block;
}

.btn-primary {
  background: #0f766e;
  color: white;
}

.btn-primary:hover:not(:disabled) {
  background: #0b5f59;
}

.btn-primary:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.btn-success {
  background: #15803d;
  color: white;
}

.btn-success:hover {
  background: #166534;
}

.btn-ghost {
  background: #f1f5f9;
  color: #334155;
  border: 1px solid #d8e0e8;
}

.btn-ghost:hover {
  background: #e2e8f0;
}

.btn-danger {
  background: #f44336;
  color: white;
}

.btn-danger:hover {
  background: #da190b;
}

@media (max-width: 900px) {
  .container {
    padding: 0 12px;
  }

  .cart-hero {
    flex-direction: column;
    align-items: flex-start;
  }

  .hero-metrics {
    width: 100%;
    min-width: 0;
  }

  .operator-header {
    flex-direction: column;
    align-items: flex-start;
  }

  .operator-actions {
    width: 100%;
  }

  .cart-item {
    flex-direction: column;
  }

  .item-main {
    width: 100%;
  }

  .item-actions {
    width: 100%;
    justify-content: flex-start;
    min-width: 0;
  }
}
</style>
