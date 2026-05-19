<template>
  <div class="admin-reports">
    <div class="page-header">
      <h1>Reports & Analytics</h1>
      <p class="subtitle">Build, manage, and schedule comprehensive reports</p>
    </div>

    <div v-if="loading" class="status-message">Loading reports data...</div>
    <div v-else-if="loadError" class="error-message">{{ loadError }}</div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        @click="activeTab = 'builder'"
        :class="['tab', { active: activeTab === 'builder' }]"
      >
        🛠️ Report Builder
      </button>
      <button
        @click="activeTab = 'listing'"
        :class="['tab', { active: activeTab === 'listing' }]"
      >
        📋 Reports
      </button>
      <button
        @click="activeTab = 'scheduling'"
        :class="['tab', { active: activeTab === 'scheduling' }]"
      >
        🕐 Scheduling
      </button>
      <button
        @click="activeTab = 'formats'"
        :class="['tab', { active: activeTab === 'formats' }]"
      >
        📊 Export Formats
      </button>
      <button
        @click="activeTab = 'dashboards'"
        :class="['tab', { active: activeTab === 'dashboards' }]"
      >
        📈 Dashboards
      </button>
    </div>

    <!-- Report Builder Tab -->
    <div v-if="activeTab === 'builder'" class="tab-content">
      <div class="builder-section">
        <h3>Report Builder</h3>

        <div class="builder-grid">
          <!-- Pre-built Reports -->
          <div class="builder-card">
            <h4>📌 Pre-built Reports</h4>
            <p class="card-description">Start with a template</p>

            <div class="template-list">
              <button
                v-for="template in prebuiltTemplates"
                :key="template.id"
                @click="selectTemplate(template)"
                :class="['template-btn', { selected: selectedTemplate?.id === template.id }]"
              >
                <span class="template-icon">{{ template.icon }}</span>
                <span class="template-name">{{ template.name }}</span>
              </button>
            </div>
          </div>

          <!-- Custom Report Builder -->
          <div class="builder-card">
            <h4>🎨 Custom Report</h4>
            <p class="card-description">Create from scratch</p>

            <div class="form-group">
              <label>Report Name</label>
              <input v-model="customReport.name" type="text" class="input" placeholder="e.g., Q1 2026 Performance" />
            </div>

            <div class="form-group">
              <label>Report Type</label>
              <select v-model="customReport.type" class="input">
                <option value="revenue">Revenue Analysis</option>
                <option value="operators">Operator Performance</option>
                <option value="bookings">Booking Trends</option>
                <option value="customers">Customer Acquisition</option>
                <option value="satisfaction">Satisfaction Scores</option>
              </select>
            </div>

            <div class="form-group">
              <label>Date Range</label>
              <div class="date-range">
                <input v-model="customReport.dateFrom" type="date" class="input" />
                <span>to</span>
                <input v-model="customReport.dateTo" type="date" class="input" />
              </div>
            </div>

            <div class="form-group">
              <label>Metrics</label>
              <div class="checkbox-group">
                <label>
                  <input v-model="customReport.metrics" type="checkbox" value="revenue" />
                  <span>Revenue</span>
                </label>
                <label>
                  <input v-model="customReport.metrics" type="checkbox" value="bookings" />
                  <span>Bookings</span>
                </label>
                <label>
                  <input v-model="customReport.metrics" type="checkbox" value="users" />
                  <span>Users</span>
                </label>
                <label>
                  <input v-model="customReport.metrics" type="checkbox" value="satisfaction" />
                  <span>Satisfaction</span>
                </label>
              </div>
            </div>

            <button @click="generateCustomReport" class="btn btn-primary">✨ Generate Report</button>
          </div>

          <!-- Quick Filters -->
          <div class="builder-card">
            <h4>⚡ Quick Filters</h4>
            <p class="card-description">Pre-set filters for quick reports</p>

            <div class="quick-filter-list">
              <button @click="applyQuickFilter('today')" class="quick-filter-btn">
                📅 Today
              </button>
              <button @click="applyQuickFilter('week')" class="quick-filter-btn">
                📆 This Week
              </button>
              <button @click="applyQuickFilter('month')" class="quick-filter-btn">
                📊 This Month
              </button>
              <button @click="applyQuickFilter('quarter')" class="quick-filter-btn">
                📈 This Quarter
              </button>
              <button @click="applyQuickFilter('year')" class="quick-filter-btn">
                📉 This Year
              </button>
              <button @click="applyQuickFilter('custom')" class="quick-filter-btn">
                🔧 Custom
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Reports Listing Tab -->
    <div v-else-if="activeTab === 'listing'" class="tab-content">
      <div class="listing-controls">
        <input
          v-model="reportSearch"
          type="text"
          placeholder="Search by report name..."
          class="search-input"
        />

        <select v-model="reportFilters.type" class="filter-select">
          <option value="">All Types</option>
          <option value="revenue">Revenue Analysis</option>
          <option value="operators">Operator Performance</option>
          <option value="bookings">Booking Trends</option>
          <option value="customers">Customer Acquisition</option>
        </select>

        <select v-model="reportFilters.status" class="filter-select">
          <option value="">All Status</option>
          <option value="completed">✓ Completed</option>
          <option value="processing">⏳ Processing</option>
          <option value="draft">📝 Draft</option>
        </select>

        <button @click="showNewReportModal = true" class="btn btn-primary">➕ New Report</button>
      </div>

      <div v-if="filteredReports.length === 0" class="empty-state">
        <p>📭 No reports found</p>
      </div>

      <div v-else class="reports-container">
        <div
          v-for="report in filteredReports"
          :key="report._id"
          :class="['report-card', `status-${report.status}`]"
        >
          <div class="report-header">
            <div class="report-info">
              <h4>{{ report.name }}</h4>
              <p class="report-type">{{ report.type }} • {{ formatDate(report.created_at) }}</p>
            </div>
            <span :class="['status-badge', `badge-${report.status}`]">
              {{ getStatusLabel(report.status) }}
            </span>
          </div>

          <div class="report-details">
            <p><strong>Size:</strong> {{ report.size }}</p>
            <p><strong>Generated by:</strong> {{ report.generated_by }}</p>
            <p><strong>Last updated:</strong> {{ formatDateTime(report.updated_at) }}</p>
          </div>

          <div class="report-actions">
            <button @click="viewReport(report)" class="btn btn-small">👁️ View</button>
            <button @click="downloadReport(report)" class="btn btn-small">📥 Download</button>
            <button @click="duplicateReport(report)" class="btn btn-small btn-secondary">📋 Duplicate</button>
            <button @click="deleteReport(report)" class="btn btn-small btn-danger">🗑️</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Scheduling Tab -->
    <div v-else-if="activeTab === 'scheduling'" class="tab-content">
      <div class="scheduling-section">
        <h3>Scheduled Reports</h3>

        <div class="schedule-controls">
          <button @click="showScheduleModal = true" class="btn btn-primary">➕ Schedule Report</button>
        </div>

        <div v-if="scheduledReports.length === 0" class="empty-state">
          <p>📭 No scheduled reports</p>
        </div>

        <div v-else class="scheduled-grid">
          <div v-for="schedule in scheduledReports" :key="schedule._id" class="schedule-card">
            <div class="schedule-header">
              <h4>{{ schedule.report_name }}</h4>
              <span :class="['status-badge', `badge-${schedule.status}`]">
                {{ schedule.status === 'active' ? '🟢' : '⚫' }} {{ schedule.status }}
              </span>
            </div>

            <div class="schedule-details">
              <p><strong>Frequency:</strong> {{ schedule.frequency }}</p>
              <p><strong>Recipients:</strong> {{ schedule.recipients.join(', ') }}</p>
              <p><strong>Format:</strong> {{ schedule.format }}</p>
              <p><strong>Next Run:</strong> {{ formatDateTime(schedule.next_run) }}</p>
            </div>

            <div class="schedule-actions">
              <button @click="editSchedule(schedule)" class="btn btn-small btn-secondary">✏️ Edit</button>
              <button v-if="schedule.status === 'active'" @click="pauseSchedule(schedule)" class="btn btn-small">⏸️ Pause</button>
              <button v-else @click="resumeSchedule(schedule)" class="btn btn-small">▶️ Resume</button>
              <button @click="deleteSchedule(schedule)" class="btn btn-small btn-danger">🗑️ Delete</button>
            </div>

            <div class="schedule-info">
              <p class="runs-count">Runs: <strong>{{ schedule.runs_count }}</strong></p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Export Formats Tab -->
    <div v-else-if="activeTab === 'formats'" class="tab-content">
      <div class="formats-section">
        <h3>Export Formats & Options</h3>

        <div class="formats-grid">
          <!-- PDF Export -->
          <div class="format-card">
            <div class="format-icon">📋</div>
            <h4>PDF Report</h4>
            <p class="format-description">Professional formatted PDF with charts and styling</p>

            <div class="format-options">
              <label>
                <input v-model="formatSettings.pdf.includeCharts" type="checkbox" />
                <span>Include Charts</span>
              </label>
              <label>
                <input v-model="formatSettings.pdf.includeImages" type="checkbox" />
                <span>Include Images</span>
              </label>
              <label>
                <input v-model="formatSettings.pdf.includeWatermark" type="checkbox" />
                <span>Add Watermark</span>
              </label>
              <label>
                <input v-model="formatSettings.pdf.includePageNumbers" type="checkbox" />
                <span>Page Numbers</span>
              </label>
            </div>

            <button @click="previewFormat('pdf')" class="btn btn-secondary btn-small">Preview</button>
          </div>

          <!-- Excel Export -->
          <div class="format-card">
            <div class="format-icon">📊</div>
            <h4>Excel Report</h4>
            <p class="format-description">Spreadsheet format with multiple sheets and formulas</p>

            <div class="format-options">
              <label>
                <input v-model="formatSettings.excel.includeSummary" type="checkbox" />
                <span>Summary Sheet</span>
              </label>
              <label>
                <input v-model="formatSettings.excel.includeCharts" type="checkbox" />
                <span>Include Charts</span>
              </label>
              <label>
                <input v-model="formatSettings.excel.freezeHeaders" type="checkbox" />
                <span>Freeze Headers</span>
              </label>
              <label>
                <input v-model="formatSettings.excel.autoFilter" type="checkbox" />
                <span>Auto Filter</span>
              </label>
            </div>

            <button @click="previewFormat('excel')" class="btn btn-secondary btn-small">Preview</button>
          </div>

          <!-- CSV Export -->
          <div class="format-card">
            <div class="format-icon">📄</div>
            <h4>CSV Report</h4>
            <p class="format-description">Simple comma-separated format for data analysis</p>

            <div class="format-options">
              <label>
                <input v-model="formatSettings.csv.includeHeaders" type="checkbox" />
                <span>Include Headers</span>
              </label>
              <label>
                <input v-model="formatSettings.csv.delimiter" type="radio" value="," />
                <span>Comma Delimiter</span>
              </label>
              <label>
                <input v-model="formatSettings.csv.delimiter" type="radio" value=";" />
                <span>Semicolon Delimiter</span>
              </label>
              <label>
                <input v-model="formatSettings.csv.includeIndexes" type="checkbox" />
                <span>Include Row Indexes</span>
              </label>
            </div>

            <button @click="previewFormat('csv')" class="btn btn-secondary btn-small">Preview</button>
          </div>

          <!-- JSON Export -->
          <div class="format-card">
            <div class="format-icon">🔗</div>
            <h4>JSON Report</h4>
            <p class="format-description">Structured JSON format for API integration</p>

            <div class="format-options">
              <label>
                <input v-model="formatSettings.json.prettyPrint" type="checkbox" />
                <span>Pretty Print</span>
              </label>
              <label>
                <input v-model="formatSettings.json.includeMetadata" type="checkbox" />
                <span>Include Metadata</span>
              </label>
              <label>
                <input v-model="formatSettings.json.compressFile" type="checkbox" />
                <span>Compress (.gz)</span>
              </label>
              <label>
                <input v-model="formatSettings.json.includeSchema" type="checkbox" />
                <span>Include Schema</span>
              </label>
            </div>

            <button @click="previewFormat('json')" class="btn btn-secondary btn-small">Preview</button>
          </div>

          <!-- HTML Export -->
          <div class="format-card">
            <div class="format-icon">🌐</div>
            <h4>HTML Report</h4>
            <p class="format-description">Interactive web format with responsive design</p>

            <div class="format-options">
              <label>
                <input v-model="formatSettings.html.includeInteractive" type="checkbox" />
                <span>Interactive Charts</span>
              </label>
              <label>
                <input v-model="formatSettings.html.includeStyles" type="checkbox" />
                <span>Custom Styling</span>
              </label>
              <label>
                <input v-model="formatSettings.html.responsive" type="checkbox" />
                <span>Responsive Design</span>
              </label>
              <label>
                <input v-model="formatSettings.html.darkMode" type="checkbox" />
                <span>Dark Mode Option</span>
              </label>
            </div>

            <button @click="previewFormat('html')" class="btn btn-secondary btn-small">Preview</button>
          </div>

          <!-- Email Delivery -->
          <div class="format-card">
            <div class="format-icon">📧</div>
            <h4>Email Delivery</h4>
            <p class="format-description">Send reports directly via email</p>

            <div class="format-options">
              <label>
                <input v-model="formatSettings.email.attachReport" type="checkbox" />
                <span>Attach Report</span>
              </label>
              <label>
                <input v-model="formatSettings.email.includeLink" type="checkbox" />
                <span>Include Download Link</span>
              </label>
              <label>
                <input v-model="formatSettings.email.includeSummary" type="checkbox" />
                <span>Email Summary</span>
              </label>
              <label>
                <input v-model="formatSettings.email.sendZipped" type="checkbox" />
                <span>Compress Attachment</span>
              </label>
            </div>

            <button @click="configureEmail" class="btn btn-secondary btn-small">⚙️ Configure</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Dashboards Tab -->
    <div v-else-if="activeTab === 'dashboards'" class="tab-content">
      <div class="dashboards-section">
        <h3>Custom Dashboards</h3>

        <div class="dashboards-controls">
          <button @click="showDashboardModal = true" class="btn btn-primary">➕ New Dashboard</button>
        </div>

        <div v-if="dashboards.length === 0" class="empty-state">
          <p>📭 No custom dashboards</p>
        </div>

        <div v-else class="dashboards-grid">
          <div
            v-for="dashboard in dashboards"
            :key="dashboard._id"
            class="dashboard-card"
          >
            <div class="dashboard-preview">
              <div class="preview-grid">
                <div v-for="(widget, index) in dashboard.widgets.slice(0, 4)" :key="index" class="preview-widget">
                  <p class="widget-name">{{ widget.name }}</p>
                </div>
              </div>
            </div>

            <div class="dashboard-info">
              <h4>{{ dashboard.name }}</h4>
              <p class="dashboard-meta">{{ dashboard.widgets.length }} widgets • Created {{ formatDate(dashboard.created_at) }}</p>
            </div>

            <div class="dashboard-actions">
              <button @click="editDashboard(dashboard)" class="btn btn-small btn-secondary">✏️ Edit</button>
              <button @click="viewDashboard(dashboard)" class="btn btn-small">👁️ View</button>
              <button @click="shareDashboard(dashboard)" class="btn btn-small">🔗 Share</button>
              <button @click="deleteDashboard(dashboard)" class="btn btn-small btn-danger">🗑️</button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- New Report Modal -->
    <div v-if="showNewReportModal" class="modal-overlay" @click.self="showNewReportModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Create New Report</h2>
          <button @click="showNewReportModal = false" class="close-btn">✕</button>
        </div>

        <form @submit.prevent="saveNewReport" class="modal-body">
          <div class="form-group">
            <label>Report Name</label>
            <input v-model="newReportForm.name" type="text" class="input" required />
          </div>

          <div class="form-group">
            <label>Report Type</label>
            <select v-model="newReportForm.type" class="input" required>
              <option value="">Select type...</option>
              <option value="revenue">Revenue Analysis</option>
              <option value="operators">Operator Performance</option>
              <option value="bookings">Booking Trends</option>
              <option value="customers">Customer Acquisition</option>
            </select>
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="newReportForm.description" class="textarea" rows="3"></textarea>
          </div>

          <div class="form-actions">
            <button type="button" @click="showNewReportModal = false" class="btn btn-secondary">Cancel</button>
            <button type="submit" class="btn btn-primary">Create Report</button>
          </div>
        </form>
      </div>
    </div>

    <!-- Schedule Report Modal -->
    <div v-if="showScheduleModal" class="modal-overlay" @click.self="showScheduleModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Schedule Report Delivery</h2>
          <button @click="showScheduleModal = false" class="close-btn">✕</button>
        </div>

        <form @submit.prevent="saveSchedule" class="modal-body">
          <div class="form-group">
            <label>Select Report</label>
            <select v-model="scheduleForm.report_id" class="input" required>
              <option value="">Choose report...</option>
              <option v-for="report in reports" :key="report._id" :value="report._id">
                {{ report.name }}
              </option>
            </select>
          </div>

          <div class="form-group">
            <label>Frequency</label>
            <select v-model="scheduleForm.frequency" class="input" required>
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
              <option value="quarterly">Quarterly</option>
            </select>
          </div>

          <div class="form-group">
            <label>Recipients (comma-separated emails)</label>
            <textarea v-model="scheduleForm.recipients" class="textarea" rows="3" required></textarea>
          </div>

          <div class="form-group">
            <label>Format</label>
            <select v-model="scheduleForm.format" class="input" required>
              <option value="pdf">PDF</option>
              <option value="excel">Excel</option>
              <option value="csv">CSV</option>
              <option value="json">JSON</option>
            </select>
          </div>

          <div class="form-actions">
            <button type="button" @click="showScheduleModal = false" class="btn btn-secondary">Cancel</button>
            <button type="submit" class="btn btn-primary">Schedule</button>
          </div>
        </form>
      </div>
    </div>

    <!-- New Dashboard Modal -->
    <div v-if="showDashboardModal" class="modal-overlay" @click.self="showDashboardModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Create New Dashboard</h2>
          <button @click="showDashboardModal = false" class="close-btn">✕</button>
        </div>

        <form @submit.prevent="saveDashboard" class="modal-body">
          <div class="form-group">
            <label>Dashboard Name</label>
            <input v-model="dashboardForm.name" type="text" class="input" required />
          </div>

          <div class="form-group">
            <label>Description</label>
            <textarea v-model="dashboardForm.description" class="textarea" rows="3"></textarea>
          </div>

          <div class="form-group">
            <label>Select Widgets</label>
            <div class="checkbox-group">
              <label>
                <input v-model="dashboardForm.widgets" type="checkbox" value="revenue" />
                <span>Revenue Chart</span>
              </label>
              <label>
                <input v-model="dashboardForm.widgets" type="checkbox" value="bookings" />
                <span>Bookings Graph</span>
              </label>
              <label>
                <input v-model="dashboardForm.widgets" type="checkbox" value="operators" />
                <span>Top Operators</span>
              </label>
              <label>
                <input v-model="dashboardForm.widgets" type="checkbox" value="satisfaction" />
                <span>Satisfaction Scores</span>
              </label>
              <label>
                <input v-model="dashboardForm.widgets" type="checkbox" value="metrics" />
                <span>Key Metrics</span>
              </label>
            </div>
          </div>

          <div class="form-actions">
            <button type="button" @click="showDashboardModal = false" class="btn btn-secondary">Cancel</button>
            <button type="submit" class="btn btn-primary">Create Dashboard</button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'

