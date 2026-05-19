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
            i.sub_location_name === item.sub_location_name
      );

      if (!exists) {
        this.cartItems.push({
          operator_id: item.operator_id,
          area_name: item.area_name,
          state: item.state,
          country: item.country,
          sub_location_name: item.sub_location_name,
          description: item.description,
          coordinates: item.coordinates,
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

    initCart() {
      this.loadFromLocalStorage();
    }
  }
});
