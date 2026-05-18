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
    meta: { requiresAuth: true, userType: 'operator' }
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
    meta: { requiresAdmin: true },
    children: [
      {
        path: 'dashboard',
        name: 'AdminDashboard',
        component: AdminDashboard,
        meta: { requiresAdmin: true }
      },
      {
        path: 'tourists',
        name: 'AdminTourists',
        component: () => import('../views/AdminTourists.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'operators',
        name: 'AdminOperators',
        component: () => import('../views/AdminOperators.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'quotes',
        name: 'AdminQuotes',
        component: () => import('../views/AdminQuotes.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'performance',
        name: 'AdminPerformance',
        component: () => import('../views/AdminPerformance.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'reviews',
        name: 'AdminReviews',
        component: () => import('../views/AdminReviews.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'notifications',
        name: 'AdminNotifications',
        component: () => import('../views/AdminNotifications.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'financial',
        name: 'AdminFinancial',
        component: () => import('../views/AdminFinancial.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'audit',
        name: 'AdminAudit',
        component: () => import('../views/AdminAudit.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'reports',
        name: 'AdminReports',
        component: () => import('../views/AdminReports.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'settings',
        name: 'AdminSettings',
        component: () => import('../views/AdminSettings.vue'),
        meta: { requiresAdmin: true }
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
  
  // Check for admin routes
  if (to.meta.requiresAdmin) {
    const adminToken = localStorage.getItem('adminToken')
    if (!adminToken) {
      next({ name: 'AdminLogin', query: { redirect: to.fullPath } })
      return
    }
    next()
    return
  }
  
  // If trying to access admin login but already authenticated
  if (to.name === 'AdminLogin' && localStorage.getItem('adminToken')) {
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
    next()
  }
})

export default router
