<template>
  <header class="header">
    <div class="container">
      <nav class="navbar">
        <div class="brand-shell">
          <router-link :to="brandLinkTarget" class="brand-link" @click="mobileMenuOpen = false">
            <img :src="brandLogo" :alt="adminBrand.logoAlt" class="brand-logo" />
          </router-link>

          <button
            class="mobile-menu-toggle"
            type="button"
            :aria-expanded="mobileMenuOpen ? 'true' : 'false'"
            aria-label="Toggle navigation"
            @click="mobileMenuOpen = !mobileMenuOpen"
          >
            <span></span>
            <span></span>
            <span></span>
          </button>
        </div>
        <div class="nav-links" :class="{ open: mobileMenuOpen }">
          <router-link v-if="!authPending && !isAuthenticated" to="/">Home</router-link>
          <router-link v-if="!authPending && !isAuthenticated" to="/search">Search Tours</router-link>
          
          <template v-if="!authPending && !isAuthenticated">
            <router-link to="/login">Login</router-link>
            <router-link to="/register" class="btn btn-primary">Register</router-link>
          </template>
          
          <template v-else-if="isAuthenticated">
            <div class="nav-auth-group nav-auth-primary">
              <router-link v-if="isOperator" to="/operator/home">Home</router-link>
              <router-link v-if="isOperator" to="/operator/dashboard">Dashboard</router-link>
              <router-link v-if="isOperator && canReadOperatorTickets" to="/operator/tickets">Support</router-link>
              <router-link v-if="isOperator && canManageOperatorTeam" to="/operator/team">Team Access</router-link>
              <router-link v-if="isTourist" to="/my-bookings">My Bookings</router-link>
              <router-link v-if="isTourist" to="/cart" class="cart-link">
                <span class="cart-icon" aria-hidden="true">🛒</span>
                <span class="cart-label">Cart</span>
                <span v-if="cartCount > 0" class="cart-badge">{{ cartCount }}</span>
              </router-link>
              <router-link to="/notifications" class="notif-link">
                <span class="notif-icon" aria-hidden="true">🔔</span>
                <span class="notif-label">Notifications</span>
                <span v-if="notificationUnreadCount > 0" class="notif-badge">{{ notificationUnreadCount }}</span>
              </router-link>
            </div>
            <div class="nav-auth-group nav-auth-meta">
              <span class="user-name">{{ user?.full_name }}</span>
              <button @click="handleLogout" class="btn btn-secondary">Logout</button>
            </div>
          </template>
        </div>
      </nav>
    </div>
  </header>
</template>

<script>
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { useCartStore } from '../stores/cart'
import { useNotificationsStore } from '../stores/notifications'
import { useAccessStore } from '../stores/access'
import brandLogo from '../../resources/logo/app_logo_compact.svg'
import { adminBrandConfig } from '../config/adminBrand'

