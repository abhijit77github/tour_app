<template>
  <div class="admin-report-dashboard">
    <div class="dashboard-shell">
      <div class="page-actions">
        <button class="ghost-button" @click="goBackToReports">← Back to Reports</button>
        <div class="page-actions-right">
          <button class="ghost-button" @click="refreshDashboard" :disabled="loading">
            {{ loading ? 'Refreshing...' : 'Refresh Data' }}
          </button>
          <button class="primary-button" @click="goToReportsHub">Manage Dashboards</button>
        </div>
      </div>

      <div v-if="loading" class="state-card">
        <h1>Loading dashboard...</h1>
        <p>Fetching the dashboard definition and live analytics widgets.</p>
      </div>

      <div v-else-if="errorMessage" class="state-card error-state">
        <h1>Dashboard unavailable</h1>
        <p>{{ errorMessage }}</p>
        <button class="primary-button" @click="refreshDashboard">Try Again</button>
      </div>

      <template v-else-if="dashboard">
        <div class="dashboard-hero">
          <div>
            <p class="eyebrow">Analytics Dashboard</p>
            <h1>{{ dashboard.name }}</h1>
            <p class="hero-copy">{{ dashboard.description || 'Live operational overview built from your selected widgets.' }}</p>
          </div>
          <div class="hero-meta">
            <div class="hero-meta-card">
              <span>Widgets</span>
              <strong>{{ dashboard.widgets.length }}</strong>
            </div>
            <div class="hero-meta-card">
              <span>Created</span>
              <strong>{{ formatDate(dashboard.created_at) }}</strong>
            </div>
            <div class="hero-meta-card">
              <span>Shared with</span>
              <strong>{{ dashboard.shared_with?.length || 0 }}</strong>
            </div>
          </div>
        </div>

        <div class="kpi-strip">
          <div v-for="item in heroMetrics" :key="item.label" class="kpi-card">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
            <small>{{ item.note }}</small>
          </div>
        </div>

        <div class="widget-grid">
          <section v-for="widget in dashboard.widgets" :key="widget.key || widget.name" class="widget-panel">
            <div class="widget-header">
              <div>
                <p class="widget-label">Widget</p>
                <h2>{{ widget.name }}</h2>
              </div>
              <span class="widget-chip">{{ widgetTypeLabel(widget) }}</span>
            </div>

            <template v-if="getDashboardWidgetType(widget) === 'revenue'">
              <div class="metric-row">
                <div v-for="bar in revenueWidgetBars" :key="bar.label" class="metric-box">
                  <span>{{ bar.label }}</span>
                  <strong>{{ formatCompactNumber(bar.value) }}</strong>
                </div>
              </div>
              <svg class="chart-svg" viewBox="0 0 360 220" role="img" aria-label="Revenue chart">
                <defs>
                  <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stop-color="#14b8a6" />
                    <stop offset="100%" stop-color="#0f4c81" />
                  </linearGradient>
                </defs>
                <line x1="36" y1="20" x2="36" y2="184" class="axis-line" />
                <line x1="36" y1="184" x2="330" y2="184" class="axis-line" />
                <g v-for="bar in revenueChartBars" :key="bar.label">
                  <rect :x="bar.x" :y="bar.y" :width="bar.width" :height="bar.height" rx="14" fill="url(#revenueGradient)" />
                  <text :x="bar.x + (bar.width / 2)" y="204" text-anchor="middle" class="chart-text">{{ bar.label }}</text>
                  <text :x="bar.x + (bar.width / 2)" :y="bar.y - 10" text-anchor="middle" class="chart-value">{{ formatCompactNumber(bar.value) }}</text>
                </g>
              </svg>
            </template>

            <template v-else-if="getDashboardWidgetType(widget) === 'bookings'">
              <div class="metric-row">
                <div v-for="bar in bookingsWidgetBars" :key="bar.label" class="metric-box">
                  <span>{{ bar.label }}</span>
                  <strong>{{ bar.value }}</strong>
                </div>
              </div>
              <svg class="chart-svg" viewBox="0 0 360 220" role="img" aria-label="Bookings chart">
                <line x1="36" y1="184" x2="330" y2="184" class="axis-line" />
                <polyline :points="bookingsTrendPoints" class="trend-line" />
                <g v-for="point in bookingsTrendSeries" :key="point.label">
                  <circle :cx="point.x" :cy="point.y" r="7" class="trend-point" />
                  <text :x="point.x" y="204" text-anchor="middle" class="chart-text">{{ point.label }}</text>
                  <text :x="point.x" :y="point.y - 14" text-anchor="middle" class="chart-value">{{ point.value }}</text>
                </g>
              </svg>
            </template>

            <template v-else-if="getDashboardWidgetType(widget) === 'operators'">
              <div class="operator-stack">
                <div v-for="operator in operatorWidgetItems.slice(0, 5)" :key="operator.rank || operator.business_name" class="operator-row">
                  <div>
                    <span class="operator-rank">#{{ operator.rank || '-' }}</span>
                    <strong>{{ operator.business_name || 'Operator' }}</strong>
                  </div>
                  <div class="operator-stats">
                    <span>{{ operator.total_quotes || 0 }} quotes</span>
                    <strong>{{ operator.avg_rating || operator.average_rating || 0 }}★</strong>
                  </div>
                </div>
              </div>
            </template>

            <template v-else-if="getDashboardWidgetType(widget) === 'satisfaction'">
              <div class="satisfaction-layout">
                <div class="satisfaction-score">
                  <strong>{{ satisfactionWidget.rating }}</strong>
                  <span>Average rating</span>
                </div>
                <div class="progress-rail">
                  <div class="progress-fill" :style="{ width: `${satisfactionWidget.percent}%` }"></div>
                </div>
                <p class="panel-note">Across {{ dashboardStats.operators?.total_profiles || 0 }} operator profiles.</p>
              </div>
            </template>

            <template v-else-if="getDashboardWidgetType(widget) === 'metrics'">
              <div class="metrics-grid-panel">
                <div v-for="item in keyMetricItems" :key="item.label" class="metric-box metric-box-compact">
                  <span>{{ item.label }}</span>
                  <strong>{{ item.value }}</strong>
                </div>
              </div>
            </template>

            <template v-else>
              <p class="panel-note">No renderer available for this widget yet.</p>
            </template>
          </section>
        </div>

        <div v-if="dashboard.shared_with?.length" class="share-section">
          <h3>Shared With</h3>
          <p>{{ dashboard.shared_with.join(', ') }}</p>
        </div>
      </template>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import api from '../services/api'

