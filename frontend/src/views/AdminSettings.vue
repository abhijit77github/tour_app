<template>
  <div class="admin-settings">
    <div class="page-header">
      <h1>System Settings</h1>
      <p class="subtitle">Configure and manage all system settings and configurations</p>
    </div>

    <div v-if="loading" class="status-message">Loading settings data...</div>
    <div v-else-if="loadError" class="error-message">{{ loadError }}</div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        @click="activeTab = 'general'"
        :class="['tab', { active: activeTab === 'general' }]"
      >
        ⚙️ General Settings
      </button>
      <button
        @click="activeTab = 'health'"
        :class="['tab', { active: activeTab === 'health' }]"
      >
        💚 System Health
      </button>
      <button
        @click="activeTab = 'users'"
        :class="['tab', { active: activeTab === 'users' }]"
      >
        👥 User Management
      </button>
      <button
        @click="activeTab = 'maintenance'"
        :class="['tab', { active: activeTab === 'maintenance' }]"
      >
        🔧 Backup & Maintenance
      </button>
      <button
        @click="activeTab = 'security'"
        :class="['tab', { active: activeTab === 'security' }]"
      >
        🔒 Security Settings
      </button>
      <button
        @click="activeTab = 'integration'"
        :class="['tab', { active: activeTab === 'integration' }]"
      >
        🔗 Integration
      </button>
    </div>

    <!-- General Settings Tab -->
    <div v-if="activeTab === 'general'" class="tab-content">
      <div class="settings-section">
        <h3>General Settings</h3>

        <div class="settings-grid">
          <!-- Application Settings -->
          <div class="settings-card">
            <h4>📱 Application Settings</h4>

            <div class="form-group">
              <label>Application Name</label>
              <input v-model="settings.general.appName" type="text" class="input" />
            </div>

            <div class="form-group">
              <label>Application URL</label>
              <input v-model="settings.general.appUrl" type="url" class="input" />
            </div>

            <div class="form-group">
              <label>Support Email</label>
              <input v-model="settings.general.supportEmail" type="email" class="input" />
            </div>

            <div class="form-group">
              <label>Support Phone</label>
              <input v-model="settings.general.supportPhone" type="tel" class="input" />
            </div>

            <button @click="saveGeneralSettings" class="btn btn-primary">💾 Save Changes</button>
          </div>

          <!-- Localization -->
          <div class="settings-card">
            <h4>🌍 Localization</h4>

            <div class="form-group">
              <label>Default Language</label>
              <select v-model="settings.general.defaultLanguage" class="input">
                <option value="en">English</option>
                <option value="es">Spanish</option>
                <option value="fr">French</option>
                <option value="de">German</option>
                <option value="hi">Hindi</option>
              </select>
            </div>

            <div class="form-group">
              <label>Timezone</label>
              <select v-model="settings.general.timezone" class="input">
                <option value="UTC">UTC</option>
                <option value="IST">IST (India)</option>
                <option value="EST">EST (US Eastern)</option>
                <option value="PST">PST (US Pacific)</option>
                <option value="GMT">GMT (UK)</option>
              </select>
            </div>

            <div class="form-group">
              <label>Date Format</label>
              <select v-model="settings.general.dateFormat" class="input">
                <option value="DD/MM/YYYY">DD/MM/YYYY</option>
                <option value="MM/DD/YYYY">MM/DD/YYYY</option>
                <option value="YYYY-MM-DD">YYYY-MM-DD</option>
              </select>
            </div>

            <button @click="saveLocalization" class="btn btn-primary">💾 Save Changes</button>
          </div>

          <!-- Feature Flags -->
          <div class="settings-card">
            <h4>🚩 Feature Flags</h4>

            <div class="checkbox-group">
              <label>
                <input v-model="settings.general.enableNotifications" type="checkbox" />
                <span>Enable Notifications</span>
              </label>
              <label>
                <input v-model="settings.general.enableReports" type="checkbox" />
                <span>Enable Reports</span>
              </label>
              <label>
                <input v-model="settings.general.enableAnalytics" type="checkbox" />
                <span>Enable Analytics</span>
              </label>
              <label>
                <input v-model="settings.general.enableApiAccess" type="checkbox" />
                <span>Enable API Access</span>
              </label>
              <label>
                <input v-model="settings.general.maintenanceMode" type="checkbox" />
                <span>Maintenance Mode</span>
              </label>
            </div>

            <button @click="saveFeatureFlags" class="btn btn-primary">💾 Save Changes</button>
          </div>
        </div>
      </div>
    </div>

    <!-- System Health Tab -->
    <div v-else-if="activeTab === 'health'" class="tab-content">
      <div class="health-section">
        <h3>System Health & Status</h3>

        <div class="health-grid">
          <!-- Overall Status -->
          <div class="status-card">
            <div class="status-header">
              <h4>🎯 Overall System Status</h4>
              <span :class="['status-indicator', `status-${systemHealth.overall}`]">
                {{ systemHealth.overall === 'healthy' ? '🟢' : '🟡' }} {{ systemHealth.overall }}
              </span>
            </div>
            <p class="status-message">All systems operational</p>
          </div>

          <!-- Database Status -->
          <div class="status-card">
            <div class="status-header">
              <h4>🗄️ Database</h4>
              <span :class="['status-indicator', `status-${systemHealth.database}`]">
                {{ systemHealth.database === 'healthy' ? '🟢' : '🟡' }} {{ systemHealth.database }}
              </span>
            </div>
            <div class="status-details">
              <p><strong>Connection:</strong> <span class="badge badge-success">Active</span></p>
              <p><strong>Response Time:</strong> {{ systemHealth.dbResponseTime }}ms</p>
              <p><strong>Queries/sec:</strong> {{ systemHealth.dbQueries }}</p>
            </div>
          </div>

          <!-- API Server -->
          <div class="status-card">
            <div class="status-header">
              <h4>🖥️ API Server</h4>
              <span :class="['status-indicator', `status-${systemHealth.apiServer}`]">
                {{ systemHealth.apiServer === 'healthy' ? '🟢' : '🟡' }} {{ systemHealth.apiServer }}
              </span>
            </div>
            <div class="status-details">
              <p><strong>Uptime:</strong> {{ systemHealth.apiUptime }}</p>
              <p><strong>CPU Usage:</strong> {{ systemHealth.cpuUsage }}%</p>
              <p><strong>Memory Usage:</strong> {{ systemHealth.memoryUsage }}%</p>
            </div>
          </div>

          <!-- Cache System -->
          <div class="status-card">
            <div class="status-header">
              <h4>⚡ Cache System</h4>
              <span :class="['status-indicator', `status-${systemHealth.cache}`]">
                {{ systemHealth.cache === 'healthy' ? '🟢' : '🟡' }} {{ systemHealth.cache }}
              </span>
            </div>
            <div class="status-details">
              <p><strong>Cache Hit Rate:</strong> {{ systemHealth.cacheHitRate }}%</p>
              <p><strong>Cached Items:</strong> {{ systemHealth.cachedItems }}</p>
              <p><strong>Cache Size:</strong> {{ systemHealth.cacheSize }}MB</p>
            </div>
          </div>

          <!-- Email Service -->
          <div class="status-card">
            <div class="status-header">
              <h4>📧 Email Service</h4>
              <span :class="['status-indicator', `status-${systemHealth.emailService}`]">
                {{ systemHealth.emailService === 'healthy' ? '🟢' : '🟡' }} {{ systemHealth.emailService }}
              </span>
            </div>
            <div class="status-details">
              <p><strong>Emails Sent Today:</strong> {{ systemHealth.emailsSent }}</p>
              <p><strong>Failed Emails:</strong> {{ systemHealth.emailsFailed }}</p>
              <p><strong>Queue Size:</strong> {{ systemHealth.emailQueueSize }}</p>
            </div>
          </div>

          <!-- Storage -->
          <div class="status-card">
            <div class="status-header">
              <h4>💾 Storage</h4>
              <span :class="['status-indicator', `status-${systemHealth.storage}`]">
                {{ systemHealth.storage === 'healthy' ? '🟢' : '🟡' }} {{ systemHealth.storage }}
              </span>
            </div>
            <div class="status-details">
              <p><strong>Used Space:</strong> {{ systemHealth.storageUsed }}GB / {{ systemHealth.storageTotal }}GB</p>
              <p><strong>Usage Percentage:</strong> <span class="usage-bar">{{ systemHealth.storagePercent }}%</span></p>
            </div>
          </div>
        </div>

        <div class="health-actions">
          <button @click="checkSystemHealth" class="btn btn-secondary">🔄 Refresh Status</button>
          <button @click="viewDetailedLogs" class="btn btn-secondary">📋 View Logs</button>
        </div>
      </div>
    </div>

    <!-- User Management Tab -->
    <div v-else-if="activeTab === 'users'" class="tab-content">
      <div class="users-section">
        <h3>Admin User Management</h3>

        <div class="users-controls">
          <input
            v-model="userSearch"
            type="text"
            placeholder="Search by name or email..."
            class="search-input"
          />
          <button @click="showAddUserModal = true" class="btn btn-primary">➕ Add Admin User</button>
        </div>

        <div v-if="adminUsers.length === 0" class="empty-state">
          <p>👤 No admin users found</p>
        </div>

        <div v-else class="users-table">
          <table>
            <thead>
              <tr>
                <th>Name</th>
                <th>Email</th>
                <th>Role</th>
                <th>Status</th>
                <th>Last Login</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="user in filteredAdminUsers" :key="user._id">
                <td>
                  <div class="user-info">
                    <span class="avatar">{{ getInitials(user.name) }}</span>
                    <span>{{ user.name }}</span>
                  </div>
                </td>
                <td>{{ user.email }}</td>
                <td>
                  <select v-model="user.role" class="role-select">
                    <option value="admin">Admin</option>
                    <option value="manager">Manager</option>
                    <option value="supervisor">Supervisor</option>
                  </select>
                </td>
                <td>
                  <span :class="['status-badge', `badge-${user.status}`]">
                    {{ user.status === 'active' ? '🟢' : '🔴' }} {{ user.status }}
                  </span>
                </td>
                <td>{{ formatDateTime(user.lastLogin) }}</td>
                <td>
                  <button @click="editUser(user)" class="btn btn-small btn-secondary">✏️</button>
                  <button @click="resetUserPassword(user)" class="btn btn-small">🔑</button>
                  <button @click="deactivateUser(user)" class="btn btn-small btn-danger">🗑️</button>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- Add Admin User Modal -->
      <div v-if="showAddUserModal" class="modal-overlay" @click.self="showAddUserModal = false">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Add Admin User</h2>
            <button @click="showAddUserModal = false" class="close-btn">✕</button>
          </div>

          <form @submit.prevent="saveAdminUser" class="modal-body">
            <div class="form-group">
              <label>Full Name</label>
              <input v-model="addUserForm.name" type="text" class="input" required />
            </div>

            <div class="form-group">
              <label>Email</label>
              <input v-model="addUserForm.email" type="email" class="input" required />
            </div>

            <div class="form-group">
              <label>Role</label>
              <select v-model="addUserForm.role" class="input" required>
                <option value="admin">Admin</option>
                <option value="manager">Manager</option>
                <option value="supervisor">Supervisor</option>
              </select>
            </div>

            <div class="form-group">
              <label>Permissions</label>
              <div class="checkbox-group">
                <label>
                  <input v-model="addUserForm.permissions" type="checkbox" value="manage_users" />
                  <span>Manage Users</span>
                </label>
                <label>
                  <input v-model="addUserForm.permissions" type="checkbox" value="manage_reports" />
                  <span>Manage Reports</span>
                </label>
                <label>
                  <input v-model="addUserForm.permissions" type="checkbox" value="manage_settings" />
                  <span>Manage Settings</span>
                </label>
                <label>
                  <input v-model="addUserForm.permissions" type="checkbox" value="view_analytics" />
                  <span>View Analytics</span>
                </label>
              </div>
            </div>

            <div class="form-actions">
              <button type="button" @click="showAddUserModal = false" class="btn btn-secondary">Cancel</button>
              <button type="submit" class="btn btn-primary">Add User</button>
            </div>
          </form>
        </div>
      </div>
    </div>

    <!-- Backup & Maintenance Tab -->
    <div v-else-if="activeTab === 'maintenance'" class="tab-content">
      <div class="maintenance-section">
        <h3>Backup & Maintenance</h3>

        <div class="maintenance-grid">
          <!-- Database Backup -->
          <div class="maintenance-card">
            <h4>🗄️ Database Backup</h4>

            <div class="status-info">
              <p><strong>Last Backup:</strong> {{ formatDateTime(backupInfo.lastBackup) }}</p>
              <p><strong>Backup Size:</strong> {{ backupInfo.lastBackupSize }}</p>
              <p><strong>Backup Status:</strong> <span class="badge badge-success">✓ Completed</span></p>
            </div>

            <div class="form-group">
              <label>Backup Frequency</label>
              <select v-model="backupSettings.frequency" class="input">
                <option value="hourly">Hourly</option>
                <option value="daily">Daily</option>
                <option value="weekly">Weekly</option>
                <option value="monthly">Monthly</option>
              </select>
            </div>

            <div class="form-group">
              <label>Retention Days</label>
              <input v-model.number="backupSettings.retentionDays" type="number" class="input" />
            </div>

            <button @click="performBackup" class="btn btn-primary">🔄 Perform Backup Now</button>
            <button @click="downloadLatestBackup" class="btn btn-secondary">📥 Download Latest</button>
          </div>

          <!-- File Backup -->
          <div class="maintenance-card">
            <h4>📁 File & Attachments</h4>

            <div class="status-info">
              <p><strong>Total Files:</strong> {{ backupInfo.totalFiles }}</p>
              <p><strong>Total Size:</strong> {{ backupInfo.filesSize }}</p>
              <p><strong>Last Backed Up:</strong> {{ formatDateTime(backupInfo.filesLastBackup) }}</p>
            </div>

            <div class="form-group">
              <label>Auto Backup</label>
              <input v-model="backupSettings.autoBackup" type="checkbox" />
              <span class="checkbox-label">Enable automatic backups</span>
            </div>

            <button @click="backupFiles" class="btn btn-primary">📦 Backup Files Now</button>
            <button @click="restoreFromBackup" class="btn btn-warning">↩️ Restore</button>
          </div>

          <!-- Cache & Cleanup -->
          <div class="maintenance-card">
            <h4>🧹 Cache & Cleanup</h4>

            <div class="status-info">
              <p><strong>Cache Size:</strong> {{ maintenanceInfo.cacheSize }}</p>
              <p><strong>Temp Files:</strong> {{ maintenanceInfo.tempFiles }}</p>
              <p><strong>Logs Size:</strong> {{ maintenanceInfo.logsSize }}</p>
            </div>

            <button @click="clearCache" class="btn btn-secondary">🗑️ Clear Cache</button>
            <button @click="cleanupTempFiles" class="btn btn-secondary">🧹 Cleanup Temp Files</button>
            <button @click="archiveLogs" class="btn btn-secondary">📦 Archive Old Logs</button>
          </div>

          <!-- System Optimization -->
          <div class="maintenance-card">
            <h4>⚡ System Optimization</h4>

            <div class="status-info">
              <p><strong>Last Optimized:</strong> {{ formatDateTime(maintenanceInfo.lastOptimized) }}</p>
              <p><strong>Fragmentation:</strong> {{ maintenanceInfo.fragmentation }}%</p>
            </div>

            <button @click="optimizeDatabase" class="btn btn-primary">🚀 Optimize Database</button>
            <button @click="rebuildIndexes" class="btn btn-secondary">🔨 Rebuild Indexes</button>
            <button @click="defragment" class="btn btn-secondary">📊 Defragment</button>
          </div>
        </div>

        <div class="backup-history">
          <h4>📋 Backup History</h4>
          <div v-for="backup in backupHistory" :key="backup._id" class="backup-item">
            <span class="backup-date">{{ formatDateTime(backup.date) }}</span>
            <span class="backup-size">{{ backup.size }}</span>
            <span :class="['backup-status', `status-${backup.status}`]">{{ backup.status }}</span>
            <button @click="downloadBackup(backup)" class="btn btn-small">📥</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Security Settings Tab -->
    <div v-else-if="activeTab === 'security'" class="tab-content">
      <div class="security-section">
        <h3>Security Settings</h3>

        <div class="security-grid">
          <!-- Authentication -->
          <div class="security-card">
            <h4>🔐 Authentication</h4>

            <div class="form-group">
              <label>Session Timeout (minutes)</label>
              <input v-model.number="securitySettings.sessionTimeout" type="number" class="input" />
            </div>

            <div class="form-group">
              <label>Max Login Attempts</label>
              <input v-model.number="securitySettings.maxLoginAttempts" type="number" class="input" />
            </div>

            <div class="form-group">
              <label>Account Lockout Duration (minutes)</label>
              <input v-model.number="securitySettings.lockoutDuration" type="number" class="input" />
            </div>

            <div class="checkbox-group">
              <label>
                <input v-model="securitySettings.twoFactorEnabled" type="checkbox" />
                <span>Require Two-Factor Authentication</span>
              </label>
              <label>
                <input v-model="securitySettings.enforceStrongPasswords" type="checkbox" />
                <span>Enforce Strong Passwords</span>
              </label>
            </div>

            <button @click="saveAuthSettings" class="btn btn-primary">💾 Save</button>
          </div>

          <!-- Password Policy -->
          <div class="security-card">
            <h4>🔑 Password Policy</h4>

            <div class="form-group">
              <label>Minimum Password Length</label>
              <input v-model.number="securitySettings.passwordMinLength" type="number" class="input" />
            </div>

            <div class="form-group">
              <label>Password Expiry (days)</label>
              <input v-model.number="securitySettings.passwordExpiry" type="number" class="input" />
            </div>

            <div class="checkbox-group">
              <label>
                <input v-model="securitySettings.requireUppercase" type="checkbox" />
                <span>Require Uppercase (A-Z)</span>
              </label>
              <label>
                <input v-model="securitySettings.requireNumbers" type="checkbox" />
                <span>Require Numbers (0-9)</span>
              </label>
              <label>
                <input v-model="securitySettings.requireSpecialChars" type="checkbox" />
                <span>Require Special Characters (!@#$)</span>
              </label>
            </div>

            <button @click="savePasswordPolicy" class="btn btn-primary">💾 Save</button>
          </div>

          <!-- IP Whitelist -->
          <div class="security-card">
            <h4>🔒 IP Whitelist</h4>

            <div class="whitelist-info">
              <p>Allowed IPs: {{ securitySettings.ipWhitelist.length }}</p>
            </div>

            <textarea
              v-model="whitelistInput"
              class="textarea"
              placeholder="Enter IP addresses (one per line)"
              rows="4"
            ></textarea>

            <button @click="saveIpWhitelist" class="btn btn-primary">💾 Save</button>
          </div>

          <!-- Data Protection -->
          <div class="security-card">
            <h4>🛡️ Data Protection</h4>

            <div class="checkbox-group">
              <label>
                <input v-model="securitySettings.enableEncryption" type="checkbox" />
                <span>Enable Data Encryption</span>
              </label>
              <label>
                <input v-model="securitySettings.enableSSL" type="checkbox" />
                <span>Enforce SSL/TLS</span>
              </label>
              <label>
                <input v-model="securitySettings.enableAuditLog" type="checkbox" />
                <span>Enable Audit Logging</span>
              </label>
              <label>
                <input v-model="securitySettings.enableDataMasking" type="checkbox" />
                <span>Enable Data Masking for Logs</span>
              </label>
            </div>

            <button @click="saveDataProtection" class="btn btn-primary">💾 Save</button>
          </div>
        </div>
      </div>
    </div>

    <!-- Integration Tab -->
    <div v-else-if="activeTab === 'integration'" class="tab-content">
      <div class="integration-section">
        <h3>Integrations & APIs</h3>

        <div class="integration-grid">
          <!-- API Keys -->
          <div class="integration-card">
            <h4>🔑 API Keys</h4>

            <div class="api-keys-list">
              <div v-for="key in apiKeys" :key="key._id" class="api-key-item">
                <div class="key-info">
                  <p><strong>{{ key.name }}</strong></p>
                  <p class="key-value">{{ maskApiKey(key.key) }}</p>
                  <p class="key-meta">Created: {{ formatDate(key.created_at) }} • Last used: {{ formatDateTime(key.lastUsed) }}</p>
                </div>
                <div class="key-actions">
                  <button @click="copyApiKey(key)" class="btn btn-small">📋</button>
                  <button @click="revokeApiKey(key)" class="btn btn-small btn-danger">🗑️</button>
                </div>
              </div>
            </div>

            <button @click="showGenerateKeyModal = true" class="btn btn-primary">➕ Generate New Key</button>
          </div>

          <!-- Webhooks -->
          <div class="integration-card">
            <h4>🪝 Webhooks</h4>

            <div class="webhooks-list">
              <div v-for="webhook in webhooks" :key="webhook._id" class="webhook-item">
                <div class="webhook-info">
                  <p><strong>{{ webhook.event }}</strong></p>
                  <p class="webhook-url">{{ webhook.url }}</p>
                  <p class="webhook-meta">Status: <span :class="['status-badge', `badge-${webhook.status}`]">{{ webhook.status }}</span></p>
                </div>
                <div class="webhook-actions">
                  <button @click="testWebhook(webhook)" class="btn btn-small btn-secondary">🧪 Test</button>
                  <button @click="deleteWebhook(webhook)" class="btn btn-small btn-danger">🗑️</button>
                </div>
              </div>
            </div>

            <button @click="showAddWebhookModal = true" class="btn btn-primary">➕ Add Webhook</button>
          </div>

          <!-- Third-party Services -->
          <div class="integration-card">
            <h4>🌐 Third-party Services</h4>

            <div class="services-list">
              <div v-for="service in thirdPartyServices" :key="service._id" class="service-item">
                <div class="service-info">
                  <p><strong>{{ service.name }}</strong></p>
                  <p class="service-status">
                    <span :class="['status-indicator', `status-${service.status}`]">
                      {{ service.status === 'connected' ? '🟢' : '🔴' }} {{ service.status }}
                    </span>
                  </p>
                </div>
                <div class="service-actions">
                  <button v-if="service.status === 'connected'" @click="disconnectService(service)" class="btn btn-small btn-danger">
                    🔌 Disconnect
                  </button>
                  <button v-else @click="connectService(service)" class="btn btn-small btn-primary">
                    ⚡ Connect
                  </button>
                </div>
              </div>
            </div>
          </div>

          <!-- Rate Limiting -->
          <div class="integration-card">
            <h4>⏱️ Rate Limiting</h4>

            <div class="form-group">
              <label>Requests per Minute</label>
              <input v-model.number="integrationSettings.rateLimitPerMinute" type="number" class="input" />
            </div>

            <div class="form-group">
              <label>Requests per Hour</label>
              <input v-model.number="integrationSettings.rateLimitPerHour" type="number" class="input" />
            </div>

            <div class="form-group">
              <label>Requests per Day</label>
              <input v-model.number="integrationSettings.rateLimitPerDay" type="number" class="input" />
            </div>

            <button @click="saveRateLimiting" class="btn btn-primary">💾 Save</button>
          </div>
        </div>
      </div>

      <!-- Generate API Key Modal -->
      <div v-if="showGenerateKeyModal" class="modal-overlay" @click.self="showGenerateKeyModal = false">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Generate API Key</h2>
            <button @click="showGenerateKeyModal = false" class="close-btn">✕</button>
          </div>

          <form @submit.prevent="generateApiKey" class="modal-body">
            <div class="form-group">
              <label>Key Name</label>
              <input v-model="apiKeyForm.name" type="text" class="input" required placeholder="e.g., Mobile App" />
            </div>

            <div class="form-group">
              <label>Permissions</label>
              <div class="checkbox-group">
                <label>
                  <input v-model="apiKeyForm.permissions" type="checkbox" value="read" />
                  <span>Read Access</span>
                </label>
                <label>
                  <input v-model="apiKeyForm.permissions" type="checkbox" value="write" />
                  <span>Write Access</span>
                </label>
                <label>
                  <input v-model="apiKeyForm.permissions" type="checkbox" value="admin" />
                  <span>Admin Access</span>
                </label>
              </div>
            </div>

            <div class="form-actions">
              <button type="button" @click="showGenerateKeyModal = false" class="btn btn-secondary">Cancel</button>
              <button type="submit" class="btn btn-primary">Generate Key</button>
            </div>
          </form>
        </div>
      </div>

      <!-- Add Webhook Modal -->
      <div v-if="showAddWebhookModal" class="modal-overlay" @click.self="showAddWebhookModal = false">
        <div class="modal-content">
          <div class="modal-header">
            <h2>Add Webhook</h2>
            <button @click="showAddWebhookModal = false" class="close-btn">✕</button>
          </div>

          <form @submit.prevent="saveWebhook" class="modal-body">
            <div class="form-group">
              <label>Event Type</label>
              <select v-model="webhookForm.event" class="input" required>
                <option value="">Select event...</option>
                <option value="booking.created">Booking Created</option>
                <option value="booking.cancelled">Booking Cancelled</option>
                <option value="payment.completed">Payment Completed</option>
                <option value="user.registered">User Registered</option>
              </select>
            </div>

            <div class="form-group">
              <label>Webhook URL</label>
              <input v-model="webhookForm.url" type="url" class="input" required placeholder="https://..." />
            </div>

            <div class="form-actions">
              <button type="button" @click="showAddWebhookModal = false" class="btn btn-secondary">Cancel</button>
              <button type="submit" class="btn btn-primary">Add Webhook</button>
            </div>
          </form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'

const activeTab = ref('general')
const loading = ref(false)
const loadError = ref('')

// General Settings
const settings = ref({
  general: {
    appName: 'Tour App',
    appUrl: 'https://tourapp.com',
    supportEmail: 'support@tourapp.com',
    supportPhone: '+91-9876543210',
    defaultLanguage: 'en',
    timezone: 'IST',
    dateFormat: 'DD/MM/YYYY',
    enableNotifications: true,
    enableReports: true,
    enableAnalytics: true,
    enableApiAccess: true,
    maintenanceMode: false
  }
})

// System Health
const systemHealth = ref({
  overall: 'healthy',
  database: 'healthy',
  apiServer: 'healthy',
  cache: 'healthy',
  emailService: 'healthy',
  storage: 'healthy',
  dbResponseTime: 45,
  dbQueries: 1250,
  apiUptime: '45 days 12 hours',
  cpuUsage: 32,
  memoryUsage: 58,
  cacheHitRate: 92,
  cachedItems: 15420,
  cacheSize: 256,
  emailsSent: 1248,
  emailsFailed: 3,
  emailQueueSize: 12,
  storageUsed: 245,
  storageTotal: 500,
  storagePercent: 49
})

// Admin Users
const adminUsers = ref([
  {
    _id: '1',
    name: 'Rajesh Kumar',
    email: 'rajesh@tourapp.com',
    role: 'admin',
    status: 'active',
    lastLogin: new Date('2026-02-06T10:30:00')
  },
  {
    _id: '2',
    name: 'Priya Singh',
    email: 'priya@tourapp.com',
    role: 'manager',
    status: 'active',
    lastLogin: new Date('2026-02-06T09:15:00')
  },
  {
    _id: '3',
    name: 'Amit Patel',
    email: 'amit@tourapp.com',
    role: 'supervisor',
    status: 'active',
    lastLogin: new Date('2026-02-05T14:45:00')
  }
])

const userSearch = ref('')
const filteredAdminUsers = computed(() => {
  return adminUsers.value.filter(user => 
    !userSearch.value || 
    user.name.toLowerCase().includes(userSearch.value.toLowerCase()) ||
    user.email.toLowerCase().includes(userSearch.value.toLowerCase())
  )
})

// Backup Info
const backupInfo = ref({
  lastBackup: new Date('2026-02-06T02:30:00'),
  lastBackupSize: '2.4 GB',
  totalFiles: 45230,
  filesSize: '125 GB',
  filesLastBackup: new Date('2026-02-06T03:00:00')
})

const backupSettings = ref({
  frequency: 'daily',
  retentionDays: 30,
  autoBackup: true
})

const backupHistory = ref([
  { _id: '1', date: new Date('2026-02-06T02:30:00'), size: '2.4 GB', status: 'completed' },
  { _id: '2', date: new Date('2026-02-05T02:15:00'), size: '2.3 GB', status: 'completed' },
  { _id: '3', date: new Date('2026-02-04T02:45:00'), size: '2.5 GB', status: 'completed' }
])

const maintenanceInfo = ref({
  cacheSize: '512 MB',
  tempFiles: 234,
  logsSize: '2.1 GB',
  lastOptimized: new Date('2026-02-01T14:00:00'),
  fragmentation: 8
})

// Security Settings
const securitySettings = ref({
  sessionTimeout: 30,
  maxLoginAttempts: 5,
  lockoutDuration: 15,
  twoFactorEnabled: true,
  enforceStrongPasswords: true,
  passwordMinLength: 8,
  passwordExpiry: 90,
  requireUppercase: true,
  requireNumbers: true,
  requireSpecialChars: true,
  ipWhitelist: ['192.168.1.1', '10.0.0.1', '172.16.0.1'],
  enableEncryption: true,
  enableSSL: true,
  enableAuditLog: true,
  enableDataMasking: true
})

const whitelistInput = ref('192.168.1.1\n10.0.0.1\n172.16.0.1')

// Integration
const apiKeys = ref([
  { _id: '1', name: 'Mobile App', key: 'sk_live_abc123def456ghi789', created_at: new Date('2026-01-15'), lastUsed: new Date('2026-02-06T10:15:00') },
  { _id: '2', name: 'Web Dashboard', key: 'sk_live_xyz789uvw456rst123', created_at: new Date('2025-12-01'), lastUsed: new Date('2026-02-05T15:30:00') }
])

const webhooks = ref([
  { _id: '1', event: 'booking.created', url: 'https://example.com/booking-created', status: 'active' },
  { _id: '2', event: 'payment.completed', url: 'https://example.com/payment-webhook', status: 'active' }
])

const thirdPartyServices = ref([
  { _id: '1', name: 'Stripe (Payments)', status: 'connected' },
  { _id: '2', name: 'Twilio (SMS)', status: 'connected' },
  { _id: '3', name: 'SendGrid (Email)', status: 'connected' },
  { _id: '4', name: 'Google Analytics', status: 'disconnected' }
])

const integrationSettings = ref({
  rateLimitPerMinute: 100,
  rateLimitPerHour: 5000,
  rateLimitPerDay: 100000
})

// Modals
const showAddUserModal = ref(false)
const showGenerateKeyModal = ref(false)
const showAddWebhookModal = ref(false)

const addUserForm = ref({
  name: '',
  email: '',
  role: 'manager',
  permissions: []
})

const apiKeyForm = ref({
  name: '',
  permissions: []
})

const webhookForm = ref({
  event: '',
  url: ''
})

const getAdminConfig = () => {
  const token = localStorage.getItem('adminToken')
  if (!token) {
    throw new Error('Admin token not found. Please login again.')
  }
  return { headers: { Authorization: `Bearer ${token}` } }
}

const loadSettingsSummary = async () => {
  loading.value = true
  loadError.value = ''

  try {
    const token = localStorage.getItem('adminToken')
    if (!token) {
      loadError.value = 'Admin token not found. Please login again.'
      return
    }

    const response = await api.get('/admin/settings/summary', {
      headers: { Authorization: `Bearer ${token}` }
    })

    const data = response.data || {}

    if (data.settings) {
      settings.value = {
        ...settings.value,
        ...data.settings
      }
    }

    if (data.systemHealth) {
      systemHealth.value = {
        ...systemHealth.value,
        ...data.systemHealth
      }
    }

    if (Array.isArray(data.adminUsers)) adminUsers.value = data.adminUsers
    if (data.backupInfo) backupInfo.value = { ...backupInfo.value, ...data.backupInfo }
    if (Array.isArray(data.backupHistory)) backupHistory.value = data.backupHistory
    if (data.maintenanceInfo) maintenanceInfo.value = { ...maintenanceInfo.value, ...data.maintenanceInfo }
    if (data.securitySettings) {
      securitySettings.value = { ...securitySettings.value, ...data.securitySettings }
      whitelistInput.value = (data.securitySettings.ipWhitelist || []).join('\n')
    }
    if (Array.isArray(data.apiKeys)) apiKeys.value = data.apiKeys
    if (Array.isArray(data.webhooks)) webhooks.value = data.webhooks
    if (Array.isArray(data.thirdPartyServices)) thirdPartyServices.value = data.thirdPartyServices
    if (data.integrationSettings) {
      integrationSettings.value = { ...integrationSettings.value, ...data.integrationSettings }
    }
  } catch (error) {
    console.error('Failed to load settings summary:', error)
    loadError.value = error.response?.data?.detail || 'Failed to load settings data'
  } finally {
    loading.value = false
  }
}

onMounted(() => {
  loadSettingsSummary()
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

const getInitials = (name) => {
  return name.split(' ').map(n => n[0]).join('').toUpperCase()
}

const saveGeneralSettings = () => {
  api.post('/admin/settings/general', settings.value.general, getAdminConfig())
    .then(() => alert('General settings saved successfully!'))
    .catch((error) => alert(error.response?.data?.detail || error.message || 'Failed to save settings'))
}

const saveLocalization = () => {
  saveGeneralSettings()
}

const saveFeatureFlags = () => {
  saveGeneralSettings()
}

const checkSystemHealth = () => {
  alert('System health check initiated...')
}

const viewDetailedLogs = () => {
  alert('Opening detailed system logs...')
}

const editUser = (user) => {
  api.patch(`/admin/settings/admin-users/${user._id}`, {
    role: user.role,
    name: user.name
  }, getAdminConfig())
    .then(() => alert(`Updated user: ${user.name}`))
    .catch((error) => alert(error.response?.data?.detail || error.message || 'Failed to update user'))
}

const resetUserPassword = (user) => {
  if (confirm(`Send password reset link to ${user.email}?`)) {
    alert('Password reset link sent!')
  }
}

const deactivateUser = (user) => {
  if (confirm(`Deactivate user ${user.name}?`)) {
    api.patch(`/admin/settings/admin-users/${user._id}`, {
      status: 'inactive'
    }, getAdminConfig())
      .then(async () => {
        user.status = 'inactive'
        alert('User deactivated')
        await loadSettingsSummary()
      })
      .catch((error) => alert(error.response?.data?.detail || error.message || 'Failed to deactivate user'))
  }
}

const saveAdminUser = () => {
  if (!addUserForm.value.name || !addUserForm.value.email) {
    alert('Please fill in all required fields')
    return
  }

  const newUser = {
    _id: Date.now().toString(),
    name: addUserForm.value.name,
    email: addUserForm.value.email,
    role: addUserForm.value.role,
    status: 'active',
    lastLogin: new Date()
  }

  adminUsers.value.push(newUser)
  alert(`Admin user "${newUser.name}" added successfully!`)
  showAddUserModal.value = false
  addUserForm.value = { name: '', email: '', role: 'manager', permissions: [] }
}

const performBackup = () => {
  alert('Backup in progress...')
}

const downloadLatestBackup = () => {
  alert('Downloading latest backup...')
}

const backupFiles = () => {
  alert('File backup initiated...')
}

const restoreFromBackup = () => {
  alert('Restore process - select backup to restore from')
}

const clearCache = () => {
  alert('Cache cleared successfully!')
}

const cleanupTempFiles = () => {
  alert('Temp files cleaned up!')
}

const archiveLogs = () => {
  alert('Old logs archived successfully!')
}

const optimizeDatabase = () => {
  alert('Database optimization in progress...')
}

const rebuildIndexes = () => {
  alert('Rebuilding database indexes...')
}

const defragment = () => {
  alert('Defragmentation in progress...')
}

const downloadBackup = (backup) => {
  alert(`Downloading backup from ${formatDateTime(backup.date)}`)
}

const saveAuthSettings = () => {
  api.post('/admin/settings/security', securitySettings.value, getAdminConfig())
    .then(() => alert('Authentication settings saved!'))
    .catch((error) => alert(error.response?.data?.detail || error.message || 'Failed to save security settings'))
}

const savePasswordPolicy = () => {
  saveAuthSettings()
}

const saveIpWhitelist = () => {
  securitySettings.value.ipWhitelist = whitelistInput.value.split('\n').filter(ip => ip.trim())
  saveAuthSettings()
}

const saveDataProtection = () => {
  saveAuthSettings()
}

const maskApiKey = (key) => {
  return key.slice(0, 8) + '...' + key.slice(-4)
}

const copyApiKey = (key) => {
  alert(`API key copied to clipboard: ${maskApiKey(key.key)}`)
}

const revokeApiKey = (key) => {
  if (confirm(`Revoke API key "${key.name}"?`)) {
    api.delete(`/admin/settings/api-keys/${key._id}`, getAdminConfig())
      .then(async () => {
        const index = apiKeys.value.findIndex(k => k._id === key._id)
        if (index > -1) apiKeys.value.splice(index, 1)
        alert('API key revoked')
        await loadSettingsSummary()
      })
      .catch((error) => alert(error.response?.data?.detail || error.message || 'Failed to revoke API key'))
  }
}

const generateApiKey = () => {
  if (!apiKeyForm.value.name || apiKeyForm.value.permissions.length === 0) {
    alert('Please fill in all required fields')
    return
  }

  api.post('/admin/settings/api-keys', {
    name: apiKeyForm.value.name,
    permissions: apiKeyForm.value.permissions
  }, getAdminConfig()).then(async (response) => {
    const newKey = response.data?.apiKey
    if (newKey) {
      apiKeys.value.push(newKey)
    }
    alert(`API key "${apiKeyForm.value.name}" generated successfully!`)
    showGenerateKeyModal.value = false
    apiKeyForm.value = { name: '', permissions: [] }
    await loadSettingsSummary()
  }).catch((error) => {
    alert(error.response?.data?.detail || error.message || 'Failed to generate API key')
  })
}

const testWebhook = (webhook) => {
  alert(`Testing webhook: ${webhook.event}`)
}

const deleteWebhook = (webhook) => {
  if (confirm(`Delete webhook for ${webhook.event}?`)) {
    api.delete(`/admin/settings/webhooks/${webhook._id}`, getAdminConfig())
      .then(async () => {
        const index = webhooks.value.findIndex(w => w._id === webhook._id)
        if (index > -1) webhooks.value.splice(index, 1)
        alert('Webhook deleted')
        await loadSettingsSummary()
      })
      .catch((error) => alert(error.response?.data?.detail || error.message || 'Failed to delete webhook'))
  }
}

const saveWebhook = () => {
  if (!webhookForm.value.event || !webhookForm.value.url) {
    alert('Please fill in all required fields')
    return
  }

  api.post('/admin/settings/webhooks', {
    event: webhookForm.value.event,
    url: webhookForm.value.url
  }, getAdminConfig()).then(async (response) => {
    const newWebhook = response.data?.webhook
    if (newWebhook) {
      webhooks.value.push(newWebhook)
    }
    alert('Webhook added successfully!')
    showAddWebhookModal.value = false
    webhookForm.value = { event: '', url: '' }
    await loadSettingsSummary()
  }).catch((error) => {
    alert(error.response?.data?.detail || error.message || 'Failed to add webhook')
  })
}

const connectService = (service) => {
  service.status = 'connected'
  alert(`Connected to ${service.name}`)
}

const disconnectService = (service) => {
  if (confirm(`Disconnect from ${service.name}?`)) {
    service.status = 'disconnected'
    alert(`Disconnected from ${service.name}`)
  }
}

const saveRateLimiting = () => {
  api.post('/admin/settings/integration', integrationSettings.value, getAdminConfig())
    .then(() => alert('Rate limiting settings saved!'))
    .catch((error) => alert(error.response?.data?.detail || error.message || 'Failed to save integration settings'))
}
</script>

<style scoped>
.admin-settings {
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
  flex-wrap: wrap;
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

/* Settings */
.settings-section h3,
.health-section h3,
.users-section h3,
.maintenance-section h3,
.security-section h3,
.integration-section h3 {
  margin: 0 0 1.5rem 0;
  color: #1a202c;
  font-size: 1.1rem;
}

.settings-grid,
.health-grid,
.security-grid,
.integration-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}

.settings-card,
.status-card,
.maintenance-card,
.security-card,
.integration-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
}

.settings-card h4,
.status-card h4,
.maintenance-card h4,
.security-card h4,
.integration-card h4 {
  margin: 0 0 1.5rem 0;
  color: #1a202c;
  font-size: 1rem;
}

.status-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.status-header h4 {
  margin: 0;
}

.status-indicator {
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.status-indicator.status-healthy {
  background: #dcfce7;
  color: #166534;
}

.status-indicator.status-warning {
  background: #fef3c7;
  color: #b45309;
}

.status-message {
  margin: 0;
  font-size: 0.9rem;
  color: #718096;
}

.status-details {
  font-size: 0.9rem;
  color: #718096;
}

.status-details p {
  margin: 0.5rem 0;
}

.badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.badge-success {
  background: #dcfce7;
  color: #166534;
}

.usage-bar {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 0.25rem 0.75rem;
  border-radius: 4px;
  font-weight: 600;
}

.health-actions {
  display: flex;
  gap: 1rem;
  margin-top: 2rem;
}

/* User Management */
.users-controls {
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

.users-table {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  overflow-x: auto;
}

table {
  width: 100%;
  border-collapse: collapse;
}

thead {
  background: #f7fafc;
}

th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #2d3748;
  border-bottom: 2px solid #e2e8f0;
}

td {
  padding: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.avatar {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  font-weight: 600;
  font-size: 0.85rem;
}

.role-select {
  padding: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 6px;
  font-size: 0.9rem;
}

.status-badge {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.status-badge.badge-active {
  background: #dcfce7;
  color: #166534;
}

.status-badge.badge-inactive {
  background: #fee2e2;
  color: #991b1b;
}

/* Form Groups */
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
.textarea,
.select {
  padding: 0.75rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  font-family: inherit;
}

.input:focus,
.textarea:focus,
.select:focus {
  outline: none;
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
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

.checkbox-label {
  margin-left: 0.5rem;
}

/* Buttons */
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

.btn-warning {
  background: #fbbf24;
  color: white;
}

.btn-warning:hover {
  background: #f59e0b;
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

/* Maintenance */
.maintenance-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
  margin-bottom: 2rem;
}

.status-info {
  background: #f7fafc;
  padding: 1rem;
  border-radius: 8px;
  margin-bottom: 1.5rem;
}

.status-info p {
  margin: 0.5rem 0;
  font-size: 0.9rem;
}

.backup-history {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
}

.backup-history h4 {
  margin: 0 0 1rem 0;
}

.backup-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  border-bottom: 1px solid #e2e8f0;
}

.backup-date {
  font-weight: 600;
}

.backup-size {
  color: #718096;
}

.backup-status {
  padding: 0.25rem 0.75rem;
  border-radius: 6px;
  font-size: 0.85rem;
  font-weight: 600;
}

.backup-status.status-completed {
  background: #dcfce7;
  color: #166534;
}

/* Integration */
.integration-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
  gap: 2rem;
}

.api-keys-list,
.webhooks-list,
.services-list {
  margin-bottom: 1.5rem;
}

.api-key-item,
.webhook-item,
.service-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  margin-bottom: 0.75rem;
}

.key-info,
.webhook-info,
.service-info {
  flex: 1;
}

.key-info p,
.webhook-info p,
.service-info p {
  margin: 0;
}

.key-value,
.webhook-url {
  font-family: monospace;
  font-size: 0.85rem;
  color: #718096;
}

.key-meta,
.webhook-meta {
  font-size: 0.85rem;
  color: #a0aec0;
  margin-top: 0.25rem;
}

.key-actions,
.webhook-actions,
.service-actions {
  display: flex;
  gap: 0.5rem;
  margin-left: 1rem;
}

.webhook-status,
.service-status {
  display: inline-block;
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

  .settings-grid,
  .health-grid,
  .security-grid,
  .integration-grid,
  .maintenance-grid {
    grid-template-columns: 1fr;
  }

  .users-controls {
    flex-direction: column;
  }

  .search-input {
    width: 100%;
  }

  .users-table {
    font-size: 0.9rem;
  }

  th,
  td {
    padding: 0.75rem;
  }

  .health-actions {
    flex-direction: column;
  }

  .health-actions .btn {
    width: 100%;
  }

  .api-key-item,
  .webhook-item,
  .service-item {
    flex-direction: column;
    align-items: flex-start;
  }

  .key-actions,
  .webhook-actions,
  .service-actions {
    margin-left: 0;
    margin-top: 1rem;
    width: 100%;
  }
}
</style>
