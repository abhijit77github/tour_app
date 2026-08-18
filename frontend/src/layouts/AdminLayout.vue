<template>
  <div class="admin-layout">
    <!-- Top Header -->
    <header class="admin-header">
      <div class="header-left">
        <button class="menu-toggle" @click="sidebarOpen = !sidebarOpen">
          ☰ Menu
        </button>
        <div class="admin-brand">
          <img :src="brandLogo" :alt="adminBrand.logoAlt" class="admin-brand-logo" />
          <div class="admin-brand-copy">
            <h1 class="header-title">{{ adminBrand.consoleTitle }}</h1>
          </div>
        </div>
      </div>

      <div class="header-right">
        <!-- Notifications -->
        <div v-if="canAccess('admin.notifications.manage')" class="notifications">
          <button class="notification-btn" title="Notifications" @click="openAdminAlerts">
            🔔
            <span v-if="adminAlertUnreadCount > 0" class="notification-badge">{{ adminAlertUnreadCount }}</span>
          </button>
        </div>

        <!-- Admin Profile -->
        <div class="admin-profile">
          <span class="profile-name">{{ adminName }}</span>
          <div class="profile-menu">
            <button @click="showProfileMenu = !showProfileMenu" class="profile-btn">
              👤
            </button>
            <div v-if="showProfileMenu" class="dropdown-menu">
              <router-link to="/admin/profile" class="menu-item">
                My Profile
              </router-link>
              <button @click="handleLogout" class="menu-item">
                Logout
              </button>
            </div>
          </div>
        </div>
      </div>
    </header>

    <!-- Main Container -->
    <div class="admin-main">
      <!-- Sidebar -->
      <aside class="admin-sidebar" :class="{ open: sidebarOpen }">
        <div class="sidebar-brand">
          <img :src="brandLogo" :alt="adminBrand.logoAlt" class="sidebar-brand-logo" />
          <div class="sidebar-brand-copy">
            <h2 class="sidebar-brand-title">{{ adminBrand.sidebarTitle }}</h2>
            <p class="sidebar-brand-description">{{ adminBrand.sidebarDescription }}</p>
          </div>
        </div>

        <nav class="sidebar-nav">
          <!-- Dashboard -->
          <router-link
            v-if="canAccess('admin.dashboard.read')"
            to="/admin/dashboard"
            class="nav-item"
            :class="{ active: $route.path.includes('dashboard') }"
            @click="sidebarOpen = false"
          >
            <span class="nav-icon">📊</span>
            <span class="nav-label">Dashboard</span>
          </router-link>

          <!-- User Management Section -->
          <div class="nav-section">
            <p class="section-title">User Management</p>
            <router-link
              v-if="canAccess('admin.tourists.read')"
              to="/admin/tourists"
              class="nav-item"
              :class="{ active: $route.path.includes('tourists') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">👥</span>
              <span class="nav-label">Tourists</span>
            </router-link>

            <router-link
              v-if="canAccess('admin.operators.read')"
              to="/admin/operators"
              class="nav-item"
              :class="{ active: $route.path.includes('operators') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">🚀</span>
              <span class="nav-label">Operators</span>
            </router-link>
          </div>

          <!-- Business Management Section -->
          <div class="nav-section">
            <p class="section-title">Business Management</p>
            <router-link
              v-if="canAccess('admin.quotes.read')"
              to="/admin/quotes"
              class="nav-item"
              :class="{ active: $route.path.includes('quotes') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">📝</span>
              <span class="nav-label">Quotes</span>
            </router-link>

            <router-link
              v-if="canAccess('admin.operators.read')"
              to="/admin/promotions"
              class="nav-item"
              :class="{ active: $route.path.includes('promotions') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">📣</span>
              <span class="nav-label">Promotions</span>
            </router-link>

            <router-link
              v-if="canAccess('admin.operators.read')"
              to="/admin/performance"
              class="nav-item"
              :class="{ active: $route.path.includes('performance') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">📈</span>
              <span class="nav-label">Performance</span>
            </router-link>

            <router-link
              v-if="canAccess('admin.audit.read')"
              to="/admin/reviews"
              class="nav-item"
              :class="{ active: $route.path.includes('reviews') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">⭐</span>
              <span class="nav-label">Reviews</span>
            </router-link>
          </div>

          <!-- Communications Section -->
          <div class="nav-section">
            <p class="section-title">Communications</p>
            <router-link
              v-if="canAccess('admin.tickets.manage')"
              to="/admin/tickets"
              class="nav-item"
              :class="{ active: $route.path.includes('tickets') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">🎫</span>
              <span class="nav-label">Tickets</span>
            </router-link>
            <router-link
              v-if="canAccess('admin.notifications.manage')"
              to="/admin/notifications"
              class="nav-item"
              :class="{ active: $route.path.includes('notifications') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">🔔</span>
              <span class="nav-label">Notifications</span>
            </router-link>
          </div>

          <!-- Financial Management Section -->
          <div class="nav-section">
            <p class="section-title">Financial Management</p>
            <router-link
              v-if="canAccess('admin.billing.read')"
              to="/admin/financial"
              class="nav-item"
              :class="{ active: $route.path.includes('financial') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">💰</span>
              <span class="nav-label">Financial</span>
            </router-link>
          </div>

          <!-- Compliance Section -->
          <div class="nav-section">
            <p class="section-title">Compliance</p>
            <router-link
              v-if="canAccess('admin.audit.read')"
              to="/admin/audit"
              class="nav-item"
              :class="{ active: $route.path.includes('audit') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">🔐</span>
              <span class="nav-label">Audit</span>
            </router-link>
          </div>

          <!-- Reports Section -->
          <div class="nav-section">
            <p class="section-title">Analytics & Reports</p>
            <router-link
              v-if="canAccess('admin.reports.read')"
              to="/admin/reports"
              class="nav-item"
              :class="{ active: $route.path.includes('reports') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">📋</span>
              <span class="nav-label">Reports</span>
            </router-link>
          </div>

          <!-- Settings Section -->
          <div class="nav-section">
            <p class="section-title">System</p>
            <router-link
              v-if="canAccess('admin.settings.manage')"
              to="/admin/settings"
              class="nav-item"
              :class="{ active: $route.path.includes('settings') && !$route.path.includes('quote-limits') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">⚙️</span>
              <span class="nav-label">Settings</span>
            </router-link>
            <router-link
              v-if="canAccess('admin.settings.manage')"
              to="/admin/quote-limits"
              class="nav-item"
              :class="{ active: $route.path.includes('quote-limits') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">📊</span>
              <span class="nav-label">Quote Limits</span>
            </router-link>
            <router-link
              v-if="canAccess('admin.backups.manage')"
              to="/admin/backups"
              class="nav-item"
              :class="{ active: $route.path.includes('backups') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">💾</span>
              <span class="nav-label">Backups</span>
            </router-link>
            <router-link
              v-if="canAccess('admin.team.manage')"
              to="/admin/team"
              class="nav-item"
              :class="{ active: $route.path.includes('team') }"
              @click="sidebarOpen = false"
            >
              <span class="nav-icon">🛡️</span>
              <span class="nav-label">Team Access</span>
            </router-link>
          </div>
        </nav>

        <!-- Sidebar Footer -->
        <div class="sidebar-footer">
          <p>Version 1.0.0</p>
        </div>
      </aside>

      <!-- Content Area -->
      <main class="admin-content">
        <div v-if="loadingContent" class="loading-state">
          <div class="spinner"></div>
          <p>Loading...</p>
        </div>
        <router-view v-else />
      </main>
    </div>

    <!-- Overlay for mobile -->
    <div v-if="sidebarOpen" class="sidebar-overlay" @click="sidebarOpen = false"></div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onBeforeUnmount } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import { useAccessStore } from '../stores/access'
