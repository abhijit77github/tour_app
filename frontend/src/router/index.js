import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Views
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import ForgotPassword from '../views/ForgotPassword.vue'
import Search from '../views/Search.vue'
import OperatorDashboard from '../views/OperatorDashboard.vue'
import OperatorHome from '../views/OperatorHome.vue'
import OperatorQuoteRequests from '../views/OperatorQuoteRequests.vue'
import TouristDashboard from '../views/TouristDashboard.vue'
import TouristHome from '../views/TouristHome.vue'
import RecommendationsPage from '../views/RecommendationsPage.vue'
import QuoteBuilder from '../views/QuoteBuilder.vue'
import OperatorProfile from '../views/OperatorProfile.vue'
import BookingDetails from '../views/BookingDetails.vue'
import MyBookings from '../views/MyBookings.vue'
import CartView from '../views/CartView.vue'

// Admin Views
import AdminLogin from '../views/AdminLogin.vue'
import AdminLayout from '../layouts/AdminLayout.vue'
import AdminDashboard from '../views/AdminDashboard.vue'
import { useAccessStore } from '../stores/access'

const routes = [
  {
    path: '/',
    name: 'Home',
    component: Home
  },
  {
    path: '/home',
    redirect: '/' // keep legacy if any
  },
  {
    path: '/login',
    name: 'Login',
    component: Login
  },
  {
    path: '/register',
    name: 'Register',
    component: Register
  },
  {
    path: '/forgot-password',
    name: 'ForgotPassword',
    component: ForgotPassword
  },
  {
    path: '/search',
    name: 'Search',
    component: Search
  },
  {
    path: '/operator/dashboard',
    name: 'OperatorDashboard',
    component: OperatorDashboard,
    meta: { requiresAuth: true, userType: 'operator' }
  },
  {
    path: '/operator/home',
    name: 'OperatorHome',
    component: OperatorHome,
    meta: { requiresAuth: true, userType: 'operator' }
  },
  {
    path: '/operator/quotes',
    name: 'OperatorQuoteRequests',
    component: OperatorQuoteRequests,
    meta: { requiresAuth: true, userType: 'operator', operatorPermission: 'operator.quotes.read' }
  },
  {
    path: '/operator/itineraries',
    name: 'OperatorItineraries',
    component: () => import('../views/OperatorItineraries.vue'),
    meta: { requiresAuth: true, userType: 'operator', operatorPermission: 'operator.itineraries.manage' }
  },
  {
    path: '/operator/promotions',
    name: 'OperatorPromotions',
    component: () => import('../views/OperatorPromotions.vue'),
    meta: { requiresAuth: true, userType: 'operator', operatorPermission: 'operator.promotions.read' }
  },
  {
    path: '/operator/billing-analytics',
    name: 'OperatorBillingAnalytics',
    component: () => import('../views/OperatorBillingAnalytics.vue'),
    meta: { requiresAuth: true, userType: 'operator', operatorPermission: 'operator.billing.read' }
  },
  {
    path: '/operator/team',
    name: 'OperatorTeamAccess',
    component: () => import('../views/OperatorTeamAccess.vue'),
    meta: { requiresAuth: true, userType: 'operator', operatorPermission: 'operator.team.manage' }
  },
  {
    path: '/operator/tickets',
    name: 'OperatorTickets',
    component: () => import('../views/OperatorTickets.vue'),
    meta: { requiresAuth: true, userType: 'operator', operatorPermission: 'operator.tickets.read' }
  },
  {
    path: '/tourist/dashboard',
    name: 'TouristDashboard',
    component: TouristDashboard,
    meta: { requiresAuth: true, userType: 'tourist' }
  },
  {
    path: '/tourist/home',
    name: 'TouristHome',
    component: TouristHome,
    meta: { requiresAuth: true, userType: 'tourist' }
  },
  {
    path: '/recommendations',
    name: 'RecommendationsPage',
    component: RecommendationsPage,
    meta: { requiresAuth: true, userType: 'tourist' }
  },
  {
    path: '/quote-builder',
    name: 'QuoteBuilder',
    component: QuoteBuilder,
    meta: { requiresAuth: true, userType: 'tourist' }
  },
  {
    path: '/itineraries',
    name: 'MyItineraries',
    component: () => import('../views/ItineraryBuilder.vue'),
    meta: { requiresAuth: true, userType: 'tourist' }
  },
  {
    path: '/operator/:id',
    name: 'OperatorProfile',
    component: OperatorProfile
  },
  {
    path: '/cart',
    name: 'Cart',
    component: CartView,
    meta: { requiresAuth: true, userType: 'tourist' }
  },
  {
    path: '/my-bookings',
    name: 'MyBookings',
    component: MyBookings,
    meta: { requiresAuth: true, userType: 'tourist' }
  },
  {
    path: '/plan',
    name: 'TourPlanner',
    component: () => import('../views/TourPlanner.vue'),
    meta: { requiresAuth: true, userType: 'tourist' }
  },
  {
    path: '/notifications',
    name: 'NotificationCenter',
    component: () => import('../views/NotificationCenter.vue'),
    meta: { requiresAuth: true }
  },
  {
    path: '/booking/:id',
    name: 'BookingDetails',
    component: BookingDetails,
    meta: { requiresAuth: true }
  },
  {
    path: '/admin/login',
    name: 'AdminLogin',
    component: AdminLogin
  },
  {
    path: '/admin',
    component: AdminLayout,
    redirect: '/admin/dashboard',
    meta: { requiresAdmin: true },
    children: [
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: AdminDashboard,
        meta: { requiresAdmin: true, adminPermission: 'admin.dashboard.read' }
      },
      {
        path: 'tourists',
        name: 'AdminTourists',
        component: () => import('../views/AdminTourists.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.tourists.read' }
      },
      {
        path: 'operators',
        name: 'AdminOperators',
        component: () => import('../views/AdminOperators.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.operators.read' }
      },
      {
        path: 'quotes',
        name: 'AdminQuotes',
        component: () => import('../views/AdminQuotes.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.quotes.read' }
      },
      {
        path: 'promotions',
        name: 'AdminPromotions',
        component: () => import('../views/AdminPromotions.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.operators.read' }
      },
      {
        path: 'performance',
        name: 'AdminPerformance',
        component: () => import('../views/AdminPerformance.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.operators.read' }
      },
      {
        path: 'reviews',
        name: 'AdminReviews',
        component: () => import('../views/AdminReviews.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.audit.read' }
      },
      {
        path: 'notifications',
        name: 'AdminNotifications',
        component: () => import('../views/AdminNotifications.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.notifications.manage' }
      },
      {
        path: 'tickets',
        name: 'AdminTickets',
        component: () => import('../views/AdminTickets.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.tickets.manage' }
      },
      {
        path: 'financial',
        name: 'AdminFinancial',
        component: () => import('../views/AdminFinancial.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.billing.read' }
      },
      {
        path: 'audit',
        name: 'AdminAudit',
        component: () => import('../views/AdminAudit.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.audit.read' }
      },
      {
        path: 'reports',
        name: 'AdminReports',
        component: () => import('../views/AdminReports.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.reports.read' }
      },
      {
        path: 'reports/dashboards/:dashboardId',
        name: 'AdminReportDashboard',
        component: () => import('../views/AdminReportDashboard.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.reports.read' }
      },
      {
        path: 'settings',
        name: 'AdminSettings',
        component: () => import('../views/AdminSettings.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.settings.manage' }
      },
      {
        path: 'backups',
        name: 'AdminBackups',
        component: () => import('../views/AdminBackups.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.backups.manage' }
      },
      {
        path: 'team',
        name: 'AdminTeamAccess',
        component: () => import('../views/AdminTeamAccess.vue'),
        meta: { requiresAdmin: true, adminPermission: 'admin.team.manage' }
      },
      {
        path: 'profile',
        name: 'AdminProfile',
        component: () => import('../views/AdminProfile.vue'),
        meta: { requiresAdmin: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  const accessStore = useAccessStore()
  
  // Check for admin routes
  if (to.meta.requiresAdmin) {
    const adminToken = localStorage.getItem('adminToken')
    if (!adminToken) {
      next({ name: 'AdminLogin', query: { redirect: to.fullPath } })
      return
    }
    if (to.meta.adminPermission) {
      try {
        await accessStore.loadAdminContext()
        if (!accessStore.hasAdminPermission(to.meta.adminPermission)) {
          next({ name: 'AdminDashboard' })
          return
        }
      } catch (error) {
        next({ name: 'AdminLogin', query: { redirect: to.fullPath } })
        return
      }
    }
    next()
    return
  }
  
  // If trying to access admin login but already authenticated
  if (to.name === 'AdminLogin' && localStorage.getItem('adminToken') && localStorage.getItem('adminUser')) {
    next({ name: 'AdminDashboard' })
    return
  }
  
  // Wait for auth initialization
  if (!authStore.initialized) {
    await authStore.initAuth()
  }
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.userType && authStore.user?.user_type !== to.meta.userType) {
    // Redirect to appropriate home page based on user type
    if (authStore.user?.user_type === 'operator') {
      next({ name: 'OperatorHome' })
    } else if (authStore.user?.user_type === 'tourist') {
      next({ name: 'TouristHome' })
    } else {
      next({ name: 'Home' })
    }
  } else {
    if (to.meta.operatorPermission && authStore.user?.user_type === 'operator') {
      try {
        await accessStore.loadOperatorContext()
        if (!accessStore.hasOperatorPermission(to.meta.operatorPermission)) {
          next({ name: 'OperatorHome' })
          return
        }
      } catch (error) {
        next({ name: 'OperatorHome' })
        return
      }
    }
    next()
  }
})

export default router
