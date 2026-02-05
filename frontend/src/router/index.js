import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../stores/auth'

// Views
import Home from '../views/Home.vue'
import Login from '../views/Login.vue'
import Register from '../views/Register.vue'
import Search from '../views/Search.vue'
import OperatorDashboard from '../views/OperatorDashboard.vue'
import TouristDashboard from '../views/TouristDashboard.vue'
import TouristHome from '../views/TouristHome.vue'
import RecommendationsPage from '../views/RecommendationsPage.vue'
import QuoteBuilder from '../views/QuoteBuilder.vue'
import OperatorProfile from '../views/OperatorProfile.vue'
import BookingDetails from '../views/BookingDetails.vue'
import MyBookings from '../views/MyBookings.vue'
import CartView from '../views/CartView.vue'

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
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// Navigation guard
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  
  if (to.meta.requiresAuth && !authStore.isAuthenticated) {
    next({ name: 'Login', query: { redirect: to.fullPath } })
  } else if (to.meta.userType && authStore.user?.user_type !== to.meta.userType) {
    next({ name: 'Home' })
  } else {
    next()
  }
})

export default router