import brandLogo from '../../resources/logo/app_logo_compact.svg'
import { adminBrandConfig } from '../config/adminBrand'

const router = useRouter()
const accessStore = useAccessStore()
const sidebarOpen = ref(false)
const showProfileMenu = ref(false)
const loadingContent = ref(false)
const adminUser = ref(null)
const adminAlertUnreadCount = ref(0)
const adminBrand = adminBrandConfig
let alertRefreshTimer = null

const adminName = computed(() => {
  return adminUser.value?.full_name || 'Admin'
})

const canAccess = (permission) => accessStore.hasAdminPermission(permission)

const loadAdminAlertSummary = async () => {
  try {
    const response = await api.get('/admin/notifications/summary')
    adminAlertUnreadCount.value = response.data?.admin_alerts?.unread_count || 0
  } catch (error) {
    console.error('Error fetching admin alert summary:', error)
  }
}

const openAdminAlerts = async () => {
  await router.push({ name: 'AdminNotifications', query: { tab: 'alerts' } })
}

onMounted(async () => {
  // Fetch admin profile
  try {
    const token = localStorage.getItem('adminToken')
    if (!token) {
      await router.push('/admin/login')
      return
    }

    api.defaults.headers.common['Authorization'] = `Bearer ${token}`

    const response = await api.get('/admin/profile')
    adminUser.value = response.data
    await accessStore.loadAdminContext(true)
    if (canAccess('admin.notifications.manage')) {
      await loadAdminAlertSummary()
      alertRefreshTimer = window.setInterval(loadAdminAlertSummary, 30000)
    }
  } catch (error) {
    console.error('Error fetching admin profile:', error)
    localStorage.removeItem('adminToken')
    localStorage.removeItem('adminUser')
    await router.push('/admin/login')
  }
})

