<template>
  <div class="admin-financial">
    <div class="page-header">
      <div class="header-copy">
        <span class="header-eyebrow">Revenue Operations</span>
        <h1>Financial and Billing Controls</h1>
        <p class="subtitle">Manage plan catalog, operator subscriptions, credit adjustments, and recent billing activity.</p>
      </div>
      <div class="header-actions">
        <div class="header-status">Live billing console</div>
        <button class="btn-refresh" @click="loadAll" :disabled="loading">{{ loading ? 'Refreshing…' : 'Refresh' }}</button>
      </div>
    </div>

    <div v-if="message.text" :class="['message-banner', message.type]">{{ message.text }}</div>
    <div v-if="loading && !plans.length && !subscriptions.length" class="state-box">Loading billing controls…</div>
    <div v-else-if="loadError" class="state-box error">{{ loadError }}</div>

    <section class="tab-shell">
      <div class="tab-bar" role="tablist" aria-label="Financial sections">
        <button :class="['tab-button', { active: activeTab === 'overview' }]" type="button" role="tab" :aria-selected="activeTab === 'overview'" @click="activeTab = 'overview'">
          <span>Overview</span>
          <small>{{ subscriptions.length }}</small>
        </button>
        <button :class="['tab-button', { active: activeTab === 'planner' }]" type="button" role="tab" :aria-selected="activeTab === 'planner'" @click="activeTab = 'planner'">
          <span>Planner</span>
          <small>{{ plannerBreakdown.length }}</small>
        </button>
        <button :class="['tab-button', { active: activeTab === 'catalog' }]" type="button" role="tab" :aria-selected="activeTab === 'catalog'" @click="activeTab = 'catalog'">
          <span>Catalog</span>
          <small>{{ plans.length }}</small>
        </button>
        <button :class="['tab-button', { active: activeTab === 'activity' }]" type="button" role="tab" :aria-selected="activeTab === 'activity'" @click="activeTab = 'activity'">
          <span>Activity</span>
          <small>{{ ledgerEntries.length + billingEvents.length }}</small>
        </button>
      </div>

      <div v-if="activeTab === 'overview'" class="tab-panel">
        <div class="metrics-grid compact-metrics-grid">
          <article class="metric-card">
            <span class="metric-label">Plans</span>
            <strong>{{ plans.length }}</strong>
            <p>{{ plans.filter(plan => plan.is_active).length }} active</p>
          </article>
          <article class="metric-card">
            <span class="metric-label">Subscriptions</span>
            <strong>{{ subscriptions.length }}</strong>
            <p>{{ subscriptions.filter(item => item.plan_status === 'active').length }} active</p>
          </article>
          <article class="metric-card">
            <span class="metric-label">Pending activation</span>
            <strong>{{ subscriptions.filter(item => item.plan_status === 'pending_activation').length }}</strong>
            <p>Operator requests awaiting review</p>
          </article>
          <article class="metric-card">
            <span class="metric-label">Outstanding credits</span>
            <strong>{{ totalRemainingCredits }}</strong>
            <p>Across loaded subscriptions</p>
          </article>
          <article class="metric-card">
            <span class="metric-label">Billable events</span>
            <strong>{{ billableEventCount }}</strong>
            <p>Current billing event sample</p>
          </article>
        </div>

        <div class="grid two-col second-row">
          <section class="panel">
            <div class="panel-head with-meta">
              <div>
                <p class="panel-kicker">Subscriptions</p>
                <h2>Operator plan state</h2>
              </div>
              <div class="panel-meta-row">
                <span class="panel-meta">{{ pageRangeLabel(subscriptions, subscriptionsPage, PAGE_SIZE.subscriptions) }}</span>
                <div class="pager">
                  <button class="pager-btn" type="button" @click="shiftPage(subscriptionsPage, -1, subscriptions, PAGE_SIZE.subscriptions)" :disabled="subscriptionsPage <= 1">Prev</button>
                  <span>{{ subscriptionsPage }} / {{ totalPagesFor(subscriptions, PAGE_SIZE.subscriptions) }}</span>
                  <button class="pager-btn" type="button" @click="shiftPage(subscriptionsPage, 1, subscriptions, PAGE_SIZE.subscriptions)" :disabled="subscriptionsPage >= totalPagesFor(subscriptions, PAGE_SIZE.subscriptions)">Next</button>
                </div>
              </div>
            </div>

            <div v-if="!subscriptions.length" class="state-box">No subscriptions found.</div>
            <div v-else class="list-wrap scroll-list compact-scroll">
              <article v-for="subscription in paginatedItems(subscriptions, subscriptionsPage, PAGE_SIZE.subscriptions)" :key="subscription._id" class="subscription-row compact-row">
                <div>
                  <h3>{{ subscription.operator_profile?.business_name || subscription.operator_profile_id }}</h3>
                  <p>{{ subscription.plan_code }} · {{ readableText(subscription.plan_status) }}</p>
                  <div class="tag-row">
                    <span class="tag">Remaining {{ subscription.credits_remaining }}</span>
                    <span class="tag">Included {{ subscription.included_credits }}</span>
                    <span v-if="subscription.requested_plan_code" class="tag request">Requested {{ subscription.requested_plan_code }}</span>
                  </div>
                </div>
                <span :class="['status-pill', subscription.plan_status]">{{ readableText(subscription.plan_status) }}</span>
              </article>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head with-meta">
              <div>
                <p class="panel-kicker">Recent events</p>
                <h2>Billable billing activity</h2>
              </div>
              <div class="panel-meta-row">
                <span class="panel-meta">{{ pageRangeLabel(billingEvents, billingEventsPage, PAGE_SIZE.events) }}</span>
                <div class="pager">
                  <button class="pager-btn" type="button" @click="shiftPage(billingEventsPage, -1, billingEvents, PAGE_SIZE.events)" :disabled="billingEventsPage <= 1">Prev</button>
                  <span>{{ billingEventsPage }} / {{ totalPagesFor(billingEvents, PAGE_SIZE.events) }}</span>
                  <button class="pager-btn" type="button" @click="shiftPage(billingEventsPage, 1, billingEvents, PAGE_SIZE.events)" :disabled="billingEventsPage >= totalPagesFor(billingEvents, PAGE_SIZE.events)">Next</button>
                </div>
              </div>
            </div>

            <div class="events-table-wrap compact-scroll">
              <table class="events-table compact-table">
                <thead>
                  <tr>
                    <th>Operator</th>
                    <th>Surface</th>
                    <th>Credits</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="event in paginatedItems(billingEvents, billingEventsPage, PAGE_SIZE.events)" :key="event._id">
                    <td>{{ operatorNameForEvent(event.operator_profile_id) }}</td>
                    <td>{{ event.source_surface }}</td>
                    <td>{{ event.credits_charged }}</td>
                    <td>₹{{ formatMoney(event.currency_amount || 0) }}</td>
                    <td>{{ event.is_billable ? 'Billable' : event.outcome_reason || 'Rejected' }}</td>
                  </tr>
                  <tr v-if="!billingEvents.length">
                    <td colspan="5" class="empty-inline">No billing events available.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>

      <div v-else-if="activeTab === 'planner'" class="tab-panel">
        <div class="grid two-col planner-row">
          <section class="panel planner-hub-panel">
            <div class="panel-head">
              <div>
                <p class="panel-kicker">Planner funnel</p>
                <h2>Tracked planner events over {{ billingSummary.days || 30 }} days</h2>
              </div>
            </div>

            <div class="planner-metrics-grid compact-metrics-grid">
              <article class="metric-card compact">
                <span class="metric-label">Recommendations served</span>
                <strong>{{ plannerFunnel.recommendations_served }}</strong>
                <p>Distinct planner sessions with recommendations</p>
              </article>
              <article class="metric-card compact">
                <span class="metric-label">Quote intents</span>
                <strong>{{ plannerFunnel.quote_intents }}</strong>
                <p>Planner add-to-cart and quote-intent actions</p>
              </article>
              <article class="metric-card compact">
                <span class="metric-label">Itinerary saves</span>
                <strong>{{ plannerFunnel.itinerary_saves }}</strong>
                <p>Template-based itinerary conversions</p>
              </article>
              <article class="metric-card compact">
                <span class="metric-label">Planner credits</span>
                <strong>{{ plannerTotals.credits_consumed }}</strong>
                <p>Credits consumed by planner events</p>
              </article>
            </div>

            <div class="planner-pricing-strip">
              <span class="tag">Search click {{ plannerPricing.search_profile_click }}</span>
              <span class="tag">Planner intent {{ plannerPricing.planner_intent_click }}</span>
              <span class="tag">Template save {{ plannerPricing.conversion }}</span>
              <span class="tag">ROI baseline {{ formatNumber(roiBaseline.qualified_leads_per_100_credits) }} leads/100 credits</span>
            </div>

            <div v-if="plannerPricingWarning" class="state-box warning planner-warning-box">{{ plannerPricingWarning }}</div>

            <div class="planner-admin-grid">
              <form class="planner-pricing-form surface-card" @submit.prevent="savePlannerPricing">
                <div class="planner-pricing-head">
                  <div>
                    <p class="panel-kicker">Billing pricing controls</p>
                    <h3>Set credit values for billable events</h3>
                    <p class="planner-pricing-note">Use whole numbers from 0 to 100. Zero keeps tracking active while disabling charges.</p>
                  </div>
                  <div class="planner-pricing-actions">
                    <button class="btn-secondary" type="button" @click="resetPlannerPricing" :disabled="savingPlannerPricing">Reset</button>
                    <button class="btn-primary" type="submit" :disabled="savingPlannerPricing">{{ savingPlannerPricing ? 'Saving…' : 'Save pricing' }}</button>
                  </div>
                </div>

                <div class="planner-pricing-grid">
                  <label class="field">
                    <span>Search profile click</span>
                    <input v-model.number="plannerPricingForm.search_profile_click" type="number" min="0" max="100" step="1" required />
                  </label>
                  <label class="field">
                    <span>Planner quote intent</span>
                    <input v-model.number="plannerPricingForm.planner_intent_click" type="number" min="0" max="100" step="1" required />
                  </label>
                  <label class="field">
                    <span>Template itinerary save</span>
                    <input v-model.number="plannerPricingForm.conversion" type="number" min="0" max="100" step="1" required />
                  </label>
                </div>

                <p class="planner-pricing-meta">
                  Source: {{ billingSummary?.planner?.pricing_source || plannerPricingSettings.source || 'environment' }}
                  <span v-if="plannerPricingSettings.updated_at"> · Updated {{ formatDateTime(plannerPricingSettings.updated_at) }}</span>
                </p>
              </form>

              <div class="planner-admin-column">
                <div class="planner-pricing-strip quota-strip">
                  <span class="tag">Daily limit {{ plannerQuota.daily_limit }}</span>
                  <span class="tag">Monthly limit {{ plannerQuota.monthly_limit }}</span>
                  <span class="tag">Ad bonus +{{ plannerQuota.ad_reward_daily_credits }}/+{{ plannerQuota.ad_reward_monthly_credits }}</span>
                  <span class="tag">Promotion bonus +{{ plannerQuota.promotion_reward_daily_credits }}/+{{ plannerQuota.promotion_reward_monthly_credits }}</span>
                </div>

                <div v-if="plannerQuotaValidation" class="state-box warning planner-warning-box">{{ plannerQuotaValidation }}</div>

                <form class="planner-pricing-form surface-card" @submit.prevent="savePlannerQuota">
                  <div class="planner-pricing-head">
                    <div>
                      <p class="panel-kicker">Tourist planner quota</p>
                      <h3>Set daily and monthly planner request limits</h3>
                      <p class="planner-pricing-note">These limits apply before Bedrock is called. Reward grants remain server-verified.</p>
                    </div>
                    <div class="planner-pricing-actions">
                      <button class="btn-secondary" type="button" @click="resetPlannerQuota" :disabled="savingPlannerQuota">Reset</button>
                      <button class="btn-primary" type="submit" :disabled="savingPlannerQuota || !!plannerQuotaValidation">{{ savingPlannerQuota ? 'Saving…' : 'Save quota' }}</button>
                    </div>
                  </div>

                  <div class="planner-pricing-grid quota-grid">
                    <label class="field">
                      <span>Daily requests</span>
                      <input v-model.number="plannerQuotaForm.daily_limit" type="number" min="0" max="100" step="1" required />
                    </label>
                    <label class="field">
                      <span>Monthly requests</span>
                      <input v-model.number="plannerQuotaForm.monthly_limit" type="number" min="0" max="1000" step="1" required />
                    </label>
                    <label class="field">
                      <span>Ad daily bonus</span>
                      <input v-model.number="plannerQuotaForm.ad_reward_daily_credits" type="number" min="0" max="20" step="1" required />
                    </label>
                    <label class="field">
                      <span>Ad monthly bonus</span>
                      <input v-model.number="plannerQuotaForm.ad_reward_monthly_credits" type="number" min="0" max="100" step="1" required />
                    </label>
                    <label class="field">
                      <span>Promotion daily bonus</span>
                      <input v-model.number="plannerQuotaForm.promotion_reward_daily_credits" type="number" min="0" max="20" step="1" required />
                    </label>
                    <label class="field">
                      <span>Promotion monthly bonus</span>
                      <input v-model.number="plannerQuotaForm.promotion_reward_monthly_credits" type="number" min="0" max="100" step="1" required />
                    </label>
                  </div>

                  <p class="planner-pricing-meta">
                    Source: {{ billingSummary?.planner?.quota_source || plannerQuotaSettings.source || 'environment' }}
                    <span v-if="plannerQuotaSettings.updated_at"> · Updated {{ formatDateTime(plannerQuotaSettings.updated_at) }}</span>
                  </p>
                </form>

                <form class="planner-pricing-form surface-card" @submit.prevent="saveRoiBaseline">
                  <div class="planner-pricing-head">
                    <div>
                      <p class="panel-kicker">ROI baseline control</p>
                      <h3>Set qualified leads baseline for plan ROI hints</h3>
                      <p class="planner-pricing-note">Used when operators have low or no usage history. Value is leads expected per 100 credits.</p>
                    </div>
                    <div class="planner-pricing-actions">
                      <button class="btn-secondary" type="button" @click="resetRoiBaseline" :disabled="savingRoiBaseline">Reset</button>
                      <button class="btn-primary" type="submit" :disabled="savingRoiBaseline">{{ savingRoiBaseline ? 'Saving…' : 'Save ROI baseline' }}</button>
                    </div>
                  </div>

                  <div class="planner-pricing-grid">
                    <label class="field">
                      <span>Qualified leads per 100 credits</span>
                      <input v-model.number="roiBaselineForm.qualified_leads_per_100_credits" type="number" min="0" max="10000" step="0.1" required />
                    </label>
                  </div>

                  <p class="planner-pricing-meta">
                    Source: {{ roiBaselineSettings.source || 'environment' }}
                    <span v-if="roiBaselineSettings.updated_at"> · Updated {{ formatDateTime(roiBaselineSettings.updated_at) }}</span>
                  </p>
                </form>
              </div>
            </div>
          </section>

          <section class="panel planner-breakdown-panel">
            <div class="panel-head">
              <div>
                <p class="panel-kicker">Planner breakdown</p>
                <h2>Planner event mix</h2>
              </div>
            </div>

            <div v-if="!plannerBreakdown.length" class="state-box compact">No planner events recorded yet.</div>
            <div v-else class="events-table-wrap planner-breakdown-wrap compact-scroll">
              <table class="events-table compact-table planner-breakdown-table">
                <thead>
                  <tr>
                    <th>Event type</th>
                    <th>Total</th>
                    <th>Billable</th>
                    <th>Non-billable</th>
                    <th>Credits</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="item in plannerBreakdown" :key="item.event_type">
                    <td>{{ readableText(item.event_type) }}</td>
                    <td>{{ item.events }}</td>
                    <td>{{ item.billable_events }}</td>
                    <td>{{ item.non_billable_events }}</td>
                    <td>{{ item.credits_consumed }}</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>

        <div class="grid two-col second-row">
          <section class="panel">
            <div class="panel-head with-meta">
              <div>
                <p class="panel-kicker">Tourist planner quota ledger</p>
                <h2>Quota consumption and grants</h2>
              </div>
              <div class="panel-meta-row">
                <span class="panel-meta">{{ pageRangeLabel(touristQuotaLedger, quotaLedgerPage, PAGE_SIZE.quotaLedger) }}</span>
                <div class="pager">
                  <button class="pager-btn" type="button" @click="shiftPage(quotaLedgerPage, -1, touristQuotaLedger, PAGE_SIZE.quotaLedger)" :disabled="quotaLedgerPage <= 1">Prev</button>
                  <span>{{ quotaLedgerPage }} / {{ totalPagesFor(touristQuotaLedger, PAGE_SIZE.quotaLedger) }}</span>
                  <button class="pager-btn" type="button" @click="shiftPage(quotaLedgerPage, 1, touristQuotaLedger, PAGE_SIZE.quotaLedger)" :disabled="quotaLedgerPage >= totalPagesFor(touristQuotaLedger, PAGE_SIZE.quotaLedger)">Next</button>
                </div>
              </div>
            </div>

            <div class="events-table-wrap quota-ops-table-wrap compact-scroll">
              <table class="events-table compact-table">
                <thead>
                  <tr>
                    <th>Tourist</th>
                    <th>Event</th>
                    <th>Source</th>
                    <th>Daily</th>
                    <th>Monthly</th>
                    <th>Recorded</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="entry in paginatedItems(touristQuotaLedger, quotaLedgerPage, PAGE_SIZE.quotaLedger)" :key="entry._id">
                    <td>{{ touristLabel(entry) }}</td>
                    <td>{{ readableText(entry.event_type) }}</td>
                    <td>{{ readableText(entry.source) }}</td>
                    <td>{{ signedCredits(entry.credits_delta_daily) }}</td>
                    <td>{{ signedCredits(entry.credits_delta_monthly) }}</td>
                    <td>{{ formatDateTime(entry.created_at) }}</td>
                  </tr>
                  <tr v-if="!touristQuotaLedger.length">
                    <td colspan="6" class="empty-inline">No tourist planner quota ledger entries yet.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head with-meta">
              <div>
                <p class="panel-kicker">Reward verification records</p>
                <h2>Server-side reward verification state</h2>
              </div>
              <div class="panel-meta-row">
                <span class="panel-meta">{{ pageRangeLabel(plannerRewardVerifications, rewardVerificationPage, PAGE_SIZE.rewards) }}</span>
                <div class="pager">
                  <button class="pager-btn" type="button" @click="shiftPage(rewardVerificationPage, -1, plannerRewardVerifications, PAGE_SIZE.rewards)" :disabled="rewardVerificationPage <= 1">Prev</button>
                  <span>{{ rewardVerificationPage }} / {{ totalPagesFor(plannerRewardVerifications, PAGE_SIZE.rewards) }}</span>
                  <button class="pager-btn" type="button" @click="shiftPage(rewardVerificationPage, 1, plannerRewardVerifications, PAGE_SIZE.rewards)" :disabled="rewardVerificationPage >= totalPagesFor(plannerRewardVerifications, PAGE_SIZE.rewards)">Next</button>
                </div>
              </div>
            </div>

            <div class="events-table-wrap quota-ops-table-wrap compact-scroll">
              <table class="events-table compact-table">
                <thead>
                  <tr>
                    <th>Tourist</th>
                    <th>Reward</th>
                    <th>Type</th>
                    <th>Status</th>
                    <th>Consumed</th>
                    <th>Recorded</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="record in paginatedItems(plannerRewardVerifications, rewardVerificationPage, PAGE_SIZE.rewards)" :key="record._id">
                    <td>{{ touristLabel(record) }}</td>
                    <td>{{ record.reward_id || 'N/A' }}</td>
                    <td>{{ readableText(record.reward_type) }}</td>
                    <td>{{ readableText(record.status || 'pending') }}</td>
                    <td>{{ record.consumed_at ? formatDateTime(record.consumed_at) : 'Not consumed' }}</td>
                    <td>{{ formatDateTime(record.created_at) }}</td>
                  </tr>
                  <tr v-if="!plannerRewardVerifications.length">
                    <td colspan="6" class="empty-inline">No reward verification records yet.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>

      <div v-else-if="activeTab === 'catalog'" class="tab-panel">
        <div class="grid two-col">
          <section class="panel plan-catalog-panel">
            <div class="panel-head with-meta">
              <div>
                <p class="panel-kicker">Plan catalog</p>
                <h2>Edit billing plans</h2>
              </div>
              <div class="panel-meta-row">
                <span class="panel-meta">{{ pageRangeLabel(plans, plansPage, PAGE_SIZE.plans) }}</span>
                <div class="pager">
                  <button class="pager-btn" type="button" @click="shiftPage(plansPage, -1, plans, PAGE_SIZE.plans)" :disabled="plansPage <= 1">Prev</button>
                  <span>{{ plansPage }} / {{ totalPagesFor(plans, PAGE_SIZE.plans) }}</span>
                  <button class="pager-btn" type="button" @click="shiftPage(plansPage, 1, plans, PAGE_SIZE.plans)" :disabled="plansPage >= totalPagesFor(plans, PAGE_SIZE.plans)">Next</button>
                </div>
              </div>
            </div>

            <div class="plan-list scroll-list compact-scroll">
              <article v-for="plan in paginatedItems(plans, plansPage, PAGE_SIZE.plans)" :key="plan._id" class="plan-card">
                <div class="plan-top">
                  <div>
                    <h3>{{ plan.code }} · {{ plan.name }}</h3>
                    <p>{{ plan.description }}</p>
                  </div>
                  <span :class="['status-pill', plan.is_active ? 'active' : 'inactive']">{{ plan.is_active ? 'Active' : 'Inactive' }}</span>
                </div>

                <div class="plan-edit-grid" v-if="planDrafts[plan._id]">
                  <label class="field">
                    <span>Monthly price</span>
                    <input v-model.number="planDrafts[plan._id].monthly_price" type="number" min="0" step="1" />
                  </label>
                  <label class="field">
                    <span>Included credits</span>
                    <input v-model.number="planDrafts[plan._id].included_credits" type="number" min="0" step="1" />
                  </label>
                  <label class="field toggle">
                    <input v-model="planDrafts[plan._id].is_active" type="checkbox" />
                    <span>Plan is active</span>
                  </label>
                </div>

                <div class="feature-tags">
                  <span v-for="feature in plan.features || []" :key="feature" class="feature-tag">{{ feature }}</span>
                </div>

                <div class="row-actions">
                  <button class="btn-primary" @click="savePlan(plan)" :disabled="savingPlanId === plan._id">
                    {{ savingPlanId === plan._id ? 'Saving…' : 'Save plan' }}
                  </button>
                </div>
              </article>
            </div>
          </section>

          <section class="panel action-panel">
            <div class="panel-head">
              <div>
                <p class="panel-kicker">Manual controls</p>
                <h2>Assign plans and adjust credits</h2>
              </div>
            </div>

            <div class="control-grid">
              <div class="control-card">
                <div class="control-card-head">
                  <p class="panel-kicker">Plan activation</p>
                  <h3>Assign or activate a provider plan</h3>
                </div>

                <form class="control-form" @submit.prevent="assignPlan">
                  <label class="field">
                    <span>Operator</span>
                    <select v-model="assignmentForm.operator_profile_id" required>
                      <option value="">Select operator</option>
                      <option v-for="operator in operatorOptions" :key="operator.operator_profile_id" :value="operator.operator_profile_id">
                        {{ operator.business_name || operator.operator_profile_id }}
                      </option>
                    </select>
                  </label>
                  <label class="field">
                    <span>Plan</span>
                    <select v-model="assignmentForm.plan_code" required>
                      <option value="">Select plan</option>
                      <option v-for="plan in plans.filter(item => item.is_active)" :key="plan.code" :value="plan.code">{{ plan.name }}</option>
                    </select>
                  </label>
                  <label class="field toggle">
                    <input v-model="assignmentForm.reset_credits" type="checkbox" />
                    <span>Reset to included credits</span>
                  </label>
                  <label class="field">
                    <span>Notes</span>
                    <input v-model="assignmentForm.notes" type="text" placeholder="Manual activation after review" required />
                  </label>
                  <button class="btn-primary" type="submit" :disabled="assigningPlan">{{ assigningPlan ? 'Assigning…' : 'Assign plan' }}</button>
                </form>
              </div>

              <div class="control-card">
                <div class="control-card-head">
                  <p class="panel-kicker">Balance adjustment</p>
                  <h3>Apply a manual credit correction</h3>
                </div>

                <form class="control-form standalone" @submit.prevent="submitAdjustment">
                  <label class="field">
                    <span>Operator</span>
                    <select v-model="adjustmentForm.operator_profile_id" required>
                      <option value="">Select operator</option>
                      <option v-for="operator in operatorOptions" :key="`${operator.operator_profile_id}-adjustment`" :value="operator.operator_profile_id">
                        {{ operator.business_name || operator.operator_profile_id }}
                      </option>
                    </select>
                  </label>
                  <label class="field">
                    <span>Credit delta</span>
                    <input v-model.number="adjustmentForm.credits_delta" type="number" step="1" required />
                  </label>
                  <label class="field">
                    <span>Notes</span>
                    <input v-model="adjustmentForm.notes" type="text" placeholder="Fraud refund or manual grant" required />
                  </label>
                  <button class="btn-primary" type="submit" :disabled="adjustingCredits">{{ adjustingCredits ? 'Applying…' : 'Apply adjustment' }}</button>
                </form>
              </div>
            </div>
          </section>
        </div>
      </div>

      <div v-else class="tab-panel">
        <section class="panel recon-panel">
          <div class="panel-head with-meta">
            <div>
              <p class="panel-kicker">Billing reconciliation ops</p>
              <h2>Anomaly monitor and export</h2>
            </div>
            <div class="panel-meta-row">
              <span class="panel-meta">Window: {{ reconciliationWindowDays }} days</span>
              <div class="pager">
                <button class="pager-btn" type="button" @click="loadReconciliationOps" :disabled="reconciliationLoading">{{ reconciliationLoading ? 'Loading…' : 'Refresh' }}</button>
              </div>
            </div>
          </div>

          <div class="metrics-grid recon-metrics-grid">
            <article class="metric-card compact">
              <span class="metric-label">Mismatch total</span>
              <strong>{{ reconciliationAnomalies.mismatch_count || 0 }}</strong>
              <p>Open issue + orphan-debit total</p>
            </article>
            <article class="metric-card compact">
              <span class="metric-label">Compensation failures</span>
              <strong>{{ reconciliationAnomalies.compensation_failure_count || 0 }}</strong>
              <p>Orders stuck in failed compensation state</p>
            </article>
            <article class="metric-card compact">
              <span class="metric-label">Duplicate attempts</span>
              <strong>{{ reconciliationAnomalies.duplicate_attempt_count || 0 }}</strong>
              <p>Repeated compensation calls detected</p>
            </article>
            <article class="metric-card compact">
              <span class="metric-label">In progress</span>
              <strong>{{ reconciliationAnomalies.compensation_processing_count || 0 }}</strong>
              <p>Compensation currently processing</p>
            </article>
          </div>

          <div class="recon-actions">
            <button class="btn-primary" type="button" @click="runReconciliationRepair" :disabled="repairingReconciliation || reconciliationLoading">{{ repairingReconciliation ? 'Repairing…' : 'Run repair pass' }}</button>
            <button class="btn-secondary" type="button" @click="exportReconciliation('csv')" :disabled="exportingReconciliation || reconciliationLoading">{{ exportingReconciliation ? 'Exporting…' : 'Export CSV' }}</button>
            <button class="btn-secondary" type="button" @click="exportReconciliation('json')" :disabled="exportingReconciliation || reconciliationLoading">{{ exportingReconciliation ? 'Exporting…' : 'Export JSON' }}</button>
          </div>

          <div class="events-table-wrap compact-scroll recon-table-wrap">
            <table class="events-table compact-table">
              <thead>
                <tr>
                  <th>Type</th>
                  <th>Operator</th>
                  <th>Event key</th>
                  <th>Credits</th>
                </tr>
              </thead>
              <tbody>
                <tr v-for="item in reconciliationIssuesPreview" :key="item.key">
                  <td>{{ readableText(item.type) }}</td>
                  <td>{{ item.operator_profile_id || 'N/A' }}</td>
                  <td>{{ item.event_idempotency_key || 'N/A' }}</td>
                  <td>{{ item.credits }}</td>
                </tr>
                <tr v-if="!reconciliationIssuesPreview.length">
                  <td colspan="4" class="empty-inline">No unresolved reconciliation rows in current preview.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </section>

        <div class="grid two-col second-row">
          <section class="panel">
            <div class="panel-head with-meta">
              <div>
                <p class="panel-kicker">Billing pricing audit</p>
                <h2>Recent pricing changes</h2>
              </div>
              <div class="panel-meta-row">
                <span class="panel-meta">{{ pageRangeLabel(plannerPricingHistory, pricingHistoryPage, PAGE_SIZE.history) }}</span>
                <div class="pager">
                  <button class="pager-btn" type="button" @click="shiftPage(pricingHistoryPage, -1, plannerPricingHistory, PAGE_SIZE.history)" :disabled="pricingHistoryPage <= 1">Prev</button>
                  <span>{{ pricingHistoryPage }} / {{ totalPagesFor(plannerPricingHistory, PAGE_SIZE.history) }}</span>
                  <button class="pager-btn" type="button" @click="shiftPage(pricingHistoryPage, 1, plannerPricingHistory, PAGE_SIZE.history)" :disabled="pricingHistoryPage >= totalPagesFor(plannerPricingHistory, PAGE_SIZE.history)">Next</button>
                </div>
              </div>
            </div>

            <div v-if="!plannerPricingHistory.length" class="state-box compact">No billing pricing changes recorded yet.</div>
            <div v-else class="planner-history-list scroll-list compact-scroll">
              <article v-for="entry in paginatedItems(plannerPricingHistory, pricingHistoryPage, PAGE_SIZE.history)" :key="entry._id" class="planner-history-row compact-row">
                <div>
                  <strong>{{ formatDateTime(entry.changed_at) }}</strong>
                  <p>Updated by {{ entry.changed_by || 'system' }}</p>
                </div>
                <div class="planner-history-values">
                  <span class="tag muted">Was {{ formatPricingTriple(entry.previous_value) }}</span>
                  <span class="tag">Now {{ formatPricingTriple(entry.new_value) }}</span>
                </div>
              </article>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head with-meta">
              <div>
                <p class="panel-kicker">Planner quota audit</p>
                <h2>Recent quota changes</h2>
              </div>
              <div class="panel-meta-row">
                <span class="panel-meta">{{ pageRangeLabel(plannerQuotaHistory, quotaHistoryPage, PAGE_SIZE.history) }}</span>
                <div class="pager">
                  <button class="pager-btn" type="button" @click="shiftPage(quotaHistoryPage, -1, plannerQuotaHistory, PAGE_SIZE.history)" :disabled="quotaHistoryPage <= 1">Prev</button>
                  <span>{{ quotaHistoryPage }} / {{ totalPagesFor(plannerQuotaHistory, PAGE_SIZE.history) }}</span>
                  <button class="pager-btn" type="button" @click="shiftPage(quotaHistoryPage, 1, plannerQuotaHistory, PAGE_SIZE.history)" :disabled="quotaHistoryPage >= totalPagesFor(plannerQuotaHistory, PAGE_SIZE.history)">Next</button>
                </div>
              </div>
            </div>

            <div v-if="!plannerQuotaHistory.length" class="state-box compact">No planner quota changes recorded yet.</div>
            <div v-else class="planner-history-list scroll-list compact-scroll">
              <article v-for="entry in paginatedItems(plannerQuotaHistory, quotaHistoryPage, PAGE_SIZE.history)" :key="entry._id" class="planner-history-row compact-row">
                <div>
                  <strong>{{ formatDateTime(entry.changed_at) }}</strong>
                  <p>Updated by {{ entry.changed_by || 'system' }}</p>
                </div>
                <div class="planner-history-values">
                  <span class="tag muted">Was {{ formatQuotaSummary(entry.previous_value) }}</span>
                  <span class="tag">Now {{ formatQuotaSummary(entry.new_value) }}</span>
                </div>
              </article>
            </div>
          </section>
        </div>

        <div class="grid two-col second-row">
          <section class="panel">
            <div class="panel-head with-meta">
              <div>
                <p class="panel-kicker">Ledger</p>
                <h2>Recent credit activity</h2>
              </div>
              <div class="panel-meta-row">
                <span class="panel-meta">{{ pageRangeLabel(ledgerEntries, ledgerPage, PAGE_SIZE.ledger) }}</span>
                <div class="pager">
                  <button class="pager-btn" type="button" @click="shiftPage(ledgerPage, -1, ledgerEntries, PAGE_SIZE.ledger)" :disabled="ledgerPage <= 1">Prev</button>
                  <span>{{ ledgerPage }} / {{ totalPagesFor(ledgerEntries, PAGE_SIZE.ledger) }}</span>
                  <button class="pager-btn" type="button" @click="shiftPage(ledgerPage, 1, ledgerEntries, PAGE_SIZE.ledger)" :disabled="ledgerPage >= totalPagesFor(ledgerEntries, PAGE_SIZE.ledger)">Next</button>
                </div>
              </div>
            </div>

            <div class="ledger-list scroll-list compact-scroll">
              <article v-for="entry in paginatedItems(ledgerEntries, ledgerPage, PAGE_SIZE.ledger)" :key="entry._id" class="ledger-row compact-row">
                <div>
                  <strong>{{ readableText(entry.entry_type) }}</strong>
                  <p>{{ entry.notes || entry.source_reference_type }}</p>
                </div>
                <div class="right-stack">
                  <span :class="['delta-pill', entry.credits_delta >= 0 ? 'positive' : 'negative']">{{ signedCredits(entry.credits_delta) }}</span>
                  <small>Balance {{ entry.balance_after }}</small>
                </div>
              </article>
              <div v-if="!ledgerEntries.length" class="state-box compact">No ledger entries available.</div>
            </div>
          </section>

          <section class="panel">
            <div class="panel-head with-meta">
              <div>
                <p class="panel-kicker">Billing events</p>
                <h2>All recorded event rows</h2>
              </div>
              <div class="panel-meta-row">
                <span class="panel-meta">{{ pageRangeLabel(billingEvents, billingEventsPage, PAGE_SIZE.events) }}</span>
                <div class="pager">
                  <button class="pager-btn" type="button" @click="shiftPage(billingEventsPage, -1, billingEvents, PAGE_SIZE.events)" :disabled="billingEventsPage <= 1">Prev</button>
                  <span>{{ billingEventsPage }} / {{ totalPagesFor(billingEvents, PAGE_SIZE.events) }}</span>
                  <button class="pager-btn" type="button" @click="shiftPage(billingEventsPage, 1, billingEvents, PAGE_SIZE.events)" :disabled="billingEventsPage >= totalPagesFor(billingEvents, PAGE_SIZE.events)">Next</button>
                </div>
              </div>
            </div>

            <div class="events-table-wrap compact-scroll">
              <table class="events-table compact-table">
                <thead>
                  <tr>
                    <th>Operator</th>
                    <th>Surface</th>
                    <th>Credits</th>
                    <th>Amount</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="event in paginatedItems(billingEvents, billingEventsPage, PAGE_SIZE.events)" :key="event._id">
                    <td>{{ operatorNameForEvent(event.operator_profile_id) }}</td>
                    <td>{{ event.source_surface }}</td>
                    <td>{{ event.credits_charged }}</td>
                    <td>₹{{ formatMoney(event.currency_amount || 0) }}</td>
                    <td>{{ event.is_billable ? 'Billable' : event.outcome_reason || 'Rejected' }}</td>
                  </tr>
                  <tr v-if="!billingEvents.length">
                    <td colspan="5" class="empty-inline">No billing events available.</td>
                  </tr>
                </tbody>
              </table>
            </div>
          </section>
        </div>
      </div>
    </section>
  </div>

  <div v-if="showPlannerPricingConfirm" class="modal-backdrop" @click.self="cancelPlannerPricingConfirm">
    <div class="modal-card">
      <div class="modal-head">
        <p class="panel-kicker">Confirm pricing change</p>
        <h3>Enable billable credit charges?</h3>
      </div>
      <p class="modal-copy">You are about to save nonzero billing pricing values. Search clicks and future matching planner events can start consuming credits based on these values while recommendation serving remains tracked-only.</p>
      <div class="planner-confirm-summary">
        <span class="tag">Search click {{ pendingPlannerPricing.search_profile_click }}</span>
        <span class="tag">Planner intent {{ pendingPlannerPricing.planner_intent_click }}</span>
        <span class="tag">Template save {{ pendingPlannerPricing.conversion }}</span>
      </div>
      <div v-if="plannerPricingWarning" class="state-box warning compact">{{ plannerPricingWarning }}</div>
      <div class="modal-actions">
        <button class="btn-secondary" type="button" @click="cancelPlannerPricingConfirm" :disabled="savingPlannerPricing">Cancel</button>
        <button class="btn-primary" type="button" @click="confirmPlannerPricingSave" :disabled="savingPlannerPricing">{{ savingPlannerPricing ? 'Saving…' : 'Confirm save' }}</button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../services/api'