const activeTab = ref('builder')
const loading = ref(false)
const loadError = ref('')

// Report Builder
const prebuiltTemplates = ref([
  { id: 1, name: 'Revenue Analysis', icon: '💰' },
  { id: 2, name: 'Operator Performance', icon: '🚀' },
  { id: 3, name: 'Booking Trends', icon: '📈' },
  { id: 4, name: 'Customer Satisfaction', icon: '⭐' },
  { id: 5, name: 'Payment Summary', icon: '💳' },
  { id: 6, name: 'Quarterly Report', icon: '📊' },
  { id: 7, name: 'Year-end Review', icon: '🏆' },
  { id: 8, name: 'Commission Report', icon: '🎯' }
])

const selectedTemplate = ref(null)
const customReport = ref({
  name: '',
  type: 'revenue',
  dateFrom: '2026-02-01',
  dateTo: '2026-02-06',
  metrics: ['revenue', 'bookings']
})

// Reports Listing
const reports = ref([
  {
    _id: '1',
    name: 'February Revenue Report',
    type: 'revenue',
    status: 'completed',
    size: '2.4 MB',
    generated_by: 'Admin User',
    created_at: new Date('2026-02-05'),
    updated_at: new Date('2026-02-06T10:30:00')
  },
  {
    _id: '2',
    name: 'Operator Performance - Feb 2026',
    type: 'operators',
    status: 'completed',
    size: '1.8 MB',
    generated_by: 'System',
    created_at: new Date('2026-02-04'),
    updated_at: new Date('2026-02-05T15:20:00')
  },
  {
    _id: '3',
    name: 'Q4 2025 Annual Review',
    type: 'revenue',
    status: 'completed',
    size: '5.2 MB',
    generated_by: 'Admin User',
    created_at: new Date('2026-01-15'),
    updated_at: new Date('2026-01-20T09:15:00')
  }
])