const route = useRoute()
const router = useRouter()

const loading = ref(true)
const errorMessage = ref('')
const dashboard = ref(null)
const dashboardStats = ref({ users: {}, quotes: {}, operators: {}, tickets: {} })
const dashboardFinancial = ref({ totalRevenue: 0, monthlyRevenue: 0, pendingPayouts: 0, commissionCollected: 0 })
const dashboardLeaderboard = ref([])

const dashboardWidgetOptions = [
  { value: 'revenue', label: 'Revenue Chart' },
  { value: 'bookings', label: 'Bookings Graph' },
  { value: 'operators', label: 'Top Operators' },
  { value: 'satisfaction', label: 'Satisfaction Scores' },
  { value: 'metrics', label: 'Key Metrics' },
]
const dashboardWidgetLabelMap = Object.fromEntries(dashboardWidgetOptions.map((option) => [option.value, option.label]))
const dashboardWidgetNameToKey = Object.fromEntries(dashboardWidgetOptions.map((option) => [option.label.toLowerCase(), option.value]))

const getAdminConfig = () => {
  const token = localStorage.getItem('adminToken')
  if (!token) {
    throw new Error('Admin token not found. Please login again.')
  }
  return { headers: { Authorization: `Bearer ${token}` } }
}

const formatDate = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString('en-IN')
}

const formatCompactNumber = (value) => {
  const numericValue = Number(value || 0)
  return new Intl.NumberFormat('en-IN', { notation: 'compact', maximumFractionDigits: 1 }).format(numericValue)
}

const normalizeDashboardWidgetKey = (widget) => {
  if (!widget) return ''
  if (typeof widget === 'string') return widget.toLowerCase()
  if (widget.key) return String(widget.key).toLowerCase()
  if (widget.name) return dashboardWidgetNameToKey[String(widget.name).toLowerCase()] || String(widget.name).toLowerCase()
  return ''
}

const getDashboardWidgetType = (widget) => normalizeDashboardWidgetKey(widget)

const widgetTypeLabel = (widget) => {
  const key = normalizeDashboardWidgetKey(widget)
  return dashboardWidgetLabelMap[key] || widget?.name || 'Custom Widget'
}

const revenueWidgetBars = computed(() => ([
  { label: 'Total', value: dashboardFinancial.value.totalRevenue || 0 },
  { label: 'Month', value: dashboardFinancial.value.monthlyRevenue || 0 },
  { label: 'Commission', value: dashboardFinancial.value.commissionCollected || 0 },
]))

