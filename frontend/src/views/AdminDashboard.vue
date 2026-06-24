<template>
  <div class="admin-dashboard">
    <div class="dashboard-header">
      <div>
        <h1>Dashboard</h1>
        <p class="subtitle">Welcome back! Here's your business overview.</p>
      </div>
      <button class="refresh-button" @click="fetchDashboardData" :disabled="loading">
        {{ loading ? 'Refreshing...' : 'Refresh Data' }}
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading dashboard data...</p>
    </div>

    <!-- Dashboard Content -->
    <div v-else class="dashboard-content">
      <!-- Key Metrics Grid -->
      <div class="metrics-grid">
        <!-- Total Users -->
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">👥</span>
            <span class="metric-label">Total Users</span>
          </div>
          <div class="metric-value">{{ stats.users?.total || 0 }}</div>
          <div class="metric-breakdown">
            <span>Tourists: {{ stats.users?.tourists || 0 }}</span>
            <span>Operators: {{ stats.users?.operators || 0 }}</span>
          </div>
        </div>

        <!-- Active Users -->
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">🟢</span>
            <span class="metric-label">Active Users (7 days)</span>
          </div>
          <div class="metric-value">{{ stats.users?.active_last_7_days || 0 }}</div>
          <div class="metric-percentage">
            {{ getPercentage(stats.users?.active_last_7_days, stats.users?.total) }}% of total
          </div>
        </div>

        <!-- Total Quotes -->
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">📝</span>
            <span class="metric-label">Total Quotes</span>
          </div>
          <div class="metric-value">{{ stats.quotes?.total || 0 }}</div>
          <div class="metric-breakdown">
            <span>Open: {{ stats.quotes?.open || 0 }}</span>
            <span>Closed: {{ stats.quotes?.closed || 0 }}</span>
          </div>
        </div>

        <!-- Quote Responses -->
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">💬</span>
            <span class="metric-label">Total Responses</span>
          </div>
          <div class="metric-value">{{ stats.quotes?.total_responses || 0 }}</div>
          <div class="metric-percentage">
            Conversion: {{ stats.quotes?.conversion_rate || 0 }}%
          </div>
        </div>

        <!-- Avg Response Time -->
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">⏱️</span>
            <span class="metric-label">Avg Response Time</span>
          </div>
          <div class="metric-value">{{ responseTime.average_hours || 0 }}h</div>
          <div class="metric-breakdown">
            <span>Min: {{ responseTime.minimum_hours || 0 }}h</span>
            <span>Max: {{ responseTime.maximum_hours || 0 }}h</span>
          </div>
        </div>

        <!-- Operator Rating -->
        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">⭐</span>
            <span class="metric-label">Avg Operator Rating</span>
          </div>
          <div class="metric-value">{{ stats.operators?.avg_rating || 0 }}</div>
          <div class="metric-breakdown">
            <span>Out of 5.0</span>
            <span>{{ stats.operators?.total_profiles || 0 }} operators</span>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-header">
            <span class="metric-icon">🎫</span>
            <span class="metric-label">Support Tickets</span>
          </div>
          <div class="metric-value">{{ stats.tickets?.open || 0 }}</div>
          <div class="metric-breakdown">
            <span>Open: {{ stats.tickets?.open || 0 }}</span>
            <span>Completed: {{ stats.tickets?.completed || 0 }}</span>
          </div>
        </div>
      </div>

      <!-- Charts Section -->
      <div class="charts-section">
        <!-- User Growth Chart -->
        <div class="chart-container">
          <h3 class="chart-title">User Growth (Last 30 Days)</h3>
          <div v-if="metrics.user_growth?.length" class="simple-chart">
            <div v-for="(item, idx) in metrics.user_growth.slice(-10)" :key="idx" class="chart-item">
              <div class="chart-label">{{ formatDate(item.date) }}</div>
              <div class="chart-bars">
                <div class="bar tourists" :style="{ height: (item.tourists * 2) + 'px' }" :title="`Tourists: ${item.tourists}`"></div>
                <div class="bar operators" :style="{ height: (item.operators * 2) + 'px' }" :title="`Operators: ${item.operators}`"></div>
              </div>
            </div>
          </div>
          <p v-else class="no-data">No data available</p>
        </div>

        <!-- Quote Trend Chart -->
        <div class="chart-container">
          <h3 class="chart-title">Quote Trend (Last 30 Days)</h3>
          <div v-if="metrics.quote_trend?.length" class="simple-chart">
            <div v-for="(item, idx) in metrics.quote_trend.slice(-10)" :key="idx" class="chart-item">
              <div class="chart-label">{{ formatDate(item.date) }}</div>
              <div class="chart-bars">
                <div class="bar quotes" :style="{ height: (item.count * 2) + 'px' }" :title="`Quotes: ${item.count}`"></div>
              </div>
            </div>
          </div>
          <p v-else class="no-data">No data available</p>
        </div>
      </div>

      <!-- Top Destinations & States -->
      <div class="info-section">
        <div class="info-container">
          <h3 class="info-title">Top Destinations</h3>
          <div v-if="metrics.top_destinations?.length" class="top-list">
            <div v-for="(dest, idx) in metrics.top_destinations.slice(0, 5)" :key="idx" class="list-item">
              <span class="rank">{{ idx + 1 }}</span>
              <span class="name">{{ dest.name }}</span>
              <span class="count">{{ dest.count }} quotes</span>
            </div>
          </div>
          <p v-else class="no-data">No data available</p>
        </div>

        <div class="info-container">
          <h3 class="info-title">Top States</h3>
          <div v-if="metrics.top_states?.length" class="top-list">
            <div v-for="(state, idx) in metrics.top_states.slice(0, 5)" :key="idx" class="list-item">
              <span class="rank">{{ idx + 1 }}</span>
              <span class="name">{{ state.name }}</span>
              <span class="count">{{ state.count }} quotes</span>
            </div>
          </div>
          <p v-else class="no-data">No data available</p>
        </div>
      </div>

      <!-- Quick Actions -->
      <div class="quick-actions">
        <router-link to="/admin/tourists" class="action-button tourists">
          <span class="icon">👥</span>
          <span>Manage Tourists</span>
        </router-link>
        <router-link to="/admin/operators" class="action-button operators">
          <span class="icon">🚀</span>
          <span>Manage Operators</span>
        </router-link>
        <router-link to="/admin/quotes" class="action-button quotes">
          <span class="icon">📝</span>
          <span>View All Quotes</span>
        </router-link>
        <router-link to="/admin/performance" class="action-button performance">
          <span class="icon">📈</span>
          <span>View Performance</span>
        </router-link>
        <router-link v-if="canManageBackups" to="/admin/backups" class="action-button backups">
          <span class="icon">💾</span>
          <span>Backups & Restore</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'