const reportSearch = ref('')
const reportFilters = ref({
  type: '',
  status: ''
})

const filteredReports = computed(() => {
  return reports.value.filter(report => {
    const matchesSearch = !reportSearch.value || 
      report.name.toLowerCase().includes(reportSearch.value.toLowerCase())
    const matchesType = !reportFilters.value.type || report.type === reportFilters.value.type
    const matchesStatus = !reportFilters.value.status || report.status === reportFilters.value.status
    
    return matchesSearch && matchesType && matchesStatus
  })
})

// Scheduled Reports
const scheduledReports = ref([
  {
    _id: '1',
    report_name: 'Monthly Revenue Report',
    frequency: 'Monthly',
    recipients: ['admin@tourapp.com', 'finance@tourapp.com'],
    format: 'PDF',
    status: 'active',
    next_run: new Date('2026-03-06'),
    runs_count: 5
  },
  {
    _id: '2',
    report_name: 'Weekly Performance Summary',
    frequency: 'Weekly',
    recipients: ['managers@tourapp.com'],
    format: 'Excel',
    status: 'active',
    next_run: new Date('2026-02-13'),
    runs_count: 8
  }
])

// Format Settings
const formatSettings = ref({
  pdf: {
    includeCharts: true,
    includeImages: true,
    includeWatermark: false,
    includePageNumbers: true
  },
  excel: {
    includeSummary: true,
    includeCharts: true,
    freezeHeaders: true,
    autoFilter: true
  },
  csv: {
    includeHeaders: true,
    delimiter: ',',
    includeIndexes: false
  },
  json: {
    prettyPrint: true,
    includeMetadata: true,
    compressFile: false,
    includeSchema: true
  },
  html: {
    includeInteractive: true,
    includeStyles: true,
    responsive: true,
    darkMode: true
  },
  email: {
    attachReport: true,
    includeLink: true,
    includeSummary: true,
    sendZipped: false
  }
})

