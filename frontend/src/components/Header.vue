<template>
  <header class="header">
    <div class="container">
      <nav class="navbar">
        <div class="logo">
          <router-link to="/">🌍 Tour App</router-link>
        </div>
        <div class="nav-links">
          <router-link v-if="!isAuthenticated" to="/">Home</router-link>
          <router-link v-if="!isOperator" to="/search">Search Tours</router-link>
          <router-link v-if="isTourist" to="/quote-builder">Get a Quote</router-link>
          <router-link v-if="isTourist" to="/plan">🗺️ Plan a Trip</router-link>
          
          <template v-if="!isAuthenticated">
            <router-link to="/login">Login</router-link>
            <router-link to="/register" class="btn btn-primary">Register</router-link>
          </template>
          
          <template v-else>
            <router-link v-if="isOperator" to="/operator/home">Home</router-link>
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
  position: sticky;
  top: 0;
  z-index: 2000;
  background: rgba(255, 255, 255, 0.94);
  backdrop-filter: blur(8px);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.08);
  border-bottom: 1px solid rgba(15, 23, 42, 0.08);
  padding: 0.85rem 0;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.logo a {
  font-size: 1.35rem;
  font-weight: 800;
  color: #1d4ed8;
  text-decoration: none;
  letter-spacing: 0.2px;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 0.95rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.nav-links a:not(.btn) {
  position: relative;
  text-decoration: none;
  color: #1f2937;
  transition: color 0.2s ease;
  font-weight: 500;
  padding: 0.2rem 0;
}

.nav-links a:not(.btn):hover {
  color: #1d4ed8;
}

.nav-links a.router-link-active:not(.btn) {
  color: #1d4ed8;
}

.nav-links a.router-link-active:not(.btn)::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -4px;
  height: 2px;
  border-radius: 999px;
  background: #1d4ed8;
}

.nav-links .btn {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-weight: 700;
}

.nav-links .btn-primary {
  color: #ffffff;
  background: #0f766e;
  box-shadow: 0 6px 16px rgba(15, 118, 110, 0.22);
}

.nav-links .btn-primary:hover {
  color: #ffffff;
  background: #0b5f59;
}

.cart-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 5px;
  font-weight: 600;
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
  font-weight: 600;
  color: #334155;
  max-width: 180px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.btn {
  padding: 0.5rem 1rem;
  border-radius: 8px;
  text-decoration: none;
  display: inline-block;
}

@media (max-width: 900px) {
  .navbar {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.7rem;
  }

  .nav-links {
    width: 100%;
    justify-content: flex-start;
    gap: 0.75rem;
  }

  .user-name {
    max-width: 100%;
  }
}
</style>