const revenueWidgetMax = computed(() => Math.max(...revenueWidgetBars.value.map((item) => Number(item.value || 0)), 0))

const bookingsWidgetBars = computed(() => ([
  { label: 'Bookings', value: Number(dashboardStats.value.quotes?.total || 0) },
  { label: 'Closed', value: Number(dashboardStats.value.quotes?.closed || 0) },
  { label: 'Open', value: Number(dashboardStats.value.quotes?.open || 0) },
]))

const bookingsWidgetMax = computed(() => Math.max(...bookingsWidgetBars.value.map((item) => Number(item.value || 0)), 0))

const operatorWidgetItems = computed(() => dashboardLeaderboard.value || [])

const satisfactionWidget = computed(() => {
  const rating = Number(dashboardStats.value.operators?.avg_rating || 0)
  return {
    rating: `${rating.toFixed(1)} / 5`,
    percent: Math.max(6, Math.round((rating / 5) * 100)),
  }
})

const keyMetricItems = computed(() => ([
  { label: 'Tourists', value: Number(dashboardStats.value.users?.tourists || 0) },
  { label: 'Operators', value: Number(dashboardStats.value.users?.operators || 0) },
  { label: 'Quotes', value: Number(dashboardStats.value.quotes?.total || 0) },
  { label: 'Tickets', value: Number(dashboardStats.value.tickets?.open || 0) },
]))

const heroMetrics = computed(() => ([
  {
    label: 'Total Revenue',
    value: formatCompactNumber(dashboardFinancial.value.totalRevenue),
    note: 'All recorded revenue',
  },
  {
    label: 'Monthly Revenue',
    value: formatCompactNumber(dashboardFinancial.value.monthlyRevenue),
    note: 'Current month performance',
  },
  {
    label: 'Open Quotes',
    value: Number(dashboardStats.value.quotes?.open || 0),
    note: 'Still awaiting closure',
  },
  {
    label: 'Average Rating',
    value: satisfactionWidget.value.rating,
    note: 'Operator review average',
  },
]))

const revenueChartBars = computed(() => {
  const maxValue = revenueWidgetMax.value || 1
  return revenueWidgetBars.value.map((item, index) => {
    const height = Math.max(18, Math.round((Number(item.value || 0) / maxValue) * 128))
    return {
      ...item,
      x: 64 + (index * 92),
      y: 184 - height,
      width: 54,
      height,
    }
  })
})

const bookingsTrendSeries = computed(() => {
  const maxValue = bookingsWidgetMax.value || 1
  return bookingsWidgetBars.value.map((item, index) => ({
    ...item,
    x: 72 + (index * 108),
    y: 184 - Math.max(18, Math.round((Number(item.value || 0) / maxValue) * 126)),
  }))
})

const bookingsTrendPoints = computed(() => bookingsTrendSeries.value.map((point) => `${point.x},${point.y}`).join(' '))

const refreshDashboard = async () => {
  loading.value = true
  errorMessage.value = ''

  try {
    const config = getAdminConfig()
    const dashboardId = route.params.dashboardId
    const [dashboardResponse, statsResponse, financialResponse, leaderboardResponse] = await Promise.all([
      api.get(`/admin/reports/dashboards/${dashboardId}`, config),
      api.get('/admin/dashboard/stats', config),
      api.get('/admin/financial/overview', config),
      api.get('/admin/operators/leaderboard?limit=5', config),
    ])

    dashboard.value = dashboardResponse.data?.dashboard || null
    dashboardStats.value = statsResponse.data || { users: {}, quotes: {}, operators: {}, tickets: {} }
    dashboardFinancial.value = financialResponse.data || { totalRevenue: 0, monthlyRevenue: 0, pendingPayouts: 0, commissionCollected: 0 }
    dashboardLeaderboard.value = leaderboardResponse.data?.leaderboard || leaderboardResponse.data?.operators || []
  } catch (error) {
    console.error('Failed to load report dashboard:', error)
    errorMessage.value = error.response?.data?.detail || error.message || 'Failed to load dashboard'
  } finally {
    loading.value = false
  }
}

const goBackToReports = () => {
  router.push({ name: 'AdminReports' })
}

const goToReportsHub = () => {
  router.push({ name: 'AdminReports' })
}

onMounted(() => {
  refreshDashboard()
})
</script>

<style scoped>
.admin-report-dashboard {
  width: 100%;
}