// Dashboards
const dashboards = ref([
  {
    _id: '1',
    name: 'Executive Dashboard',
    widgets: [
      { name: 'Revenue Chart' },
      { name: 'Bookings Trend' },
      { name: 'Top Operators' },
      { name: 'KPIs' }
    ],
    created_at: new Date('2026-02-01'),
    shared_with: []
  },
  {
    _id: '2',
    name: 'Operations Dashboard',
    widgets: [
      { name: 'Booking Status' },
      { name: 'Active Users' },
      { name: 'Performance Metrics' }
    ],
    created_at: new Date('2026-02-03'),
    shared_with: ['team@tourapp.com']
  }
])

// Modals & Forms
const showNewReportModal = ref(false)
const showScheduleModal = ref(false)
const showDashboardModal = ref(false)

const newReportForm = ref({
  name: '',
  type: '',
  description: ''
})

const scheduleForm = ref({
  report_id: '',
  frequency: 'monthly',
  recipients: '',
  format: 'pdf'
})

const dashboardForm = ref({
  name: '',
  description: '',
  widgets: []
})

const getAdminConfig = () => {
  const token = localStorage.getItem('adminToken')
  if (!token) {
    throw new Error('Admin token not found. Please login again.')
  }
  return { headers: { Authorization: `Bearer ${token}` } }
}