onBeforeUnmount(() => {
  if (alertRefreshTimer) {
    window.clearInterval(alertRefreshTimer)
  }
})

const handleLogout = async () => {
  localStorage.removeItem('adminToken')
  localStorage.removeItem('adminUser')
  accessStore.reset()
  delete api.defaults.headers.common['Authorization']
  await router.push('/admin/login')
}
</script>

<style scoped>
.admin-layout {
  display: flex;
  flex-direction: column;
  height: 100vh;
  background: #f7fafc;
  font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
}

/* Header */
.admin-header {
  background: rgba(255, 255, 255, 0.96);
  border-bottom: 1px solid rgba(226, 232, 240, 0.9);
  padding: 1rem 2rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  position: sticky;
  top: 0;
  z-index: 100;
  backdrop-filter: blur(10px);
}

.header-left {
  display: flex;
  align-items: center;
  gap: 1.5rem;
}

.admin-brand {
  display: flex;
  align-items: center;
  gap: 0.9rem;
}

.admin-brand-logo {
  width: 132px;
  height: 44px;
  object-fit: contain;
}

.admin-brand-copy {
  display: flex;
  flex-direction: column;
  justify-content: center;
}

.menu-toggle {
  display: none;
  background: #0f766e;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  font-size: 0.9rem;
}

.header-title {
  font-size: 1.35rem;
  font-weight: 700;
  margin: 0;
  background: linear-gradient(135deg, #0f766e 0%, #102a43 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 2rem;
}

/* Notifications */
.notifications {
  position: relative;
}

.notification-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  position: relative;
  transition: transform 0.2s;
}

.notification-btn:hover {
  transform: scale(1.1);
}

.notification-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: #f56565;
  color: white;
  font-size: 0.75rem;
  font-weight: 700;
  width: 20px;
  height: 20px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
}