const loading = ref(false)
const loadError = ref('')
const message = ref({ type: 'info', text: '' })
const activeTab = ref('overview')
const plans = ref([])
const subscriptions = ref([])
const ledgerEntries = ref([])
const billingEvents = ref([])
const touristQuotaLedger = ref([])
const plannerRewardVerifications = ref([])
const operators = ref([])
const billingSummary = ref({ days: 30, planner: { totals: {}, funnel: {}, by_event_type: [] }, by_surface: [] })
const plannerPricingSettings = ref({ values: { search_profile_click: 1, planner_intent_click: 0, qualified_lead: 0, conversion: 0 }, source: 'environment', updated_at: null, updated_by: null })
const plannerPricingHistory = ref([])
const plannerQuotaSettings = ref({ values: { daily_limit: 3, monthly_limit: 10, ad_reward_daily_credits: 1, ad_reward_monthly_credits: 1, promotion_reward_daily_credits: 1, promotion_reward_monthly_credits: 2 }, source: 'environment', updated_at: null, updated_by: null })
const plannerQuotaHistory = ref([])
const roiBaselineSettings = ref({ values: { qualified_leads_per_100_credits: 10 }, source: 'environment', updated_at: null, updated_by: null })
const planDrafts = ref({})
const savingPlanId = ref('')
const assigningPlan = ref(false)
const adjustingCredits = ref(false)
const savingPlannerPricing = ref(false)
const savingPlannerQuota = ref(false)
const savingRoiBaseline = ref(false)
const showPlannerPricingConfirm = ref(false)
const pendingPlannerPricing = ref({ search_profile_click: 1, planner_intent_click: 0, qualified_lead: 0, conversion: 0 })
const plansPage = ref(1)
const subscriptionsPage = ref(1)
const ledgerPage = ref(1)
const billingEventsPage = ref(1)
const pricingHistoryPage = ref(1)
const quotaHistoryPage = ref(1)
const quotaLedgerPage = ref(1)
const rewardVerificationPage = ref(1)
const reconciliationWindowDays = ref(30)
const reconciliationAnomalies = ref({
  duplicate_attempt_count: 0,
  compensation_failure_count: 0,
  compensation_processing_count: 0,
  mismatch_count: 0,
  mismatch_breakdown: {},
  reconciliation_scan: {},
})
const reconciliationIssuesPreview = ref([])
const reconciliationLoading = ref(false)
const repairingReconciliation = ref(false)
const exportingReconciliation = ref(false)

