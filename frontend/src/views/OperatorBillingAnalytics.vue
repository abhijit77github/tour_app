<template>
  <div class="analytics-page">
    <section class="hero">
      <div class="hero-orb hero-orb-left"></div>
      <div class="hero-orb hero-orb-right"></div>
      <div class="hero-inner">
        <div>
          <span class="eyebrow">Operator billing analytics</span>
          <h1>Track spend trends, credit burn, and billing mix from one view</h1>
          <p class="hero-copy">This page focuses on operator-side billing analytics only: daily spend trends, credit usage, billable activity, surface mix, and recent ledger movement.</p>
        </div>

        <div class="hero-actions">
          <div class="range-toggle" role="group" aria-label="Analytics range">
            <button
              v-for="option in rangeOptions"
              :key="option"
              type="button"
              :class="['range-chip', { active: selectedDays === option }]"
              @click="changeRange(option)"
              :disabled="loading"
            >
              {{ option }}d
            </button>
          </div>

          <div class="hero-links">
            <router-link class="btn-ghost" to="/operator/promotions">Billing and promotions</router-link>
            <button class="btn-primary" type="button" @click="loadAnalytics" :disabled="loading">
              {{ loading ? 'Refreshing…' : 'Refresh analytics' }}
            </button>
          </div>
        </div>
      </div>
    </section>

    <div class="page-shell">
      <div v-if="notice.text" :class="['notice', notice.type]">{{ notice.text }}</div>
      <div v-if="loadError" class="notice error">{{ loadError }}</div>

      <div class="metrics-grid">
        <article class="metric-card highlight">
          <span>Current credits</span>
          <strong>{{ currentCredits }}</strong>
          <p>{{ currentPlan?.name || 'Free plan' }}</p>
        </article>
        <article class="metric-card">
          <span>Tracked spend</span>
          <strong>₹{{ formatMoney(totals.spend_amount) }}</strong>
          <p>Across the last {{ selectedDays }} days</p>
        </article>
        <article class="metric-card">
          <span>Credits consumed</span>
          <strong>{{ totals.credits_consumed }}</strong>
          <p>{{ averageCreditsPerBillableEvent }} avg per billable event</p>
        </article>
        <article class="metric-card">
          <span>Billable events</span>
          <strong>{{ totals.billable_events }}</strong>
          <p>{{ totals.non_billable_events }} tracked but non-billable</p>
        </article>
      </div>

      <div class="main-grid">
        <section class="panel chart-panel">
          <div class="panel-head">
            <div>
              <p class="panel-kicker">Trend chart</p>
              <h2>Daily spend and credits</h2>
            </div>
            <div class="chart-controls">
              <div class="legend">
              <span class="legend-item"><i class="legend-swatch spend"></i> Spend</span>
              <span class="legend-item"><i class="legend-swatch credits"></i> Credits</span>
              </div>
              <div v-if="surfaceFilters.length" class="surface-toggle-group">
                <button
                  v-for="surface in surfaceFilters"
                  :key="surface.value"
                  type="button"
                  :class="['surface-toggle', { active: isSurfaceActive(surface.value) }]"
                  @click="toggleSurface(surface.value)"
                >
                  {{ surface.label }}
                </button>
              </div>
            </div>
          </div>

          <div v-if="!dailySeries.length" class="empty-box">No billable activity yet for the selected range.</div>
          <div v-else class="trend-chart-wrap">
            <div class="bar-chart" aria-label="Daily spend chart">
              <div
                v-for="point in dailySeries"
                :key="point.date"
                :class="['bar-column', { active: hoveredPoint?.date === point.date }]"
                @mouseenter="setHoveredPoint(point)"
                @focusin="setHoveredPoint(point)"
              >
                <div class="bar-value">₹{{ formatCompact(point.spend_amount) }}</div>
                <div class="bar-track">
                  <div class="bar-fill" :style="{ height: `${point.spendRatio}%` }"></div>
                </div>
                <div class="bar-label">{{ point.shortLabel }}</div>
                <div v-if="hoveredPoint?.date === point.date" class="chart-tooltip">
                  <strong>{{ point.label }}</strong>
                  <span>Spend ₹{{ formatMoney(point.spend_amount) }}</span>
                  <span>Credits {{ point.credits_consumed }}</span>
                  <span>Events {{ point.events }}</span>
                  <span>Top {{ humanize(point.topSurface) }}</span>
                </div>
              </div>
            </div>

            <div class="line-chart-box">
              <svg viewBox="0 0 100 36" preserveAspectRatio="none" class="line-chart" role="img" aria-label="Daily credits trend line">
                <polyline class="line-path" :points="creditPolyline"></polyline>
                <circle
                  v-for="point in creditChartPoints"
                  :key="point.date"
                  class="line-point"
                  :cx="point.x"
                  :cy="point.y"
                  r="1.2"
                  @mouseenter="setHoveredPoint(point.raw)"
                ></circle>
              </svg>
              <div class="line-axis">
                <span>{{ dailySeries[0]?.shortLabel }}</span>
                <span>{{ dailySeries[dailySeries.length - 1]?.shortLabel }}</span>
              </div>
            </div>

            <div class="hover-panel">
              <div>
                <span class="hover-label">Hover detail</span>
                <strong>{{ activeInspectorPoint.label }}</strong>
              </div>
              <div class="hover-stats">
                <span>Spend ₹{{ formatMoney(activeInspectorPoint.spend_amount) }}</span>
                <span>Credits {{ activeInspectorPoint.credits_consumed }}</span>
                <span>Events {{ activeInspectorPoint.events }}</span>
                <span>Surface {{ humanize(activeInspectorPoint.topSurface) }}</span>
              </div>
            </div>
          </div>
        </section>

        <section class="panel summary-panel">
          <div class="panel-head">
            <div>
              <p class="panel-kicker">Breakdown</p>
              <h2>Surface and efficiency mix</h2>
            </div>
          </div>

          <div class="breakdown-list">
            <article v-for="row in surfaceBreakdown" :key="row.surface" class="breakdown-card">
              <div class="breakdown-top">
                <div>
                  <h3>{{ humanize(row.surface) }}</h3>
                  <p>{{ row.shareLabel }}</p>
                </div>
                <strong>₹{{ formatMoney(row.spend_amount) }}</strong>
              </div>
              <div class="mix-bar">
                <div class="mix-fill" :style="{ width: `${row.spendShare}%` }"></div>
              </div>
              <div class="breakdown-stats">
                <span>{{ row.billable_events }} billable</span>
                <span>{{ row.non_billable_events }} non-billable</span>
                <span>{{ row.credits_consumed }} credits</span>
              </div>
            </article>
            <div v-if="!surfaceBreakdown.length" class="empty-box compact">No billing surfaces recorded yet.</div>
          </div>

          <div class="insight-list">
            <article class="insight-card">
              <span>Peak spend day</span>
              <strong>{{ peakSpendDay.label }}</strong>
              <p>₹{{ formatMoney(peakSpendDay.spend_amount) }}</p>
            </article>
            <article class="insight-card">
              <span>Peak credit day</span>
              <strong>{{ peakCreditDay.label }}</strong>
              <p>{{ peakCreditDay.credits_consumed }} credits</p>
            </article>
            <article class="insight-card">
              <span>Daily average spend</span>
              <strong>₹{{ formatMoney(dailyAverageSpend) }}</strong>
              <p>{{ activeDays }} active days in range</p>
            </article>
          </div>
        </section>
      </div>

      <div class="secondary-grid">
        <section class="panel">
          <div class="panel-head">
            <div>
              <p class="panel-kicker">Daily spend table</p>
              <h2>Daily billable activity</h2>
            </div>
          </div>

          <div class="table-wrap">
            <table class="analytics-table">
              <thead>
                <tr>
                  <th>Date</th>
                  <th>Spend</th>
                  <th>Credits</th>
                  <th>Billable events</th>
                  <th>Top surface</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="point in activeDailyRows" :key="point.date">
                  <td>{{ point.label }}</td>
                  <td>₹{{ formatMoney(point.spend_amount) }}</td>
                  <td>{{ point.credits_consumed }}</td>
                  <td>{{ point.events }}</td>
                  <td>{{ humanize(point.topSurface) }}</td>
                </tr>
                <tr v-if="!activeDailyRows.length">
                  <td colspan="5" class="empty-inline">No daily spend rows yet.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <section class="panel">
          <div class="panel-head">
            <div>
              <p class="panel-kicker">Ledger</p>
              <h2>Recent credit movement</h2>
            </div>
          </div>

          <div class="ledger-list">
            <article v-for="entry in ledgerEntries.slice(0, 10)" :key="entry._id" class="ledger-row">
              <div>
                <strong>{{ readableLedgerType(entry.entry_type) }}</strong>
                <p>{{ entry.notes || humanize(entry.source_reference_type) }}</p>
              </div>
              <div class="ledger-right">
                <span :class="['delta-pill', entry.credits_delta >= 0 ? 'positive' : 'negative']">{{ signedCredits(entry.credits_delta) }}</span>
                <small>{{ formatDate(entry.created_at) }} · Balance {{ entry.balance_after }}</small>
              </div>
            </article>
            <div v-if="!ledgerEntries.length" class="empty-box compact">No credit ledger entries yet.</div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../services/api'