/* Admin Profile */
.admin-profile {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.profile-name {
  font-weight: 600;
  color: #2d3748;
  font-size: 0.95rem;
}

.profile-menu {
  position: relative;
}

.profile-btn {
  background: #edf7f6;
  border: none;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  font-size: 1.2rem;
  cursor: pointer;
  transition: all 0.2s;
}

.profile-btn:hover {
  background: #dff1ee;
  transform: scale(1.05);
}

.dropdown-menu {
  position: absolute;
  right: 0;
  top: 3rem;
  background: white;
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
  min-width: 150px;
  z-index: 1000;
  overflow: hidden;
}

.menu-item {
  display: block;
  width: 100%;
  padding: 0.75rem 1rem;
  text-align: left;
  background: none;
  border: none;
  cursor: pointer;
  color: #2d3748;
  text-decoration: none;
  transition: background 0.2s;
  font-size: 0.95rem;
}

.menu-item:hover {
  background: #f7fafc;
}

.menu-item:first-child {
  border-bottom: 1px solid #e2e8f0;
}

/* Main Content Area */
.admin-main {
  display: flex;
  flex: 1;
  overflow: hidden;
}

/* Sidebar */
.admin-sidebar {
  width: 250px;
  background: #2d3748;
  color: white;
  overflow-y: auto;
  border-right: 1px solid #1a202c;
  display: flex;
  flex-direction: column;
}

.sidebar-brand {
  padding: 1.1rem 1rem 0.75rem;
  border-bottom: 1px solid rgba(160, 174, 192, 0.18);
  background: linear-gradient(180deg, rgba(15, 118, 110, 0.18), rgba(15, 23, 42, 0));
}

.sidebar-brand-logo {
  width: 158px;
  height: 56px;
  object-fit: contain;
  display: block;
}

.sidebar-brand-copy {
  margin-top: 0.85rem;
}

.sidebar-brand-title {
  margin: 0.35rem 0 0;
  font-size: 1.05rem;
  font-weight: 700;
  color: #f8fafc;
}

.sidebar-brand-description {
  margin: 0.45rem 0 0;
  font-size: 0.82rem;
  line-height: 1.5;
  color: #cbd5e0;
}

.sidebar-nav {
  flex: 1;
  padding: 1rem 0;
}

.nav-section {
  margin-bottom: 2rem;
  padding: 0 1rem;
}

.section-title {
  font-size: 0.75rem;
  font-weight: 700;
  color: #a0aec0;
  text-transform: uppercase;
  margin: 0 0 0.75rem 0;
  letter-spacing: 0.05em;
}

.nav-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  margin-bottom: 0.5rem;
  border-radius: 6px;
  color: #cbd5e0;
  text-decoration: none;
  transition: all 0.2s;
  cursor: pointer;
}

.nav-item:hover {
  background: #4a5568;
  color: white;
}

.nav-item.active {
  background: linear-gradient(135deg, #0f766e 0%, #102a43 100%);
  color: white;
  font-weight: 600;
}

.nav-icon {
  font-size: 1.25rem;
  width: 1.5rem;
  text-align: center;
}

.nav-label {
  flex: 1;
}

/* Sidebar Footer */
.sidebar-footer {
  padding: 1rem;
  border-top: 1px solid #4a5568;
  text-align: center;
  color: #a0aec0;
  font-size: 0.8rem;
}

/* Content Area */
.admin-content {
  flex: 1;
  overflow-y: auto;
  padding: 2rem;
}

.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  height: 100%;
  color: #718096;
}

.spinner {
  width: 3rem;
  height: 3rem;
  border: 4px solid #e2e8f0;
  border-top-color: #667eea;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
  margin-bottom: 1rem;
}

@keyframes spin {
  to {
    transform: rotate(360deg);
  }
}

.sidebar-overlay {
  display: none;
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  z-index: 99;
}

/* Responsive */
@media (max-width: 768px) {
  .admin-header {
    padding: 1rem;
  }

  .menu-toggle {
    display: block;
  }

  .profile-name {
    display: none;
  }

  .admin-sidebar {
    position: fixed;
    left: -250px;
    top: 0;
    height: 100vh;
    z-index: 101;
    transition: left 0.3s ease;
  }

  .admin-sidebar.open {
    left: 0;
  }

  .sidebar-brand {
    padding-top: 1.25rem;
  }

  .sidebar-overlay {
    display: block;
  }

  .sidebar-overlay.hidden {
    display: none;
  }

  .admin-content {
    padding: 1.5rem;
  }

  .header-right {
    gap: 1rem;
  }

  .header-title {
    font-size: 1.25rem;
  }

  .admin-brand-logo {
    width: 112px;
    height: 40px;
  }
}

@media (max-width: 480px) {
  .admin-header {
    padding: 0.75rem;
  }

  .header-left {
    gap: 0.75rem;
  }

  .admin-brand-logo {
    width: 102px;
    height: 36px;
  }

  .header-title {
    font-size: 1rem;
  }

  .admin-sidebar {
    width: 100%;
    left: -100%;
  }

  .admin-content {
    padding: 1rem;
  }
}
</style>