const PAGE_SIZE = {
  plans: 3,
  subscriptions: 5,
  ledger: 6,
  events: 8,
  history: 4,
  quotaLedger: 8,
  rewards: 8,
}

const assignmentForm = ref({
  operator_profile_id: '',
  plan_code: '',
  notes: 'Manual activation after review',
  reset_credits: true,
})

const adjustmentForm = ref({
  operator_profile_id: '',
  credits_delta: 0,
  notes: 'Manual credit adjustment',
})

const plannerPricingForm = ref({
  search_profile_click: 1,
  planner_intent_click: 0,
  qualified_lead: 0,
  conversion: 0,
})

const plannerQuotaForm = ref({
  daily_limit: 3,
  monthly_limit: 10,
  ad_reward_daily_credits: 1,
  ad_reward_monthly_credits: 1,
  promotion_reward_daily_credits: 1,
  promotion_reward_monthly_credits: 2,
})

const roiBaselineForm = ref({
  qualified_leads_per_100_credits: 10,
})

const adminHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('adminToken') || ''}`,
}))

const operatorOptions = computed(() => {
  const fromOperators = (operators.value || [])
    .filter(operator => operator.profile?._id)
    .map(operator => ({
      operator_profile_id: operator.profile._id,
      business_name: operator.profile.business_name || operator.full_name || operator.email,
    }))

  const fromSubscriptions = (subscriptions.value || []).map(subscription => ({
    operator_profile_id: subscription.operator_profile_id,
    business_name: subscription.operator_profile?.business_name || subscription.operator_profile_id,
  }))

  const byId = new Map()
  ;[...fromOperators, ...fromSubscriptions].forEach((item) => {
    if (!byId.has(item.operator_profile_id)) {
      byId.set(item.operator_profile_id, item)
    }
  })
  return Array.from(byId.values())
})

const totalRemainingCredits = computed(() =>
  subscriptions.value.reduce((sum, item) => sum + Number(item.credits_remaining || 0), 0)
)

const billableEventCount = computed(() =>
  billingEvents.value.filter(item => item.is_billable).length
)

const plannerTotals = computed(() => billingSummary.value?.planner?.totals || {
  events: 0,
  billable_events: 0,
  non_billable_events: 0,
  credits_consumed: 0,
  spend_amount: 0,
})

const plannerFunnel = computed(() => billingSummary.value?.planner?.funnel || {
  recommendations_served: 0,
  quote_intents: 0,
  itinerary_saves: 0,
})

const plannerBreakdown = computed(() => billingSummary.value?.planner?.by_event_type || [])
const plannerPricing = computed(() => billingSummary.value?.planner?.pricing || {
  search_profile_click: 1,
  planner_intent_click: 0,
  qualified_lead: 0,
  conversion: 0,
})

const plannerQuota = computed(() => billingSummary.value?.planner?.quota || {
  daily_limit: 3,
  monthly_limit: 10,
  ad_reward_daily_credits: 1,
  ad_reward_monthly_credits: 1,
  promotion_reward_daily_credits: 1,
  promotion_reward_monthly_credits: 2,
})

const roiBaseline = computed(() => roiBaselineSettings.value?.values || {
  qualified_leads_per_100_credits: 10,
})

const zeroCreditActiveSubscriptions = computed(() =>
  subscriptions.value.filter(item => item.plan_status === 'active' && Number(item.included_credits || 0) === 0)
)

const plannerPricingEnabled = computed(() => {
  const values = plannerPricingForm.value
  return Number(values.search_profile_click || 0) > 0 || Number(values.planner_intent_click || 0) > 0 || Number(values.conversion || 0) > 0
})

const plannerPricingWarning = computed(() => {
  if (!plannerPricingEnabled.value || !zeroCreditActiveSubscriptions.value.length) return ''
  const impacted = zeroCreditActiveSubscriptions.value.length
  return `${impacted} active operator ${impacted === 1 ? 'subscription is' : 'subscriptions are'} still on zero-credit plans. Enabling billable event pricing now will log those events but they will not successfully debit credits until those operators move to plans with credits.`
})

const plannerQuotaValidation = computed(() => {
  const values = plannerQuotaForm.value
  if (Number(values.daily_limit || 0) > Number(values.monthly_limit || 0)) {
    return 'Daily limit cannot exceed monthly limit.'
  }
  if (Number(values.ad_reward_daily_credits || 0) > Number(values.ad_reward_monthly_credits || 0)) {
    return 'Ad reward daily bonus cannot exceed the ad monthly bonus.'
  }
  if (Number(values.promotion_reward_daily_credits || 0) > Number(values.promotion_reward_monthly_credits || 0)) {
    return 'Promotion reward daily bonus cannot exceed the promotion monthly bonus.'
  }
  return ''
})

const setMessage = (type, text) => {
  message.value = { type, text }
  window.clearTimeout(setMessage.timeoutId)
  setMessage.timeoutId = window.setTimeout(() => {
    message.value = { type: 'info', text: '' }
  }, 4500)
}

const buildPlanDrafts = () => {
  const drafts = {}
  plans.value.forEach((plan) => {
    drafts[plan._id] = {
      monthly_price: Number(plan.monthly_price || 0),
      included_credits: Number(plan.included_credits || 0),
      is_active: Boolean(plan.is_active),
    }
  })
  planDrafts.value = drafts
}

const buildPlannerPricingForm = () => {
  plannerPricingForm.value = {
    search_profile_click: Number(plannerPricingSettings.value?.values?.search_profile_click || 1),
    planner_intent_click: Number(plannerPricingSettings.value?.values?.planner_intent_click || 0),
    qualified_lead: Number(plannerPricingSettings.value?.values?.qualified_lead || 0),
    conversion: Number(plannerPricingSettings.value?.values?.conversion || 0),
  }
}

const buildPlannerQuotaForm = () => {
  plannerQuotaForm.value = {
    daily_limit: Number(plannerQuotaSettings.value?.values?.daily_limit || 3),
    monthly_limit: Number(plannerQuotaSettings.value?.values?.monthly_limit || 10),
    ad_reward_daily_credits: Number(plannerQuotaSettings.value?.values?.ad_reward_daily_credits || 1),
    ad_reward_monthly_credits: Number(plannerQuotaSettings.value?.values?.ad_reward_monthly_credits || 1),
    promotion_reward_daily_credits: Number(plannerQuotaSettings.value?.values?.promotion_reward_daily_credits || 1),
    promotion_reward_monthly_credits: Number(plannerQuotaSettings.value?.values?.promotion_reward_monthly_credits || 2),
  }
}

const buildRoiBaselineForm = () => {
  roiBaselineForm.value = {
    qualified_leads_per_100_credits: Number(roiBaselineSettings.value?.values?.qualified_leads_per_100_credits || 10),
  }
}

const totalPagesFor = (items, pageSize) => {
  const totalItems = Array.isArray(items) ? items.length : 0
  return Math.max(1, Math.ceil(totalItems / pageSize))
}

const paginatedItems = (items, page, pageSize) => {
  const list = Array.isArray(items) ? items : []
  const safePage = Math.max(1, Number(page || 1))
  const start = (safePage - 1) * pageSize
  return list.slice(start, start + pageSize)
}

const pageRangeLabel = (items, page, pageSize) => {
  const list = Array.isArray(items) ? items : []
  if (!list.length) return '0-0 of 0'
  const safePage = Math.min(Math.max(1, Number(page || 1)), totalPagesFor(list, pageSize))
  const start = (safePage - 1) * pageSize + 1
  const end = Math.min(safePage * pageSize, list.length)
  return `${start}-${end} of ${list.length}`
}

const shiftPage = (pageRef, delta, items, pageSize) => {
  const nextPage = Math.min(totalPagesFor(items, pageSize), Math.max(1, pageRef.value + delta))
  pageRef.value = nextPage
}

const resetAllPages = () => {
  plansPage.value = 1
  subscriptionsPage.value = 1
  ledgerPage.value = 1
  billingEventsPage.value = 1
  pricingHistoryPage.value = 1
  quotaHistoryPage.value = 1
  quotaLedgerPage.value = 1
  rewardVerificationPage.value = 1
}

const loadAll = async () => {
  loading.value = true
  loadError.value = ''
  try {
    const [plansRes, subscriptionsRes, ledgerRes, eventsRes, summaryRes, pricingRes, historyRes, quotaRes, quotaHistoryRes, roiBaselineRes, quotaLedgerRes, rewardVerificationRes, operatorsRes] = await Promise.all([
      api.get('/admin/billing/plans', { headers: adminHeaders.value }),
      api.get('/admin/billing/subscriptions', { headers: adminHeaders.value }),
      api.get('/admin/billing/ledger', { headers: adminHeaders.value }),
      api.get('/admin/billing/events', { headers: adminHeaders.value }),
      api.get('/admin/billing/summary', { headers: adminHeaders.value }),
      api.get('/admin/billing/planner-pricing', { headers: adminHeaders.value }),
      api.get('/admin/billing/planner-pricing/history', { headers: adminHeaders.value }),
      api.get('/admin/billing/planner-quota', { headers: adminHeaders.value }),
      api.get('/admin/billing/planner-quota/history', { headers: adminHeaders.value }),
      api.get('/admin/billing/roi-baseline', { headers: adminHeaders.value }),
      api.get('/admin/billing/planner-quota/ledger', { headers: adminHeaders.value }),
      api.get('/admin/billing/planner-quota/reward-verifications', { headers: adminHeaders.value }),
      api.get('/admin/operators?skip=0&limit=200', { headers: adminHeaders.value }),
    ])

    plans.value = plansRes.data.plans || []
    subscriptions.value = subscriptionsRes.data.subscriptions || []
    ledgerEntries.value = ledgerRes.data.entries || []
    billingEvents.value = eventsRes.data.events || []
    billingSummary.value = summaryRes.data || { days: 30, planner: { totals: {}, funnel: {}, by_event_type: [] }, by_surface: [] }
    plannerPricingSettings.value = pricingRes.data.settings || { values: { search_profile_click: 1, planner_intent_click: 0, qualified_lead: 0, conversion: 0 }, source: 'environment', updated_at: null, updated_by: null }
    plannerPricingHistory.value = historyRes.data.history || []
    plannerQuotaSettings.value = quotaRes.data.settings || { values: { daily_limit: 3, monthly_limit: 10, ad_reward_daily_credits: 1, ad_reward_monthly_credits: 1, promotion_reward_daily_credits: 1, promotion_reward_monthly_credits: 2 }, source: 'environment', updated_at: null, updated_by: null }
    plannerQuotaHistory.value = quotaHistoryRes.data.history || []
    roiBaselineSettings.value = roiBaselineRes.data.settings || { values: { qualified_leads_per_100_credits: 10 }, source: 'environment', updated_at: null, updated_by: null }
    touristQuotaLedger.value = quotaLedgerRes.data.entries || []
    plannerRewardVerifications.value = rewardVerificationRes.data.records || []
    operators.value = operatorsRes.data.operators || []
    resetAllPages()
    buildPlanDrafts()
    buildPlannerPricingForm()
    buildPlannerQuotaForm()
    buildRoiBaselineForm()
    await loadReconciliationOps()
  } catch (error) {
    console.error('Failed to load billing admin data:', error)
    loadError.value = error.response?.data?.detail || 'Failed to load billing controls'
  } finally {
    loading.value = false
  }
}

const mapReconciliationPreviewRows = (issues, orphans) => {
  const fromIssues = (issues || []).slice(0, 8).map((issue, index) => {
    const event = issue?.event || {}
    const ledger = issue?.ledger
    let credits = '-'
    if (Array.isArray(ledger)) {
      credits = ledger.map(item => item?.credits_delta).join(', ')
    } else if (ledger && typeof ledger === 'object') {
      credits = `${ledger.credits_delta ?? '-'}`
    } else if (event?.credits_charged != null) {
      credits = `${event.credits_charged}`
    }
    return {
      key: `issue-${index}-${event.idempotency_key || 'none'}`,
      type: issue?.type || 'issue',
      operator_profile_id: issue?.operator_profile_id || event?.operator_profile_id,
      event_idempotency_key: event?.idempotency_key || '-',
      credits,
    }
  })

  const fromOrphans = (orphans || []).slice(0, 8).map((debit, index) => ({
    key: `orphan-${index}-${debit?._id || 'none'}`,
    type: 'orphan_debit',
    operator_profile_id: debit?.operator_profile_id,
    event_idempotency_key: debit?.billing_event_idempotency_key || '-',
    credits: `${debit?.credits_delta ?? '-'}`,
  }))

  return [...fromIssues, ...fromOrphans].slice(0, 12)
}

const loadReconciliationOps = async () => {
  reconciliationLoading.value = true
  try {
    const days = reconciliationWindowDays.value
    const [anomalyRes, reportRes] = await Promise.all([
      api.get('/admin/billing/reconciliation/credit-events/anomalies', {
        headers: adminHeaders.value,
        params: { days, limit: 500 },
      }),
      api.get('/admin/billing/reconciliation/credit-events', {
        headers: adminHeaders.value,
        params: { days, limit: 50 },
      }),
    ])

    reconciliationAnomalies.value = anomalyRes.data?.anomalies || reconciliationAnomalies.value
    reconciliationIssuesPreview.value = mapReconciliationPreviewRows(reportRes.data?.issues, reportRes.data?.orphan_debits)
  } catch (error) {
    console.error('Failed to load reconciliation ops:', error)
    setMessage('error', error.response?.data?.detail || 'Failed to load reconciliation metrics')
  } finally {
    reconciliationLoading.value = false
  }
}

const runReconciliationRepair = async () => {
  repairingReconciliation.value = true
  try {
    const response = await api.post(
      '/admin/billing/reconciliation/credit-events/repair',
      null,
      {
        headers: adminHeaders.value,
        params: { days: reconciliationWindowDays.value, limit: 500, max_repairs: 500 },
      }
    )
    const repaired = Number(response.data?.repaired || 0)
    setMessage('success', `Reconciliation repair completed. Repaired ${repaired} row${repaired === 1 ? '' : 's'}.`)
    await loadReconciliationOps()
  } catch (error) {
    console.error('Failed to run reconciliation repair:', error)
    setMessage('error', error.response?.data?.detail || 'Failed to run reconciliation repair')
  } finally {
    repairingReconciliation.value = false
  }
}

const exportReconciliation = async (format) => {
  exportingReconciliation.value = true
  try {
    const response = await api.get('/admin/billing/reconciliation/credit-events/export', {
      headers: adminHeaders.value,
      params: { days: reconciliationWindowDays.value, limit: 500, format },
      responseType: format === 'json' ? 'json' : 'text',
    })

    const timestamp = new Date().toISOString().slice(0, 19).replaceAll(':', '-')
    const fileName = `billing-reconciliation-${timestamp}.${format}`
    let blob
    if (format === 'json') {
      blob = new Blob([JSON.stringify(response.data || {}, null, 2)], { type: 'application/json;charset=utf-8' })
    } else {
      blob = new Blob([response.data || ''], { type: 'text/csv;charset=utf-8' })
    }
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = fileName
    document.body.appendChild(link)
    link.click()
    link.remove()
    URL.revokeObjectURL(url)
    setMessage('success', `Reconciliation export ready (${format.toUpperCase()}).`)
  } catch (error) {
    console.error('Failed to export reconciliation report:', error)
    setMessage('error', error.response?.data?.detail || 'Failed to export reconciliation report')
  } finally {
    exportingReconciliation.value = false
  }
}

const normalizePlannerPricingForm = () => ({
  search_profile_click: Math.max(0, Math.min(100, Number(plannerPricingForm.value.search_profile_click || 0))),
  planner_intent_click: Math.max(0, Math.min(100, Number(plannerPricingForm.value.planner_intent_click || 0))),
  qualified_lead: 0,
  conversion: Math.max(0, Math.min(100, Number(plannerPricingForm.value.conversion || 0))),
})

const normalizePlannerQuotaForm = () => ({
  daily_limit: Math.max(0, Math.min(100, Number(plannerQuotaForm.value.daily_limit || 0))),
  monthly_limit: Math.max(0, Math.min(1000, Number(plannerQuotaForm.value.monthly_limit || 0))),
  ad_reward_daily_credits: Math.max(0, Math.min(20, Number(plannerQuotaForm.value.ad_reward_daily_credits || 0))),
  ad_reward_monthly_credits: Math.max(0, Math.min(100, Number(plannerQuotaForm.value.ad_reward_monthly_credits || 0))),
  promotion_reward_daily_credits: Math.max(0, Math.min(20, Number(plannerQuotaForm.value.promotion_reward_daily_credits || 0))),
  promotion_reward_monthly_credits: Math.max(0, Math.min(100, Number(plannerQuotaForm.value.promotion_reward_monthly_credits || 0))),
})

const normalizeRoiBaselineForm = () => ({
  qualified_leads_per_100_credits: Math.max(0, Math.min(10000, Number(roiBaselineForm.value.qualified_leads_per_100_credits || 0))),
})

const persistPlannerPricing = async (payload) => {
  savingPlannerPricing.value = true
  try {
    await api.post('/admin/billing/planner-pricing', payload, { headers: adminHeaders.value })
    setMessage('success', 'Billing credit values saved')
    showPlannerPricingConfirm.value = false
    await loadAll()
  } catch (error) {
    console.error('Failed to save planner pricing:', error)
    setMessage('error', error.response?.data?.detail || 'Failed to save billing pricing')
  } finally {
    savingPlannerPricing.value = false
  }
}

const persistPlannerQuota = async (payload) => {
  savingPlannerQuota.value = true
  try {
    await api.post('/admin/billing/planner-quota', payload, { headers: adminHeaders.value })
    setMessage('success', 'Planner quota settings saved')
    await loadAll()
  } catch (error) {
    console.error('Failed to save planner quota:', error)
    setMessage('error', error.response?.data?.detail || 'Failed to save planner quota settings')
  } finally {
    savingPlannerQuota.value = false
  }
}

const persistRoiBaseline = async (payload) => {
  savingRoiBaseline.value = true
  try {
    await api.post('/admin/billing/roi-baseline', payload, { headers: adminHeaders.value })
    setMessage('success', 'ROI baseline saved')
    await loadAll()
  } catch (error) {
    console.error('Failed to save ROI baseline:', error)
    setMessage('error', error.response?.data?.detail || 'Failed to save ROI baseline')
  } finally {
    savingRoiBaseline.value = false
  }
}

const savePlannerPricing = async () => {
  const payload = normalizePlannerPricingForm()
  const requiresConfirmation = payload.search_profile_click > 0 || payload.planner_intent_click > 0 || payload.conversion > 0
  if (requiresConfirmation) {
    pendingPlannerPricing.value = payload
    showPlannerPricingConfirm.value = true
    return
  }
  await persistPlannerPricing(payload)
}

const confirmPlannerPricingSave = async () => {
  await persistPlannerPricing({ ...pendingPlannerPricing.value })
}

const cancelPlannerPricingConfirm = () => {
  showPlannerPricingConfirm.value = false
}

const resetPlannerPricing = () => {
  plannerPricingForm.value = { search_profile_click: 0, planner_intent_click: 0, qualified_lead: 0, conversion: 0 }
}

const savePlannerQuota = async () => {
  if (plannerQuotaValidation.value) {
    setMessage('error', plannerQuotaValidation.value)
    return
  }
  await persistPlannerQuota(normalizePlannerQuotaForm())
}

const resetPlannerQuota = () => {
  plannerQuotaForm.value = {
    daily_limit: 3,
    monthly_limit: 10,
    ad_reward_daily_credits: 1,
    ad_reward_monthly_credits: 1,
    promotion_reward_daily_credits: 1,
    promotion_reward_monthly_credits: 2,
  }
}

const saveRoiBaseline = async () => {
  await persistRoiBaseline(normalizeRoiBaselineForm())
}

const resetRoiBaseline = () => {
  buildRoiBaselineForm()
}

const savePlan = async (plan) => {
  const draft = planDrafts.value[plan._id]
  if (!draft) return
  savingPlanId.value = plan._id
  try {
    await api.patch(`/admin/billing/plans/${plan._id}`, draft, { headers: adminHeaders.value })
    setMessage('success', `Updated ${plan.name}`)
    await loadAll()
  } catch (error) {
    console.error('Failed to save billing plan:', error)
    setMessage('error', error.response?.data?.detail || 'Failed to save billing plan')
  } finally {
    savingPlanId.value = ''
  }
}

const assignPlan = async () => {
  assigningPlan.value = true
  try {
    await api.post(
      `/admin/billing/subscriptions/${assignmentForm.value.operator_profile_id}/assign`,
      assignmentForm.value,
      { headers: adminHeaders.value }
    )
    setMessage('success', 'Operator plan assigned')
    assignmentForm.value = {
      operator_profile_id: '',
      plan_code: '',
      notes: 'Manual activation after review',
      reset_credits: true,
    }
    await loadAll()
  } catch (error) {
    console.error('Failed to assign plan:', error)
    setMessage('error', error.response?.data?.detail || 'Failed to assign operator plan')
  } finally {
    assigningPlan.value = false
  }
}

const submitAdjustment = async () => {
  adjustingCredits.value = true
  try {
    await api.post('/admin/billing/adjustments', adjustmentForm.value, { headers: adminHeaders.value })
    setMessage('success', 'Credit adjustment applied')
    adjustmentForm.value = {
      operator_profile_id: '',
      credits_delta: 0,
      notes: 'Manual credit adjustment',
    }
    await loadAll()
  } catch (error) {
    console.error('Failed to apply credit adjustment:', error)
    setMessage('error', error.response?.data?.detail || 'Failed to apply credit adjustment')
  } finally {
    adjustingCredits.value = false
  }
}

const readableText = (value) => String(value || '').replaceAll('_', ' ')
const signedCredits = (value) => `${value > 0 ? '+' : ''}${value}`
const formatMoney = (value) => Number(value || 0).toFixed(2)
const formatNumber = (value, digits = 1) => Number(value || 0).toFixed(digits)
const formatDateTime = (value) => value ? new Date(value).toLocaleString() : 'Never'
const formatPricingTriple = (value) => {
  const pricing = value || {}
  return `S:${Number(pricing.search_profile_click || 0)} P:${Number(pricing.planner_intent_click || 0)} T:${Number(pricing.conversion || 0)}`
}
const formatQuotaSummary = (value) => {
  const quota = value || {}
  return `D:${Number(quota.daily_limit || 0)} M:${Number(quota.monthly_limit || 0)} Ad:+${Number(quota.ad_reward_daily_credits || 0)}/+${Number(quota.ad_reward_monthly_credits || 0)} Promo:+${Number(quota.promotion_reward_daily_credits || 0)}/+${Number(quota.promotion_reward_monthly_credits || 0)}`
}
const operatorNameForEvent = (operatorProfileId) => {
  const subscription = subscriptions.value.find(item => item.operator_profile_id === operatorProfileId)
  if (subscription?.operator_profile?.business_name) return subscription.operator_profile.business_name
  const operator = operatorOptions.value.find(item => item.operator_profile_id === operatorProfileId)
  return operator?.business_name || operatorProfileId
}

const touristLabel = (record) => {
  const user = record?.tourist_user || {}
  return user.full_name || user.email || record?.user_id || 'Unknown tourist'
}

onMounted(loadAll)
</script>

<style scoped>
:global(body) {
  background:
    radial-gradient(circle at top left, rgba(14, 165, 233, 0.08), transparent 28%),
    radial-gradient(circle at top right, rgba(16, 185, 129, 0.08), transparent 22%),
    #f4f8fc;
}

.admin-financial {
  --surface: rgba(255, 255, 255, 0.9);
  --surface-strong: #ffffff;
  --surface-muted: #f8fbff;
  --stroke: #d9e3ee;
  --stroke-strong: #c7d6e5;
  --text: #0f172a;
  --text-muted: #5f6f84;
  --accent: #0f766e;
  --accent-soft: #ecfeff;
  font-size: 0.94rem;
  display: flex;
  flex-direction: column;
  gap: 1.4rem;
  padding: 0.25rem 0 1rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
  padding: 1.45rem 1.55rem;
  border: 1px solid rgba(209, 221, 235, 0.9);
  border-radius: 24px;
  background:
    linear-gradient(135deg, rgba(255, 255, 255, 0.98), rgba(247, 250, 255, 0.92)),
    linear-gradient(120deg, rgba(14, 165, 233, 0.08), rgba(16, 185, 129, 0.06));
  box-shadow: 0 18px 44px rgba(15, 23, 42, 0.08);
}

.header-copy {
  max-width: 760px;
}

.header-eyebrow,
.metric-label,
.panel-kicker {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  font-size: 0.7rem;
  font-weight: 800;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  color: #7c8ea3;
}

.page-header h1 {
  margin: 0.45rem 0 0;
  font-size: clamp(1.85rem, 2vw, 2.4rem);
  line-height: 1.05;
  color: var(--text);
}

.subtitle {
  margin: 0.65rem 0 0;
  max-width: 62ch;
  color: var(--text-muted);
  line-height: 1.6;
}

.header-actions {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.7rem;
  min-width: 180px;
}

.header-status {
  display: inline-flex;
  align-items: center;
  gap: 0.45rem;
  padding: 0.38rem 0.75rem;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.08);
  color: var(--accent);
  font-size: 0.77rem;
  font-weight: 700;
}

.btn-refresh,
.btn-primary,
.btn-secondary {
  border-radius: 12px;
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  transition: transform 140ms ease, box-shadow 140ms ease, border-color 140ms ease, background 140ms ease;
}

.btn-refresh:hover,
.btn-primary:hover,
.btn-secondary:hover {
  transform: translateY(-1px);
}

.btn-refresh,
.btn-secondary {
  border: 1px solid var(--stroke);
  background: rgba(255, 255, 255, 0.92);
  color: #334155;
  box-shadow: 0 8px 16px rgba(148, 163, 184, 0.12);
}

.btn-refresh {
  padding: 0.8rem 1rem;
}

.btn-secondary {
  padding: 0.78rem 1rem;
}

.btn-primary {
  border: none;
  background: linear-gradient(135deg, #0f766e, #0ea5e9);
  color: #fff;
  padding: 0.82rem 1rem;
  box-shadow: 0 12px 22px rgba(14, 165, 233, 0.22);
}

.message-banner,
.state-box {
  padding: 0.95rem 1rem;
  border-radius: 16px;
}

.message-banner.success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.message-banner.error,
.state-box.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}

.state-box.warning {
  background: #fff7ed;
  border: 1px solid #fed7aa;
  color: #c2410c;
}

.state-box {
  background: rgba(255, 255, 255, 0.72);
  border: 1px dashed var(--stroke-strong);
  color: var(--text-muted);
  text-align: center;
}

.state-box.compact {
  margin-top: 0.85rem;
}

.tab-shell {
  display: grid;
  gap: 1rem;
}

.tab-bar {
  display: flex;
  flex-wrap: wrap;
  gap: 0.75rem;
  padding: 0.7rem;
  border: 1px solid rgba(214, 223, 234, 0.92);
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.82);
  backdrop-filter: blur(10px);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.05);
}

.tab-button {
  min-width: 138px;
  display: inline-flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
  padding: 0.75rem 0.95rem;
  border: 1px solid transparent;
  border-radius: 14px;
  background: transparent;
  color: var(--text-muted);
  font: inherit;
  font-weight: 700;
  cursor: pointer;
  transition: background 140ms ease, border-color 140ms ease, color 140ms ease, transform 140ms ease;
}

.tab-button:hover {
  transform: translateY(-1px);
  background: rgba(248, 251, 255, 0.92);
  border-color: var(--stroke);
}

.tab-button.active {
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.12), rgba(14, 165, 233, 0.14));
  border-color: rgba(14, 165, 233, 0.2);
  color: var(--text);
}

.tab-button small {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  min-width: 1.7rem;
  height: 1.7rem;
  padding: 0 0.4rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
  color: var(--accent);
  font-size: 0.72rem;
  font-weight: 800;
}

.tab-panel {
  display: grid;
  gap: 1rem;
}

.metrics-grid,
.grid.two-col,
.planner-admin-grid,
.control-grid,
.planner-metrics-grid,
.planner-pricing-grid,
.plan-edit-grid {
  display: grid;
  gap: 1rem;
}

.metrics-grid {
  grid-template-columns: repeat(5, minmax(0, 1fr));
}

.grid.two-col {
  grid-template-columns: minmax(0, 1.08fr) minmax(340px, 0.92fr);
  align-items: start;
}

.planner-admin-grid,
.control-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.planner-metrics-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.planner-pricing-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.plan-edit-grid {
  grid-template-columns: repeat(3, minmax(0, 1fr));
}

.planner-row,
.second-row {
  margin-top: 0.15rem;
}

.metric-card,
.panel,
.surface-card,
.control-card {
  border-radius: 22px;
  border: 1px solid rgba(214, 223, 234, 0.92);
  background: var(--surface);
  backdrop-filter: blur(8px);
  box-shadow: 0 14px 34px rgba(15, 23, 42, 0.07);
}

.metric-card {
  position: relative;
  overflow: hidden;
  padding: 1.1rem 1rem 1rem;
}

.metric-card::before {
  content: '';
  position: absolute;
  inset: 0 auto auto 0;
  width: 100%;
  height: 3px;
  background: linear-gradient(90deg, rgba(15, 118, 110, 0.9), rgba(14, 165, 233, 0.6));
}

.metric-card.compact {
  padding: 0.95rem;
}

.metric-card.wide {
  grid-column: span 2;
}

.metric-card strong {
  display: block;
  margin-top: 0.45rem;
  font-size: 1.55rem;
  letter-spacing: -0.03em;
  color: var(--text);
}

.metric-card p {
  margin: 0.4rem 0 0;
  color: var(--text-muted);
  line-height: 1.45;
}

.panel {
  padding: 1.35rem;
}

.planner-hub-panel {
  background:
    linear-gradient(180deg, rgba(255, 255, 255, 0.94), rgba(249, 252, 255, 0.92));
}

.surface-card,
.control-card {
  padding: 1rem;
}

.panel-head,
.planner-pricing-head,
.plan-top,
.subscription-row,
.ledger-row,
.planner-history-row,
.row-actions,
.modal-actions {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.panel-head {
  margin-bottom: 1rem;
}

.panel-head.with-meta {
  align-items: center;
}

.panel-head h2,
.planner-pricing-head h3,
.plan-card h3,
.subscription-row h3,
.ledger-row strong,
.control-card-head h3,
.modal-head h3 {
  margin: 0;
  color: var(--text);
}

.planner-pricing-head,
.control-card-head {
  margin-bottom: 0.9rem;
}

.panel-meta-row {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.panel-meta {
  color: #7c8ea3;
  font-size: 0.76rem;
  font-weight: 700;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.pager {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.28rem 0.36rem;
  border: 1px solid var(--stroke);
  border-radius: 999px;
  background: rgba(248, 251, 255, 0.9);
  color: var(--text-muted);
  font-size: 0.78rem;
  font-weight: 700;
}

.pager-btn {
  border: none;
  border-radius: 999px;
  padding: 0.35rem 0.6rem;
  background: #fff;
  color: #334155;
  font: inherit;
  font-size: 0.76rem;
  font-weight: 700;
  cursor: pointer;
  box-shadow: 0 4px 10px rgba(148, 163, 184, 0.14);
}

.pager-btn:disabled {
  opacity: 0.45;
  cursor: not-allowed;
  box-shadow: none;
}

.planner-pricing-note,
.planner-pricing-meta,
.modal-copy,
.control-card-head p,
.plan-card p,
.subscription-row p,
.ledger-row p,
.planner-history-row p {
  margin: 0.35rem 0 0;
  color: var(--text-muted);
  line-height: 1.55;
}

.planner-pricing-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
  justify-content: flex-end;
}

.planner-pricing-strip,
.feature-tags,
.tag-row,
.planner-history-values,
.planner-confirm-summary {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.recon-panel {
  display: grid;
  gap: 0.9rem;
}

.recon-metrics-grid {
  grid-template-columns: repeat(4, minmax(0, 1fr));
}

.recon-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.65rem;
}

.recon-table-wrap {
  max-height: 16rem;
}

.planner-pricing-strip {
  margin-top: 0.95rem;
}

.planner-admin-grid {
  margin-top: 1.1rem;
}

.planner-admin-column,
.planner-history-list,
.plan-list,
.list-wrap,
.ledger-list {
  display: flex;
  flex-direction: column;
  gap: 0.95rem;
}

.planner-warning-box {
  margin-top: 0.85rem;
}

.planner-pricing-form {
  display: grid;
  gap: 0.95rem;
}

.planner-history-panel {
  display: grid;
  gap: 0.8rem;
}

.compact-head {
  margin-bottom: 0;
}

.planner-history-row,
.plan-card,
.subscription-row,
.ledger-row {
  padding: 0.95rem 1rem;
  border: 1px solid var(--stroke);
  border-radius: 18px;
  background: linear-gradient(180deg, #fbfdff, #f6faff);
}

.compact-row {
  padding: 0.82rem 0.9rem;
}

.status-pill,
.tag,
.feature-tag,
.delta-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.28rem 0.62rem;
  font-size: 0.75rem;
  font-weight: 700;
}

.status-pill.active,
.delta-pill.positive {
  background: #ecfdf5;
  color: #166534;
}

.status-pill.inactive {
  background: #f8fafc;
  color: #64748b;
}

.status-pill.pending_activation,
.tag.request {
  background: #fff7ed;
  color: #c2410c;
}

.delta-pill.negative {
  background: #fef2f2;
  color: #b91c1c;
}

.feature-tag {
  background: #ecfeff;
  color: #0f766e;
}

.tag {
  background: #eff6ff;
  color: #1d4ed8;
}

.tag.muted {
  background: #f8fafc;
  color: #64748b;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.38rem;
}

.field span {
  color: #475569;
  font-size: 0.79rem;
  font-weight: 700;
}

.field input,
.field select {
  width: 100%;
  border: 1px solid var(--stroke);
  border-radius: 13px;
  background: var(--surface-muted);
  padding: 0.82rem 0.88rem;
  font: inherit;
  color: var(--text);
  transition: border-color 140ms ease, box-shadow 140ms ease, background 140ms ease;
}

.field input:focus,
.field select:focus {
  outline: none;
  border-color: #7dd3fc;
  box-shadow: 0 0 0 4px rgba(14, 165, 233, 0.14);
  background: #fff;
}

.scroll-list,
.compact-scroll {
  scrollbar-width: thin;
  scrollbar-color: rgba(148, 163, 184, 0.6) transparent;
}

.scroll-list::-webkit-scrollbar,
.compact-scroll::-webkit-scrollbar {
  width: 8px;
  height: 8px;
}

.scroll-list::-webkit-scrollbar-thumb,
.compact-scroll::-webkit-scrollbar-thumb {
  background: rgba(148, 163, 184, 0.55);
  border-radius: 999px;
}

.scroll-list {
  max-height: 34rem;
  overflow: auto;
  padding-right: 0.25rem;
}

.compact-scroll {
  max-height: 28rem;
  overflow: auto;
}

.field.toggle {
  justify-content: flex-end;
  gap: 0.6rem;
}

.field.toggle input {
  width: auto;
}

.control-form {
  display: grid;
  gap: 0.9rem;
}

.control-form.standalone {
  margin-bottom: 0;
}

.right-stack {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  gap: 0.28rem;
}

.events-table-wrap {
  overflow-x: auto;
  border: 1px solid var(--stroke);
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.82);
}

.events-table {
  width: 100%;
  border-collapse: collapse;
}

.events-table th,
.events-table td {
  padding: 0.8rem 0.7rem;
  border-bottom: 1px solid #edf2f7;
  text-align: left;
  vertical-align: top;
}

.compact-table th,
.compact-table td {
  padding: 0.65rem 0.58rem;
  font-size: 0.82rem;
  line-height: 1.35;
}

.events-table th {
  position: sticky;
  top: 0;
  background: #f8fbff;
  font-size: 0.74rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #94a3b8;
}

.empty-inline {
  text-align: center;
  color: #94a3b8;
}

.modal-backdrop {
  position: fixed;
  inset: 0;
  z-index: 40;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(15, 23, 42, 0.48);
  backdrop-filter: blur(4px);
}

.modal-card {
  width: min(560px, 100%);
  padding: 1.25rem;
  border-radius: 22px;
  border: 1px solid rgba(214, 223, 234, 0.9);
  background: #fff;
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.24);
  display: grid;
  gap: 1rem;
}

@media (max-width: 1400px) {
  .grid.two-col,
  .planner-admin-grid,
  .control-grid {
    grid-template-columns: 1fr;
  }

  .metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .metric-card.wide {
    grid-column: span 2;
  }

  .planner-pricing-grid,
  .plan-edit-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .recon-metrics-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .tab-button {
    flex: 1 1 180px;
  }
}

@media (max-width: 1100px) {
  .planner-pricing-grid,
  .plan-edit-grid {
    grid-template-columns: 1fr;
  }

  .recon-metrics-grid {
    grid-template-columns: 1fr;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .metric-card.wide {
    grid-column: auto;
  }

  .planner-metrics-grid {
    grid-template-columns: 1fr;
  }

  .panel-head.with-meta {
    align-items: flex-start;
  }
}

@media (max-width: 720px) {
  .admin-financial {
    gap: 1rem;
  }

  .page-header,
  .header-actions,
  .panel-head,
  .panel-meta-row,
  .planner-pricing-head,
  .planner-history-row,
  .plan-top,
  .subscription-row,
  .ledger-row,
  .row-actions,
  .modal-actions {
    flex-direction: column;
  }

  .page-header,
  .panel,
  .surface-card,
  .control-card,
  .metric-card {
    border-radius: 18px;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .tab-bar {
    padding: 0.55rem;
    gap: 0.55rem;
  }

  .tab-button {
    min-width: 0;
    width: 100%;
  }

  .header-actions,
  .right-stack {
    align-items: flex-start;
  }

  .planner-history-values,
  .planner-pricing-actions {
    justify-content: flex-start;
  }

  .events-table th,
  .events-table td {
    padding: 0.72rem 0.58rem;
  }
}
</style>