const rangeOptions = [7, 30, 60, 90]

const loading = ref(false)
const loadError = ref('')
const notice = ref({ type: 'info', text: '' })
const selectedDays = ref(30)
const planState = ref(null)
const analytics = ref(null)
const ledgerEntries = ref([])
const hoveredPoint = ref(null)
const selectedSurfaces = ref([])

const currentSubscription = computed(() => planState.value?.subscription || null)
const currentPlan = computed(() => planState.value?.plan || null)
const currentCredits = computed(() => Number(currentSubscription.value?.credits_remaining || 0))
const totals = computed(() => analytics.value?.totals || {
  billable_events: 0,
  non_billable_events: 0,
  credits_consumed: 0,
  spend_amount: 0,
})

const surfaceFilters = computed(() => {
  const seen = new Set()
  const rows = analytics.value?.by_surface || []
  return rows
    .map((row) => row.surface)
    .filter((surface) => {
      if (!surface || seen.has(surface)) return false
      seen.add(surface)
      return true
    })
    .map((surface) => ({ value: surface, label: humanize(surface) }))
})

const filteredDailyRows = computed(() => {
  const rows = analytics.value?.daily || []
  if (!selectedSurfaces.value.length) return rows
  return rows.filter((row) => selectedSurfaces.value.includes(row.surface))
})

