<template>
  <div class="admin-audit">
    <div class="page-header">
      <h1>Audit & Compliance</h1>
      <p class="subtitle">Monitor system activities and security events</p>
    </div>

    <div v-if="loading" class="status-message">Loading audit data...</div>
    <div v-else-if="loadError" class="error-message">{{ loadError }}</div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        @click="activeTab = 'activity'"
        :class="['tab', { active: activeTab === 'activity' }]"
      >
        📋 Activity Log
      </button>
      <button
        @click="activeTab = 'system'"
        :class="['tab', { active: activeTab === 'system' }]"
      >
        🔧 System Events
      </button>
      <button
        @click="activeTab = 'sessions'"
        :class="['tab', { active: activeTab === 'sessions' }]"
      >
        👤 User Sessions
      </button>
      <button
        @click="activeTab = 'security'"
        :class="['tab', { active: activeTab === 'security' }]"
      >
        🔐 Security Events
      </button>
      <button
        @click="activeTab = 'export'"
        :class="['tab', { active: activeTab === 'export' }]"
      >
        📥 Export & Analysis
      </button>
    </div>

    <!-- Activity Log Tab -->
    <div v-if="activeTab === 'activity'" class="tab-content">
      <div class="filter-controls">
        <input
          v-model="activitySearch"
          type="text"
          placeholder="Search by user, action, resource..."
          class="search-input"
        />

        <select v-model="activityFilters.actionType" class="filter-select">
          <option value="">All Actions</option>
          <option value="create">➕ Create</option>
          <option value="update">✏️ Update</option>
          <option value="delete">🗑️ Delete</option>
          <option value="view">👁️ View</option>
          <option value="export">📥 Export</option>
        </select>

        <select v-model="activityFilters.resource" class="filter-select">
          <option value="">All Resources</option>
          <option value="user">User</option>
          <option value="tour">Tour</option>
          <option value="booking">Booking</option>
          <option value="payment">Payment</option>
          <option value="settings">Settings</option>
        </select>

        <input
          v-model="activityFilters.dateFrom"
          type="date"
          class="filter-input"
        />

        <input
          v-model="activityFilters.dateTo"
          type="date"
          class="filter-input"
        />
      </div>

      <div v-if="filteredActivityLogs.length === 0" class="empty-state">
        <p>📭 No activity logs found</p>
      </div>

      <div v-else class="activity-timeline">
        <div v-for="log in paginatedActivityLogs" :key="log._id" class="activity-item">
          <div class="activity-icon" :class="`icon-${log.actionType}`">
            {{ getActionIcon(log.actionType) }}
          </div>

          <div class="activity-content">
            <div class="activity-header">
              <span class="user-name">{{ log.user_name }}</span>
              <span class="action-type" :class="`action-${log.actionType}`">
                {{ log.actionType.toUpperCase() }}
              </span>
              <span class="resource-type">{{ log.resource }}</span>
            </div>

            <p class="activity-description">{{ log.description }}</p>

            <div class="activity-details">
              <span class="detail-item">🕐 {{ formatDateTime(log.timestamp) }}</span>
              <span class="detail-item">💻 {{ log.ip_address }}</span>
              <span class="detail-item">🌐 {{ log.user_agent }}</span>
            </div>

            <div class="activity-changes" v-if="log.changes">
              <p class="changes-title">Changes:</p>
              <div class="change-item">
                <span class="change-field">{{ log.changes.field }}</span>
                <span class="change-arrow">→</span>
                <span class="change-from">{{ log.changes.from }}</span>
                <span class="change-to">{{ log.changes.to }}</span>
              </div>
            </div>
          </div>

          <button @click="viewActivityDetail(log)" class="detail-btn">Details</button>
        </div>

        <!-- Pagination -->
        <div class="pagination">
          <button
            @click="activityPage = Math.max(1, activityPage - 1)"
            :disabled="activityPage === 1"
            class="pagination-btn"
          >
            ← Previous
          </button>

          <div class="page-buttons">
            <button
              v-for="page in visibleActivityPages"
              :key="page"
              @click="activityPage = page"
              :class="['page-btn', { active: activityPage === page }]"
            >
              {{ page }}
            </button>
          </div>

          <button
            @click="activityPage++"
            :disabled="activityPage >= totalActivityPages"
            class="pagination-btn"
          >
            Next →
          </button>
        </div>
      </div>
    </div>

    <!-- System Events Tab -->
    <div v-else-if="activeTab === 'system'" class="tab-content">
      <div class="system-controls">
        <input
          v-model="systemSearch"
          type="text"
          placeholder="Search by event type, service, or message..."
          class="search-input"
        />

        <select v-model="systemFilters.severity" class="filter-select">
          <option value="">All Severity</option>
          <option value="critical">🔴 Critical</option>
          <option value="warning">🟡 Warning</option>
          <option value="info">🔵 Info</option>
        </select>

        <select v-model="systemFilters.service" class="filter-select">
          <option value="">All Services</option>
          <option value="api">API</option>
          <option value="database">Database</option>
          <option value="auth">Authentication</option>
          <option value="payment">Payment</option>
          <option value="notification">Notification</option>
        </select>

        <label class="checkbox">
          <input v-model="systemFilters.unreadOnly" type="checkbox" />
          <span>Unread Only</span>
        </label>
      </div>

      <div v-if="filteredSystemEvents.length === 0" class="empty-state">
        <p>✓ No system events</p>
      </div>

      <div v-else class="system-events-container">
        <div
          v-for="event in filteredSystemEvents"
          :key="event._id"
          :class="['system-event', `severity-${event.severity}`, { unread: !event.read }]"
        >
          <div class="event-icon">{{ getSeverityIcon(event.severity) }}</div>

          <div class="event-content">
            <div class="event-header">
              <h4 class="event-title">{{ event.title }}</h4>
              <span class="event-time">{{ formatTime(event.timestamp) }}</span>
            </div>

            <p class="event-message">{{ event.message }}</p>

            <div class="event-meta">
              <span class="meta-item">
                <strong>Service:</strong> {{ event.service }}
              </span>
              <span class="meta-item">
                <strong>Code:</strong> {{ event.error_code }}
              </span>
            </div>

            <div v-if="event.details" class="event-details">
              <p class="details-label">Details:</p>
              <code class="details-code">{{ event.details }}</code>
            </div>
          </div>

          <div class="event-actions">
            <button
              v-if="!event.read"
              @click="markEventRead(event)"
              class="action-btn"
              title="Mark as read"
            >
              ✓
            </button>
            <button @click="dismissEvent(event)" class="action-btn" title="Dismiss">
              ✕
            </button>
          </div>
        </div>

        <div class="pagination">
          <button
            @click="systemPage = Math.max(1, systemPage - 1)"
            :disabled="!systemPagination.hasPrev"
            class="pagination-btn"
          >
            ← Previous
          </button>

          <div class="page-buttons">
            <button
              v-for="page in visibleSystemPages"
              :key="`system-${page}`"
              @click="systemPage = page"
              :class="['page-btn', { active: systemPage === page }]"
            >
              {{ page }}
            </button>
          </div>

          <span class="pagination-summary">Page {{ systemPagination.page }} of {{ systemPagination.totalPages }}</span>

          <button
            @click="systemPage = Math.min(systemPagination.totalPages, systemPage + 1)"
            :disabled="!systemPagination.hasNext"
            class="pagination-btn"
          >
            Next →
          </button>
        </div>
      </div>
    </div>

    <!-- User Sessions Tab -->
    <div v-else-if="activeTab === 'sessions'" class="tab-content">
      <div class="sessions-header">
        <div class="sessions-stats">
          <div class="stat-card">
            <p class="stat-label">Active Sessions</p>
            <p class="stat-value">{{ sessionsSummary.activeCount }}</p>
          </div>

          <div class="stat-card">
            <p class="stat-label">Total Users Online</p>
            <p class="stat-value">{{ sessionsSummary.uniqueUsersOnline }}</p>
          </div>

          <div class="stat-card">
            <p class="stat-label">Avg Session Duration</p>
            <p class="stat-value">{{ sessionsSummary.avgSessionDuration }} min</p>
          </div>
        </div>

        <button @click="refreshSessions" class="btn btn-secondary">🔄 Refresh</button>
      </div>

      <div class="sessions-controls">
        <input
          v-model="sessionSearch"
          type="text"
          placeholder="Search by user, device, or IP..."
          class="search-input"
        />

        <select v-model="sessionFilters.userType" class="filter-select">
          <option value="">All Users</option>
          <option value="admin">Admin</option>
          <option value="operator">Operator</option>
          <option value="tourist">Tourist</option>
        </select>

        <select v-model="sessionFilters.deviceType" class="filter-select">
          <option value="">All Devices</option>
          <option value="desktop">🖥️ Desktop</option>
          <option value="mobile">📱 Mobile</option>
          <option value="tablet">⌚ Tablet</option>
        </select>
      </div>

      <div v-if="filteredSessions.length === 0" class="empty-state">
        <p>📭 No active sessions</p>
      </div>

      <div v-else class="sessions-grid">
        <div v-for="session in filteredSessions" :key="session._id" class="session-card">
          <div class="session-header">
            <div class="user-info">
              <p class="user-name">{{ session.user_name }}</p>
              <p class="user-email">{{ session.email }}</p>
            </div>
            <span class="status-badge" :class="`status-${session.status}`">
              {{ session.status === 'active' ? '🟢' : '⚫' }} {{ session.status }}
            </span>
          </div>

          <div class="session-details">
            <div class="detail-row">
              <span class="label">Device:</span>
              <span class="value">{{ getDeviceIcon(session.device_type) }} {{ session.device_type }}</span>
            </div>
            <div class="detail-row">
              <span class="label">IP Address:</span>
              <span class="value">{{ session.ip_address }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Location:</span>
              <span class="value">{{ session.location }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Started:</span>
              <span class="value">{{ formatDateTime(session.created_at) }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Last Active:</span>
              <span class="value">{{ formatDateTime(session.last_activity) }}</span>
            </div>
            <div class="detail-row">
              <span class="label">Duration:</span>
              <span class="value">{{ getSessionDuration(session.created_at, session.last_activity) }} min</span>
            </div>
          </div>

          <div class="session-actions">
            <button @click="viewSessionDetail(session)" class="btn btn-small btn-secondary">
              👁️ Details
            </button>
            <button v-if="session.status === 'active'" @click="terminateSession(session)" class="btn btn-small btn-danger">
              ⛔ Terminate
            </button>
          </div>
        </div>

        <div class="pagination sessions-pagination">
          <button
            @click="sessionsPage = Math.max(1, sessionsPage - 1)"
            :disabled="!sessionsPagination.hasPrev"
            class="pagination-btn"
          >
            ← Previous
          </button>

          <div class="page-buttons">
            <button
              v-for="page in visibleSessionsPages"
              :key="`sessions-${page}`"
              @click="sessionsPage = page"
              :class="['page-btn', { active: sessionsPage === page }]"
            >
              {{ page }}
            </button>
          </div>

          <span class="pagination-summary">Page {{ sessionsPagination.page }} of {{ sessionsPagination.totalPages }}</span>

          <button
            @click="sessionsPage = Math.min(sessionsPagination.totalPages, sessionsPage + 1)"
            :disabled="!sessionsPagination.hasNext"
            class="pagination-btn"
          >
            Next →
          </button>
        </div>
      </div>
    </div>

    <!-- Security Events Tab -->
    <div v-else-if="activeTab === 'security'" class="tab-content">
      <div class="security-alerts">
        <div class="alert-card alert-critical">
          <p class="alert-label">Failed Login Attempts</p>
          <p class="alert-count">{{ failedLoginAttempts }}</p>
        </div>

        <div class="alert-card alert-warning">
          <p class="alert-label">Suspicious Activities</p>
          <p class="alert-count">{{ suspiciousActivities }}</p>
        </div>

        <div class="alert-card alert-warning">
          <p class="alert-label">Anomalies Detected</p>
          <p class="alert-count">{{ anomaliesDetected }}</p>
        </div>

        <div class="alert-card alert-info">
          <p class="alert-label">Rate Limit Hits</p>
          <p class="alert-count">{{ rateLimitHits }}</p>
        </div>
      </div>

      <div class="authz-report-card">
        <div class="authz-report-header">
          <div>
            <h3>Authorization Decisions</h3>
            <p>Live RBAC allow/deny observability for admin and operator surfaces.</p>
          </div>
          <button @click="loadAuthorizationReport" class="btn btn-secondary" :disabled="authzLoading">
            {{ authzLoading ? 'Refreshing...' : 'Refresh' }}
          </button>
        </div>

        <div class="authz-controls">
          <select v-model.number="authzFilters.hours" class="filter-select">
            <option :value="1">Last 1 hour</option>
            <option :value="6">Last 6 hours</option>
            <option :value="24">Last 24 hours</option>
            <option :value="72">Last 72 hours</option>
            <option :value="168">Last 7 days</option>
          </select>

          <select v-model="authzFilters.principalType" class="filter-select">
            <option value="">All principals</option>
            <option value="admin">Admin</option>
            <option value="user">User</option>
          </select>

          <select v-model="authzFilters.decision" class="filter-select">
            <option value="">All decisions</option>
            <option value="allowed">Allowed</option>
            <option value="denied">Denied</option>
          </select>

          <input
            v-model.trim="authzFilters.permission"
            type="text"
            placeholder="Permission filter"
            class="search-input"
          />

          <input
            v-model.trim="authzFilters.pathContains"
            type="text"
            placeholder="Path contains"
            class="search-input"
          />
        </div>

        <div v-if="authzError" class="error-message">{{ authzError }}</div>

        <div class="authz-summary-grid">
          <div class="authz-summary-item">
            <p class="authz-label">Total Decisions</p>
            <p class="authz-value">{{ authzSummary.total }}</p>
          </div>
          <div class="authz-summary-item allowed">
            <p class="authz-label">Allowed</p>
            <p class="authz-value">{{ authzSummary.allowed }}</p>
          </div>
          <div class="authz-summary-item denied">
            <p class="authz-label">Denied</p>
            <p class="authz-value">{{ authzSummary.denied }}</p>
          </div>
          <div class="authz-summary-item rate">
            <p class="authz-label">Denial Rate</p>
            <p class="authz-value">{{ authzSummary.denialRate }}%</p>
          </div>
        </div>

        <div class="authz-trend-card">
          <div class="authz-trend-header">
            <h4>Allowed vs Denied Trend</h4>
            <span class="mini-meta">{{ authzFilters.hours }}h window</span>
          </div>
          <svg viewBox="0 0 220 42" class="authz-sparkline" role="img" aria-label="Authorization decisions trend">
            <polyline :points="authzAllowedPoints" class="sparkline-line allowed" />
            <polyline :points="authzDeniedPoints" class="sparkline-line denied" />
          </svg>
          <div class="authz-legend">
            <span class="legend-item"><span class="legend-dot allowed"></span>Allowed</span>
            <span class="legend-item"><span class="legend-dot denied"></span>Denied</span>
          </div>
        </div>

        <div class="authz-breakdown-grid">
          <div class="authz-list-card">
            <h4>Top Denied Permissions</h4>
            <div v-if="authzTopDeniedPermissions.length === 0" class="mini-empty">No denied permissions in selected window.</div>
            <div v-else class="mini-list">
              <div v-for="item in authzTopDeniedPermissions" :key="`perm-${item.permission}`" class="mini-row">
                <span class="mini-name">{{ item.permission }}</span>
                <span class="mini-count">{{ item.count }}</span>
              </div>
            </div>
          </div>

          <div class="authz-list-card">
            <h4>Top Denied Routes</h4>
            <div v-if="authzTopDeniedRoutes.length === 0" class="mini-empty">No denied routes in selected window.</div>
            <div v-else class="mini-list">
              <div v-for="item in authzTopDeniedRoutes" :key="`route-${item.route}`" class="mini-row">
                <span class="mini-name">{{ item.route }}</span>
                <span class="mini-count">{{ item.count }}</span>
              </div>
            </div>
          </div>

          <div class="authz-list-card">
            <h4>Principal Breakdown</h4>
            <div v-if="authzPrincipalBreakdown.length === 0" class="mini-empty">No principal activity in selected window.</div>
            <div v-else class="mini-list">
              <div v-for="item in authzPrincipalBreakdown" :key="`principal-${item.principal_type}`" class="mini-row stacked">
                <span class="mini-name">{{ item.principal_type }}</span>
                <span class="mini-meta">A: {{ item.allowed }} | D: {{ item.denied }} | T: {{ item.total }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="authz-events-table-wrap">
          <h4>Recent Authorization Decisions</h4>
          <div v-if="authzEvents.length === 0" class="mini-empty">No authorization decisions available for current filters.</div>
          <table v-else class="authz-events-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>Principal</th>
                <th>Decision</th>
                <th>Permission</th>
                <th>Route</th>
              </tr>
            </thead>
            <tbody>
              <template v-for="(event, index) in authzEvents" :key="authzEventKey(event, index)">
                <tr class="authz-row" @click="toggleAuthzRow(authzEventKey(event, index))">
                  <td>
                    <span class="expand-indicator">{{ isAuthzRowExpanded(authzEventKey(event, index)) ? '▼' : '▶' }}</span>
                    {{ formatDateTime(event.timestamp) }}
                  </td>
                  <td>{{ event.principal_type || 'unknown' }}</td>
                  <td>
                    <span :class="['decision-pill', event.decision === 'denied' ? 'denied' : 'allowed']">
                      {{ event.decision || 'unknown' }}
                    </span>
                  </td>
                  <td>{{ event.permission || 'none' }}</td>
                  <td>{{ event.method }} {{ event.path }}</td>
                </tr>
                <tr v-if="isAuthzRowExpanded(authzEventKey(event, index))" class="authz-row-expanded">
                  <td colspan="5">
                    <div class="authz-detail-text">{{ event.detail || 'No additional detail recorded.' }}</div>
                  </td>
                </tr>
              </template>
            </tbody>
          </table>
        </div>
      </div>

      <div class="security-controls">
        <input
          v-model="securitySearch"
          type="text"
          placeholder="Search by user, event type, or details..."
          class="search-input"
        />

        <select v-model="securityFilters.eventType" class="filter-select">
          <option value="">All Events</option>
          <option value="failed_login">🔴 Failed Login</option>
          <option value="suspicious">⚠️ Suspicious Activity</option>
          <option value="anomaly">🔍 Anomaly</option>
          <option value="brute_force">🚨 Brute Force</option>
          <option value="rate_limit">⏱️ Rate Limit</option>
        </select>

        <input
          v-model="securityFilters.dateFrom"
          type="date"
          class="filter-input"
        />
      </div>

      <div v-if="filteredSecurityEvents.length === 0" class="empty-state">
        <p>✓ No security events</p>
      </div>

      <div v-else class="security-events-container">
        <div
          v-for="event in filteredSecurityEvents"
          :key="event._id"
          :class="['security-event', `severity-${event.severity}`]"
        >
          <div class="event-type-badge">{{ event.event_type }}</div>

          <div class="event-info">
            <div class="info-header">
              <h4>{{ event.title }}</h4>
              <span class="event-time">{{ formatDateTime(event.timestamp) }}</span>
            </div>

            <div class="event-details">
              <p><strong>User:</strong> {{ event.user_name }}</p>
              <p><strong>IP Address:</strong> {{ event.ip_address }}</p>
              <p><strong>Location:</strong> {{ event.location }}</p>
              <p><strong>Description:</strong> {{ event.description }}</p>
            </div>

            <div v-if="event.remediation" class="remediation-box">
              <p class="remediation-label">⚙️ Recommended Action:</p>
              <p class="remediation-text">{{ event.remediation }}</p>
            </div>
          </div>

          <div class="event-risk">
            <span :class="['risk-badge', `risk-${event.severity}`]">
              {{ event.severity.toUpperCase() }}
            </span>
          </div>

          <div class="event-actions">
            <button @click="acknowledgeEvent(event)" class="btn btn-small btn-secondary">
              ✓ Acknowledge
            </button>
            <button @click="blockUser(event)" class="btn btn-small btn-danger">
              🚫 Block User
            </button>
          </div>
        </div>

        <div class="pagination">
          <button
            @click="securityPage = Math.max(1, securityPage - 1)"
            :disabled="!securityPagination.hasPrev"
            class="pagination-btn"
          >
            ← Previous
          </button>

          <div class="page-buttons">
            <button
              v-for="page in visibleSecurityPages"
              :key="`security-${page}`"
              @click="securityPage = page"
              :class="['page-btn', { active: securityPage === page }]"
            >
              {{ page }}
            </button>
          </div>

          <span class="pagination-summary">Page {{ securityPagination.page }} of {{ securityPagination.totalPages }}</span>

          <button
            @click="securityPage = Math.min(securityPagination.totalPages, securityPage + 1)"
            :disabled="!securityPagination.hasNext"
            class="pagination-btn"
          >
            Next →
          </button>
        </div>
      </div>
    </div>

    <!-- Export & Analysis Tab -->
    <div v-else-if="activeTab === 'export'" class="tab-content">
      <div class="export-section">
        <h3>Export Audit Logs</h3>

        <div class="export-options">
          <div class="option-card">
            <h4>Select Log Type</h4>
            <div class="checkbox-group">
              <label>
                <input v-model="exportLogs.activity" type="checkbox" />
                <span>Activity Logs</span>
              </label>
              <label>
                <input v-model="exportLogs.system" type="checkbox" />
                <span>System Events</span>
              </label>
              <label>
                <input v-model="exportLogs.sessions" type="checkbox" />
                <span>User Sessions</span>
              </label>
              <label>
                <input v-model="exportLogs.security" type="checkbox" />
                <span>Security Events</span>
              </label>
            </div>
          </div>

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
                @click="exportFormat = 'json'"
                :class="['format-btn', { active: exportFormat === 'json' }]"
              >
                🔗 JSON
              </button>
              <button
                @click="exportFormat = 'pdf'"
                :class="['format-btn', { active: exportFormat === 'pdf' }]"
              >
                📋 PDF
              </button>
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
            <h4>Compliance Reports</h4>
            <div class="checkbox-group">
              <label>
                <input v-model="complianceReports.dataAccess" type="checkbox" />
                <span>Data Access Report</span>
              </label>
              <label>
                <input v-model="complianceReports.changes" type="checkbox" />
                <span>Data Changes Report</span>
              </label>
              <label>
                <input v-model="complianceReports.security" type="checkbox" />
                <span>Security Report</span>
              </label>
            </div>
          </div>
        </div>

        <div class="export-actions">
          <button @click="resetExportForm" class="btn btn-secondary">Clear</button>
          <button @click="exportAuditLogs" class="btn btn-primary">📥 Export Now</button>
        </div>

        <div v-if="exportSuccess" class="success-message">{{ exportSuccess }}</div>
        <div v-if="exportError" class="error-message">{{ exportError }}</div>
      </div>

      <div class="analysis-section">
        <h3>Audit Analysis</h3>

        <div class="analysis-grid">
          <div class="analysis-card">
            <h4>Activity Summary</h4>
            <div class="analysis-content">
              <p>Total Activities: <strong>{{ activityStats.total }}</strong></p>
              <p>Creates: <strong>{{ activityStats.creates }}</strong></p>
              <p>Updates: <strong>{{ activityStats.updates }}</strong></p>
              <p>Deletes: <strong>{{ activityStats.deletes }}</strong></p>
            </div>
          </div>

          <div class="analysis-card">
            <h4>Top Users</h4>
            <div class="analysis-content">
              <div v-for="(user, index) in topUsers" :key="index" class="user-stat">
                <span class="user-rank">{{ index + 1 }}.</span>
                <span class="user-name">{{ user.name }}</span>
                <span class="user-count">{{ user.count }}</span>
              </div>
            </div>
          </div>

          <div class="analysis-card">
            <h4>Security Score</h4>
            <div class="analysis-content security-score">
              <div class="score-display">
                <p class="score-value">{{ securityScore }}</p>
                <p class="score-label">/ 100</p>
              </div>
              <p class="score-status" :class="`status-${getSecurityStatus()}`">
                {{ getSecurityStatus().toUpperCase() }}
              </p>
            </div>
          </div>

          <div class="analysis-card">
            <h4>Compliance Status</h4>
            <div class="analysis-content">
              <p>✓ Data Integrity: <strong>99.8%</strong></p>
              <p>✓ Access Control: <strong>98.5%</strong></p>
              <p>✓ Audit Trail: <strong>100%</strong></p>
              <p>Overall: <strong>Good Standing</strong></p>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Activity Detail Modal -->
    <div v-if="showActivityModal" class="modal-overlay" @click.self="showActivityModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Activity Details</h2>
          <button @click="showActivityModal = false" class="close-btn">✕</button>
        </div>

        <div v-if="selectedActivity" class="modal-body">
          <div class="detail-section">
            <h3>Basic Information</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">User:</span>
                <span class="value">{{ selectedActivity.user_name }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Action:</span>
                <span class="value">{{ selectedActivity.actionType }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Resource:</span>
                <span class="value">{{ selectedActivity.resource }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Timestamp:</span>
                <span class="value">{{ formatDateTime(selectedActivity.timestamp) }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3>Technical Details</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">IP Address:</span>
                <span class="value">{{ selectedActivity.ip_address }}</span>
              </div>
              <div class="detail-item">
                <span class="label">User Agent:</span>
                <span class="value">{{ selectedActivity.user_agent }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Status Code:</span>
                <span class="value">{{ selectedActivity.status_code }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="showActivityModal = false" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>

    <!-- Session Detail Modal -->
    <div v-if="showSessionModal" class="modal-overlay" @click.self="showSessionModal = false">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Session Details</h2>
          <button @click="showSessionModal = false" class="close-btn">✕</button>
        </div>

        <div v-if="selectedSession" class="modal-body">
          <div class="detail-section">
            <h3>User Information</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">Name:</span>
                <span class="value">{{ selectedSession.user_name }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Email:</span>
                <span class="value">{{ selectedSession.email }}</span>
              </div>
              <div class="detail-item">
                <span class="label">User Type:</span>
                <span class="value">{{ selectedSession.user_type }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3>Session Information</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">Session ID:</span>
                <span class="value">{{ selectedSession._id }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Status:</span>
                <span class="value">{{ selectedSession.status }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Created:</span>
                <span class="value">{{ formatDateTime(selectedSession.created_at) }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Last Active:</span>
                <span class="value">{{ formatDateTime(selectedSession.last_activity) }}</span>
              </div>
            </div>
          </div>

          <div class="detail-section">
            <h3>Device & Location</h3>
            <div class="detail-grid">
              <div class="detail-item">
                <span class="label">Device Type:</span>
                <span class="value">{{ selectedSession.device_type }}</span>
              </div>
              <div class="detail-item">
                <span class="label">IP Address:</span>
                <span class="value">{{ selectedSession.ip_address }}</span>
              </div>
              <div class="detail-item">
                <span class="label">Location:</span>
                <span class="value">{{ selectedSession.location }}</span>
              </div>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="showSessionModal = false" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import api from '../services/api'
import { adminBrandConfig } from '../config/adminBrand'

const activeTab = ref('activity')
const loading = ref(false)
const loadError = ref('')
const authzLoading = ref(false)
const authzError = ref('')
const adminBrand = adminBrandConfig
const defaultAuditPerPage = 10
let auditReloadTimer = null
let authzReloadTimer = null
let suppressAuditWatch = false

const createPaginationState = (overrides = {}) => ({
  page: 1,
  perPage: defaultAuditPerPage,
  total: 0,
  totalPages: 1,
  hasPrev: false,
  hasNext: false,
  ...overrides,
})

const buildVisiblePages = (pagination) => {
  const total = Math.max(1, Number(pagination?.totalPages || 1))
  const current = Math.min(Math.max(1, Number(pagination?.page || 1)), total)
  const pages = []
  const maxVisible = 5

  if (total <= maxVisible) {
    for (let page = 1; page <= total; page += 1) pages.push(page)
    return pages
  }

  const half = Math.floor(maxVisible / 2)
  let start = Math.max(1, current - half)
  let end = Math.min(total, start + maxVisible - 1)
  if (end - start < maxVisible - 1) {
    start = Math.max(1, end - maxVisible + 1)
  }
  for (let page = start; page <= end; page += 1) pages.push(page)
  return pages
}

// Activity Log
const activityLogs = ref([
  {
    _id: '1',
    user_name: 'Admin User',
    actionType: 'create',
    resource: 'user',
    description: 'Created new operator account for Mountain Guides Co.',
    timestamp: new Date('2026-02-06T10:30:00'),
    ip_address: '192.168.1.100',
    user_agent: 'Mozilla/5.0 (Windows NT 10.0; Win64; x64)',
    status_code: 201,
    changes: null
  },
  {
    _id: '2',
    user_name: 'Operator Manager',
    actionType: 'update',
    resource: 'tour',
    description: 'Updated tour pricing for Everest Trek',
    timestamp: new Date('2026-02-06T09:15:00'),
    ip_address: '192.168.1.101',
    user_agent: 'Mozilla/5.0 (iPhone; CPU iPhone OS 15_0)',
    status_code: 200,
    changes: { field: 'price', from: '₹5000', to: '₹5500' }
  },
  {
    _id: '3',
    user_name: 'System Admin',
    actionType: 'delete',
    resource: 'booking',
    description: 'Cancelled booking due to operator request',
    timestamp: new Date('2026-02-06T08:45:00'),
    ip_address: '192.168.1.102',
    user_agent: 'Mozilla/5.0 (iPad)',
    status_code: 204,
    changes: null
  }
])

const activitySearch = ref('')
const activityFilters = ref({
  actionType: '',
  resource: '',
  dateFrom: '',
  dateTo: ''
})
const activityPage = ref(1)
const itemsPerPage = ref(10)

const filteredActivityLogs = computed(() => {
  return activityLogs.value.filter(log => {
    const matchesSearch = !activitySearch.value ||
      log.user_name.toLowerCase().includes(activitySearch.value.toLowerCase()) ||
      log.description.toLowerCase().includes(activitySearch.value.toLowerCase()) ||
      log.resource.toLowerCase().includes(activitySearch.value.toLowerCase())
    
    const matchesAction = !activityFilters.value.actionType || log.actionType === activityFilters.value.actionType
    const matchesResource = !activityFilters.value.resource || log.resource === activityFilters.value.resource
    
    return matchesSearch && matchesAction && matchesResource
  })
})

const totalActivityPages = computed(() => {
  return Math.ceil(filteredActivityLogs.value.length / itemsPerPage.value)
})

const paginatedActivityLogs = computed(() => {
  const start = (activityPage.value - 1) * itemsPerPage.value
  return filteredActivityLogs.value.slice(start, start + itemsPerPage.value)
})

const visibleActivityPages = computed(() => {
  const total = totalActivityPages.value
  const current = activityPage.value
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

// System Events
const systemEvents = ref([])

const systemSearch = ref('')
const systemFilters = ref({
  severity: '',
  service: '',
  unreadOnly: false
})
const systemPage = ref(1)
const systemPagination = ref(createPaginationState())

const filteredSystemEvents = computed(() => {
  return systemEvents.value
})
const visibleSystemPages = computed(() => buildVisiblePages(systemPagination.value))

// User Sessions
const sessions = ref([
  {
    _id: '1',
    user_name: 'John Operator',
    email: 'john@mountainguides.com',
    user_type: 'operator',
    status: 'active',
    device_type: 'desktop',
    ip_address: '203.0.113.45',
    location: 'New Delhi, IN',
    created_at: new Date('2026-02-06T08:00:00'),
    last_activity: new Date('2026-02-06T11:30:00')
  },
  {
    _id: '2',
    user_name: 'Jane Tourist',
    email: 'jane@example.com',
    user_type: 'tourist',
    status: 'active',
    device_type: 'mobile',
    ip_address: '203.0.113.46',
    location: 'Mumbai, IN',
    created_at: new Date('2026-02-06T09:15:00'),
    last_activity: new Date('2026-02-06T11:25:00')
  },
  {
    _id: '3',
    user_name: 'Admin System',
    email: adminBrand.emails.admin,
    user_type: 'admin',
    status: 'active',
    device_type: 'desktop',
    ip_address: '192.168.1.100',
    location: 'Internal Network',
    created_at: new Date('2026-02-06T06:00:00'),
    last_activity: new Date('2026-02-06T11:28:00')
  }
])

const sessionSearch = ref('')
const sessionFilters = ref({
  userType: '',
  deviceType: ''
})
const sessionsPage = ref(1)
const sessionsPagination = ref(createPaginationState())
const sessionsSummary = ref({
  activeCount: 0,
  uniqueUsersOnline: 0,
  avgSessionDuration: 0,
})

const filteredSessions = computed(() => {
  return sessions.value
})
const visibleSessionsPages = computed(() => buildVisiblePages(sessionsPagination.value))

// Security Events
const securityEvents = ref([])

const securitySearch = ref('')
const securityFilters = ref({
  eventType: '',
  dateFrom: ''
})
const securityPage = ref(1)
const securityPagination = ref(createPaginationState())

const filteredSecurityEvents = computed(() => {
  return securityEvents.value
})
const visibleSecurityPages = computed(() => buildVisiblePages(securityPagination.value))

const failedLoginAttempts = ref(12)
const suspiciousActivities = ref(5)
const anomaliesDetected = ref(3)
const rateLimitHits = ref(18)

const authzFilters = ref({
  hours: 24,
  principalType: '',
  decision: '',
  permission: '',
  pathContains: '',
})
const authzSummary = ref({
  total: 0,
  allowed: 0,
  denied: 0,
  denialRate: 0,
})
const authzTopDeniedPermissions = ref([])
const authzTopDeniedRoutes = ref([])
const authzPrincipalBreakdown = ref([])
const authzEvents = ref([])
const authzTrendEvents = ref([])
const expandedAuthzRows = ref({})

const authzTrendBuckets = computed(() => {
  const bucketCount = 12
  const hours = Math.max(1, Number(authzFilters.value.hours || 24))
  const nowMs = Date.now()
  const windowMs = hours * 60 * 60 * 1000
  const startMs = nowMs - windowMs
  const buckets = Array.from({ length: bucketCount }, () => ({ allowed: 0, denied: 0 }))

  for (const event of authzTrendEvents.value) {
    const ts = Date.parse(event?.timestamp || '')
    if (Number.isNaN(ts) || ts < startMs || ts > nowMs) {
      continue
    }
    const ratio = (ts - startMs) / windowMs
    const idx = Math.min(bucketCount - 1, Math.max(0, Math.floor(ratio * bucketCount)))
    const decisionValue = String(event?.decision || '').toLowerCase()
    if (decisionValue === 'denied') {
      buckets[idx].denied += 1
    } else if (decisionValue === 'allowed') {
      buckets[idx].allowed += 1
    }
  }

  return buckets
})

const buildSparklinePoints = (decisionKey) => {
  const buckets = authzTrendBuckets.value
  const width = 220
  const height = 42
  const maxValue = Math.max(1, ...buckets.map((bucket) => Math.max(bucket.allowed, bucket.denied)))
  return buckets
    .map((bucket, index) => {
      const x = (index / Math.max(1, buckets.length - 1)) * (width - 4) + 2
      const y = height - 2 - ((Number(bucket[decisionKey]) || 0) / maxValue) * (height - 6)
      return `${x.toFixed(2)},${y.toFixed(2)}`
    })
    .join(' ')
}

const authzAllowedPoints = computed(() => buildSparklinePoints('allowed'))
const authzDeniedPoints = computed(() => buildSparklinePoints('denied'))

// Export & Analysis
const exportFormat = ref('csv')
const exportLogs = ref({
  activity: true,
  system: true,
  sessions: true,
  security: true
})
const exportDateRange = ref({
  from: '2026-02-01',
  to: '2026-02-06'
})
const complianceReports = ref({
  dataAccess: true,
  changes: true,
  security: true
})
const exportSuccess = ref('')
const exportError = ref('')

const activityStats = ref({
  total: 1250,
  creates: 340,
  updates: 680,
  deletes: 230
})

const topUsers = ref([
  { name: 'Admin User', count: 342 },
  { name: 'System Service', count: 289 },
  { name: 'Operator Manager', count: 156 }
])

const securityScore = ref(87)

// Modals
const showActivityModal = ref(false)
const selectedActivity = ref(null)
const showSessionModal = ref(false)
const selectedSession = ref(null)

const queueAuditReload = () => {
  if (suppressAuditWatch) {
    return
  }
  if (auditReloadTimer) {
    clearTimeout(auditReloadTimer)
  }
  auditReloadTimer = setTimeout(() => {
    auditReloadTimer = null
    loadAuditSummary()
  }, 250)
}

const syncPaginationState = (targetRef, pageRef, payload) => {
  const nextState = createPaginationState(payload || {})
  targetRef.value = nextState
  pageRef.value = nextState.page
}

const loadAuditSummary = async () => {
  loading.value = true
  loadError.value = ''

  try {
    const token = localStorage.getItem('adminToken')
    if (!token) {
      loadError.value = 'Admin token not found. Please login again.'
      return
    }

    const response = await api.get('/admin/audit/summary', {
      headers: { Authorization: `Bearer ${token}` },
      params: {
        system_page: systemPage.value,
        system_per_page: systemPagination.value.perPage,
        system_search: systemSearch.value,
        system_severity: systemFilters.value.severity,
        system_service: systemFilters.value.service,
        system_unread_only: systemFilters.value.unreadOnly,
        sessions_page: sessionsPage.value,
        sessions_per_page: sessionsPagination.value.perPage,
        session_search: sessionSearch.value,
        session_user_type: sessionFilters.value.userType,
        session_device_type: sessionFilters.value.deviceType,
        security_page: securityPage.value,
        security_per_page: securityPagination.value.perPage,
        security_search: securitySearch.value,
        security_event_type: securityFilters.value.eventType,
        security_date_from: securityFilters.value.dateFrom,
      },
    })

    const data = response.data || {}

    suppressAuditWatch = true
    try {
      if (Array.isArray(data.activityLogs)) activityLogs.value = data.activityLogs
      if (Array.isArray(data.systemEvents)) systemEvents.value = data.systemEvents
      if (Array.isArray(data.sessions)) sessions.value = data.sessions
      if (Array.isArray(data.securityEvents)) securityEvents.value = data.securityEvents

      syncPaginationState(systemPagination, systemPage, data.systemEventsPagination)
      syncPaginationState(sessionsPagination, sessionsPage, data.sessionsPagination)
      syncPaginationState(securityPagination, securityPage, data.securityEventsPagination)

      if (data.sessionsSummary) {
        sessionsSummary.value = {
          activeCount: Number(data.sessionsSummary.activeCount || 0),
          uniqueUsersOnline: Number(data.sessionsSummary.uniqueUsersOnline || 0),
          avgSessionDuration: Number(data.sessionsSummary.avgSessionDuration || 0),
        }
      }
    } finally {
      suppressAuditWatch = false
    }

    failedLoginAttempts.value = Number(data.failedLoginAttempts || 0)
    suspiciousActivities.value = Number(data.suspiciousActivities || 0)
    anomaliesDetected.value = Number(data.anomaliesDetected || 0)
    rateLimitHits.value = Number(data.rateLimitHits || 0)

    if (data.activityStats) {
      activityStats.value = {
        ...activityStats.value,
        ...data.activityStats
      }
    }

    if (Array.isArray(data.topUsers)) topUsers.value = data.topUsers
    if (typeof data.securityScore === 'number') securityScore.value = data.securityScore
  } catch (error) {
    console.error('Failed to load audit summary:', error)
    loadError.value = error.response?.data?.detail || 'Failed to load audit data'
  } finally {
    loading.value = false
  }
}

const queueAuthorizationReload = () => {
  if (authzReloadTimer) {
    clearTimeout(authzReloadTimer)
  }
  authzReloadTimer = setTimeout(() => {
    authzReloadTimer = null
    loadAuthorizationReport()
  }, 300)
}

const loadAuthorizationReport = async () => {
  if (activeTab.value !== 'security') {
    return
  }

  authzLoading.value = true
  authzError.value = ''
  try {
    const response = await api.get('/admin/audit/authorization-decisions', {
      params: {
        hours: authzFilters.value.hours,
        limit: 50,
        principal_type: authzFilters.value.principalType,
        decision: authzFilters.value.decision,
        permission: authzFilters.value.permission,
        path_contains: authzFilters.value.pathContains,
      },
    })
    const data = response.data || {}
    authzSummary.value = {
      total: Number(data.summary?.total || 0),
      allowed: Number(data.summary?.allowed || 0),
      denied: Number(data.summary?.denied || 0),
      denialRate: Number(data.summary?.denialRate || 0),
    }
    authzTopDeniedPermissions.value = Array.isArray(data.topDeniedPermissions) ? data.topDeniedPermissions : []
    authzTopDeniedRoutes.value = Array.isArray(data.topDeniedRoutes) ? data.topDeniedRoutes : []
    authzPrincipalBreakdown.value = Array.isArray(data.principalBreakdown) ? data.principalBreakdown : []
    authzTrendEvents.value = Array.isArray(data.events) ? data.events : []
    authzEvents.value = Array.isArray(data.events) ? data.events.slice(0, 12) : []
    expandedAuthzRows.value = {}
  } catch (error) {
    console.error('Failed to load authorization report:', error)
    authzError.value = error.response?.data?.detail || 'Failed to load authorization decision report'
  } finally {
    authzLoading.value = false
  }
}

onMounted(() => {
  loadAuditSummary()
})

onUnmounted(() => {
  if (auditReloadTimer) {
    clearTimeout(auditReloadTimer)
    auditReloadTimer = null
  }
  if (authzReloadTimer) {
    clearTimeout(authzReloadTimer)
    authzReloadTimer = null
  }
})

watch(activeTab, (nextTab) => {
  if (nextTab === 'security') {
    loadAuthorizationReport()
  }
})

watch([activitySearch, () => activityFilters.value.actionType, () => activityFilters.value.resource, () => activityFilters.value.dateFrom, () => activityFilters.value.dateTo], () => {
  activityPage.value = 1
})

watch([systemPage], queueAuditReload)
watch([() => systemSearch.value, () => systemFilters.value.severity, () => systemFilters.value.service, () => systemFilters.value.unreadOnly], () => {
  systemPage.value = 1
  queueAuditReload()
})

watch([sessionsPage], queueAuditReload)
watch([() => sessionSearch.value, () => sessionFilters.value.userType, () => sessionFilters.value.deviceType], () => {
  sessionsPage.value = 1
  queueAuditReload()
})

watch([securityPage], queueAuditReload)
watch([() => securitySearch.value, () => securityFilters.value.eventType, () => securityFilters.value.dateFrom], () => {
  securityPage.value = 1
  queueAuditReload()
})

watch(
  [
    () => authzFilters.value.hours,
    () => authzFilters.value.principalType,
    () => authzFilters.value.decision,
    () => authzFilters.value.permission,
    () => authzFilters.value.pathContains,
  ],
  () => {
    if (activeTab.value === 'security') {
      queueAuthorizationReload()
    }
  }
)

// Methods
const formatDateTime = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleString('en-IN')
}

const formatTime = (date) => {
  if (!date) return 'N/A'
  const now = new Date()
  const diff = Math.floor((now - new Date(date)) / 1000)
  
  if (diff < 60) return `${diff}s ago`
  if (diff < 3600) return `${Math.floor(diff / 60)}m ago`
  if (diff < 86400) return `${Math.floor(diff / 3600)}h ago`
  return new Date(date).toLocaleDateString('en-IN')
}

const getActionIcon = (action) => {
  const icons = {
    create: '➕',
    update: '✏️',
    delete: '🗑️',
    view: '👁️',
    export: '📥'
  }
  return icons[action] || '◉'
}

const getSeverityIcon = (severity) => {
  const icons = {
    critical: '🔴',
    warning: '🟡',
    info: '🔵'
  }
  return icons[severity] || '⚫'
}

const getDeviceIcon = (device) => {
  const icons = {
    desktop: '🖥️',
    mobile: '📱',
    tablet: '⌚'
  }
  return icons[device] || '💻'
}

const getSessionDuration = (start, end) => {
  const startDate = new Date(start)
  const endDate = new Date(end)
  return Math.floor((endDate - startDate) / (1000 * 60))
}

const getSecurityStatus = () => {
  if (securityScore.value >= 90) return 'excellent'
  if (securityScore.value >= 80) return 'good'
  if (securityScore.value >= 70) return 'fair'
  return 'poor'
}

const authzEventKey = (event, index) => {
  return `${event?.timestamp || 'na'}|${event?.principal_id || event?.principal_type || 'na'}|${event?.method || 'na'}|${event?.path || 'na'}|${index}`
}

const isAuthzRowExpanded = (key) => {
  return Boolean(expandedAuthzRows.value[key])
}

const toggleAuthzRow = (key) => {
  expandedAuthzRows.value = {
    ...expandedAuthzRows.value,
    [key]: !expandedAuthzRows.value[key],
  }
}

const viewActivityDetail = (activity) => {
  selectedActivity.value = activity
  showActivityModal.value = true
}

const viewSessionDetail = (session) => {
  selectedSession.value = session
  showSessionModal.value = true
}

const markEventRead = (event) => {
  event.read = true
}

const dismissEvent = (event) => {
  const index = systemEvents.value.findIndex(e => e._id === event._id)
  if (index > -1) {
    systemEvents.value.splice(index, 1)
  }
}

const refreshSessions = async () => {
  await loadAuditSummary()
}

const terminateSession = (session) => {
  if (confirm(`Terminate session for ${session.user_name}?`)) {
    session.status = 'terminated'
    alert('Session terminated successfully')
  }
}

const acknowledgeEvent = (event) => {
  alert(`Security event acknowledged: ${event.title}`)
}

const blockUser = (event) => {
  if (confirm(`Block user: ${event.user_name}?`)) {
    alert(`User ${event.user_name} has been blocked`)
  }
}

const exportAuditLogs = async () => {
  exportError.value = ''
  exportSuccess.value = ''
  
  if (!exportLogs.value.activity && !exportLogs.value.system && 
      !exportLogs.value.sessions && !exportLogs.value.security) {
    exportError.value = 'Please select at least one log type to export'
    return
  }
  
  exportSuccess.value = `Audit logs exported as ${exportFormat.value.toUpperCase()}!`
  setTimeout(() => { exportSuccess.value = '' }, 3000)
}

const resetExportForm = () => {
  exportLogs.value = { activity: true, system: true, sessions: true, security: true }
  complianceReports.value = { dataAccess: true, changes: true, security: true }
}
</script>

<style scoped>
.admin-audit {
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

/* Filter Controls */
.filter-controls,
.system-controls,
.sessions-controls,
.security-controls {
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

.checkbox {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  font-weight: 500;
  cursor: pointer;
}

/* Activity Timeline */
.activity-timeline {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.activity-item {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  display: flex;
  gap: 1.5rem;
  transition: all 0.2s;
}

.activity-item:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.activity-icon {
  font-size: 2rem;
  min-width: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.activity-content {
  flex: 1;
}

.activity-header {
  display: flex;
  gap: 1rem;
  align-items: center;
  margin-bottom: 0.5rem;
  flex-wrap: wrap;
}

.user-name {
  font-weight: 600;
  color: #1a202c;
}

.action-type {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  font-weight: 600;
}

.action-create { background: #dcfce7; color: #166534; }
.action-update { background: #e0e7ff; color: #3730a3; }
.action-delete { background: #fee2e2; color: #991b1b; }
.action-view { background: #dbeafe; color: #0c4a6e; }
.action-export { background: #fce7f3; color: #831843; }

.resource-type {
  font-size: 0.85rem;
  color: #718096;
  background: #f7fafc;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
}

.activity-description {
  margin: 0.5rem 0;
  color: #2d3748;
  line-height: 1.5;
}

.activity-details {
  display: flex;
  gap: 1.5rem;
  margin: 1rem 0;
  flex-wrap: wrap;
}

.detail-item {
  font-size: 0.85rem;
  color: #718096;
}

.activity-changes {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.changes-title {
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
}

.change-item {
  display: flex;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #4a5568;
}

.change-field {
  font-weight: 600;
  color: #1a202c;
}

.change-arrow {
  color: #a0aec0;
}

.change-from {
  color: #f56565;
  text-decoration: line-through;
}

.change-to {
  color: #48bb78;
  font-weight: 600;
}

.detail-btn {
  padding: 0.5rem 1rem;
  border: 2px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.2s;
}

.detail-btn:hover {
  border-color: #667eea;
  color: #667eea;
}

/* System Events */
.system-events-container {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.system-event {
  background: white;
  border-left: 4px solid #e2e8f0;
  border-radius: 8px;
  padding: 1.5rem;
  display: grid;
  grid-template-columns: 60px 1fr 100px;
  gap: 1.5rem;
  align-items: start;
  transition: all 0.2s;
}

.system-event:hover {
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.system-event.unread {
  background: #f0f9ff;
}

.system-event.severity-critical {
  border-left-color: #ef4444;
}

.system-event.severity-warning {
  border-left-color: #f59e0b;
}

.system-event.severity-info {
  border-left-color: #3b82f6;
}

.event-icon {
  font-size: 2rem;
  text-align: center;
}

.event-content {
  flex: 1;
}

.event-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
}

.event-title {
  margin: 0;
  color: #1a202c;
  font-weight: 600;
}

.event-time {
  font-size: 0.85rem;
  color: #718096;
}

.event-message {
  margin: 0.5rem 0;
  color: #2d3748;
}

.event-meta {
  display: flex;
  gap: 1.5rem;
  font-size: 0.85rem;
  color: #718096;
  margin: 0.75rem 0;
}

.meta-item {
  display: flex;
  gap: 0.5rem;
}

.event-details {
  margin-top: 1rem;
  padding-top: 1rem;
  border-top: 1px solid #e2e8f0;
}

.details-label {
  font-weight: 600;
  color: #2d3748;
  margin: 0 0 0.5rem 0;
}

.details-code {
  background: #1a202c;
  color: #48bb78;
  padding: 0.75rem;
  border-radius: 6px;
  font-size: 0.8rem;
  overflow-x: auto;
  display: block;
}

.event-actions {
  display: flex;
  gap: 0.5rem;
}

.action-btn {
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  background: white;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 1rem;
}

.action-btn:hover {
  background: #f7fafc;
  border-color: #667eea;
}

/* Sessions */
.sessions-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 2rem;
  gap: 1.5rem;
}

.sessions-stats {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  flex: 1;
}

.stat-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1rem;
  text-align: center;
}

.stat-label {
  margin: 0;
  font-size: 0.85rem;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.stat-value {
  margin: 0.5rem 0 0 0;
  font-size: 1.75rem;
  font-weight: 700;
  color: #667eea;
}

.sessions-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 1.5rem;
}

.session-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.session-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.session-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.user-info {
  flex: 1;
}

.user-name {
  margin: 0;
  font-weight: 600;
  color: #1a202c;
}

.user-email {
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

.status-active {
  background: #dcfce7;
  color: #166534;
}

.session-details {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1.5rem;
}

.detail-row {
  display: flex;
  justify-content: space-between;
  font-size: 0.9rem;
}

.detail-row .label {
  font-weight: 600;
  color: #718096;
}

.detail-row .value {
  color: #1a202c;
}

.session-actions {
  display: flex;
  gap: 0.5rem;
}

/* Security Alerts */
.security-alerts {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
  margin-bottom: 2rem;
}

.alert-card {
  padding: 1.5rem;
  border-radius: 12px;
  text-align: center;
  border-left: 4px solid;
}

.alert-label {
  margin: 0;
  font-size: 0.85rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.alert-count {
  margin: 0.75rem 0 0 0;
  font-size: 2.5rem;
  font-weight: 700;
}

.alert-critical {
  background: #fee2e2;
  color: #991b1b;
  border-left-color: #ef4444;
}

.alert-warning {
  background: #fef3c7;
  color: #b45309;
  border-left-color: #f59e0b;
}

.alert-info {
  background: #dbeafe;
  color: #0c4a6e;
  border-left-color: #3b82f6;
}

.authz-report-card {
  background: #ffffff;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.25rem;
  margin-bottom: 1.5rem;
}

.authz-report-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
  margin-bottom: 1rem;
}

.authz-report-header h3 {
  margin: 0;
  color: #1a202c;
}

.authz-report-header p {
  margin: 0.35rem 0 0 0;
  color: #64748b;
  font-size: 0.9rem;
}

.authz-controls {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.authz-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.authz-summary-item {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.9rem;
  background: #f8fafc;
}

.authz-summary-item.allowed {
  background: #ecfdf5;
  border-color: #86efac;
}

.authz-summary-item.denied {
  background: #fef2f2;
  border-color: #fca5a5;
}

.authz-summary-item.rate {
  background: #eff6ff;
  border-color: #93c5fd;
}

.authz-label {
  margin: 0;
  color: #64748b;
  font-size: 0.8rem;
  text-transform: uppercase;
  letter-spacing: 0.04em;
}

.authz-value {
  margin: 0.35rem 0 0 0;
  color: #0f172a;
  font-size: 1.35rem;
  font-weight: 700;
}

.authz-breakdown-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 0.75rem;
  margin-bottom: 1rem;
}

.authz-trend-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.85rem;
  background: #ffffff;
  margin-bottom: 1rem;
}

.authz-trend-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.45rem;
}

.authz-trend-header h4 {
  margin: 0;
  font-size: 0.95rem;
  color: #1e293b;
}

.authz-sparkline {
  width: 100%;
  max-width: 100%;
  height: 44px;
  background: #f8fafc;
  border-radius: 8px;
}

.sparkline-line {
  fill: none;
  stroke-width: 2;
}

.sparkline-line.allowed {
  stroke: #16a34a;
}

.sparkline-line.denied {
  stroke: #dc2626;
}

.authz-legend {
  display: flex;
  gap: 1rem;
  margin-top: 0.4rem;
}

.legend-item {
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
  color: #475569;
  font-size: 0.8rem;
}

.legend-dot {
  width: 8px;
  height: 8px;
  border-radius: 999px;
}

.legend-dot.allowed {
  background: #16a34a;
}

.legend-dot.denied {
  background: #dc2626;
}

.authz-list-card {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.85rem;
  background: #ffffff;
}

.authz-list-card h4 {
  margin: 0 0 0.6rem 0;
  font-size: 0.95rem;
  color: #1e293b;
}

.mini-empty {
  color: #94a3b8;
  font-size: 0.85rem;
}

.mini-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.mini-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.mini-row.stacked {
  flex-direction: column;
  align-items: flex-start;
}

.mini-name {
  color: #0f172a;
  font-size: 0.86rem;
  overflow-wrap: anywhere;
}

.mini-count {
  color: #334155;
  font-size: 0.85rem;
  font-weight: 700;
}

.mini-meta {
  color: #64748b;
  font-size: 0.8rem;
}

.authz-events-table-wrap {
  border: 1px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.85rem;
  overflow-x: auto;
}

.authz-events-table-wrap h4 {
  margin: 0 0 0.6rem 0;
  font-size: 0.95rem;
  color: #1e293b;
}

.authz-events-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 0.84rem;
}

.authz-events-table th,
.authz-events-table td {
  text-align: left;
  border-bottom: 1px solid #e2e8f0;
  padding: 0.55rem;
  vertical-align: top;
}

.authz-row {
  cursor: pointer;
}

.authz-row:hover td {
  background: #f8fafc;
}

.expand-indicator {
  display: inline-block;
  width: 1rem;
  color: #64748b;
  font-size: 0.75rem;
}

.authz-row-expanded td {
  background: #f8fafc;
}

.authz-detail-text {
  font-size: 0.84rem;
  color: #334155;
  white-space: pre-wrap;
}

.decision-pill {
  display: inline-block;
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
}

.decision-pill.allowed {
  background: #dcfce7;
  color: #166534;
}

.decision-pill.denied {
  background: #fee2e2;
  color: #991b1b;
}

/* Security Events */
.security-events-container {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.security-event {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  display: grid;
  grid-template-columns: auto 1fr auto 150px;
  gap: 1.5rem;
  align-items: start;
  transition: all 0.2s;
}

.security-event:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.event-type-badge {
  padding: 0.5rem 1rem;
  background: #f0f9ff;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  color: #0c4a6e;
  white-space: nowrap;
}

.event-info {
  flex: 1;
}

.info-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.info-header h4 {
  margin: 0;
  color: #1a202c;
}

.event-details {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  font-size: 0.9rem;
  color: #2d3748;
}

.event-details p {
  margin: 0;
}

.event-details strong {
  color: #1a202c;
}

.remediation-box {
  margin-top: 1rem;
  padding: 1rem;
  background: #f0fdf4;
  border-left: 3px solid #22c55e;
  border-radius: 6px;
}

.remediation-label {
  margin: 0;
  font-weight: 600;
  color: #166534;
  font-size: 0.9rem;
}

.remediation-text {
  margin: 0.5rem 0 0 0;
  color: #15803d;
  font-size: 0.85rem;
}

.event-risk {
  display: flex;
  align-items: center;
}

.risk-badge {
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.8rem;
}

.risk-critical {
  background: #fee2e2;
  color: #991b1b;
}

.risk-warning {
  background: #fef3c7;
  color: #b45309;
}

.event-actions {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

/* Export & Analysis */
.export-section,
.analysis-section {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  margin-bottom: 2rem;
}

.export-section h3,
.analysis-section h3 {
  margin: 0 0 1.5rem 0;
  color: #1a202c;
  font-size: 1.1rem;
}

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

.date-inputs {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.date-inputs .input {
  flex: 1;
}

.input {
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.9rem;
}

.export-actions {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  margin-bottom: 1.5rem;
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

.analysis-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1.5rem;
}

.analysis-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  transition: all 0.2s;
}

.analysis-card:hover {
  border-color: #667eea;
  box-shadow: 0 5px 15px rgba(0, 0, 0, 0.1);
}

.analysis-card h4 {
  margin: 0 0 1rem 0;
  color: #1a202c;
}

.analysis-content {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.analysis-content p {
  margin: 0;
  font-size: 0.9rem;
  color: #2d3748;
}

.user-stat {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.5rem 0;
}

.user-rank {
  font-weight: 700;
  color: #667eea;
  min-width: 20px;
}

.user-name {
  flex: 1;
  color: #1a202c;
}

.user-count {
  font-weight: 600;
  color: #718096;
}

.security-score {
  align-items: center;
  justify-content: center;
}

.score-display {
  text-align: center;
}

.score-value {
  margin: 0;
  font-size: 2.5rem;
  font-weight: 700;
  color: #667eea;
}

.score-label {
  margin: 0;
  font-size: 0.9rem;
  color: #718096;
}

.score-status {
  margin-top: 0.5rem;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
  text-align: center;
}

.status-excellent {
  background: #dcfce7;
  color: #166534;
}

.status-good {
  background: #e0e7ff;
  color: #3730a3;
}

.status-fair {
  background: #fef3c7;
  color: #b45309;
}

.status-poor {
  background: #fee2e2;
  color: #991b1b;
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

.detail-section {
  margin-bottom: 1.5rem;
}

.detail-section h3 {
  margin: 0 0 1rem 0;
  font-size: 1rem;
  color: #1a202c;
  border-bottom: 1px solid #e2e8f0;
  padding-bottom: 0.5rem;
}

.detail-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1.5rem;
}

.detail-item {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.detail-item .label {
  font-weight: 600;
  color: #718096;
  font-size: 0.85rem;
}

.detail-item .value {
  color: #1a202c;
  font-size: 0.95rem;
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

.pagination-summary {
  color: #718096;
  font-size: 0.9rem;
  font-weight: 600;
}

.sessions-pagination {
  grid-column: 1 / -1;
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

  .filter-controls,
  .system-controls,
  .sessions-controls,
  .security-controls,
  .authz-controls {
    flex-direction: column;
  }

  .search-input,
  .filter-select,
  .filter-input {
    width: 100%;
  }

  .activity-item {
    flex-direction: column;
  }

  .system-event,
  .security-event {
    grid-template-columns: 1fr;
  }

  .sessions-grid {
    grid-template-columns: 1fr;
  }

  .session-header {
    flex-direction: column;
  }

  .export-options {
    grid-template-columns: 1fr;
  }

  .analysis-grid {
    grid-template-columns: 1fr;
  }

  .detail-grid {
    grid-template-columns: 1fr;
  }
}
</style>
