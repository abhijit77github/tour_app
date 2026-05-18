<template>
  <div class="admin-financial">
    <div class="page-header">
      <h1>Financial Management</h1>
      <p class="subtitle">Track payments, commissions, and payouts</p>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        @click="activeTab = 'dashboard'"
        :class="['tab', { active: activeTab === 'dashboard' }]"
      >
        📊 Dashboard
      </button>
      <button
        @click="activeTab = 'transactions'"
        :class="['tab', { active: activeTab === 'transactions' }]"
      >
        💳 Transactions
      </button>
      <button
        @click="activeTab = 'commissions'"
        :class="['tab', { active: activeTab === 'commissions' }]"
      >
        📈 Commissions
      </button>
      <button
        @click="activeTab = 'payouts'"
        :class="['tab', { active: activeTab === 'payouts' }]"
      >
        💰 Payouts
      </button>
      <button
        @click="activeTab = 'reports'"
        :class="['tab', { active: activeTab === 'reports' }]"
      >
        📋 Reports
      </button>
      <button
        @click="activeTab = 'export'"
        :class="['tab', { active: activeTab === 'export' }]"
      >
        📥 Export
      </button>
    </div>

    <!-- Dashboard Tab -->
    <div v-if="activeTab === 'dashboard'" class="tab-content">
      <div class="metrics-grid">
        <!-- Total Revenue Card -->
        <div class="metric-card">
          <div class="metric-icon">💵</div>
          <div class="metric-content">
            <p class="metric-label">Total Revenue</p>
            <p class="metric-value">{{ formatCurrency(financialData.totalRevenue) }}</p>
            <p class="metric-subtitle">All-time earnings</p>
          </div>
        </div>

        <!-- Monthly Revenue Card -->
        <div class="metric-card">
          <div class="metric-icon">📅</div>
          <div class="metric-content">
            <p class="metric-label">Monthly Revenue</p>
            <p class="metric-value">{{ formatCurrency(financialData.monthlyRevenue) }}</p>
            <p class="metric-subtitle">Current month</p>
          </div>
        </div>

        <!-- Pending Payouts Card -->
        <div class="metric-card">
          <div class="metric-icon">⏳</div>
          <div class="metric-content">
            <p class="metric-label">Pending Payouts</p>
            <p class="metric-value">{{ formatCurrency(financialData.pendingPayouts) }}</p>
            <p class="metric-subtitle">{{ financialData.pendingPayoutCount }} operators</p>
          </div>
        </div>

        <!-- Commission Collected Card -->
        <div class="metric-card">
          <div class="metric-icon">🎯</div>
          <div class="metric-content">
            <p class="metric-label">Commission Collected</p>
            <p class="metric-value">{{ formatCurrency(financialData.commissionCollected) }}</p>
            <p class="metric-subtitle">{{ financialData.commissionPercentage }}% avg</p>
          </div>
        </div>

        <!-- Processing Fee Card -->
        <div class="metric-card">
          <div class="metric-icon">⚙️</div>
          <div class="metric-content">
            <p class="metric-label">Processing Fees</p>
            <p class="metric-value">{{ formatCurrency(financialData.processingFees) }}</p>
            <p class="metric-subtitle">Payment gateway fees</p>
          </div>
        </div>

        <!-- Avg Transaction Card -->
        <div class="metric-card">
          <div class="metric-icon">📊</div>
          <div class="metric-content">
            <p class="metric-label">Avg Transaction</p>
            <p class="metric-value">{{ formatCurrency(financialData.avgTransaction) }}</p>
            <p class="metric-subtitle">Average value</p>
          </div>
        </div>
      </div>

      <!-- Charts Section -->
      <div class="charts-section">
        <div class="chart-container">
          <h3>Revenue Trend (Last 12 Months)</h3>
          <div class="chart-placeholder">
            <p>📈 Revenue trend chart would display here</p>
            <div class="chart-bars">
              <div v-for="month in 12" :key="month" class="chart-bar" :style="{ height: (Math.random() * 80 + 20) + '%' }"></div>
            </div>
          </div>
        </div>

        <div class="chart-container">
          <h3>Payment Method Breakdown</h3>
          <div class="chart-placeholder">
            <p>🥧 Payment method distribution</p>
            <div class="payment-breakdown">
              <div class="payment-item">
                <span class="payment-label">Card</span>
                <div class="payment-bar" style="width: 45%"></div>
                <span class="payment-value">45%</span>
              </div>
              <div class="payment-item">
                <span class="payment-label">UPI</span>
                <div class="payment-bar" style="width: 35%"></div>
                <span class="payment-value">35%</span>
              </div>
              <div class="payment-item">
                <span class="payment-label">Wallet</span>
                <div class="payment-bar" style="width: 20%"></div>
                <span class="payment-value">20%</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Transactions Tab -->
    <div v-else-if="activeTab === 'transactions'" class="tab-content">
      <div class="transaction-controls">
        <input
          v-model="transactionSearch"
          type="text"
          placeholder="Search by transaction ID, tourist, operator..."
          class="search-input"
        />

        <select v-model="transactionFilters.status" class="filter-select">
          <option value="">All Status</option>
          <option value="completed">✓ Completed</option>
          <option value="pending">⏳ Pending</option>
          <option value="failed">✗ Failed</option>
        </select>

        <select v-model="transactionFilters.method" class="filter-select">
          <option value="">All Methods</option>
          <option value="card">💳 Card</option>
          <option value="upi">📱 UPI</option>
          <option value="wallet">👛 Wallet</option>
        </select>

        <input
          v-model.number="transactionFilters.minAmount"
          type="number"
          placeholder="Min amount"
          class="filter-input"
        />

        <input
          v-model.number="transactionFilters.maxAmount"
          type="number"
          placeholder="Max amount"
          class="filter-input"
        />
      </div>

      <div v-if="filteredTransactions.length === 0" class="empty-state">
        <p>📭 No transactions found</p>
      </div>

      <div v-else class="transactions-container">
        <div class="transactions-table">
          <div class="table-header">
            <div class="col col-date">Date</div>
            <div class="col col-id">Transaction ID</div>
            <div class="col col-tourist">Tourist</div>
            <div class="col col-operator">Operator</div>
            <div class="col col-amount">Amount</div>
            <div class="col col-commission">Commission</div>
            <div class="col col-method">Method</div>
            <div class="col col-status">Status</div>
            <div class="col col-actions">Actions</div>
          </div>

          <div
            v-for="transaction in paginatedTransactions"
            :key="transaction._id"
            class="table-row"
          >
            <div class="col col-date">{{ formatDate(transaction.date) }}</div>
            <div class="col col-id">{{ transaction.transaction_id }}</div>
            <div class="col col-tourist">{{ transaction.tourist_name }}</div>
            <div class="col col-operator">{{ transaction.operator_name }}</div>
            <div class="col col-amount">{{ formatCurrency(transaction.amount) }}</div>
            <div class="col col-commission">{{ formatCurrency(transaction.commission) }}</div>
            <div class="col col-method">{{ getPaymentMethodIcon(transaction.method) }} {{ transaction.method }}</div>
            <div class="col col-status">
              <span :class="['status-badge', `status-${transaction.status}`]">
                {{ getStatusLabel(transaction.status) }}
              </span>
            </div>
            <div class="col col-actions">
              <button @click="viewTransactionDetail(transaction)" class="action-btn view">👁️</button>
              <button v-if="transaction.status !== 'failed'" @click="refundTransaction(transaction)" class="action-btn refund">↩️</button>
              <button @click="markDisputed(transaction)" class="action-btn dispute">⚠️</button>
            </div>
          </div>
        </div>

        <!-- Pagination -->
        <div class="pagination">
          <button
            @click="transactionPage = Math.max(1, transactionPage - 1)"
            :disabled="transactionPage === 1"
            class="pagination-btn"
          >
            ← Previous
          </button>

          <div class="page-buttons">
            <button
              v-for="page in visibleTransactionPages"
              :key="page"
              @click="transactionPage = page"
              :class="['page-btn', { active: transactionPage === page }]"
            >
              {{ page }}
            </button>
          </div>

          <button
            @click="transactionPage++"
            :disabled="transactionPage >= totalTransactionPages"
            class="pagination-btn"
          >
            Next →
          </button>
        </div>
      </div>
    </div>

    <!-- Commissions Tab -->
    <div v-else-if="activeTab === 'commissions'" class="tab-content">
      <div class="commissions-container">
        <!-- Commission Rules Section -->
        <div class="section">
          <h3>Commission Rules</h3>
          <div class="commission-rules">
            <div class="rule-card">
              <label>Default Commission %</label>
              <div class="input-group">
                <input v-model.number="commissionRules.default" type="number" class="input" />
                <span class="unit">%</span>
              </div>
            </div>

            <div class="rule-card">
              <label>Tier 1 (Premium)</label>
              <div class="input-group">
                <input v-model.number="commissionRules.tier1" type="number" class="input" />
                <span class="unit">%</span>
              </div>
              <p class="rule-note">For high-rated operators</p>
            </div>

            <div class="rule-card">
              <label>Tier 2 (Standard)</label>
              <div class="input-group">
                <input v-model.number="commissionRules.tier2" type="number" class="input" />
                <span class="unit">%</span>
              </div>
              <p class="rule-note">For regular operators</p>
            </div>

            <div class="rule-card">
              <label>Holiday Multiplier</label>
              <div class="input-group">
                <input v-model.number="commissionRules.holidayMultiplier" type="number" step="0.1" class="input" />
                <span class="unit">x</span>
              </div>
              <p class="rule-note">1.2 = 20% increase</p>
            </div>
          </div>

          <button @click="saveCommissionRules" class="btn btn-primary">💾 Save Rules</button>
        </div>

        <!-- Commission History Section -->
        <div class="section">
          <h3>Commission History by Operator</h3>

          <div class="commission-search">
            <input
              v-model="commissionSearch"
              type="text"
              placeholder="Search operator name..."
              class="search-input"
            />
          </div>

          <div v-if="filteredCommissions.length === 0" class="empty-state">
            <p>📭 No commission records</p>
          </div>

          <div v-else class="commissions-list">
            <div
              v-for="commission in filteredCommissions"
              :key="commission._id"
              class="commission-card"
            >
              <div class="commission-header">
                <h4>{{ commission.operator_name }}</h4>
                <span class="commission-total">{{ formatCurrency(commission.earned) }}</span>
              </div>

              <div class="commission-details">
                <div class="detail-item">
                  <span class="label">Period:</span>
                  <span class="value">{{ commission.period }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Earned:</span>
                  <span class="value">{{ formatCurrency(commission.earned) }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Adjustments:</span>
                  <span class="value">{{ formatCurrency(commission.adjustments) }}</span>
                </div>
                <div class="detail-item">
                  <span class="label">Net:</span>
                  <span class="value">{{ formatCurrency(commission.net) }}</span>
                </div>
              </div>

              <p class="commission-note">Status: {{ commission.status }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Payouts Tab -->
    <div v-else-if="activeTab === 'payouts'" class="tab-content">
      <div class="payouts-container">
        <!-- Pending Payouts Section -->
        <div class="section">
          <h3>Pending Payouts ({{ pendingPayouts.length }} operators)</h3>

          <div class="payout-controls">
            <button @click="initiatePayoutAll" class="btn btn-primary">💸 Payout All</button>
            <input
              v-model.number="payoutThreshold"
              type="number"
              placeholder="Minimum payout amount"
              class="filter-input"
            />
            <button @click="saveBulkPayoutSettings" class="btn btn-secondary">Save Settings</button>
          </div>

          <div v-if="pendingPayouts.length === 0" class="empty-state">
            <p>✓ No pending payouts</p>
          </div>

          <div v-else class="payouts-grid">
            <div
              v-for="payout in pendingPayouts"
              :key="payout._id"
              class="payout-card"
            >
              <div class="payout-header">
                <h4>{{ payout.operator_name }}</h4>
                <span class="payout-amount">{{ formatCurrency(payout.amount) }}</span>
              </div>

              <div class="payout-details">
                <p><span class="label">Days Pending:</span> {{ payout.daysPending }}</p>
                <p><span class="label">Bank:</span> {{ payout.bankName }}</p>
                <p><span class="label">Account:</span> ****{{ payout.accountLast4 }}</p>
              </div>

              <div class="payout-actions">
                <button @click="initiatePayout(payout)" class="btn btn-small btn-primary">
                  💰 Initiate
                </button>
                <button @click="schedulePayout(payout)" class="btn btn-small btn-secondary">
                  🕐 Schedule
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- Payout History Section -->
        <div class="section">
          <h3>Payout History</h3>

          <div class="payout-history-controls">
            <select v-model="payoutHistoryFilter.status" class="filter-select">
              <option value="">All Status</option>
              <option value="completed">✓ Completed</option>
              <option value="processing">⏳ Processing</option>
              <option value="failed">✗ Failed</option>
            </select>
          </div>

          <div v-if="filteredPayoutHistory.length === 0" class="empty-state">
            <p>📭 No payout history</p>
          </div>

          <div v-else class="payout-history-list">
            <div
              v-for="history in filteredPayoutHistory"
              :key="history._id"
              class="history-item"
            >
              <div class="history-content">
                <div class="history-main">
                  <h4>{{ history.operator_name }}</h4>
                  <span class="history-date">{{ formatDate(history.date) }}</span>
                </div>
                <div class="history-details">
                  <span class="amount">{{ formatCurrency(history.amount) }}</span>
                  <span :class="['status', `status-${history.status}`]">{{ getStatusLabel(history.status) }}</span>
                </div>
              </div>

              <p class="reference">Ref: {{ history.reference_id }}</p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Reports Tab -->
    <div v-else-if="activeTab === 'reports'" class="tab-content">
      <div class="reports-container">
        <h3>Financial Reports</h3>

        <div class="report-grid">
          <div class="report-card">
            <div class="report-icon">📊</div>
            <h4>Revenue by Period</h4>
            <p>Monthly and yearly revenue breakdown</p>
            <button @click="generateReport('revenue')" class="btn btn-secondary">Generate</button>
          </div>

          <div class="report-card">
            <div class="report-icon">🎯</div>
            <h4>Commission Breakdown</h4>
            <p>Commission collected vs platform revenue</p>
            <button @click="generateReport('commission')" class="btn btn-secondary">Generate</button>
          </div>

          <div class="report-card">
            <div class="report-icon">🚀</div>
            <h4>Operator Earnings</h4>
            <p>Top earners and payment distribution</p>
            <button @click="generateReport('operators')" class="btn btn-secondary">Generate</button>
          </div>

          <div class="report-card">
            <div class="report-icon">💳</div>
            <h4>Payment Methods</h4>
            <p>Analysis of payment methods used</p>
            <button @click="generateReport('methods')" class="btn btn-secondary">Generate</button>
          </div>

          <div class="report-card">
            <div class="report-icon">📈</div>
            <h4>Growth Metrics</h4>
            <p>Platform growth and trends</p>
            <button @click="generateReport('growth')" class="btn btn-secondary">Generate</button>
          </div>

          <div class="report-card">
            <div class="report-icon">💰</div>
            <h4>Customer Acquisition</h4>
            <p>Cost per acquisition analysis</p>
            <button @click="generateReport('cac')" class="btn btn-secondary">Generate</button>
          </div>
        </div>

        <div class="generated-reports">
          <h4>Generated Reports</h4>
          <div v-if="generatedReports.length === 0" class="empty-state">
            <p>📭 No reports generated yet</p>
          </div>

          <div v-else class="reports-list">
            <div v-for="report in generatedReports" :key="report._id" class="report-item">
              <div class="report-info">
                <p class="report-name">{{ report.name }}</p>
                <p class="report-date">Generated: {{ formatDate(report.generated_at) }}</p>
              </div>
              <div class="report-actions">
                <button @click="downloadReport(report)" class="btn btn-small">📥 Download</button>
                <button @click="deleteReport(report)" class="btn btn-small btn-danger">🗑️</button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Export Tab -->
    <div v-else-if="activeTab === 'export'" class="tab-content">
      <div class="export-container">
        <div class="export-section">
          <h3>Export Financial Data</h3>

          <div class="export-options">
            <div class="option-card">
              <h4>Export Format</h4>
              <div class="format-buttons">
                <button
                  @click="exportFormat = 'csv'"
                  :class="['format-btn', { active: exportFormat === 'csv' }]"
                >
                  📄 CSV
                </button>
                <button
                  @click="exportFormat = 'excel'"
                  :class="['format-btn', { active: exportFormat === 'excel' }]"
                >
                  📊 Excel
                </button>
                <button
                  @click="exportFormat = 'pdf'"
                  :class="['format-btn', { active: exportFormat === 'pdf' }]"
                >
                  📋 PDF
                </button>
                <button
                  @click="exportFormat = 'json'"
                  :class="['format-btn', { active: exportFormat === 'json' }]"
                >
                  🔗 JSON
                </button>
              </div>
            </div>

            <div class="option-card">
              <h4>Data to Export</h4>
              <div class="checkbox-group">
                <label>
                  <input v-model="exportData.transactions" type="checkbox" />
                  <span>Transactions</span>
                </label>
                <label>
                  <input v-model="exportData.commissions" type="checkbox" />
                  <span>Commissions</span>
                </label>
                <label>
                  <input v-model="exportData.payouts" type="checkbox" />
                  <span>Payouts</span>
                </label>
                <label>
                  <input v-model="exportData.summaries" type="checkbox" />
                  <span>Financial Summary</span>
                </label>
              </div>
            </div>

            <div class="option-card">
              <h4>Date Range</h4>
              <div class="date-inputs">
                <input v-model="exportDateRange.from" type="date" class="input" />
                <span>to</span>
                <input v-model="exportDateRange.to" type="date" class="input" />
              </div>
            </div>

            <div class="option-card">
              <h4>Additional Options</h4>
              <div class="checkbox-group">
                <label>
                  <input v-model="exportOptions.includeCharts" type="checkbox" />
                  <span>Include charts (PDF only)</span>
                </label>
                <label>
                  <input v-model="exportOptions.compress" type="checkbox" />
                  <span>Compress file</span>
                </label>
                <label>
                  <input v-model="exportOptions.sendEmail" type="checkbox" />
                  <span>Send to email</span>
                </label>
              </div>
            </div>
          </div>

          <div class="export-email" v-if="exportOptions.sendEmail">
            <input v-model="exportEmail" type="email" placeholder="Email address" class="input" />
          </div>

          <div class="export-actions">
            <button @click="resetExportForm" class="btn btn-secondary">Clear</button>
            <button @click="exportFinancialData" class="btn btn-primary">📥 Export Now</button>
          </div>

          <div v-if="exportSuccess" class="success-message">{{ exportSuccess }}</div>
          <div v-if="exportError" class="error-message">{{ exportError }}</div>
        </div>

        <div class="export-schedule">
          <h3>Scheduled Exports</h3>

          <div v-if="scheduledExports.length === 0" class="empty-state">
            <p>📭 No scheduled exports</p>
          </div>

          <div v-else class="scheduled-list">
            <div v-for="scheduled in scheduledExports" :key="scheduled._id" class="scheduled-item">
              <div class="scheduled-info">
                <p class="scheduled-name">{{ scheduled.frequency }} - {{ scheduled.format }}</p>
                <p class="scheduled-recipients">📧 {{ scheduled.recipients.join(', ') }}</p>
                <p class="scheduled-next">Next: {{ formatDate(scheduled.next_run) }}</p>
              </div>
              <button @click="deleteScheduledExport(scheduled)" class="btn btn-small btn-danger">🗑️</button>
            </div>
          </div>

          <button @click="showScheduleModal = true" class="btn btn-primary">➕ Schedule Export</button>
        </div>
      </div>
    </div>

    <!-- Transaction Detail Modal -->
    <div v-if="showTransactionModal" class="modal-overlay" @click.self="closeTransactionModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Transaction Details</h2>
          <button @click="closeTransactionModal" class="close-btn">✕</button>
        </div>

        <div v-if="selectedTransaction" class="modal-body">
          <div class="detail-grid">
            <div class="detail-item">
              <span class="label">Transaction ID:</span>
              <span class="value">{{ selectedTransaction.transaction_id }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Date:</span>
              <span class="value">{{ formatDate(selectedTransaction.date) }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Tourist:</span>
              <span class="value">{{ selectedTransaction.tourist_name }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Operator:</span>
              <span class="value">{{ selectedTransaction.operator_name }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Amount:</span>
              <span class="value">{{ formatCurrency(selectedTransaction.amount) }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Commission ({{ selectedTransaction.commission_rate }}%):</span>
              <span class="value">{{ formatCurrency(selectedTransaction.commission) }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Payment Method:</span>
              <span class="value">{{ selectedTransaction.method }}</span>
            </div>
            <div class="detail-item">
              <span class="label">Status:</span>
              <span :class="['value', `status-${selectedTransaction.status}`]">{{ getStatusLabel(selectedTransaction.status) }}</span>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeTransactionModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>

    <!-- Schedule Payout Modal -->
    <div v-if="showSchedulePayoutModal" class="modal-overlay" @click.self="showSchedulePayoutModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Schedule Payout</h2>
          <button @click="showSchedulePayoutModal = false" class="close-btn">✕</button>
        </div>

        <form @submit.prevent="saveScheduledPayout" class="modal-body">
          <div class="form-group">
            <label>Operator</label>
            <input :value="payoutToSchedule?.operator_name" type="text" class="input" disabled />
          </div>

          <div class="form-group">
            <label>Amount</label>
            <input :value="formatCurrency(payoutToSchedule?.amount)" type="text" class="input" disabled />
          </div>

          <div class="form-group">
            <label>Schedule Date</label>
            <input v-model="schedulePayoutForm.date" type="date" class="input" required />
          </div>

          <div class="form-group">
            <label>Notes (optional)</label>
            <textarea v-model="schedulePayoutForm.notes" class="textarea" rows="3"></textarea>
          </div>

          <div class="form-actions">
            <button type="button" @click="showSchedulePayoutModal = false" class="btn btn-secondary">Cancel</button>
            <button type="submit" class="btn btn-primary">🕐 Schedule</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Schedule Export Modal -->
    <div v-if="showScheduleModal" class="modal-overlay" @click.self="showScheduleModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Schedule Export</h2>
          <button @click="showScheduleModal = false" class="close-btn">✕</button>
        </div>

        <form @submit.prevent="saveScheduledExport" class="modal-body">
          <div class="form-group">
            <label>Frequency</label>
            <select v-model="scheduleForm.frequency" class="input" required>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </div>

          <div class="form-group">
            <label>Export Format</label>
            <select v-model="scheduleForm.format" class="input" required>
              <option value="csv">CSV</option>
              <option value="excel">Excel</option>
              <option value="pdf">PDF</option>
            </select>
          </div>

          <div class="form-group">
            <label>Recipients (email addresses, comma-separated)</label>
            <textarea v-model="scheduleForm.recipients" class="textarea" placeholder="email1@example.com, email2@example.com" required></textarea>
          </div>

          <div class="form-actions">
            <button type="button" @click="showScheduleModal = false" class="btn btn-secondary">Cancel</button>
            <button type="submit" class="btn btn-primary">📅 Schedule</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const activeTab = ref('dashboard')

// Financial Data
const financialData = ref({
  totalRevenue: 125750,
  monthlyRevenue: 15230,
  pendingPayouts: 8950,
  pendingPayoutCount: 12,
  commissionCollected: 18865,
  commissionPercentage: 15,
  processingFees: 2105,
  avgTransaction: 245
})

// Transactions
const transactions = ref([
  {
    _id: '1',
    transaction_id: 'TXN001',
    date: new Date('2024-01-20'),
    tourist_name: 'John Doe',
    operator_name: 'Adventure Tours',
    amount: 500,
    commission: 75,
    commission_rate: 15,
    method: 'card',
    status: 'completed'
  },
  {
    _id: '2',
    transaction_id: 'TXN002',
    date: new Date('2024-01-19'),
    tourist_name: 'Jane Smith',
    operator_name: 'Mountain Guides',
    amount: 350,
    commission: 52.5,
    commission_rate: 15,
    method: 'upi',
    status: 'completed'
  },
  {
    _id: '3',
    transaction_id: 'TXN003',
    date: new Date('2024-01-18'),
    tourist_name: 'Mike Johnson',
    operator_name: 'Beach Tours',
    amount: 200,
    commission: 40,
    commission_rate: 20,
    method: 'wallet',
    status: 'pending'
  }
])

const transactionSearch = ref('')
const transactionFilters = ref({
  status: '',
  method: '',
  minAmount: null,
  maxAmount: null
})
const transactionPage = ref(1)
const itemsPerPage = ref(10)

const filteredTransactions = computed(() => {
  return transactions.value.filter(t => {
    const matchesSearch = !transactionSearch.value || 
      t.transaction_id.includes(transactionSearch.value) ||
      t.tourist_name.toLowerCase().includes(transactionSearch.value.toLowerCase()) ||
      t.operator_name.toLowerCase().includes(transactionSearch.value.toLowerCase())
    
    const matchesStatus = !transactionFilters.value.status || t.status === transactionFilters.value.status
    const matchesMethod = !transactionFilters.value.method || t.method === transactionFilters.value.method
    const matchesAmount = (!transactionFilters.value.minAmount || t.amount >= transactionFilters.value.minAmount) &&
      (!transactionFilters.value.maxAmount || t.amount <= transactionFilters.value.maxAmount)
    
    return matchesSearch && matchesStatus && matchesMethod && matchesAmount
  })
})

const totalTransactionPages = computed(() => {
  return Math.ceil(filteredTransactions.value.length / itemsPerPage.value)
})

const paginatedTransactions = computed(() => {
  const start = (transactionPage.value - 1) * itemsPerPage.value
  return filteredTransactions.value.slice(start, start + itemsPerPage.value)
})

const visibleTransactionPages = computed(() => {
  const total = totalTransactionPages.value
  const current = transactionPage.value
  const pages = []
  const maxVisible = 5
  
  if (total <= maxVisible) {
    for (let i = 1; i <= total; i++) pages.push(i)
  } else {
    const half = Math.floor(maxVisible / 2)
    let start = Math.max(1, current - half)
    let end = Math.min(total, start + maxVisible - 1)
    if (end - start < maxVisible - 1) start = Math.max(1, end - maxVisible + 1)
    for (let i = start; i <= end; i++) pages.push(i)
  }
  
  return pages
})

// Commissions
const commissionRules = ref({
  default: 15,
  tier1: 12,
  tier2: 18,
  holidayMultiplier: 1.2
})

const commissionSearch = ref('')

const commissions = ref([
  {
    _id: '1',
    operator_name: 'Adventure Tours',
    period: 'Jan 2024',
    earned: 2500,
    adjustments: -100,
    net: 2400,
    status: 'settled'
  },
  {
    _id: '2',
    operator_name: 'Mountain Guides',
    period: 'Jan 2024',
    earned: 1800,
    adjustments: 0,
    net: 1800,
    status: 'pending'
  },
  {
    _id: '3',
    operator_name: 'Beach Tours',
    period: 'Jan 2024',
    earned: 950,
    adjustments: -50,
    net: 900,
    status: 'settled'
  }
])

const filteredCommissions = computed(() => {
  return commissions.value.filter(c =>
    c.operator_name.toLowerCase().includes(commissionSearch.value.toLowerCase())
  )
})

// Payouts
const payoutThreshold = ref(500)

const payouts = ref([
  {
    _id: '1',
    operator_name: 'Adventure Tours',
    amount: 2400,
    daysPending: 3,
    bankName: 'ICICI Bank',
    accountLast4: '4521'
  },
  {
    _id: '2',
    operator_name: 'Mountain Guides',
    amount: 1800,
    daysPending: 5,
    bankName: 'HDFC Bank',
    accountLast4: '7834'
  },
  {
    _id: '3',
    operator_name: 'Beach Tours',
    amount: 900,
    daysPending: 1,
    bankName: 'Axis Bank',
    accountLast4: '2156'
  }
])

const pendingPayouts = computed(() => payouts.value.filter(p => p.amount > 0))

const payoutHistory = ref([
  {
    _id: '1',
    operator_name: 'City Walks',
    date: new Date('2024-01-15'),
    amount: 3200,
    status: 'completed',
    reference_id: 'PAY20240115001'
  },
  {
    _id: '2',
    operator_name: 'Heritage Tours',
    date: new Date('2024-01-12'),
    amount: 2100,
    status: 'completed',
    reference_id: 'PAY20240112001'
  }
])

const payoutHistoryFilter = ref({
  status: ''
})

const filteredPayoutHistory = computed(() => {
  return payoutHistory.value.filter(p =>
    !payoutHistoryFilter.value.status || p.status === payoutHistoryFilter.value.status
  )
})

// Reports
const generatedReports = ref([
  {
    _id: '1',
    name: 'Revenue Report - Jan 2024',
    generated_at: new Date('2024-01-20')
  },
  {
    _id: '2',
    name: 'Commission Breakdown - Jan 2024',
    generated_at: new Date('2024-01-19')
  }
])

// Export
const exportFormat = ref('csv')
const exportData = ref({
  transactions: true,
  commissions: true,
  payouts: true,
  summaries: true
})
const exportDateRange = ref({
  from: '2024-01-01',
  to: '2024-01-31'
})
const exportOptions = ref({
  includeCharts: false,
  compress: false,
  sendEmail: false
})
const exportEmail = ref('')
const exportSuccess = ref('')
const exportError = ref('')

const scheduledExports = ref([
  {
    _id: '1',
    frequency: 'Monthly',
    format: 'PDF',
    recipients: ['admin@example.com'],
    next_run: new Date('2024-02-01')
  }
])

// Modals
const showTransactionModal = ref(false)
const selectedTransaction = ref(null)
const showSchedulePayoutModal = ref(false)
const payoutToSchedule = ref(null)
const schedulePayoutForm = ref({
  date: '',
  notes: ''
})
const showScheduleModal = ref(false)
const scheduleForm = ref({
  frequency: 'monthly',
  format: 'csv',
  recipients: ''
})

// Methods
const formatCurrency = (amount) => {
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR'
  }).format(amount)
}

const formatDate = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString('en-IN')
}

const getPaymentMethodIcon = (method) => {
  const icons = {
    card: '💳',
    upi: '📱',
    wallet: '👛'
  }
  return icons[method] || '💳'
}

const getStatusLabel = (status) => {
  const labels = {
    completed: '✓ Completed',
    pending: '⏳ Pending',
    failed: '✗ Failed',
    processing: '⏳ Processing'
  }
  return labels[status] || status
}

const viewTransactionDetail = (transaction) => {
  selectedTransaction.value = transaction
  showTransactionModal.value = true
}

const closeTransactionModal = () => {
  showTransactionModal.value = false
  selectedTransaction.value = null
}

const refundTransaction = async (transaction) => {
  if (confirm(`Refund transaction ${transaction.transaction_id}?`)) {
    transaction.status = 'failed'
  }
}

const markDisputed = async (transaction) => {
  if (confirm(`Mark transaction ${transaction.transaction_id} as disputed?`)) {
    alert('Transaction marked as disputed. Support team will review.')
  }
}

const saveCommissionRules = async () => {
  alert('Commission rules saved successfully!')
}

const saveBulkPayoutSettings = async () => {
  alert(`Minimum payout threshold set to ${formatCurrency(payoutThreshold.value)}`)
}

const initiatePayoutAll = async () => {
  if (confirm(`Process payouts for ${pendingPayouts.value.length} operators?`)) {
    alert('Payout batch processing initiated!')
  }
}

const initiatePayout = async (payout) => {
  if (confirm(`Initiate payout of ${formatCurrency(payout.amount)} to ${payout.operator_name}?`)) {
    alert('Payout initiated successfully!')
  }
}

const schedulePayout = (payout) => {
  payoutToSchedule.value = payout
  schedulePayoutForm.value = { date: '', notes: '' }
  showSchedulePayoutModal.value = true
}

const saveScheduledPayout = async () => {
  alert(`Payout scheduled for ${schedulePayoutForm.value.date}`)
  showSchedulePayoutModal.value = false
}

const generateReport = async (type) => {
  const reportNames = {
    revenue: 'Revenue Report',
    commission: 'Commission Breakdown',
    operators: 'Operator Earnings',
    methods: 'Payment Methods Analysis',
    growth: 'Growth Metrics',
    cac: 'Customer Acquisition Cost'
  }
  
  generatedReports.value.unshift({
    _id: Date.now().toString(),
    name: `${reportNames[type]} - ${new Date().toLocaleDateString('en-IN')}`,
    generated_at: new Date()
  })
  
  alert(`${reportNames[type]} generated successfully!`)
}

const downloadReport = async (report) => {
  alert(`Downloading: ${report.name}`)
}

const deleteReport = (report) => {
  const index = generatedReports.value.findIndex(r => r._id === report._id)
  if (index > -1) {
    generatedReports.value.splice(index, 1)
  }
}

const exportFinancialData = async () => {
  exportError.value = ''
  exportSuccess.value = ''
  
  if (!exportData.value.transactions && !exportData.value.commissions && 
      !exportData.value.payouts && !exportData.value.summaries) {
    exportError.value = 'Please select at least one data type to export'
    return
  }
  
  if (exportOptions.value.sendEmail && !exportEmail.value) {
    exportError.value = 'Please provide an email address'
    return
  }
  
  exportSuccess.value = `Financial data exported as ${exportFormat.value.toUpperCase()} and ready for download!`
  resetExportForm()
  setTimeout(() => { exportSuccess.value = '' }, 3000)
}

const resetExportForm = () => {
  exportData.value = { transactions: true, commissions: true, payouts: true, summaries: true }
  exportEmail.value = ''
  exportOptions.value = { includeCharts: false, compress: false, sendEmail: false }
}

const saveScheduledExport = async () => {
  const recipients = scheduleForm.value.recipients.split(',').map(r => r.trim())
  scheduledExports.value.unshift({
    _id: Date.now().toString(),
    frequency: scheduleForm.value.frequency,
    format: scheduleForm.value.format,
    recipients,
    next_run: new Date()
  })
  
  alert('Export scheduled successfully!')
  showScheduleModal.value = false
  scheduleForm.value = { frequency: 'monthly', format: 'csv', recipients: '' }
}

const deleteScheduledExport = (scheduled) => {
  const index = scheduledExports.value.findIndex(s => s._id === scheduled._id)
  if (index > -1) {
    scheduledExports.value.splice(index, 1)
  }
}
</script>

<style scoped>
.admin-financial {
  width: 100%;
}

.page-header {
  margin-bottom: 2rem;
}

.page-header h1 {
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

/* Tabs */
.tabs {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 2rem;
  border-bottom: 2px solid #e2e8f0;
  overflow-x: auto;
  padding-bottom: 0;
}

.tab {
  padding: 1rem 1.5rem;
  border: none;
  background: none;
  color: #718096;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  border-bottom: 3px solid transparent;
  margin-bottom: -2px;
  white-space: nowrap;
}

.tab:hover {
  color: #667eea;
}

.tab.active {
  color: #667eea;
  border-bottom-color: #667eea;
}

.tab-content {
  animation: fadeIn 0.3s ease-in;
}

@keyframes fadeIn {
  from { opacity: 0; }
  to { opacity: 1; }
}

/* Dashboard Tab */
.metrics-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.metric-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  gap: 1.5rem;
  align-items: center;
  transition: all 0.2s;
}

.metric-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.1);
}

.metric-icon {
  font-size: 2.5rem;
  min-width: 60px;
}

.metric-content {
  flex: 1;
}

.metric-label {
  margin: 0;
  font-size: 0.85rem;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  font-weight: 600;
}

.metric-value {
  margin: 0.5rem 0 0.25rem 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: #1a202c;
}

.metric-subtitle {
  margin: 0;
  font-size: 0.85rem;
  color: #a0aec0;
}

.charts-section {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}

.chart-container {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
}

.chart-container h3 {
  margin: 0 0 1rem 0;
  color: #1a202c;
  font-size: 1.1rem;
}

.chart-placeholder {
  text-align: center;
  color: #718096;
  padding: 2rem 1rem;
}

.chart-bars {
  display: flex;
  align-items: flex-end;
  justify-content: space-around;
  gap: 0.5rem;
  margin-top: 1rem;
  height: 150px;
}

.chart-bar {
  width: 100%;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 4px;
  transition: all 0.2s;
}

.chart-bar:hover {
  opacity: 0.8;
}

.payment-breakdown {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-top: 1rem;
}

.payment-item {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.payment-label {
  min-width: 60px;
  font-weight: 600;
  color: #2d3748;
}

.payment-bar {
  height: 20px;
  background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
  border-radius: 10px;
  flex: 1;
}

.payment-value {
  min-width: 40px;
  text-align: right;
  font-weight: 600;
  color: #667eea;
}

/* Transactions Tab */
.transaction-controls,
.commission-search,
.payout-history-controls {
  display: flex;
  gap: 1rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 200px;
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
}

.filter-select,
.filter-input {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  background: white;
  cursor: pointer;
}

.filter-input {
  width: 150px;
}

.transactions-table {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow: hidden;
}

.table-header {
  display: grid;
  grid-template-columns: 80px 100px 120px 120px 80px 100px 80px 100px 80px;
  gap: 0;
  background: #f7fafc;
  padding: 0;
  border-bottom: 2px solid #e2e8f0;
  font-weight: 600;
  color: #2d3748;
}

.table-header .col {
  padding: 1rem;
  border-right: 1px solid #e2e8f0;
}

.table-header .col:last-child {
  border-right: none;
}

.table-row {
  display: grid;
  grid-template-columns: 80px 100px 120px 120px 80px 100px 80px 100px 80px;
  gap: 0;
  border-bottom: 1px solid #e2e8f0;
  align-items: center;
}

.table-row:hover {
  background: #f7fafc;
}

.col {
  padding: 1rem;
  border-right: 1px solid #e2e8f0;
  font-size: 0.9rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.col:last-child {
  border-right: none;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.status-completed {
  background: #dcfce7;
  color: #166534;
}

.status-pending {
  background: #fef3c7;
  color: #b45309;
}

.status-failed {
  background: #fee2e2;
  color: #991b1b;
}

.action-btn {
  padding: 0.3rem 0.6rem;
  border: none;
  background: none;
  cursor: pointer;
  font-size: 1rem;
  transition: all 0.2s;
  border-radius: 4px;
}

.action-btn:hover {
  background: rgba(102, 126, 234, 0.1);
}

.action-btn.view {
  color: #0284c7;
}

.action-btn.refund {
  color: #667eea;
}

.action-btn.dispute {
  color: #f59e0b;
}

.pagination {
  display: flex;
  justify-content: center;
  gap: 1rem;
  align-items: center;
  margin-top: 1.5rem;
  padding: 1rem;
}

.pagination-btn {
  padding: 0.5rem 1rem;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.pagination-btn:hover:not(:disabled) {
  border-color: #667eea;
  color: #667eea;
}

.pagination-btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.page-buttons {
  display: flex;
  gap: 0.5rem;
}

.page-btn {
  padding: 0.5rem 0.75rem;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
}

.page-btn:hover {
  border-color: #667eea;
}

.page-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: white;
}

/* Commissions Tab */
.commissions-container,
.payouts-container,
.reports-container,
.export-container {
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.section {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
}

.section h3 {
  margin: 0 0 1.5rem 0;
  color: #1a202c;
  font-size: 1.1rem;
  font-weight: 600;
}

.commission-rules {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.rule-card {
  padding: 1rem;
  background: #f7fafc;
  border-radius: 8px;
}

.rule-card label {
  display: block;
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: #2d3748;
}

.input-group {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.input {
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.9rem;
}

.unit {
  font-weight: 600;
  color: #667eea;
}

.rule-note {
  margin: 0.5rem 0 0 0;
  font-size: 0.8rem;
  color: #718096;
}

.commissions-list,
.payouts-grid,
.payout-history-list {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.commission-card,
.payout-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.commission-card:hover,
.payout-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.commission-header,
.payout-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.commission-header h4,
.payout-header h4 {
  margin: 0;
  color: #1a202c;
}

.commission-total,
.payout-amount {
  font-size: 1.5rem;
  font-weight: 700;
  color: #667eea;
}

.commission-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.detail-item {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}

.detail-item .label {
  font-weight: 600;
  color: #718096;
}

.detail-item .value {
  color: #1a202c;
  font-weight: 500;
}

.commission-note,
.payout-details p {
  margin: 0;
  font-size: 0.85rem;
  color: #718096;
}

.payout-details {
  margin-bottom: 1rem;
}

.payout-details p {
  margin: 0.5rem 0;
  display: flex;
  justify-content: space-between;
}

.payout-actions {
  display: flex;
  gap: 0.5rem;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.95rem;
}

.btn-primary {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

.btn-secondary {
  background: #e2e8f0;
  color: #2d3748;
}

.btn-secondary:hover {
  background: #cbd5e0;
}

.btn-small {
  padding: 0.5rem 1rem;
  font-size: 0.85rem;
}

.btn-danger {
  background: #fee2e2;
  color: #991b1b;
}

.btn-danger:hover {
  background: #fecaca;
}

.payout-history-list {
  grid-template-columns: 1fr;
}

.history-item {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  transition: all 0.2s;
}

.history-item:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.history-content {
  flex: 1;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.history-main h4 {
  margin: 0;
  color: #1a202c;
}

.history-date {
  font-size: 0.85rem;
  color: #718096;
  display: block;
  margin-top: 0.25rem;
}

.history-details {
  display: flex;
  gap: 2rem;
  align-items: center;
}

.amount {
  font-size: 1.25rem;
  font-weight: 700;
  color: #667eea;
}

.status {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.reference {
  font-size: 0.85rem;
  color: #a0aec0;
  margin-top: 0.5rem;
}

/* Reports Tab */
.report-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.report-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
  transition: all 0.2s;
}

.report-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.report-icon {
  font-size: 2.5rem;
  margin-bottom: 0.5rem;
}

.report-card h4 {
  margin: 0.5rem 0;
  color: #1a202c;
}

.report-card p {
  margin: 0.75rem 0;
  font-size: 0.9rem;
  color: #718096;
}

.generated-reports {
  margin-top: 2rem;
}

.generated-reports h4 {
  margin: 0 0 1rem 0;
  color: #1a202c;
}

.reports-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.report-item {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.report-info {
  flex: 1;
}

.report-name {
  margin: 0;
  font-weight: 600;
  color: #1a202c;
}

.report-date {
  margin: 0.25rem 0 0 0;
  font-size: 0.85rem;
  color: #718096;
}

.report-actions {
  display: flex;
  gap: 0.5rem;
}

/* Export Tab */
.export-options {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
  margin-bottom: 1.5rem;
}

.option-card {
  background: #f7fafc;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
}

.option-card h4 {
  margin: 0 0 1rem 0;
  color: #1a202c;
}

.format-buttons {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.format-btn {
  flex: 1;
  min-width: 80px;
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-weight: 600;
}

.format-btn:hover {
  border-color: #667eea;
}

.format-btn.active {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: white;
}

.checkbox-group {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.checkbox-group label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.checkbox-group input[type="checkbox"] {
  cursor: pointer;
}

.date-inputs {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.date-inputs .input {
  flex: 1;
}

.export-email {
  margin-bottom: 1.5rem;
}

.export-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-bottom: 1.5rem;
}

.export-schedule {
  margin-top: 2rem;
}

.scheduled-list {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.scheduled-item {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.scheduled-name {
  margin: 0;
  font-weight: 600;
  color: #1a202c;
}

.scheduled-recipients,
.scheduled-next {
  margin: 0.25rem 0;
  font-size: 0.9rem;
  color: #718096;
}

/* Modal */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
  padding: 2rem;
}

.modal-content {
  background: white;
  border-radius: 12px;
  max-width: 500px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem;
  border-bottom: 1px solid #e2e8f0;
}

.modal-header h2 {
  margin: 0;
  font-size: 1.5rem;
  color: #1a202c;
}

.close-btn {
  background: none;
  border: none;
  font-size: 1.5rem;
  cursor: pointer;
  color: #718096;
}

.close-btn:hover {
  color: #2d3748;
}

.modal-body {
  padding: 1.5rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1.5rem;
}

.form-group label {
  font-weight: 600;
  color: #2d3748;
}

.textarea {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-family: inherit;
  font-size: 0.95rem;
  resize: vertical;
}

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
}

.modal-footer {
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  background: #f7fafc;
}

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  color: #718096;
}

.success-message {
  padding: 1rem;
  background: #dcfce7;
  border-left: 3px solid #22c55e;
  color: #166534;
  border-radius: 6px;
  margin-bottom: 1rem;
}

.error-message {
  padding: 1rem;
  background: #fee2e2;
  border-left: 3px solid #ef4444;
  color: #991b1b;
  border-radius: 6px;
  margin-bottom: 1rem;
}

/* Responsive */
@media (max-width: 768px) {
  .tabs {
    flex-direction: column;
    border-bottom: none;
  }

  .tab {
    border-bottom: none;
    border-left: 3px solid transparent;
    padding-left: 1rem;
  }

  .tab.active {
    border-left-color: #667eea;
    border-bottom: none;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .charts-section {
    grid-template-columns: 1fr;
  }

  .transaction-controls {
    flex-direction: column;
  }

  .filter-input {
    width: 100%;
  }

  .table-header,
  .table-row {
    grid-template-columns: repeat(4, 1fr);
  }

  .col {
    padding: 0.75rem 0.5rem;
  }

  .commissions-list,
  .payouts-grid,
  .report-grid {
    grid-template-columns: 1fr;
  }

  .commission-rules {
    grid-template-columns: 1fr;
  }

  .export-options {
    grid-template-columns: 1fr;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }

  .history-content {
    flex-direction: column;
    align-items: flex-start;
  }

  .history-details {
    width: 100%;
    flex-direction: column;
    gap: 0.5rem;
  }
}
</style>