const loadReportsSummary = async () => {
  loading.value = true
  loadError.value = ''

  try {
    const token = localStorage.getItem('adminToken')
    if (!token) {
      loadError.value = 'Admin token not found. Please login again.'
      return
    }

    const response = await api.get('/admin/reports/summary', {
      headers: { Authorization: `Bearer ${token}` }
    })

    const data = response.data || {}

    if (Array.isArray(data.prebuiltTemplates)) {
      prebuiltTemplates.value = data.prebuiltTemplates
    }

    if (Array.isArray(data.reports)) {
      reports.value = data.reports
    }

    if (Array.isArray(data.scheduledReports)) {
      scheduledReports.value = data.scheduledReports
    }

    if (Array.isArray(data.dashboards)) {
      dashboards.value = data.dashboards
    }
  } catch (error) {
    console.error('Failed to load reports summary:', error)
    loadError.value = error.response?.data?.detail || 'Failed to load reports data'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadReportsSummary()
})

// Methods
const formatDate = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString('en-IN')
}

const formatDateTime = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleString('en-IN')
}

const getStatusLabel = (status) => {
  const labels = {
    completed: '✓ Completed',
    processing: '⏳ Processing',
    draft: '📝 Draft'
  }
  return labels[status] || status
}

const selectTemplate = (template) => {
  selectedTemplate.value = template
  alert(`Selected template: ${template.name}`)
}