const surfaceBreakdown = computed(() => {
  const rows = analytics.value?.by_surface || []
  const visibleRows = selectedSurfaces.value.length
    ? rows.filter((row) => selectedSurfaces.value.includes(row.surface))
    : rows
  const totalSpend = visibleRows.reduce((sum, row) => sum + Number(row.spend_amount || 0), 0)
  return visibleRows
    .map((row) => {
      const spend = Number(row.spend_amount || 0)
      const share = totalSpend > 0 ? (spend / totalSpend) * 100 : 0
      return {
        ...row,
        spendShare: Number(share.toFixed(1)),
        shareLabel: `${share.toFixed(1)}% of spend`,
      }
    })
    .sort((left, right) => Number(right.spend_amount || 0) - Number(left.spend_amount || 0))
})

const dailySeries = computed(() => {
  const aggregated = new Map()
  const rawRows = filteredDailyRows.value

  rawRows.forEach((row) => {
    const existing = aggregated.get(row.date) || {
      date: row.date,
      spend_amount: 0,
      credits_consumed: 0,
      events: 0,
      topSurface: row.surface,
      topSurfaceSpend: 0,
    }

    existing.spend_amount += Number(row.spend_amount || 0)
    existing.credits_consumed += Number(row.credits_consumed || 0)
    existing.events += Number(row.events || 0)

    const rowSpend = Number(row.spend_amount || 0)
    if (rowSpend >= existing.topSurfaceSpend) {
      existing.topSurfaceSpend = rowSpend
      existing.topSurface = row.surface
    }

    aggregated.set(row.date, existing)
  })

  const maxSpend = Math.max(...Array.from(aggregated.values()).map(item => item.spend_amount), 0)
  const points = []
  for (let offset = selectedDays.value - 1; offset >= 0; offset -= 1) {
    const current = new Date()
    current.setHours(0, 0, 0, 0)
    current.setDate(current.getDate() - offset)
    const dateKey = current.toISOString().slice(0, 10)
    const row = aggregated.get(dateKey) || {
      date: dateKey,
      spend_amount: 0,
      credits_consumed: 0,
      events: 0,
      topSurface: 'none',
    }
    points.push({
      ...row,
      label: current.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }),
      shortLabel: current.toLocaleDateString(undefined, { month: 'short', day: 'numeric' }).replace(' ', '\n'),
      spendRatio: maxSpend > 0 ? Math.max(8, Math.round((row.spend_amount / maxSpend) * 100)) : 0,
    })
  }
  return points
})