import api from '../services/api'
import { useAccessStore } from '../stores/access'

const loading = ref(true)
const accessStore = useAccessStore()
const stats = ref({
  users: {},
  quotes: {},
  operators: {}
})
const metrics = ref({
  user_growth: [],
  quote_trend: [],
  top_destinations: [],
  top_states: []
})
const responseTime = ref({
  average_hours: 0,
  minimum_hours: 0,
  maximum_hours: 0,
  median_hours: 0
})
let refreshIntervalId = null

const canManageBackups = computed(() => accessStore.hasAdminPermission('admin.backups.manage'))

const getPercentage = (part, total) => {
  if (!total) return 0
  return Math.round((part / total) * 100)
}

const formatDate = (dateStr) => {
  try {
    const date = new Date(dateStr)
    return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric' })
  } catch {
    return dateStr
  }
}

const fetchDashboardData = async () => {
  try {
    loading.value = true

    const token = localStorage.getItem('adminToken')
    if (!token) return

    // Fetch dashboard stats
    const statsRes = await api.get('/admin/dashboard/stats', {
      headers: { Authorization: `Bearer ${token}` }
    })
    stats.value = statsRes.data

    // Fetch dashboard metrics
    const metricsRes = await api.get('/admin/dashboard/metrics', {
      headers: { Authorization: `Bearer ${token}` }
    })
    metrics.value = metricsRes.data

    // Fetch response times
    const timeRes = await api.get('/admin/dashboard/response-times', {
      headers: { Authorization: `Bearer ${token}` }
    })
    responseTime.value = timeRes.data
  } catch (error) {
    console.error('Error fetching dashboard data:', error)
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  fetchDashboardData()
  // Refresh data every 30 seconds
  refreshIntervalId = setInterval(fetchDashboardData, 30000)
})

onUnmounted(() => {
  if (refreshIntervalId) {
    clearInterval(refreshIntervalId)
    refreshIntervalId = null
  }
})
</script>