const generateCustomReport = async () => {
  if (!customReport.value.name) {
    alert('Please enter a report name')
    return
  }

  try {
    await api.post('/admin/reports', {
      name: customReport.value.name,
      type: customReport.value.type,
      status: 'completed',
      size: '1.0 MB',
      description: `Date range ${customReport.value.dateFrom || 'N/A'} to ${customReport.value.dateTo || 'N/A'}`
    }, getAdminConfig())

    await loadReportsSummary()
    alert(`Report "${customReport.value.name}" generated successfully!`)
    customReport.value = { name: '', type: 'revenue', dateFrom: '', dateTo: '', metrics: [] }
  } catch (error) {
    alert(error.response?.data?.detail || error.message || 'Failed to generate report')
  }
}

const applyQuickFilter = (filter) => {
  alert(`Applied quick filter: ${filter}`)
}

const viewReport = (report) => {
  alert(`Viewing report: ${report.name}`)
}

const downloadReport = (report) => {
  alert(`Downloading report: ${report.name}`)
}

const duplicateReport = (report) => {
  saveNewReportFromExisting(report)
}

const deleteReport = async (report) => {
  if (confirm(`Delete report "${report.name}"?`)) {
    try {
      await api.delete(`/admin/reports/${report._id}`, getAdminConfig())
      await loadReportsSummary()
      alert('Report deleted')
    } catch (error) {
      alert(error.response?.data?.detail || error.message || 'Failed to delete report')
    }
  }
}

const saveNewReportFromExisting = async (report) => {
  try {
    await api.post('/admin/reports', {
      name: `${report.name} (Copy)`,
      type: report.type,
      status: 'draft',
      size: report.size || '0 MB',
      description: 'Duplicated report draft'
    }, getAdminConfig())
    await loadReportsSummary()
    alert(`Report duplicated: ${report.name} (Copy)`)
  } catch (error) {
    alert(error.response?.data?.detail || error.message || 'Failed to duplicate report')
  }
}