const activeDailyRows = computed(() => dailySeries.value.filter(item => item.spend_amount > 0 || item.credits_consumed > 0 || item.events > 0).reverse())
const activeInspectorPoint = computed(() => hoveredPoint.value || peakSpendDay.value)

const peakSpendDay = computed(() => {
  const row = activeDailyRows.value.reduce((best, current) => (
    Number(current.spend_amount || 0) > Number(best.spend_amount || 0) ? current : best
  ), { label: 'No activity', spend_amount: 0 })
  return row
})

const peakCreditDay = computed(() => {
  const row = activeDailyRows.value.reduce((best, current) => (
    Number(current.credits_consumed || 0) > Number(best.credits_consumed || 0) ? current : best
  ), { label: 'No activity', credits_consumed: 0 })
  return row
})

const activeDays = computed(() => activeDailyRows.value.length)
const dailyAverageSpend = computed(() => activeDays.value ? Number(totals.value.spend_amount || 0) / activeDays.value : 0)
const averageCreditsPerBillableEvent = computed(() => {
  const billable = Number(totals.value.billable_events || 0)
  return billable ? (Number(totals.value.credits_consumed || 0) / billable).toFixed(2) : '0.00'
})

const creditPolyline = computed(() => {
  const series = dailySeries.value
  if (!series.length) return ''
  const maxCredits = Math.max(...series.map(item => Number(item.credits_consumed || 0)), 0)
  return series.map((point, index) => {
    const x = series.length === 1 ? 50 : (index / (series.length - 1)) * 100
    const y = maxCredits > 0 ? 32 - ((Number(point.credits_consumed || 0) / maxCredits) * 28) : 32
    return `${x},${y}`
  }).join(' ')
})

const creditChartPoints = computed(() => {
  const series = dailySeries.value
  if (!series.length) return []
  const maxCredits = Math.max(...series.map(item => Number(item.credits_consumed || 0)), 0)
  return series.map((point, index) => ({
    date: point.date,
    x: series.length === 1 ? 50 : (index / (series.length - 1)) * 100,
    y: maxCredits > 0 ? 32 - ((Number(point.credits_consumed || 0) / maxCredits) * 28) : 32,
    raw: point,
  }))
})

const setNotice = (type, text) => {
  notice.value = { type, text }
  window.clearTimeout(setNotice.timeoutId)
  setNotice.timeoutId = window.setTimeout(() => {
    notice.value = { type: 'info', text: '' }
  }, 4500)
}

const setHoveredPoint = (point) => {
  hoveredPoint.value = point
}

const isSurfaceActive = (surface) => !selectedSurfaces.value.length || selectedSurfaces.value.includes(surface)

const toggleSurface = (surface) => {
  const hasExplicitSelection = selectedSurfaces.value.length > 0
  if (!hasExplicitSelection) {
    selectedSurfaces.value = surfaceFilters.value
      .map((item) => item.value)
      .filter((value) => value !== surface)
  } else if (selectedSurfaces.value.includes(surface)) {
    selectedSurfaces.value = selectedSurfaces.value.filter((value) => value !== surface)
  } else {
    selectedSurfaces.value = [...selectedSurfaces.value, surface]
  }

  if (!selectedSurfaces.value.length || selectedSurfaces.value.length === surfaceFilters.value.length) {
    selectedSurfaces.value = []
  }
}

