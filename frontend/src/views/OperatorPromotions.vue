<template>
  <div class="opromo-page">
    <section class="hero">
      <div class="hero-bg"></div>
      <div class="hero-inner">
        <div>
          <span class="eyebrow">Operator Billing</span>
          <h1>Manage paid distribution, campaign orders, and credit usage in one place</h1>
          <p class="hero-sub">This view combines the production billing slice with the existing promotion purchase flow: current plan state, upgrade requests, recent credit usage, and location promotion orders.</p>
        </div>
        <div class="hero-metrics">
          <div class="metric-card">
            <strong>{{ currentPlan?.name || 'Free' }}</strong>
            <span>Current plan</span>
          </div>
          <div class="metric-card">
            <strong>{{ currentCredits }}</strong>
            <span>Credits remaining</span>
          </div>
          <div class="metric-card">
            <strong>{{ analytics?.totals?.billable_events || 0 }}</strong>
            <span>Billed events (30d)</span>
          </div>
          <div class="metric-card">
            <strong>{{ totalPurchaseOrders }}</strong>
            <span>Purchase orders</span>
          </div>
        </div>
      </div>
    </section>

    <div class="page-shell">
      <div v-if="notice.text" :class="['notice', notice.type]">{{ notice.text }}</div>

      <section class="workspace-shell">
        <div class="workspace-topbar">
          <div class="workspace-copy">
            <p class="panel-kicker">Operator Revenue Console</p>
            <h2>Plans, orders, usage, and transaction history</h2>
          </div>
          <button class="btn-secondary" @click="loadAll" :disabled="loading">{{ loading ? 'Refreshing…' : 'Refresh' }}</button>
        </div>

        <div class="tab-bar" role="tablist" aria-label="Operator billing tabs">
          <button :class="['tab-button', { active: activeTab === 'overview' }]" type="button" @click="activeTab = 'overview'">
            <span>Overview</span>
            <small>{{ overviewCount }}</small>
          </button>
          <button :class="['tab-button', { active: activeTab === 'plans' }]" type="button" @click="activeTab = 'plans'">
            <span>Plans & orders</span>
            <small>{{ billingPlans.length + planOrdersPagination.totalItems }}</small>
          </button>
          <button :class="['tab-button', { active: activeTab === 'promotions' }]" type="button" @click="activeTab = 'promotions'">
            <span>Promotion orders</span>
            <small>{{ promotionOrdersPagination.totalItems }}</small>
          </button>
          <button :class="['tab-button', { active: activeTab === 'usage' }]" type="button" @click="activeTab = 'usage'">
            <span>Usage & ledger</span>
            <small>{{ ledgerPagination.totalItems }}</small>
          </button>
        </div>

        <div v-if="activeTab === 'overview'" class="tab-panel">
          <div class="compact-summary-grid">
            <article class="summary-card compact-card">
              <span class="summary-label">Current plan</span>
              <strong>{{ currentPlan?.name || 'Free' }}</strong>
              <p>{{ currentPlan?.description || 'Organic listing only until a paid plan is activated.' }}</p>
            </article>
            <article class="summary-card compact-card">
              <span class="summary-label">Credits</span>
              <strong>{{ currentCredits }}</strong>
              <p>{{ creditSummaryText }}</p>
            </article>
            <article class="summary-card compact-card">
              <span class="summary-label">Open plan order</span>
              <strong>{{ openPlanOrder ? formatStatus(openPlanOrder.order_status) : 'None' }}</strong>
              <p>{{ openPlanOrder ? `${openPlanOrder.plan_snapshot?.name} · ₹${formatMoney(openPlanOrder.amount)}` : 'No payment is waiting for settlement.' }}</p>
            </article>
            <article class="summary-card compact-card">
              <span class="summary-label">Active campaigns</span>
              <strong>{{ planState?.active_promotions || 0 }}</strong>
              <p>Campaigns only serve while the plan is active and credits remain.</p>
            </article>
          </div>

          <div v-if="openPlanOrder" class="pending-banner">
            Open plan order: <strong>{{ openPlanOrder.plan_snapshot?.name }}</strong> · {{ providerLabel(openPlanOrder.payment_provider) }} · {{ formatStatus(openPlanOrder.order_status) }} · ₹{{ formatMoney(openPlanOrder.amount) }}
          </div>
          <div v-else-if="requestedPlan" class="pending-banner">
            Legacy pending plan request: <strong>{{ requestedPlan.name }}</strong>. Future paid upgrades should use plan orders instead.
          </div>

          <div class="content-grid two-col">
            <section class="panel compact-panel">
              <div class="panel-head with-meta">
                <div>
                  <p class="panel-kicker">Recent plan orders</p>
                  <h2>Paid plan purchase queue</h2>
                </div>
                <div class="panel-meta-row">
                  <span class="panel-meta">{{ pageRangeLabel(planOrdersPagination, planOrdersPage, planOrders.length, PAGE_SIZE.planOrders) }}</span>
                  <div class="pager">
                    <button class="pager-btn" type="button" @click="changePlanOrdersPage(-1)" :disabled="planOrdersPage <= 1 || loading">Prev</button>
                    <span>{{ planOrdersPage }} / {{ totalPagesFor(planOrdersPagination, PAGE_SIZE.planOrders) }}</span>
                    <button class="pager-btn" type="button" @click="changePlanOrdersPage(1)" :disabled="!planOrdersPagination.hasMore || loading">Next</button>
                  </div>
                </div>
              </div>

              <div v-if="!planOrders.length" class="empty-box compact-empty">No plan purchase orders yet.</div>
              <div v-else class="orders-list scroll-list compact-scroll">
                <article v-for="order in planOrders" :key="order._id" class="order-row compact-row">
                  <div>
                    <h3>{{ order.plan_snapshot?.name }}</h3>
                    <p>{{ order.order_code }} · {{ providerLabel(order.payment_provider) }}</p>
                    <div class="pkg-meta">
                      <span>{{ order.plan_snapshot?.included_credits || 0 }} credits</span>
                      <span>{{ formatDate(order.created_at) }}</span>
                      <span>₹{{ formatMoney(order.amount) }}</span>
                    </div>
                  </div>
                  <div class="order-actions">
                    <span :class="['status-chip', order.order_status]">{{ formatStatus(order.order_status) }}</span>
                    <button v-if="canCancelPlanOrder(order)" class="btn-danger" @click="cancelPlanOrder(order._id)" type="button">Cancel</button>
                  </div>
                </article>
              </div>
            </section>

            <section class="panel compact-panel">
              <div class="panel-head with-meta">
                <div>
                  <p class="panel-kicker">Recent transactions</p>
                  <h2>Credit movement snapshot</h2>
                </div>
                <div class="panel-meta-row">
                  <span class="panel-meta">{{ pageRangeLabel(ledgerPagination, ledgerPage, ledgerEntries.length, PAGE_SIZE.ledger) }}</span>
                  <div class="pager">
                    <button class="pager-btn" type="button" @click="changeLedgerPage(-1)" :disabled="ledgerPage <= 1 || loading">Prev</button>
                    <span>{{ ledgerPage }} / {{ totalPagesFor(ledgerPagination, PAGE_SIZE.ledger) }}</span>
                    <button class="pager-btn" type="button" @click="changeLedgerPage(1)" :disabled="!ledgerPagination.hasMore || loading">Next</button>
                  </div>
                </div>
              </div>

              <div v-if="!ledgerEntries.length" class="empty-box compact-empty">No ledger entries yet.</div>
              <div v-else class="surface-table-wrap compact-scroll ledger-table-wrap">
                <table class="surface-table compact-table ledger-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Reference</th>
                      <th>Delta</th>
                      <th>Balance</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="entry in ledgerEntries"
                      :key="entry._id"
                      :class="['ledger-table-row', entry.credits_delta >= 0 ? 'positive' : 'negative']"
                    >
                      <td>
                        <span class="ledger-type-badge">{{ readableLedgerType(entry.entry_type) }}</span>
                      </td>
                      <td>
                        <div class="ledger-reference-cell">
                          <strong>{{ entry.notes || entry.source_reference_type || 'Credit ledger update' }}</strong>
                          <span>{{ entry.source_reference_type || 'manual_adjustment' }}</span>
                        </div>
                      </td>
                      <td>
                        <span :class="['delta-pill', entry.credits_delta >= 0 ? 'positive' : 'negative']">{{ signedCredits(entry.credits_delta) }}</span>
                      </td>
                      <td class="ledger-balance-cell">{{ entry.balance_after }}</td>
                      <td class="ledger-time-cell">{{ formatDate(entry.created_at) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </div>

        <div v-else-if="activeTab === 'plans'" class="tab-panel">
          <div class="content-grid two-col">
            <section class="panel compact-panel">
              <div class="panel-head">
                <div>
                  <p class="panel-kicker">Plan catalog</p>
                  <h2>Buy active credit plans</h2>
                </div>
              </div>

              <div class="plan-guidance">
                <h3>How paid plans create business gain</h3>
                <p>Paid plans keep your distribution active and give predictable credit inventory for billable search and planner surfaces.</p>
                <div class="journey-chips">
                  <span class="journey-chip">1. Pick a plan by coverage</span>
                  <span class="journey-chip">2. Create paid order</span>
                  <span class="journey-chip">3. Credits activate after settlement</span>
                </div>
              </div>

              <div class="plan-value-strip" v-if="planDecisionRows.length">
                <div class="value-strip-head">
                  <div>
                    <strong>Quick compare</strong>
                    <p class="value-strip-sub">{{ roiBaselineLabel }}</p>
                  </div>
                  <span>Based on your recent usage trend</span>
                </div>
                <div class="value-pill-row">
                  <article v-for="row in planDecisionRows" :key="`value-${row.code}`" class="value-pill" :class="{ recommended: row.code === recommendedPlanCode, current: currentPlan?.code === row.code }">
                    <div class="value-pill-top">
                      <strong>{{ row.name }}</strong>
                      <span v-if="row.code === recommendedPlanCode" class="status-chip completed">Recommended</span>
                      <span v-else-if="currentPlan?.code === row.code" class="status-chip current">Current</span>
                    </div>
                    <p>₹{{ formatMoney(row.monthly_price) }} · {{ row.included_credits }} credits · ₹{{ formatMoney(row.cost_per_credit) }}/credit</p>
                    <small class="roi-small">Est. qualified leads: {{ formatDecimal(row.estimated_qualified_leads, 1) }}/month</small>
                    <small class="roi-small">Est. cost per qualified lead: ₹{{ row.cost_per_qualified_lead ? formatMoney(row.cost_per_qualified_lead) : '0.00' }}</small>
                    <small>{{ row.runway_label }}</small>
                  </article>
                </div>
              </div>

              <label class="field inline-provider compact-provider">
                <span>Preferred payment provider for plan purchase</span>
                <select v-model="selectedPlanProvider">
                  <option v-for="provider in paymentProviders" :key="`plan-${provider}`" :value="provider">{{ providerLabel(provider) }}</option>
                </select>
              </label>

              <div class="plan-list scroll-list compact-scroll">
                <article v-for="plan in billingPlans" :key="plan._id" :class="['plan-card', { current: currentPlan?.code === plan.code }]">
                  <div class="plan-top">
                    <div>
                      <h3>{{ plan.name }}</h3>
                      <p>{{ plan.description }}</p>
                    </div>
                    <div class="plan-price">₹{{ formatMoney(plan.monthly_price) }}</div>
                  </div>
                  <div class="plan-meta">
                    <span>{{ plan.included_credits }} credits</span>
                    <span>{{ plan.currency }}</span>
                    <span v-if="plan.code !== 'FREE'">₹{{ formatMoney(costPerCredit(plan)) }}/credit</span>
                    <span v-if="plan.code !== 'FREE'">{{ planRunwayLabel(plan) }}</span>
                    <span v-if="plan.code !== 'FREE'">Est. leads {{ formatDecimal(estimatedQualifiedLeadsForCredits(plan.included_credits), 1) }}/mo</span>
                  </div>
                  <div class="feature-tags">
                    <span v-for="feature in plan.features || []" :key="feature" class="feature-tag">{{ feature }}</span>
                  </div>
                  <div class="plan-actions">
                    <span v-if="plan.code === 'FREE'" class="status-chip current">No purchase required</span>
                    <span v-else-if="hasOpenPlanOrder" class="status-chip pending_payment">Order already open</span>
                    <button v-else class="btn-primary" @click="createPlanOrder(plan.code)" :disabled="requestingPlan === plan.code">
                      {{ requestingPlan === plan.code ? 'Creating…' : currentPlan?.code === plan.code ? 'Buy again' : 'Start paid order' }}
                    </button>
                  </div>
                </article>
              </div>
            </section>

            <section class="panel compact-panel">
              <div class="panel-head with-meta">
                <div>
                  <p class="panel-kicker">Plan orders</p>
                  <h2>Track credit-plan purchase orders</h2>
                </div>
                <div class="panel-meta-row">
                  <span class="panel-meta">{{ pageRangeLabel(planOrdersPagination, planOrdersPage, planOrders.length, PAGE_SIZE.planOrders) }}</span>
                  <div class="pager">
                    <button class="pager-btn" type="button" @click="changePlanOrdersPage(-1)" :disabled="planOrdersPage <= 1 || loading">Prev</button>
                    <span>{{ planOrdersPage }} / {{ totalPagesFor(planOrdersPagination, PAGE_SIZE.planOrders) }}</span>
                    <button class="pager-btn" type="button" @click="changePlanOrdersPage(1)" :disabled="!planOrdersPagination.hasMore || loading">Next</button>
                  </div>
                </div>
              </div>

              <div v-if="!planOrders.length" class="empty-box compact-empty">No plan purchase orders yet.</div>
              <div v-else class="orders-list scroll-list compact-scroll">
                <article v-for="order in planOrders" :key="order._id" class="order-row compact-row">
                  <div>
                    <h3>{{ order.plan_snapshot?.name }}</h3>
                    <p>{{ order.order_code }} · {{ providerLabel(order.payment_provider) }}</p>
                    <div class="pkg-meta">
                      <span>{{ order.plan_snapshot?.included_credits || 0 }} credits</span>
                      <span>{{ formatDate(order.created_at) }}</span>
                      <span>₹{{ formatMoney(order.amount) }}</span>
                    </div>
                  </div>
                  <div class="order-actions">
                    <span :class="['status-chip', order.order_status]">{{ formatStatus(order.order_status) }}</span>
                    <button v-if="canCancelPlanOrder(order)" class="btn-danger" @click="cancelPlanOrder(order._id)" type="button">Cancel</button>
                  </div>
                </article>
              </div>
            </section>
          </div>
        </div>

        <div v-else-if="activeTab === 'promotions'" class="tab-panel">
          <div class="content-grid two-col">
            <section class="panel compact-panel">
              <div class="panel-head">
                <div>
                  <p class="panel-kicker">Promotion packages</p>
                  <h2>Create location promotion orders</h2>
                </div>
              </div>

              <div v-if="loading && !packages.length" class="empty-box compact-empty">Loading packages…</div>
              <div v-else class="package-list scroll-list compact-scroll">
                <button
                  v-for="pkg in packages"
                  :key="pkg._id"
                  class="package-card"
                  :class="{ active: selectedPackage?._id === pkg._id }"
                  @click="selectPackage(pkg)"
                  type="button"
                >
                  <div class="pkg-top">
                    <div>
                      <h3>{{ pkg.name }}</h3>
                      <p>{{ pkg.description }}</p>
                    </div>
                    <strong>₹{{ formatMoney(pkg.price) }}</strong>
                  </div>
                  <div class="pkg-meta">
                    <span>{{ pkg.duration_days }} days</span>
                    <span>{{ formatServiceTypes(pkg.available_service_types) }}</span>
                    <span>Priority {{ pkg.priority }}</span>
                  </div>
                </button>
              </div>

              <form v-if="selectedPackage" class="order-form compact-form" @submit.prevent="submitPurchase">
                <label class="field">
                  <span>Target location</span>
                  <select v-model="selectedAreaIndex" required>
                    <option value="">Select one of your serving areas</option>
                    <option v-for="(area, index) in servingAreas" :key="`${area.area_name}-${area.state}-${index}`" :value="String(index)">
                      {{ formatArea(area) }}
                    </option>
                  </select>
                </label>
                <label class="field">
                  <span>Service type</span>
                  <select v-model="selectedServiceType" required>
                    <option value="">Select service type</option>
                    <option v-for="svc in availableServiceTypes" :key="svc" :value="svc">{{ formatServiceType(svc) }}</option>
                  </select>
                </label>
                <label class="field">
                  <span>Payment provider</span>
                  <select v-model="selectedProvider" required>
                    <option v-for="provider in paymentProviders" :key="provider" :value="provider">{{ providerLabel(provider) }}</option>
                  </select>
                </label>

                <div class="gateway-note">
                  Gateway status: <strong>{{ gatewayStatus }}</strong>. Payment capture and webhook settlement can attach without changing the operator purchase path.
                </div>

                <button class="btn-primary" type="submit" :disabled="submittingOrder || !selectedArea || !selectedServiceType || !selectedProvider">
                  {{ submittingOrder ? 'Creating…' : `Create order for ₹${formatMoney(selectedPackage.price)}` }}
                </button>
              </form>
            </section>

            <section class="panel compact-panel">
              <div class="panel-head with-meta">
                <div>
                  <p class="panel-kicker">Promotion orders</p>
                  <h2>Purchase history and current queue</h2>
                </div>
                <div class="panel-meta-row">
                  <span class="panel-meta">{{ pageRangeLabel(promotionOrdersPagination, promotionOrdersPage, orders.length, PAGE_SIZE.promotionOrders) }}</span>
                  <div class="pager">
                    <button class="pager-btn" type="button" @click="changePromotionOrdersPage(-1)" :disabled="promotionOrdersPage <= 1 || loading">Prev</button>
                    <span>{{ promotionOrdersPage }} / {{ totalPagesFor(promotionOrdersPagination, PAGE_SIZE.promotionOrders) }}</span>
                    <button class="pager-btn" type="button" @click="changePromotionOrdersPage(1)" :disabled="!promotionOrdersPagination.hasMore || loading">Next</button>
                  </div>
                </div>
              </div>

              <div v-if="loading && !orders.length" class="empty-box compact-empty">Loading orders…</div>
              <div v-else-if="!orders.length" class="empty-box compact-empty">No promotion orders yet.</div>
              <div v-else class="orders-list scroll-list compact-scroll">
                <article v-for="order in orders" :key="order._id" class="order-row compact-row">
                  <div>
                    <h3>{{ order.package_snapshot?.name }}</h3>
                    <p>{{ formatLocationScope(order.location_scope) }}</p>
                    <div class="pkg-meta">
                      <span>{{ formatServiceType(order.service_type) }}</span>
                      <span>{{ providerLabel(order.payment_provider) }}</span>
                      <span>{{ formatDate(order.created_at) }}</span>
                      <span>₹{{ formatMoney(order.amount) }}</span>
                    </div>
                  </div>
                  <div class="order-actions">
                    <span :class="['status-chip', order.order_status]">{{ formatStatus(order.order_status) }}</span>
                    <button v-if="order.order_status === 'pending_payment'" class="btn-danger" @click="cancelOrder(order._id)" type="button">Cancel</button>
                  </div>
                </article>
              </div>
            </section>
          </div>
        </div>

        <div v-else class="tab-panel">
          <div class="content-grid usage-stack">
            <section class="panel compact-panel">
              <div class="panel-head">
                <div>
                  <p class="panel-kicker">Usage metrics</p>
                  <h2>Billing analytics and spend mix</h2>
                </div>
                <router-link to="/operator/billing-analytics" class="btn-secondary analytics-link">Open full analytics</router-link>
              </div>

              <div class="analytics-grid compact-analytics-grid">
                <div class="stat-box compact-stat-box">
                  <span>Billable events</span>
                  <strong>{{ analytics?.totals?.billable_events || 0 }}</strong>
                </div>
                <div class="stat-box compact-stat-box">
                  <span>Non-billable events</span>
                  <strong>{{ analytics?.totals?.non_billable_events || 0 }}</strong>
                </div>
                <div class="stat-box compact-stat-box">
                  <span>Credits consumed</span>
                  <strong>{{ analytics?.totals?.credits_consumed || 0 }}</strong>
                </div>
                <div class="stat-box compact-stat-box">
                  <span>Tracked spend</span>
                  <strong>₹{{ formatMoney(analytics?.totals?.spend_amount || 0) }}</strong>
                </div>
              </div>

              <div class="surface-table-wrap compact-scroll">
                <table class="surface-table compact-table">
                  <thead>
                    <tr>
                      <th>Surface</th>
                      <th>Billable</th>
                      <th>Non-billable</th>
                      <th>Credits</th>
                      <th>Spend</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr v-for="row in analytics?.by_surface || []" :key="row.surface">
                      <td>{{ row.surface }}</td>
                      <td>{{ row.billable_events }}</td>
                      <td>{{ row.non_billable_events }}</td>
                      <td>{{ row.credits_consumed }}</td>
                      <td>₹{{ formatMoney(row.spend_amount) }}</td>
                    </tr>
                    <tr v-if="!(analytics?.by_surface || []).length">
                      <td colspan="5" class="empty-inline">No billing events yet.</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>

            <section class="panel compact-panel">
              <div class="panel-head with-meta">
                <div>
                  <p class="panel-kicker">Transaction history</p>
                  <h2>Credit ledger</h2>
                </div>
                <div class="panel-meta-row">
                  <span class="panel-meta">{{ pageRangeLabel(ledgerPagination, ledgerPage, ledgerEntries.length, PAGE_SIZE.ledger) }}</span>
                  <div class="pager">
                    <button class="pager-btn" type="button" @click="changeLedgerPage(-1)" :disabled="ledgerPage <= 1 || loading">Prev</button>
                    <span>{{ ledgerPage }} / {{ totalPagesFor(ledgerPagination, PAGE_SIZE.ledger) }}</span>
                    <button class="pager-btn" type="button" @click="changeLedgerPage(1)" :disabled="!ledgerPagination.hasMore || loading">Next</button>
                  </div>
                </div>
              </div>

              <div v-if="!ledgerEntries.length" class="empty-box compact-empty">No ledger entries yet.</div>
              <div v-else class="surface-table-wrap compact-scroll ledger-table-wrap">
                <table class="surface-table compact-table ledger-table">
                  <thead>
                    <tr>
                      <th>Type</th>
                      <th>Reference</th>
                      <th>Delta</th>
                      <th>Balance</th>
                      <th>Time</th>
                    </tr>
                  </thead>
                  <tbody>
                    <tr
                      v-for="entry in ledgerEntries"
                      :key="entry._id"
                      :class="['ledger-table-row', entry.credits_delta >= 0 ? 'positive' : 'negative']"
                    >
                      <td>
                        <span class="ledger-type-badge">{{ readableLedgerType(entry.entry_type) }}</span>
                      </td>
                      <td>
                        <div class="ledger-reference-cell">
                          <strong>{{ entry.notes || entry.source_reference_type || 'Credit ledger update' }}</strong>
                          <span>{{ entry.source_reference_type || 'manual_adjustment' }}</span>
                        </div>
                      </td>
                      <td>
                        <span :class="['delta-pill', entry.credits_delta >= 0 ? 'positive' : 'negative']">{{ signedCredits(entry.credits_delta) }}</span>
                      </td>
                      <td class="ledger-balance-cell">{{ entry.balance_after }}</td>
                      <td class="ledger-time-cell">{{ formatDate(entry.created_at) }}</td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </section>
          </div>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../services/api'

const loading = ref(false)
const submittingOrder = ref(false)
const requestingPlan = ref('')
const activeTab = ref('overview')
const packages = ref([])
const billingPlans = ref([])
const orders = ref([])
const planOrders = ref([])
const ledgerEntries = ref([])
const analytics = ref(null)
const planState = ref(null)
const profile = ref(null)
const selectedPackage = ref(null)
const selectedAreaIndex = ref('')
const selectedServiceType = ref('')
const selectedProvider = ref('razorpay')
const selectedPlanProvider = ref('razorpay')
const gatewayStatus = ref('not_configured')
const paymentProviders = ref(['razorpay', 'stripe', 'payu'])
const notice = ref({ type: 'info', text: '' })
const planOrdersPage = ref(1)
const promotionOrdersPage = ref(1)
const ledgerPage = ref(1)
const planOrdersPagination = ref({ totalItems: 0, hasMore: false, nextCursor: null })
const promotionOrdersPagination = ref({ totalItems: 0, hasMore: false, nextCursor: null })
const ledgerPagination = ref({ totalItems: 0, hasMore: false, nextCursor: null })
const planOrderCursors = ref([null])
const promotionOrderCursors = ref([null])
const ledgerCursors = ref([null])

const PAGE_SIZE = {
  planOrders: 5,
  promotionOrders: 6,
  ledger: 8,
}

const servingAreas = computed(() => profile.value?.serving_areas || [])
const selectedArea = computed(() => {
  if (selectedAreaIndex.value === '') return null
  return servingAreas.value[Number(selectedAreaIndex.value)] || null
})
const availableServiceTypes = computed(() => {
  if (!selectedPackage.value) return []
  const operatorTypes = profile.value?.service_types || ['tour']
  return (selectedPackage.value.available_service_types || []).filter(type => operatorTypes.includes(type))
})
const currentSubscription = computed(() => planState.value?.subscription || null)
const currentPlan = computed(() => planState.value?.plan || null)
const requestedPlan = computed(() => planState.value?.requested_plan || null)
const openPlanOrder = computed(() => planState.value?.open_plan_order || planOrders.value.find(order => ['pending_payment', 'payment_pending', 'payment_received', 'fulfillment_pending'].includes(order.order_status)) || null)
const hasOpenPlanOrder = computed(() => Boolean(openPlanOrder.value))
const currentCredits = computed(() => Number(currentSubscription.value?.credits_remaining || 0))
const totalPurchaseOrders = computed(() => promotionOrdersPagination.value.totalItems + planOrdersPagination.value.totalItems)
const overviewCount = computed(() => [openPlanOrder.value, currentPlan.value, analytics.value, ledgerEntries.value.length].filter(Boolean).length)
const usageWindowDays = computed(() => {
  const dailyRows = analytics.value?.daily || []
  if (dailyRows.length) return dailyRows.length
  return 30
})
const averageDailyCreditBurn = computed(() => {
  const consumed = Number(analytics.value?.totals?.credits_consumed || 0)
  const days = Math.max(1, usageWindowDays.value)
  return consumed / days
})
const qualifiedLeadsPer100Credits = computed(() => {
  const consumed = Number(analytics.value?.totals?.credits_consumed || 0)
  const billableEvents = Number(analytics.value?.totals?.billable_events || 0)
  const configuredFallback = Number(analytics.value?.roi_baseline_qualified_leads_per_100_credits || 10)
  if (consumed <= 0 || billableEvents <= 0) return configuredFallback
  return (billableEvents / consumed) * 100
})
const roiBaselineLabel = computed(() => {
  const observed = Number(analytics.value?.totals?.credits_consumed || 0) > 0
  const baseline = formatDecimal(qualifiedLeadsPer100Credits.value, 1)
  if (observed) {
    return `Baseline: ${baseline} qualified leads per 100 credits from your recent billed activity.`
  }
  return `Baseline: ${baseline} qualified leads per 100 credits (starter estimate until usage history grows).`
})
const planDecisionRows = computed(() => {
  return (billingPlans.value || [])
    .filter(plan => plan?.code && plan.code !== 'FREE')
    .map((plan) => {
      const credits = Number(plan.included_credits || 0)
      const price = Number(plan.monthly_price || 0)
      const perCredit = credits > 0 ? price / credits : 0
      const estimatedQualifiedLeads = estimatedQualifiedLeadsForCredits(credits)
      const costPerQualifiedLead = estimatedQualifiedLeads > 0 ? price / estimatedQualifiedLeads : 0
      const runwayDays = averageDailyCreditBurn.value > 0 && credits > 0
        ? credits / averageDailyCreditBurn.value
        : null
      return {
        code: plan.code,
        name: plan.name,
        monthly_price: price,
        included_credits: credits,
        cost_per_credit: perCredit,
        estimated_qualified_leads: estimatedQualifiedLeads,
        cost_per_qualified_lead: costPerQualifiedLead,
        runway_days: runwayDays,
        runway_label: runwayDays
          ? `${Math.round(runwayDays)} day coverage at current usage`
          : 'Runway appears unlimited until burn starts',
      }
    })
})
const recommendedPlanCode = computed(() => {
  if (!planDecisionRows.value.length) return ''
  const targetDays = 30
  const sorted = [...planDecisionRows.value].sort((a, b) => a.monthly_price - b.monthly_price)
  const fit = sorted.find(row => Number(row.runway_days || 0) >= targetDays)
  return (fit || sorted[sorted.length - 1]).code
})
const creditSummaryText = computed(() => {
  if (openPlanOrder.value) {
    return 'A paid plan order is open. Your current subscription keeps running until settlement and fulfillment complete.'
  }
  if (currentSubscription.value?.requested_plan_code) {
    return 'Legacy upgrade request is still visible until it is cleared by a fulfilled order.'
  }
  return 'Credits are consumed by configured billable search and planner events.'
})

const setNotice = (type, text) => {
  notice.value = { type, text }
  window.clearTimeout(setNotice.timeoutId)
  setNotice.timeoutId = window.setTimeout(() => {
    notice.value = { type: 'info', text: '' }
  }, 4500)
}

const resetSelection = () => {
  selectedAreaIndex.value = ''
  selectedServiceType.value = ''
  selectedProvider.value = 'razorpay'
}

const buildClientRequestId = () => {
  if (window.crypto?.randomUUID) return window.crypto.randomUUID()
  return `plan-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

const totalPagesFor = (pagination, pageSize) => {
  const totalItems = Number(pagination?.totalItems || 0)
  return Math.max(1, Math.ceil(totalItems / pageSize))
}

const pageRangeLabel = (pagination, page, currentCount, pageSize) => {
  const totalItems = Number(pagination?.totalItems || 0)
  if (!totalItems || !currentCount) return '0-0 of 0'
  const safePage = Math.min(Math.max(1, Number(page || 1)), totalPagesFor(pagination, pageSize))
  const start = (safePage - 1) * pageSize + 1
  const end = start + currentCount - 1
  return `${start}-${end} of ${totalItems}`
}

const syncCursorState = (cursorRef, page, nextCursor) => {
  if (cursorRef.value.length === page) {
    cursorRef.value.push(nextCursor)
  } else {
    cursorRef.value[page] = nextCursor
  }
  cursorRef.value = cursorRef.value.slice(0, page + 1)
}

const resetPages = () => {
  planOrdersPage.value = 1
  promotionOrdersPage.value = 1
  ledgerPage.value = 1
  planOrderCursors.value = [null]
  promotionOrderCursors.value = [null]
  ledgerCursors.value = [null]
}

const loadAll = async () => {
  loading.value = true
  try {
    const [
      profileRes,
      packagesRes,
      ordersRes,
      billingPlansRes,
      planRes,
      planOrdersRes,
      ledgerRes,
      analyticsRes,
    ] = await Promise.all([
      api.get('/operators/profile/me'),
      api.get('/operator/promotions/packages', { params: { limit: 50 } }),
      api.get('/operator/promotions/orders', { params: { page_size: PAGE_SIZE.promotionOrders, cursor: promotionOrderCursors.value[promotionOrdersPage.value - 1] || undefined } }),
      api.get('/operator/billing/plans'),
      api.get('/operator/billing/plan'),
      api.get('/operator/billing/orders', { params: { page_size: PAGE_SIZE.planOrders, cursor: planOrderCursors.value[planOrdersPage.value - 1] || undefined } }),
      api.get('/operator/billing/ledger', { params: { page_size: PAGE_SIZE.ledger, cursor: ledgerCursors.value[ledgerPage.value - 1] || undefined } }),
      api.get('/operator/billing/analytics'),
    ])

    profile.value = profileRes.data
    packages.value = packagesRes.data.packages || []
    orders.value = ordersRes.data.orders || []
    billingPlans.value = billingPlansRes.data.plans || []
    planState.value = planRes.data
    planOrders.value = planOrdersRes.data.orders || []
    ledgerEntries.value = ledgerRes.data.entries || []
    analytics.value = analyticsRes.data || null
    promotionOrdersPagination.value = {
      totalItems: ordersRes.data.pagination?.total_items || orders.value.length,
      hasMore: Boolean(ordersRes.data.pagination?.has_more),
      nextCursor: ordersRes.data.pagination?.next_cursor || null,
    }
    planOrdersPagination.value = {
      totalItems: planOrdersRes.data.pagination?.total_items || planOrders.value.length,
      hasMore: Boolean(planOrdersRes.data.pagination?.has_more),
      nextCursor: planOrdersRes.data.pagination?.next_cursor || null,
    }
    ledgerPagination.value = {
      totalItems: ledgerRes.data.pagination?.total_items || ledgerEntries.value.length,
      hasMore: Boolean(ledgerRes.data.pagination?.has_more),
      nextCursor: ledgerRes.data.pagination?.next_cursor || null,
    }
    syncCursorState(promotionOrderCursors, promotionOrdersPage.value, promotionOrdersPagination.value.nextCursor)
    syncCursorState(planOrderCursors, planOrdersPage.value, planOrdersPagination.value.nextCursor)
    syncCursorState(ledgerCursors, ledgerPage.value, ledgerPagination.value.nextCursor)
    paymentProviders.value = billingPlansRes.data.payment_providers || packagesRes.data.payment_providers || ['razorpay', 'stripe', 'payu']
    gatewayStatus.value = billingPlansRes.data.gateway_status || packagesRes.data.gateway_status || 'not_configured'
    if (!paymentProviders.value.includes(selectedPlanProvider.value)) {
      selectedPlanProvider.value = paymentProviders.value[0] || 'razorpay'
    }

    if (!selectedPackage.value && packages.value.length) {
      selectedPackage.value = packages.value[0]
    } else if (selectedPackage.value) {
      const refreshed = packages.value.find(pkg => pkg._id === selectedPackage.value._id)
      selectedPackage.value = refreshed || packages.value[0] || null
    }
    if (selectedPackage.value && !availableServiceTypes.value.includes(selectedServiceType.value)) {
      selectedServiceType.value = availableServiceTypes.value[0] || ''
    }
  } catch (error) {
    console.error('Failed to load operator billing data:', error)
    setNotice('error', error.response?.data?.detail || 'Failed to load billing data')
  } finally {
    loading.value = false
  }
}

const createPlanOrder = async (planCode) => {
  requestingPlan.value = planCode
  try {
    const response = await api.post('/operator/billing/orders', {
      plan_code: planCode,
      payment_provider: selectedPlanProvider.value,
      client_request_id: buildClientRequestId(),
    })
    setNotice('success', response.data.message)
    resetPages()
    await loadAll()
  } catch (error) {
    console.error('Failed to create plan order:', error)
    setNotice('error', error.response?.data?.detail || 'Failed to create plan order')
  } finally {
    requestingPlan.value = ''
  }
}

const canCancelPlanOrder = (order) => ['pending_payment', 'payment_pending', 'payment_received'].includes(order?.order_status)

const cancelPlanOrder = async (orderId) => {
  try {
    await api.delete(`/operator/billing/orders/${orderId}`)
    setNotice('success', 'Plan order cancelled')
    resetPages()
    await loadAll()
  } catch (error) {
    console.error('Failed to cancel plan order:', error)
    setNotice('error', error.response?.data?.detail || 'Failed to cancel plan order')
  }
}

const selectPackage = (pkg) => {
  selectedPackage.value = pkg
  selectedServiceType.value = availableServiceTypes.value[0] || ''
}

const submitPurchase = async () => {
  if (!selectedPackage.value || !selectedArea.value || !selectedServiceType.value || !selectedProvider.value) {
    setNotice('error', 'Choose a package, location, service type, and provider')
    return
  }

  submittingOrder.value = true
  try {
    const response = await api.post('/operator/promotions/purchase', {
      package_id: selectedPackage.value._id,
      location_scope: {
        area_name: selectedArea.value.area_name || null,
        state: selectedArea.value.state || null,
        country: selectedArea.value.country || null,
      },
      service_type: selectedServiceType.value,
      payment_provider: selectedProvider.value,
    })
    setNotice('success', response.data.message)
    resetPages()
    await loadAll()
    resetSelection()
  } catch (error) {
    console.error('Failed to create promotion order:', error)
    setNotice('error', error.response?.data?.detail || 'Failed to create promotion order')
  } finally {
    submittingOrder.value = false
  }
}

const cancelOrder = async (orderId) => {
  try {
    await api.delete(`/operator/promotions/orders/${orderId}`)
    setNotice('success', 'Promotion order cancelled')
    resetPages()
    await loadAll()
  } catch (error) {
    console.error('Failed to cancel order:', error)
    setNotice('error', error.response?.data?.detail || 'Failed to cancel order')
  }
}

const formatMoney = (value) => Number(value || 0).toFixed(2)
const formatDecimal = (value, digits = 1) => Number(value || 0).toFixed(digits)
const formatServiceTypes = (types) => (types || []).map(formatServiceType).join(' / ')
const formatServiceType = (type) => (type === 'car' ? 'Car service' : 'Tour service')
const formatArea = (area) => [area.area_name, area.state, area.country].filter(Boolean).join(', ')
const formatLocationScope = (scope) => [scope?.area_name, scope?.state, scope?.country].filter(Boolean).join(', ')
const formatStatus = (value) => String(value || '').replaceAll('_', ' ')
const providerLabel = (provider) => {
  if (provider === 'payu') return 'PayU'
  if (provider === 'stripe') return 'Stripe'
  return 'Razorpay'
}
const formatDate = (value) => new Date(value).toLocaleString()
const signedCredits = (value) => `${value > 0 ? '+' : ''}${value}`
const readableLedgerType = (value) => String(value || '').replaceAll('_', ' ')
const costPerCredit = (plan) => {
  const credits = Number(plan?.included_credits || 0)
  const price = Number(plan?.monthly_price || 0)
  if (!credits) return 0
  return price / credits
}
const planRunwayLabel = (plan) => {
  const credits = Number(plan?.included_credits || 0)
  const burn = Number(averageDailyCreditBurn.value || 0)
  if (!credits || burn <= 0) return 'Runway updates after usage starts'
  const days = Math.max(1, Math.round(credits / burn))
  return `${days} day estimated coverage`
}
const estimatedQualifiedLeadsForCredits = (credits) => {
  const normalizedCredits = Number(credits || 0)
  if (normalizedCredits <= 0) return 0
  return (normalizedCredits / 100) * Number(qualifiedLeadsPer100Credits.value || 0)
}

const changePlanOrdersPage = async (delta) => {
  const nextPage = Math.max(1, planOrdersPage.value + delta)
  if (nextPage === planOrdersPage.value) return
  if (delta > 0 && !planOrdersPagination.value.hasMore) return
  planOrdersPage.value = nextPage
  await loadAll()
}

const changePromotionOrdersPage = async (delta) => {
  const nextPage = Math.max(1, promotionOrdersPage.value + delta)
  if (nextPage === promotionOrdersPage.value) return
  if (delta > 0 && !promotionOrdersPagination.value.hasMore) return
  promotionOrdersPage.value = nextPage
  await loadAll()
}

const changeLedgerPage = async (delta) => {
  const nextPage = Math.max(1, ledgerPage.value + delta)
  if (nextPage === ledgerPage.value) return
  if (delta > 0 && !ledgerPagination.value.hasMore) return
  ledgerPage.value = nextPage
  await loadAll()
}

onMounted(loadAll)
</script>

<style scoped>
.opromo-page {
  min-height: 100vh;
  background: #eef3f8;
  padding-bottom: 5rem;
}

.hero {
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #0f172a 0%, #18324d 55%, #0f766e 100%);
  padding: 4rem 2rem 7rem;
}

.hero-bg {
  position: absolute;
  inset: 0;
  background: radial-gradient(circle at 10% 30%, rgba(56,189,248,0.18), transparent 40%), radial-gradient(circle at 90% 10%, rgba(16,185,129,0.14), transparent 42%);
}

.hero-inner {
  position: relative;
  z-index: 1;
  max-width: 1200px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 1.4rem;
  align-items: end;
}

.eyebrow,
.panel-kicker {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.eyebrow {
  margin-bottom: 1rem;
  padding: 0.32rem 0.85rem;
  border-radius: 999px;
  background: rgba(56,189,248,0.15);
  border: 1px solid rgba(56,189,248,0.28);
  color: #7dd3fc;
}

.hero-inner h1 {
  margin: 0;
  color: #fff;
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 1.08;
}

.hero-sub {
  margin: 1rem 0 0;
  color: rgba(255,255,255,0.72);
  line-height: 1.6;
}

.hero-metrics {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.metric-card {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 18px;
  padding: 1rem;
}

.metric-card strong {
  display: block;
  color: #fff;
  font-size: 1.3rem;
}

.metric-card span {
  color: rgba(255,255,255,0.58);
  font-size: 0.8rem;
}

.page-shell {
  max-width: 1200px;
  margin: -3.2rem auto 0;
  padding: 0 1.5rem;
  position: relative;
  z-index: 2;
}

.workspace-shell {
  display: grid;
  gap: 1rem;
}

.workspace-topbar {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  padding: 1rem 1.1rem;
  border: 1px solid rgba(255,255,255,0.6);
  border-radius: 20px;
  background: rgba(255,255,255,0.74);
  backdrop-filter: blur(10px);
}

.workspace-copy h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.2rem;
}

.tab-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0.7rem;
  border: 1px solid rgba(215,225,236,0.9);
  border-radius: 20px;
  background: rgba(255,255,255,0.9);
  box-shadow: 0 12px 30px rgba(15,23,42,0.06);
}

.tab-button {
  min-width: 160px;
  display: inline-flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
  padding: 0.8rem 1rem;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: #64748b;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, border-color 140ms ease, transform 140ms ease, color 140ms ease;
}

.tab-button:hover {
  transform: translateY(-1px);
  background: #f8fbff;
  border-color: #d7e1ec;
}

.tab-button.active {
  background: linear-gradient(135deg, rgba(14,165,233,0.12), rgba(37,99,235,0.14));
  border-color: rgba(14,165,233,0.22);
  color: #0f172a;
}

.tab-button small {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.8rem;
  height: 1.8rem;
  padding: 0 0.45rem;
  border-radius: 999px;
  background: rgba(255,255,255,0.9);
  color: #0369a1;
  font-size: 0.72rem;
  font-weight: 800;
}

.tab-panel {
  display: grid;
  gap: 1rem;
}

.notice {
  margin-bottom: 1rem;
  padding: 0.9rem 1rem;
  border-radius: 14px;
  font-weight: 600;
}

.notice.success { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; }
.notice.error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; }

.top-grid,
.bottom-grid {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 1.4rem;
}

.content-grid {
  display: grid;
  gap: 1rem;
}

.content-grid.two-col {
  grid-template-columns: 1.08fr 0.92fr;
}

.content-grid.usage-stack {
  grid-template-columns: 1fr;
  gap: 0.9rem;
}

.compact-summary-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 0.85rem;
}

.bottom-grid { margin-top: 1.4rem; }

.panel {
  background: #fff;
  border: 1px solid #e7edf4;
  border-radius: 22px;
  box-shadow: 0 10px 32px rgba(15,23,42,0.08);
  padding: 1.4rem;
}

.compact-panel {
  padding: 1.15rem;
}

.panel-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1rem;
}

.panel-head.with-meta {
  align-items: center;
}

.panel-meta-row {
  display: flex;
  align-items: center;
  gap: 0.7rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.panel-meta {
  color: #94a3b8;
  font-size: 0.74rem;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.pager {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.28rem 0.35rem;
  border: 1px solid #dbe4ee;
  border-radius: 999px;
  background: #f8fbff;
  color: #64748b;
  font-size: 0.76rem;
  font-weight: 700;
}

.pager-btn {
  border: none;
  border-radius: 999px;
  padding: 0.34rem 0.58rem;
  background: #fff;
  color: #334155;
  font: inherit;
  font-size: 0.74rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(148,163,184,0.14);
}

.pager-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

.panel-kicker { color: #94a3b8; margin-bottom: 0.2rem; }

.panel-head h2 {
  margin: 0;
  color: #0f172a;
  font-size: 1.2rem;
}

.btn-primary,
.btn-secondary,
.btn-danger {
  border: none;
  border-radius: 12px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
}

.btn-primary {
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: #fff;
  padding: 0.8rem 1.05rem;
}

.btn-secondary {
  background: #fff;
  border: 1px solid #d7e1ec;
  color: #334155;
  padding: 0.75rem 0.95rem;
}

.btn-danger {
  background: #fff5f5;
  border: 1px solid #fecaca;
  color: #b91c1c;
  padding: 0.7rem 0.95rem;
}

.plan-summary,
.analytics-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8rem;
}

.analytics-grid { grid-template-columns: repeat(2, minmax(0, 1fr)); margin-top: 1rem; }

.summary-card,
.stat-box {
  background: #f8fafc;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  padding: 1rem;
}

.compact-card,
.compact-stat-box {
  padding: 0.9rem;
}

.summary-label,
.stat-box span {
  display: block;
  color: #64748b;
  font-size: 0.78rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.summary-card strong,
.stat-box strong {
  display: block;
  color: #0f172a;
  font-size: 1.15rem;
  margin-top: 0.35rem;
}

.summary-card p {
  margin: 0.4rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
  line-height: 1.55;
}

.pending-banner {
  margin-top: 1rem;
  padding: 0.85rem 1rem;
  border-radius: 14px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
}

.plan-guidance {
  margin-bottom: 1rem;
  padding: 0.9rem 1rem;
  border-radius: 16px;
  border: 1px solid #bae6fd;
  background: linear-gradient(180deg, #f0f9ff, #ecfeff);
}

.plan-guidance h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
}

.plan-guidance p {
  margin: 0.45rem 0 0;
  color: #334155;
  line-height: 1.5;
  font-size: 0.86rem;
}

.journey-chips,
.value-pill-row {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.journey-chips {
  margin-top: 0.75rem;
}

.journey-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.28rem 0.64rem;
  font-size: 0.74rem;
  font-weight: 700;
  color: #0c4a6e;
  background: rgba(255,255,255,0.9);
  border: 1px solid #bae6fd;
}

.plan-value-strip {
  margin-bottom: 1rem;
  padding: 0.8rem 0.9rem;
  border-radius: 16px;
  border: 1px solid #dbeafe;
  background: #f8fbff;
}

.value-strip-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.7rem;
  margin-bottom: 0.65rem;
}

.value-strip-head strong {
  color: #0f172a;
  font-size: 0.9rem;
}

.value-strip-sub {
  margin: 0.3rem 0 0;
  color: #475569;
  font-size: 0.78rem;
  line-height: 1.45;
}

.value-strip-head span {
  color: #64748b;
  font-size: 0.76rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 700;
}

.value-pill {
  flex: 1 1 220px;
  border: 1px solid #dbe4ee;
  border-radius: 14px;
  background: #fff;
  padding: 0.72rem 0.75rem;
}

.value-pill.recommended {
  border-color: #86efac;
  background: #f0fdf4;
}

.value-pill.current {
  border-color: #7dd3fc;
  background: #f0f9ff;
}

.value-pill-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.5rem;
}

.value-pill p,
.value-pill small {
  margin: 0.35rem 0 0;
  color: #475569;
  line-height: 1.45;
}

.value-pill small {
  display: block;
  font-size: 0.76rem;
}

.roi-small {
  color: #334155;
  font-weight: 600;
}

.inline-provider {
  margin-top: 1rem;
}

.inline-provider select {
  max-width: 240px;
}

.compact-provider {
  margin-top: 0;
  margin-bottom: 1rem;
}

.plan-list,
.package-list,
.orders-list,
.ledger-list {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin-top: 1rem;
}

.plan-card,
.package-card,
.order-row,
.ledger-row {
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: #fafcff;
  padding: 1rem;
}

.plan-card.current { border-color: #38bdf8; background: #f0f9ff; }

.plan-top,
.pkg-top {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.plan-card h3,
.package-card h3,
.order-row h3 {
  margin: 0;
  color: #0f172a;
}

.plan-card p,
.package-card p,
.order-row p,
.ledger-row p {
  margin: 0.3rem 0 0;
  color: #64748b;
  line-height: 1.5;
}

.plan-price {
  font-size: 1.2rem;
  color: #0f172a;
}

.plan-meta,
.pkg-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
  margin-top: 0.7rem;
}

.plan-meta span,
.pkg-meta span,
.feature-tag,
.status-chip {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.22rem 0.58rem;
  font-size: 0.75rem;
  font-weight: 700;
}

.plan-meta span,
.pkg-meta span { background: #fff; border: 1px solid #dbe4ee; color: #475569; }
.feature-tags { display: flex; flex-wrap: wrap; gap: 0.45rem; margin-top: 0.8rem; }
.feature-tag { background: #ecfeff; color: #0f766e; }
.plan-actions { margin-top: 0.9rem; display: flex; justify-content: flex-end; }

.plan-orders-block {
  margin-top: 1.25rem;
  border-top: 1px solid #eef2f7;
  padding-top: 1rem;
}

.compact-head {
  margin-bottom: 0.9rem;
}

.compact-row {
  padding: 0.82rem 0.9rem;
}

.status-chip.current,
.status-chip.pending_activation { background: #fff7ed; color: #c2410c; border: 1px solid #fdba74; }
.status-chip.pending_payment { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }
.status-chip.payment_pending,
.status-chip.payment_received,
.status-chip.fulfillment_pending { background: #ecfeff; color: #155e75; border: 1px solid #a5f3fc; }
.status-chip.completed { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.status-chip.cancelled { background: #f8fafc; color: #64748b; border: 1px solid #dbe4ee; }

.surface-table-wrap { margin-top: 1rem; overflow-x: auto; }
.surface-table { width: 100%; border-collapse: collapse; }
.surface-table th,
.surface-table td { padding: 0.75rem 0.5rem; border-bottom: 1px solid #eef2f7; text-align: left; }
.surface-table th { font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em; color: #94a3b8; }
.compact-table th,
.compact-table td { font-size: 0.81rem; padding: 0.62rem 0.52rem; }
.empty-inline { color: #94a3b8; text-align: center; }

.ledger-table-wrap {
  margin-top: 0;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  background: linear-gradient(180deg, #fcfdff 0%, #f8fbff 100%);
}

.ledger-table {
  min-width: 700px;
}

.ledger-table tbody tr {
  transition: background 140ms ease;
}

.ledger-table-row.positive {
  background: rgba(240, 253, 244, 0.72);
}

.ledger-table-row.negative {
  background: rgba(255, 247, 237, 0.78);
}

.ledger-table-row:hover {
  background: rgba(226, 232, 240, 0.42);
}

.ledger-type-badge {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.22rem 0.58rem;
  background: rgba(255,255,255,0.92);
  border: 1px solid #dbe4ee;
  color: #334155;
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ledger-reference-cell {
  display: flex;
  flex-direction: column;
  gap: 0.18rem;
  min-width: 0;
}

.ledger-reference-cell strong {
  color: #0f172a;
  font-size: 0.8rem;
  line-height: 1.35;
}

.ledger-reference-cell span {
  color: #64748b;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.ledger-balance-cell {
  color: #0f172a;
  font-weight: 800;
  white-space: nowrap;
}

.ledger-time-cell {
  color: #475569;
  white-space: nowrap;
}

.scroll-list,
.compact-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(148,163,184,0.6) transparent;
}

.scroll-list::-webkit-scrollbar,
.compact-scroll::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.scroll-list::-webkit-scrollbar-thumb,
.compact-scroll::-webkit-scrollbar-thumb {
  background: rgba(148,163,184,0.55);
  border-radius: 999px;
}

.scroll-list {
  max-height: 34rem;
  overflow: auto;
  padding-right: 0.2rem;
}

.compact-scroll {
  max-height: 28rem;
  overflow: auto;
}

.ledger-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: center;
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
  border-radius: 999px;
  padding: 0.24rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 800;
}

.delta-pill.positive { background: #f0fdf4; color: #166534; }
.delta-pill.negative { background: #fef2f2; color: #b91c1c; }

.order-form {
  display: grid;
  gap: 0.85rem;
  margin-top: 1rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field span {
  color: #475569;
  font-size: 0.8rem;
  font-weight: 700;
}

.field select {
  width: 100%;
  border: 1px solid #dbe4ee;
  border-radius: 12px;
  background: #f8fafc;
  padding: 0.8rem 0.9rem;
  font: inherit;
}

.gateway-note {
  padding: 0.85rem 1rem;
  border-radius: 14px;
  background: #fffbeb;
  border: 1px solid #fde68a;
  color: #92400e;
  line-height: 1.5;
}

.order-row {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
}

.order-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.5rem;
}

.empty-box {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 160px;
  border-radius: 14px;
  border: 1px dashed #dbe4ee;
  background: #f8fafc;
  color: #64748b;
  text-align: center;
  padding: 1rem;
}

.compact-empty {
  min-height: 120px;
}

@media (max-width: 1024px) {
  .hero-inner,
  .top-grid,
  .bottom-grid,
  .content-grid.two-col,
  .compact-summary-grid {
    grid-template-columns: 1fr;
  }

  .plan-summary { grid-template-columns: 1fr; }
}

@media (max-width: 720px) {
  .hero { padding: 3rem 1rem 6rem; }
  .page-shell { padding: 0 1rem; }
  .panel { padding: 1.1rem; }
  .hero-metrics,
  .analytics-grid { grid-template-columns: 1fr; }
  .plan-top,
  .pkg-top,
  .panel-head,
  .workspace-topbar,
  .panel-meta-row,
  .order-row { flex-direction: column; }
  .order-actions,
  .ledger-right { align-items: flex-start; }

  .ledger-table {
    min-width: 620px;
  }

  .tab-bar {
    gap: 0.55rem;
    padding: 0.55rem;
  }

  .tab-button {
    min-width: 0;
    width: 100%;
  }

  .value-strip-head {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