export default {
  name: 'Header',
  setup() {
    const authStore = useAuthStore()
    const cartStore = useCartStore()
    const notificationsStore = useNotificationsStore()
    const accessStore = useAccessStore()
    const router = useRouter()
    const route = useRoute()
    const adminBrand = adminBrandConfig

    const isAuthenticated = computed(() => !!authStore.user)
    const isOperator = computed(() => authStore.isOperator)
    const isTourist = computed(() => authStore.isTourist)
    const user = computed(() => authStore.user)
    const authPending = computed(() => !!authStore.token && !authStore.initialized)
    const cartCount = computed(() => cartStore.cartCount)
    const notificationUnreadCount = computed(() => notificationsStore.unreadCount)
    const canReadOperatorTickets = computed(() => accessStore.hasOperatorPermission('operator.tickets.read'))
    const canManageOperatorTeam = computed(() => accessStore.hasOperatorPermission('operator.team.manage'))
    const brandLinkTarget = computed(() => {
      if (isTourist.value) {
        return '/tourist/home'
      }
      if (isOperator.value) {
        return '/operator/home'
      }
      return '/'
    })
    const mobileMenuOpen = ref(false)

    onMounted(() => {
      if (isTourist.value) {
        cartStore.initCart()
      }
      if (isAuthenticated.value) {
        notificationsStore.loadSummary()
        if (isOperator.value) {
          accessStore.loadOperatorContext().catch(() => {})
        }
      }
    })

    watch(isAuthenticated, (authenticated) => {
      if (authenticated) {
        notificationsStore.loadSummary()
        if (isOperator.value) {
          accessStore.loadOperatorContext(true).catch(() => {})
        }
      } else {
        notificationsStore.reset()
        accessStore.reset()
      }
    })

    watch(() => route.fullPath, () => {
      mobileMenuOpen.value = false
    })

    const handleLogout = () => {
      mobileMenuOpen.value = false
      notificationsStore.reset()
      accessStore.reset()
      authStore.logout()
      router.push('/')
    }

    return {
      isAuthenticated,
      isOperator,
      isTourist,
      user,
      authPending,
      cartCount,
      notificationUnreadCount,
      canReadOperatorTickets,
      canManageOperatorTeam,
      brandLinkTarget,
      adminBrand,
      brandLogo,
      mobileMenuOpen,
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
  padding: 0.72rem 0;
}

.header :deep(.container) {
  max-width: 1040px;
  padding: 0 20px;
}

.navbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.8rem;
}

.brand-shell {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  flex: 0 0 auto;
}

.brand-link {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
}

.brand-logo {
  width: 164px;
  height: 52px;
  object-fit: contain;
  flex-shrink: 0;
}

.nav-links {
  display: flex;
  align-items: center;
  gap: 0.55rem;
  flex-wrap: nowrap;
  justify-content: flex-end;
  flex: 1 1 auto;
  min-width: 0;
}

.nav-auth-group {
  display: flex;
  align-items: center;
  gap: 0.28rem;
  min-width: 0;
}

.nav-auth-primary {
  justify-content: flex-end;
  flex: 0 0 auto;
}

.nav-auth-meta {
  flex: 0 0 auto;
  padding-left: 0.35rem;
  margin-left: 0;
  border-left: 1px solid rgba(148, 163, 184, 0.22);
}

.nav-links a:not(.btn) {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
  text-decoration: none;
  color: #1f2937;
  transition: color 0.22s ease, background 0.22s ease, box-shadow 0.22s ease, transform 0.22s ease;
  font-weight: 600;
  padding: 0.38rem 0.48rem;
  border-radius: 999px;
  font-size: 0.95rem;
}

.nav-links a:not(.btn):hover {
  color: #0f766e;
  background: rgba(15, 118, 110, 0.08);
  box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.08);
  transform: translateY(-1px);
}

.nav-links a.router-link-active:not(.btn) {
  color: #0f766e;
  background: rgba(15, 118, 110, 0.09);
  box-shadow: inset 0 0 0 1px rgba(15, 118, 110, 0.12);
}

.nav-links a.router-link-active:not(.btn)::after {
  content: none;
}

.nav-links .btn {
  text-decoration: none;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  padding: 0.42rem 0.82rem;
  border-radius: 8px;
  font-weight: 700;
  border: 1px solid transparent;
  transition: transform 0.22s ease, box-shadow 0.22s ease, background 0.22s ease, border-color 0.22s ease;
}

.nav-links .btn-secondary {
  white-space: nowrap;
}

.nav-links .btn::before {
  content: '';
  position: absolute;
  inset: 0;
  background: linear-gradient(120deg, transparent 20%, rgba(255, 255, 255, 0.22) 50%, transparent 80%);
  transform: translateX(-130%);
  transition: transform 0.32s ease;
}