const loadAnalytics = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const [planRes, analyticsRes, ledgerRes] = await Promise.all([
      api.get('/operator/billing/plan'),
      api.get(`/operator/billing/analytics?days=${selectedDays.value}`),
      api.get('/operator/billing/ledger?limit=20'),
    ])

    planState.value = planRes.data
    analytics.value = analyticsRes.data || null
    ledgerEntries.value = ledgerRes.data.entries || []
    hoveredPoint.value = null
  } catch (error) {
    console.error('Failed to load operator billing analytics:', error)
    loadError.value = error.response?.data?.detail || 'Failed to load operator billing analytics'
    setNotice('error', loadError.value)
  } finally {
    loading.value = false
  }
}

const changeRange = async (days) => {
  if (selectedDays.value === days) return
  selectedDays.value = days
  await loadAnalytics()
}

const formatMoney = (value) => Number(value || 0).toFixed(2)
const formatCompact = (value) => {
  const amount = Number(value || 0)
  if (amount >= 1000) return `${(amount / 1000).toFixed(1)}k`
  return amount.toFixed(0)
}
const formatDate = (value) => new Date(value).toLocaleString()
const humanize = (value) => String(value || 'none').replaceAll('_', ' ')
const signedCredits = (value) => `${value > 0 ? '+' : ''}${value}`
const readableLedgerType = (value) => String(value || '').replaceAll('_', ' ')

onMounted(loadAnalytics)
</script>

<style scoped>
.analytics-page {
  min-height: 100vh;
  background:
    radial-gradient(circle at top left, rgba(251, 191, 36, 0.12), transparent 28%),
    linear-gradient(180deg, #f4efe7 0%, #edf4f7 42%, #eff5fb 100%);
  padding-bottom: 5rem;
}

.hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #10201f 0%, #155e75 48%, #1d4ed8 100%);
  padding: 3.8rem 1.6rem 6.6rem;
}

.hero-orb {
  position: absolute;
  border-radius: 999px;
  filter: blur(10px);
  opacity: 0.32;
}

.hero-orb-left {
  width: 240px;
  height: 240px;
  left: -40px;
  top: 18px;
  background: #f59e0b;
}

.hero-orb-right {
  width: 280px;
  height: 280px;
  right: -70px;
  top: -20px;
  background: #38bdf8;
}

.hero-inner {
  position: relative;
  z-index: 1;
  max-width: 1240px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
  gap: 1.4rem;
  align-items: end;
}