const saveNewReport = () => {
  if (!newReportForm.value.name || !newReportForm.value.type) {
    alert('Please fill in all required fields')
    return
  }

  api.post('/admin/reports', {
    name: newReportForm.value.name,
    type: newReportForm.value.type,
    status: 'draft',
    size: '0 MB',
    description: newReportForm.value.description
  }, getAdminConfig()).then(async () => {
    await loadReportsSummary()
    alert(`Report "${newReportForm.value.name}" created as draft`)
    showNewReportModal.value = false
    newReportForm.value = { name: '', type: '', description: '' }
  }).catch((error) => {
    alert(error.response?.data?.detail || error.message || 'Failed to create report')
  })
}

const editSchedule = (schedule) => {
  alert(`Editing schedule: ${schedule.report_name}`)
}

const pauseSchedule = async (schedule) => {
  try {
    await api.patch(`/admin/reports/schedules/${schedule._id}`, {
      status: 'paused'
    }, getAdminConfig())
    await loadReportsSummary()
    alert(`Schedule paused: ${schedule.report_name}`)
  } catch (error) {
    alert(error.response?.data?.detail || error.message || 'Failed to pause schedule')
  }
}

const resumeSchedule = async (schedule) => {
  try {
    await api.patch(`/admin/reports/schedules/${schedule._id}`, {
      status: 'active'
    }, getAdminConfig())
    await loadReportsSummary()
    alert(`Schedule resumed: ${schedule.report_name}`)
  } catch (error) {
    alert(error.response?.data?.detail || error.message || 'Failed to resume schedule')
  }
}

const deleteSchedule = async (schedule) => {
  if (confirm(`Delete schedule for "${schedule.report_name}"?`)) {
    try {
      await api.delete(`/admin/reports/schedules/${schedule._id}`, getAdminConfig())
      await loadReportsSummary()
      alert('Schedule deleted')
    } catch (error) {
      alert(error.response?.data?.detail || error.message || 'Failed to delete schedule')
    }
  }
}

const saveSchedule = () => {
  if (!scheduleForm.value.report_id || !scheduleForm.value.recipients) {
    alert('Please fill in all required fields')
    return
  }

  const selectedReport = reports.value.find((r) => r._id === scheduleForm.value.report_id)
  const payload = {
    report_id: scheduleForm.value.report_id,
    report_name: selectedReport?.name || 'Scheduled Report',
    frequency: scheduleForm.value.frequency,
    recipients: scheduleForm.value.recipients.split(',').map(r => r.trim()).filter(Boolean),
    format: scheduleForm.value.format
  }

  api.post('/admin/reports/schedules', payload, getAdminConfig()).then(async () => {
    await loadReportsSummary()
    alert('Report scheduled successfully!')
    showScheduleModal.value = false
    scheduleForm.value = { report_id: '', frequency: 'monthly', recipients: '', format: 'pdf' }
  }).catch((error) => {
    alert(error.response?.data?.detail || error.message || 'Failed to schedule report')
  })
}

const previewFormat = (format) => {
  alert(`Preview format: ${format}`)
}

const configureEmail = () => {
  alert('Email configuration panel')
}

const editDashboard = (dashboard) => {
  alert(`Editing dashboard: ${dashboard.name}`)
}

const viewDashboard = (dashboard) => {
  alert(`Viewing dashboard: ${dashboard.name}`)
}

const shareDashboard = (dashboard) => {
  alert(`Share dashboard: ${dashboard.name}`)
}

const deleteDashboard = (dashboard) => {
  if (confirm(`Delete dashboard "${dashboard.name}"?`)) {
    const index = dashboards.value.findIndex(d => d._id === dashboard._id)
    if (index > -1) dashboards.value.splice(index, 1)
    alert('Dashboard deleted')
  }
}

const saveDashboard = () => {
  if (!dashboardForm.value.name || dashboardForm.value.widgets.length === 0) {
    alert('Please fill in name and select at least one widget')
    return
  }
  
  const dashboard = {
    _id: Date.now().toString(),
    name: dashboardForm.value.name,
    widgets: dashboardForm.value.widgets.map(w => ({ name: w })),
    created_at: new Date(),
    shared_with: []
  }
  
  dashboards.value.unshift(dashboard)
  alert(`Dashboard "${dashboard.name}" created successfully!`)
  showDashboardModal.value = false
  dashboardForm.value = { name: '', description: '', widgets: [] }
}
</script>

<style scoped>
.admin-reports {
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

.status-message {
  background: #ebf8ff;
  color: #2b6cb0;
  border: 1px solid #bee3f8;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
}

.error-message {
  background: #fff5f5;
  color: #c53030;
  border: 1px solid #fed7d7;
  border-radius: 8px;
  padding: 0.75rem 1rem;
  margin-bottom: 1rem;
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

/* Report Builder */
.builder-section h3 {
  margin: 0 0 1.5rem 0;
  color: #1a202c;
  font-size: 1.1rem;
}

.builder-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}

.builder-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
}