.nav-links .btn-primary {
  color: #ffffff;
  background: linear-gradient(135deg, #0f766e 0%, #0d9488 100%);
  border-color: rgba(15, 118, 110, 0.18);
  box-shadow: 0 10px 22px rgba(15, 118, 110, 0.2);
}

.nav-links .btn-primary:hover {
  color: #ffffff;
  background: linear-gradient(135deg, #0c6a64 0%, #14b8a6 100%);
  border-color: rgba(204, 251, 241, 0.62);
  box-shadow:
    0 16px 30px rgba(15, 118, 110, 0.3),
    0 0 0 4px rgba(45, 212, 191, 0.16);
  transform: translateY(-2px);
}

.nav-links .btn-primary:active {
  transform: translateY(0);
  box-shadow: 0 8px 18px rgba(15, 118, 110, 0.2);
}

.nav-links .btn:hover::before,
.nav-links .btn:focus-visible::before {
  transform: translateX(130%);
}

.mobile-menu-toggle {
  display: none;
  width: 46px;
  height: 46px;
  border: 1px solid rgba(15, 23, 42, 0.08);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.9);
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.08);
  align-items: center;
  justify-content: center;
  gap: 4px;
  flex-direction: column;
}

.mobile-menu-toggle span {
  width: 18px;
  height: 2px;
  border-radius: 999px;
  background: #0f172a;
}

.cart-link {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.25rem;
  font-weight: 600;
}

.cart-icon {
  font-size: 0.95rem;
  line-height: 1;
}

.cart-label {
  white-space: nowrap;
}

.notif-link {
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 0.38rem;
  font-weight: 600;
}

.notif-icon {
  font-size: 0.95rem;
  line-height: 1;
}

.notif-label {
  white-space: nowrap;
}

.notif-badge {
  position: absolute;
  top: -8px;
  right: -12px;
  background: #0f766e;
  color: #fff;
  border-radius: 999px;
  min-width: 20px;
  height: 20px;
  padding: 0 0.35rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-weight: 800;
}

.cart-badge {
  position: absolute;
  top: -8px;
  right: -10px;
  background: #e74c3c;
  color: #fff;
  border-radius: 999px;
  min-width: 20px;
  height: 20px;
  padding: 0 0.35rem;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  font-size: 0.72rem;
  font-weight: 800;
}

.user-name {
  font-weight: 600;
  color: #334155;
  max-width: 96px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  font-size: 0.84rem;
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
    align-items: stretch;
    gap: 0.9rem;
  }

  .brand-shell {
    justify-content: space-between;
  }

  .brand-logo {
    width: 164px;
    height: 52px;
  }

  .mobile-menu-toggle {
    display: inline-flex;
  }

  .nav-links {
    display: none;
    width: 100%;
    justify-content: flex-start;
    flex-wrap: wrap;
    gap: 0.8rem;
    padding: 1rem;
    border-radius: 18px;
    background: linear-gradient(180deg, rgba(255, 255, 255, 0.98), rgba(248, 250, 252, 0.98));
    border: 1px solid rgba(148, 163, 184, 0.18);
    box-shadow: 0 18px 30px rgba(15, 23, 42, 0.08);
  }

  .nav-links.open {
    display: grid;
  }

  .nav-auth-group {
    display: contents;
  }

  .nav-auth-meta {
    padding-left: 0;
    margin-left: 0;
    border-left: 0;
  }

  .nav-auth-meta {
    border-left: 0;
    padding-left: 0;
    margin-left: 0;
  }

  .nav-links a:not(.btn),
  .nav-links .btn,
  .nav-links .user-name,
  .nav-links button {
    width: 100%;
  }

  .nav-links a:not(.btn) {
    padding: 0.55rem 0;
  }

  .nav-links .btn,
  .nav-links button {
    justify-content: center;
  }

  .user-name {
    max-width: 100%;
    padding: 0.25rem 0;
  }

  .notif-link,
  .cart-link {
    justify-content: flex-start;
  }
}
</style>