.dashboard-shell {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.page-actions {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  flex-wrap: wrap;
}

.page-actions-right {
  display: flex;
  gap: 0.75rem;
  flex-wrap: wrap;
}

.ghost-button,
.primary-button {
  border-radius: 999px;
  padding: 0.8rem 1.1rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.2s ease, box-shadow 0.2s ease, background 0.2s ease;
}

.ghost-button {
  border: 1px solid #cbd5e1;
  background: #ffffff;
  color: #1e293b;
}

.primary-button {
  border: none;
  background: linear-gradient(135deg, #0f766e 0%, #0f4c81 100%);
  color: #ffffff;
  box-shadow: 0 14px 30px rgba(15, 118, 110, 0.22);
}

.ghost-button:hover,
.primary-button:hover {
  transform: translateY(-1px);
}

.ghost-button:disabled,
.primary-button:disabled {
  opacity: 0.65;
  cursor: wait;
  transform: none;
}

.state-card,
.dashboard-hero,
.share-section {
  background: linear-gradient(160deg, #ffffff 0%, #f3f8ff 100%);
  border: 1px solid rgba(148, 163, 184, 0.25);
  border-radius: 28px;
  padding: 1.5rem;
}

.error-state {
  border-color: rgba(220, 38, 38, 0.25);
  background: linear-gradient(160deg, #fff7f7 0%, #fff1f2 100%);
}

.dashboard-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.8fr) minmax(280px, 1fr);
  gap: 1.25rem;
  align-items: start;
}

.eyebrow,
.widget-label {
  margin: 0 0 0.5rem;
  color: #0f766e;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.dashboard-hero h1,
.state-card h1 {
  margin: 0;
  color: #0f172a;
  font-size: 2.2rem;
}

.hero-copy,
.state-card p,
.share-section p,
.panel-note {
  color: #475569;
  line-height: 1.6;
}

.hero-meta,
.kpi-strip,
.metric-row,
.metrics-grid-panel {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 0.9rem;
}

.hero-meta-card,
.kpi-card,
.metric-box {
  background: rgba(255, 255, 255, 0.82);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px;
  padding: 1rem;
}

.hero-meta-card span,
.kpi-card span,
.metric-box span,
.operator-rank {
  color: #64748b;
  font-size: 0.82rem;
}

.hero-meta-card strong,
.kpi-card strong,
.metric-box strong,
.satisfaction-score strong {
  display: block;
  margin-top: 0.35rem;
  color: #0f172a;
  font-size: 1.3rem;
}

.kpi-card small {
  color: #64748b;
}

.widget-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(320px, 1fr));
  gap: 1.25rem;
}

.widget-panel {
  background: #ffffff;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 26px;
  padding: 1.35rem;
  box-shadow: 0 20px 40px rgba(15, 23, 42, 0.06);
}

.widget-header {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: start;
  margin-bottom: 1rem;
}

.widget-header h2,
.share-section h3 {
  margin: 0;
  color: #0f172a;
}

.widget-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  background: #ecfeff;
  color: #155e75;
  padding: 0.45rem 0.75rem;
  font-size: 0.8rem;
  font-weight: 700;
}

.chart-svg {
  width: 100%;
  height: auto;
  margin-top: 0.5rem;
}

.axis-line,
.trend-line {
  fill: none;
  stroke: #cbd5e1;
  stroke-width: 2;
}

.trend-line {
  stroke: #0f766e;
  stroke-linecap: round;
  stroke-linejoin: round;
  stroke-width: 4;
}

.chart-text,
.chart-value {
  fill: #475569;
  font-size: 12px;
  font-weight: 700;
}

.chart-value {
  fill: #0f172a;
}

.trend-point {
  fill: #ffffff;
  stroke: #0f766e;
  stroke-width: 4;
}

.operator-stack {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.operator-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 18px;
  padding: 0.9rem 1rem;
  background: #f8fafc;
}

.operator-row strong,
.operator-stats strong {
  color: #0f172a;
}

.operator-stats {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  color: #64748b;
  font-size: 0.88rem;
}

.satisfaction-layout {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.satisfaction-score span {
  color: #64748b;
}

.progress-rail {
  height: 16px;
  border-radius: 999px;
  background: #e2e8f0;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  border-radius: inherit;
  background: linear-gradient(90deg, #f59e0b 0%, #10b981 100%);
}

.metric-box-compact strong {
  font-size: 1.15rem;
}

@media (max-width: 960px) {
  .dashboard-hero {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .dashboard-hero h1,
  .state-card h1 {
    font-size: 1.8rem;
  }

  .widget-grid {
    grid-template-columns: 1fr;
  }

  .page-actions,
  .page-actions-right {
    flex-direction: column;
  }

  .ghost-button,
  .primary-button {
    width: 100%;
  }
}
</style>