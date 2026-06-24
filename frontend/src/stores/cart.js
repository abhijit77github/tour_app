import { defineStore } from 'pinia';
import api from '../services/api';

export const useCartStore = defineStore('cart', {
  state: () => ({
    cartItems: [], // Array of selected sub-locations
    selectedOperator: null,
    loading: false,
    error: null
  }),

  getters: {
    cartCount: (state) => state.cartItems.length,
    
    hasItems: (state) => state.cartItems.length > 0,
    
    cartByArea: (state) => {
      const grouped = {};
      state.cartItems.forEach(item => {
        const key = `${item.area_name}-${item.state}`;
        if (!grouped[key]) {
          grouped[key] = {
            area_name: item.area_name,
            state: item.state,
            country: item.country,
            operator_id: item.operator_id,
            items: []
          };
        }
        grouped[key].items.push(item);
      });
      return Object.values(grouped);
    },

    cartLocations: (state) => {
      return state.cartItems.map(item => ({
        lat: Number(item.coordinates?.latitude),
        lng: Number(item.coordinates?.longitude),
        title: item.sub_location_name,
        description: item.description
      })).filter(loc => Number.isFinite(loc.lat) && Number.isFinite(loc.lng));
    }
  },

  actions: {
    addToCart(item) {
      // Check if item already exists
      const exists = this.cartItems.find(
        i => i.operator_id === item.operator_id && 
            i.sub_location_name === item.sub_location_name &&
            (i.service_type || 'tour') === (item.service_type || 'tour')
      );

      if (!exists) {
        this.cartItems.push({
          operator_id: item.operator_id,
          operator_name: item.operator_name,
          service_type: item.service_type || 'tour',
          area_name: item.area_name,
          state: item.state,
          country: item.country,
          sub_location_name: item.sub_location_name,
          description: item.description,
          coordinates: item.coordinates,
          vehicle_type: item.vehicle_type,
          seats: item.seats,
          pricing_model: item.pricing_model,
          base_fare: item.base_fare,
          images: item.images || [],
          selected: true
        });
        this.saveToLocalStorage();
      }
    },

    removeFromCart(index) {
      this.cartItems.splice(index, 1);
      this.saveToLocalStorage();
    },

    toggleItemSelection(index) {
      if (this.cartItems[index]) {
        this.cartItems[index].selected = !this.cartItems[index].selected;
        this.saveToLocalStorage();
      }
    },

    clearCart() {
      this.cartItems = [];
      this.selectedOperator = null;
      this.saveToLocalStorage();
    },

    async sendBookingRequest(operatorId) {
      this.loading = true;
      this.error = null;

      try {
        // Group cart items by area for this operator
        const operatorItems = this.cartItems.filter(item => item.operator_id === operatorId);
        
        if (operatorItems.length === 0) {
          throw new Error('No items for this operator');
        }

        const firstItem = operatorItems[0];
        
        const bookingData = {
          operator_id: operatorId,
          cart: {
            area_name: firstItem.area_name,
            state: firstItem.state,
            country: firstItem.country,
            items: operatorItems.map(item => ({
              sub_location_name: item.sub_location_name,
              description: item.description,
              selected: item.selected
            }))
          }
        };

        const response = await api.post('/bookings/', bookingData);
        
        // Remove sent items from cart
        this.cartItems = this.cartItems.filter(item => item.operator_id !== operatorId);
        this.saveToLocalStorage();

        return response.data;
      } catch (err) {
        this.error = err.response?.data?.detail || 'Failed to send booking request';
        throw err;
      } finally {
        this.loading = false;
      }
    },

    saveToLocalStorage() {
      localStorage.setItem('cart', JSON.stringify(this.cartItems));
    },

    loadFromLocalStorage() {
      const saved = localStorage.getItem('cart');
      if (saved) {
        try {
          this.cartItems = JSON.parse(saved);
        } catch (e) {
          console.error('Failed to load cart from localStorage:', e);
          this.cartItems = [];
        }
      }
    },

    async rehydrateMissingCoordinates() {
      const missingItems = this.cartItems.filter(
        item => !Number.isFinite(Number(item.coordinates?.latitude)) ||
                !Number.isFinite(Number(item.coordinates?.longitude))
      );

      if (missingItems.length === 0) {
        return;
      }

      const profileCache = new Map();
      let changed = false;

      for (const item of missingItems) {
        if (!item.operator_id) continue;

        if (!profileCache.has(item.operator_id)) {
          try {
            const response = await api.get(`/operators/${item.operator_id}`);
            profileCache.set(item.operator_id, response.data || null);
          } catch (err) {
            profileCache.set(item.operator_id, null);
            continue;
          }
        }

        const profile = profileCache.get(item.operator_id);
        if (!profile) continue;

        const areaName = (item.area_name || '').trim().toLowerCase();
        const area = (profile.serving_areas || []).find(
          a => (a.area_name || '').trim().toLowerCase() === areaName
        );
        if (!area) continue;

        let coords = area.coordinates || null;
        if (!coords || coords.latitude == null || coords.longitude == null) {
          const firstSub = (area.sub_locations || []).find(
            sub => sub.coordinates && sub.coordinates.latitude != null && sub.coordinates.longitude != null
          );
          coords = firstSub?.coordinates || null;
        }

        if (coords && coords.latitude != null && coords.longitude != null) {
          item.coordinates = {
            latitude: Number(coords.latitude),
            longitude: Number(coords.longitude),
          };
          changed = true;
        }
      }

      if (changed) {
        this.saveToLocalStorage();
      }
    },

    initCart() {
      this.loadFromLocalStorage();
    }
  }
});