<style scoped>
.admin-dashboard {
  width: 100%;
}

.dashboard-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 2rem;
}

.refresh-button {
  border: 1px solid #cbd5e1;
  background: #f8fafc;
  color: #1e293b;
  border-radius: 10px;
  padding: 0.6rem 0.95rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s ease;
}

.refresh-button:hover:not(:disabled) {
  border-color: #94a3b8;
  background: #eef2f7;
}

.refresh-button:focus-visible,
.action-button:focus-visible {
  outline: 3px solid rgba(37, 99, 235, 0.35);
  outline-offset: 2px;
}

.refresh-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.dashboard-header h1 {
  font-size: 2rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 0.5rem 0;
}

.subtitle {
  color: #718096;
  font-size: 1rem;
  margin: 0;
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 500px;
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

/* Metrics Grid */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.metric-card {
  background: white;
  border-radius: 12px;
  padding: 1.5rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
  transition: all 0.3s ease;
  animation: slideUp 0.4s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.metric-card:hover {
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
  border-color: #cbd5e0;
}

.metric-header {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.metric-icon {
  font-size: 1.5rem;
}

.metric-label {
  font-size: 0.9rem;
  color: #718096;
  font-weight: 600;
}

.metric-value {
  font-size: 2.5rem;
  font-weight: 700;
  color: #1a202c;
  margin-bottom: 0.5rem;
}

.metric-breakdown {
  display: flex;
  gap: 1rem;
  font-size: 0.85rem;
  color: #a0aec0;
}

.metric-breakdown span {
  display: block;
}

.metric-percentage {
  font-size: 0.9rem;
  color: #667eea;
  font-weight: 600;
}

/* Charts Section */
.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(400px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}

.chart-container {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.chart-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 1.5rem 0;
}

.simple-chart {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: 0.5rem;
  height: 250px;
  padding: 1rem 0;
}

.chart-item {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
}

.chart-label {
  font-size: 0.75rem;
  color: #a0aec0;
  text-align: center;
}

.chart-bars {
  display: flex;
  gap: 0.25rem;
  align-items: flex-end;
  height: 200px;
}

.bar {
  flex: 1;
  border-radius: 4px 4px 0 0;
  min-height: 10px;
  transition: all 0.2s;
}

.bar.tourists {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.bar.operators {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.bar.quotes {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.bar:hover {
  opacity: 0.8;
}

.no-data {
  text-align: center;
  color: #a0aec0;
  padding: 2rem;
  margin: 0;
}

/* Info Section */
.info-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}

.info-container {
  background: white;
  border-radius: 12px;
  padding: 2rem;
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
  border: 1px solid #e2e8f0;
}

.info-title {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 1rem 0;
}

.top-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.list-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 0.75rem;
  background: #f7fafc;
  border-radius: 8px;
  transition: background 0.2s;
}

.list-item:hover {
  background: #edf2f7;
}

.rank {
  width: 2rem;
  height: 2rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 600;
  font-size: 0.9rem;
}

.name {
  flex: 1;
  font-weight: 600;
  color: #2d3748;
}

.count {
  font-size: 0.9rem;
  color: #a0aec0;
}

/* Quick Actions */
.quick-actions {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
}

.action-button {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.75rem;
  padding: 1.5rem;
  border-radius: 12px;
  text-decoration: none;
  color: white;
  font-weight: 600;
  transition: all 0.3s ease;
  border: none;
  cursor: pointer;
}

.action-button .icon {
  font-size: 2rem;
}

.action-button.tourists {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.action-button.operators {
  background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);
}

.action-button.quotes {
  background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);
}

.action-button.performance {
  background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);
}

.action-button.backups {
  background: linear-gradient(135deg, #f59e0b 0%, #ea580c 100%);
}

.action-button:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
}

/* Responsive */
@media (max-width: 768px) {
  .dashboard-header {
    flex-direction: column;
    align-items: stretch;
  }

  .metrics-grid {
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  }

  .charts-section {
    grid-template-columns: 1fr;
  }

  .info-section {
    grid-template-columns: 1fr;
  }

  .simple-chart {
    height: 200px;
  }

  .dashboard-header h1 {
    font-size: 1.5rem;
  }
}

@media (prefers-reduced-motion: reduce) {
  .metric-card,
  .bar,
  .action-button,
  .refresh-button,
  .list-item {
    transition: none !important;
  }
}
</style>