.builder-card h4 {
  margin: 0 0 0.5rem 0;
  color: #1a202c;
  font-size: 1rem;
}

.card-description {
  margin: 0 0 1.5rem 0;
  font-size: 0.85rem;
  color: #718096;
}

.template-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.template-btn {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  display: flex;
  align-items: center;
  gap: 0.75rem;
  transition: all 0.2s;
  text-align: left;
}

.template-btn:hover {
  border-color: #667eea;
  background: #f0f9ff;
}

.template-btn.selected {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: transparent;
  color: white;
}

.template-icon {
  font-size: 1.25rem;
}

.template-name {
  font-weight: 600;
}

.form-group {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.form-group label {
  font-weight: 600;
  color: #2d3748;
}

.input,
.textarea {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  font-family: inherit;
}

.input:focus,
.textarea:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

.date-range {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.date-range .input {
  flex: 1;
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
  font-weight: 500;
}

.checkbox-group input[type="checkbox"] {
  cursor: pointer;
}

.quick-filter-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.quick-filter-btn {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 8px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.quick-filter-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

/* Reports Listing */
.listing-controls {
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

.filter-select {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  background: white;
  cursor: pointer;
}

.reports-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.report-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.report-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.report-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.report-info h4 {
  margin: 0;
  color: #1a202c;
}

.report-type {
  margin: 0.25rem 0 0 0;
  font-size: 0.85rem;
  color: #718096;
}

.status-badge {
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.badge-completed {
  background: #dcfce7;
  color: #166534;
}

.badge-processing {
  background: #fef3c7;
  color: #b45309;
}

.badge-draft {
  background: #dbeafe;
  color: #0c4a6e;
}

.report-details {
  font-size: 0.9rem;
  color: #718096;
  margin-bottom: 1.5rem;
}

.report-details p {
  margin: 0.5rem 0;
}

.report-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
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

/* Scheduling */
.scheduling-section h3 {
  margin: 0 0 1.5rem 0;
  color: #1a202c;
}

.schedule-controls {
  margin-bottom: 1.5rem;
}

.scheduled-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 1.5rem;
}

.schedule-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.schedule-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.schedule-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.schedule-header h4 {
  margin: 0;
  color: #1a202c;
}

.schedule-details {
  font-size: 0.9rem;
  color: #718096;
  margin-bottom: 1.5rem;
}

.schedule-details p {
  margin: 0.5rem 0;
}

.schedule-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
  margin-bottom: 1rem;
}

.schedule-info {
  font-size: 0.85rem;
  color: #718096;
  border-top: 1px solid #e2e8f0;
  padding-top: 1rem;
}

.runs-count {
  margin: 0;
}

/* Export Formats */
.formats-section h3 {
  margin: 0 0 1.5rem 0;
  color: #1a202c;
}

.formats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
  gap: 1.5rem;
}

.format-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
}

.format-icon {
  font-size: 2.5rem;
  margin-bottom: 0.75rem;
}

.format-card h4 {
  margin: 0 0 0.5rem 0;
  color: #1a202c;
}

.format-description {
  margin: 0 0 1rem 0;
  font-size: 0.9rem;
  color: #718096;
}

.format-options {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.format-options label {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  cursor: pointer;
}

.format-options input[type="checkbox"],
.format-options input[type="radio"] {
  cursor: pointer;
}

/* Dashboards */
.dashboards-section h3 {
  margin: 0 0 1.5rem 0;
  color: #1a202c;
}

.dashboards-controls {
  margin-bottom: 1.5rem;
}

.dashboards-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.dashboard-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.dashboard-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.dashboard-preview {
  margin-bottom: 1rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
}

.preview-widget {
  background: #f7fafc;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  padding: 0.75rem;
  text-align: center;
}

.widget-name {
  margin: 0;
  font-size: 0.75rem;
  color: #718096;
  font-weight: 600;
}

.dashboard-info h4 {
  margin: 0 0 0.25rem 0;
  color: #1a202c;
}

.dashboard-meta {
  margin: 0 0 1.5rem 0;
  font-size: 0.85rem;
  color: #718096;
}

.dashboard-actions {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
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

.form-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-top: 1.5rem;
}

.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  color: #718096;
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

  .builder-grid {
    grid-template-columns: 1fr;
  }

  .listing-controls {
    flex-direction: column;
  }

  .search-input,
  .filter-select {
    width: 100%;
  }

  .reports-container {
    grid-template-columns: 1fr;
  }

  .formats-grid {
    grid-template-columns: 1fr;
  }

  .dashboards-grid {
    grid-template-columns: 1fr;
  }

  .date-range {
    flex-direction: column;
  }

  .date-range .input {
    width: 100%;
  }
}
</style>