.eyebrow,
.panel-kicker {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eyebrow {
  margin-bottom: 1rem;
  padding: 0.34rem 0.82rem;
  border-radius: 999px;
  border: 1px solid rgba(255,255,255,0.24);
  background: rgba(255,255,255,0.11);
  color: #fef3c7;
}

.hero h1 {
  margin: 0;
  color: #fff;
  font-size: clamp(2rem, 4vw, 3.1rem);
  line-height: 1.04;
}

.hero-copy {
  margin: 1rem 0 0;
  max-width: 700px;
  color: rgba(255,255,255,0.74);
  line-height: 1.6;
}

.hero-actions {
  display: grid;
  gap: 1rem;
  justify-items: end;
}

.range-toggle,
.hero-links {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  justify-content: flex-end;
}

.range-chip,
.btn-primary,
.btn-ghost {
  border-radius: 999px;
  border: 1px solid transparent;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  text-decoration: none;
}

.range-chip {
  padding: 0.68rem 0.9rem;
  background: rgba(255,255,255,0.08);
  color: rgba(255,255,255,0.74);
  border-color: rgba(255,255,255,0.12);
}

.range-chip.active {
  background: #fff;
  color: #0f172a;
}

.btn-primary {
  padding: 0.82rem 1.05rem;
  background: linear-gradient(135deg, #f59e0b, #ea580c);
  color: #fff;
}

.btn-ghost {
  padding: 0.8rem 1.02rem;
  border-color: rgba(255,255,255,0.24);
  background: rgba(255,255,255,0.08);
  color: #fff;
}

.page-shell {
  max-width: 1240px;
  margin: -2.8rem auto 0;
  padding: 0 1.5rem;
  position: relative;
  z-index: 2;
}

.notice {
  margin-bottom: 1rem;
  padding: 0.95rem 1rem;
  border-radius: 16px;
  font-weight: 600;
}

.notice.success { background: #ecfdf5; border: 1px solid #bbf7d0; color: #166534; }
.notice.error { background: #fff1f2; border: 1px solid #fecdd3; color: #be123c; }

.metrics-grid,
.main-grid,
.secondary-grid {
  display: grid;
  gap: 1rem;
}

.metrics-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
  margin-bottom: 1rem;
}

.main-grid {
  grid-template-columns: minmax(0, 1.2fr) minmax(320px, 0.8fr);
}

.secondary-grid {
  grid-template-columns: minmax(0, 1fr) minmax(320px, 0.8fr);
  margin-top: 1rem;
}

.metric-card,
.panel {
  background: rgba(255,255,255,0.92);
  border: 1px solid rgba(226,232,240,0.95);
  border-radius: 24px;
  box-shadow: 0 16px 40px rgba(15,23,42,0.08);
}

.metric-card {
  padding: 1.2rem;
}

.metric-card.highlight {
  background: linear-gradient(135deg, #fff7ed, #fffbeb);
  border-color: #fed7aa;
}

.metric-card span,
.insight-card span,
.panel-kicker {
  color: #64748b;
}

.metric-card span,
.insight-card span {
  display: block;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.metric-card strong,
.insight-card strong {
  display: block;
  margin-top: 0.35rem;
  font-size: 1.45rem;
  color: #0f172a;
}

.metric-card p,
.insight-card p,
.breakdown-card p,
.ledger-row p {
  margin: 0.45rem 0 0;
  color: #64748b;
  line-height: 1.5;
}

.panel {
  padding: 1.35rem;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}

.panel-head h2,
.breakdown-card h3 {
  margin: 0;
  color: #0f172a;
}

.legend {
  display: flex;
  flex-wrap: wrap;
  gap: 0.7rem;
}

.chart-controls {
  display: grid;
  gap: 0.8rem;
  justify-items: end;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  color: #475569;
  font-size: 0.85rem;
  font-weight: 600;
}

.legend-swatch {
  width: 14px;
  height: 14px;
  border-radius: 999px;
  display: inline-block;
}

.legend-swatch.spend { background: linear-gradient(180deg, #0ea5e9, #1d4ed8); }
.legend-swatch.credits { background: #f59e0b; }

.trend-chart-wrap {
  display: grid;
  gap: 1rem;
}

.bar-chart {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(18px, 1fr));
  gap: 0.42rem;
  min-height: 240px;
  align-items: end;
}

.bar-column {
  display: grid;
  gap: 0.35rem;
  justify-items: center;
  position: relative;
}

.bar-column.active .bar-fill {
  background: linear-gradient(180deg, #f59e0b, #ea580c);
}

.bar-value,
.bar-label,
.line-axis {
  color: #64748b;
  font-size: 0.7rem;
}

.bar-value {
  min-height: 1rem;
}

.bar-track {
  width: 100%;
  height: 170px;
  border-radius: 999px;
  background: linear-gradient(180deg, #e0f2fe, #f8fafc);
  position: relative;
  overflow: hidden;
}

.bar-fill {
  position: absolute;
  inset-inline: 0;
  bottom: 0;
  border-radius: 999px;
  background: linear-gradient(180deg, #0ea5e9, #1d4ed8);
  min-height: 4px;
}

.line-chart-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 0.8rem;
}

.line-chart {
  width: 100%;
  height: 140px;
}

.line-path {
  fill: none;
  stroke: #f59e0b;
  stroke-width: 1.8;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.line-point {
  fill: #fff;
  stroke: #f59e0b;
  stroke-width: 0.7;
}

.line-axis {
  display: flex;
  justify-content: space-between;
  margin-top: 0.5rem;
}

.chart-tooltip {
  position: absolute;
  bottom: calc(100% + 0.5rem);
  left: 50%;
  transform: translateX(-50%);
  display: grid;
  gap: 0.2rem;
  min-width: 132px;
  padding: 0.55rem 0.65rem;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.94);
  color: #fff;
  box-shadow: 0 12px 30px rgba(15, 23, 42, 0.25);
  z-index: 4;
}

.chart-tooltip strong {
  font-size: 0.75rem;
}

.chart-tooltip span,
.hover-label {
  font-size: 0.72rem;
  color: rgba(255,255,255,0.75);
}

.hover-panel {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  padding: 0.9rem 1rem;
  border-radius: 16px;
  background: #fff7ed;
  border: 1px solid #fed7aa;
}

.hover-panel strong {
  display: block;
  margin-top: 0.15rem;
  color: #7c2d12;
}

.hover-stats {
  display: flex;
  flex-wrap: wrap;
  gap: 0.55rem;
  justify-content: flex-end;
}

.hover-stats span,
.surface-toggle {
  display: inline-flex;
  align-items: center;
  padding: 0.28rem 0.65rem;
  border-radius: 999px;
  font-size: 0.76rem;
  font-weight: 700;
}

.hover-stats span {
  background: #fff;
  border: 1px solid #fdba74;
  color: #9a3412;
}

.surface-toggle-group {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  justify-content: flex-end;
}

.surface-toggle {
  border: 1px solid #cbd5e1;
  background: #fff;
  color: #475569;
  cursor: pointer;
}

.surface-toggle.active {
  background: #0f172a;
  border-color: #0f172a;
  color: #fff;
}

.breakdown-list,
.insight-list,
.ledger-list {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}

.breakdown-card,
.insight-card,
.ledger-row {
  background: #fafcff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  padding: 1rem;
}

.breakdown-top,
.ledger-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.breakdown-top strong {
  color: #0f172a;
  font-size: 1.15rem;
}

.mix-bar {
  margin-top: 0.75rem;
  height: 10px;
  background: #e2e8f0;
  border-radius: 999px;
  overflow: hidden;
}

.mix-fill {
  height: 100%;
  min-width: 4px;
  border-radius: 999px;
  background: linear-gradient(90deg, #f59e0b, #fb7185);
}

.breakdown-stats {
  margin-top: 0.8rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.breakdown-stats span {
  display: inline-flex;
  align-items: center;
  padding: 0.24rem 0.62rem;
  border-radius: 999px;
  background: #fff;
  border: 1px solid #dbe4ee;
  color: #475569;
  font-size: 0.76rem;
  font-weight: 700;
}

.insight-list {
  margin-top: 1rem;
}

.table-wrap {
  overflow-x: auto;
}

.analytics-table {
  width: 100%;
  border-collapse: collapse;
}

.analytics-table th,
.analytics-table td {
  padding: 0.8rem 0.55rem;
  border-bottom: 1px solid #eef2f7;
  text-align: left;
}

.analytics-table th {
  color: #94a3b8;
  font-size: 0.74rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.07em;
}

.ledger-right {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.3rem;
}

.delta-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.24rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 800;
}

.delta-pill.positive { background: #ecfdf5; color: #166534; }
.delta-pill.negative { background: #fff1f2; color: #be123c; }

.empty-box,
.empty-inline {
  color: #94a3b8;
  text-align: center;
}

.empty-box {
  min-height: 160px;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 1px dashed #dbe4ee;
  border-radius: 16px;
  background: #f8fafc;
  padding: 1rem;
}

.empty-box.compact {
  min-height: 110px;
}

@media (max-width: 1100px) {
  .hero-inner,
  .main-grid,
  .secondary-grid,
  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .hero-actions {
    justify-items: start;
  }

  .chart-controls,
  .range-toggle,
  .hero-links {
    justify-content: flex-start;
    justify-items: start;
  }
}

@media (max-width: 720px) {
  .hero {
    padding: 3rem 1rem 6rem;
  }

  .page-shell {
    padding: 0 1rem;
  }

  .panel,
  .metric-card {
    padding: 1rem;
  }

  .panel-head,
  .breakdown-top,
  .ledger-row,
  .hover-panel {
    flex-direction: column;
  }

  .ledger-right {
    align-items: flex-start;
  }

  .surface-toggle-group,
  .hover-stats {
    justify-content: flex-start;
  }

  .bar-chart {
    grid-template-columns: repeat(auto-fit, minmax(14px, 1fr));
  }

  .bar-label,
  .bar-value {
    font-size: 0.64rem;
  }
}
</style>