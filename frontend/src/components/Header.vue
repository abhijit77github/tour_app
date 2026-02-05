<template>
  <header class="header">
    <div class="container">
      <nav class="navbar">
        <div class="logo">
          <router-link to="/">🌍 Tour App</router-link>
        </div>
        <div class="nav-links">
          <router-link v-if="!isAuthenticated" to="/">Home</router-link>
          <router-link to="/search">Search Tours</router-link>
          <router-link v-if="isTourist" to="/quote-builder">Get a Quote</router-link>
          
          <template v-if="!isAuthenticated">
            <router-link to="/login">Login</router-link>
            <router-link to="/register" class="btn btn-primary">Register</router-link>
          </template>
          
          <template v-else>
            <router-link v-if="isOperator" to="/operator/dashboard">Dashboard</router-link>
            <router-link v-if="isTourist && !isOnTouristHome" to="/tourist/home">Home</router-link>
            <router-link v-if="isTourist" to="/my-bookings">My Bookings</router-link>
            <router-link v-if="isTourist" to="/cart" class="cart-link">
              🛒 Cart
              <span v-if="cartCount > 0" class="cart-badge">{{ cartCount }}</span>
            </router-link>
            <span class="user-name">{{ user?.full_name }}</span>
            <button @click="handleLogout" class="btn btn-secondary">Logout</button>
          </template>
        </div>
      </nav>
    </div>
  </header>
</template>

<script>
import { computed, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useCartStore } from '../stores/cart'

export default {
  name: 'Header',
  setup() {
    const authStore = useAuthStore()
    const cartStore = useCartStore()
    const router = useRouter()
    const route = useRoute()

    const isAuthenticated = computed(() => authStore.isAuthenticated)
    const isOperator = computed(() => authStore.isOperator)
    const isTourist = computed(() => authStore.isTourist)
    const user = computed(() => authStore.user)
    const cartCount = computed(() => cartStore.cartCount)
    const isOnTouristHome = computed(() => route.name === 'TouristHome')

    onMounted(() => {
      if (isTourist.value) {
        cartStore.initCart()
      }
    })

    const handleLogout = () => {
      authStore.logout()
      router.push('/')
    }

    return {
      isAuthenticated,
      isOperator,
      isTourist,
      user,
      cartCount,
      isOnTouristHome,
      handleLogout
    }
  }
}
</script>

<style scoped>
.header {
  background: white;
  box-shadow: 0 2px 4px rgba(0,0,0,0.1);
  padding: 1rem 0;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo a {
  font-size: 1.5rem;
  font-weight: bold;
  color: #3498db;
  text-decoration: none;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.nav-links a {
  text-decoration: none;
  color: #333;
  transition: color 0.3s;
}

.nav-links a:hover {
  color: #3498db;
}

.cart-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 500;
}

.cart-badge {
  position: absolute;
  top: -8px;
  right: -10px;
  background: #e74c3c;
  color: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 0.7em;
  font-weight: bold;
}


.user-name {
  font-weight: 500;
  color: #555;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 5px;
  text-decoration: none;
  display: inline-block;
}
</style>
