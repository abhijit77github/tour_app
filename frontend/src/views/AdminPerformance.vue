<template>
  <div class="admin-performance">
    <div class="page-header">
      <h1>Operator Performance</h1>
      <p class="subtitle">View operator performance metrics and leaderboard</p>
    </div>

    <!-- Tabs -->
    <div class="tabs">
      <button
        @click="activeTab = 'leaderboard'"
        :class="['tab', { active: activeTab === 'leaderboard' }]"
      >
        📊 Leaderboard
      </button>
      <button
        @click="activeTab = 'metrics'"
        :class="['tab', { active: activeTab === 'metrics' }]"
      >
        📈 Performance Metrics
      </button>
    </div>

    <!-- Loading State -->
    <div v-if="loading" class="loading-state">
      <div class="spinner"></div>
      <p>Loading performance data...</p>
    </div>

    <!-- Leaderboard Tab -->
    <div v-else-if="activeTab === 'leaderboard'" class="tab-content">
      <div class="leaderboard-filters">
        <select v-model="sortBy" class="filter-select">
          <option value="rating">Sort by Rating</option>
          <option value="responses">Sort by Responses</option>
          <option value="response_time">Sort by Response Time</option>
        </select>
      </div>

      <div v-if="leaderboardData.length === 0" class="empty-state">
        <p>No performance data available</p>
      </div>

      <div v-else class="leaderboard-container">
        <div v-for="(operator, index) in leaderboardData" :key="operator._id" class="leaderboard-card">
          <div class="rank-badge">{{ index + 1 }}</div>
          
          <div class="operator-info">
            <h3>{{ operator.profile?.business_name || operator.full_name }}</h3>
            <p class="owner">{{ operator.full_name }}</p>
          </div>

          <div class="metrics-grid">
            <div class="metric-item">
              <span class="metric-label">Rating</span>
              <span class="metric-value">⭐ {{ (operator.profile?.average_rating || 0).toFixed(1) }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Responses</span>
              <span class="metric-value">{{ operator.total_responses || 0 }}</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Response Time</span>
              <span class="metric-value">{{ operator.avg_response_time_hours || 0 }}h</span>
            </div>
            <div class="metric-item">
              <span class="metric-label">Serving Areas</span>
              <span class="metric-value">{{ operator.serving_areas_count || 0 }}</span>
            </div>
          </div>

          <button @click="viewDetails(operator)" class="details-btn">
            View Details →
          </button>
        </div>
      </div>
    </div>

    <!-- Performance Metrics Tab -->
    <div v-else-if="activeTab === 'metrics'" class="tab-content">
      <div class="metrics-toolbar">
        <div class="search-box">
          <input
            v-model="operatorSearchQuery"
            type="text"
            placeholder="Search operator..."
            class="search-input"
          />
          <span class="search-icon">🔍</span>
        </div>
      </div>

      <div v-if="filteredMetrics.length === 0" class="empty-state">
        <p>No metrics found</p>
      </div>

      <div v-else class="metrics-table-container">
        <table class="metrics-table">
          <thead>
            <tr>
              <th>Business Name</th>
              <th>Owner</th>
              <th>Avg Rating</th>
              <th>Total Responses</th>
              <th>Avg Response Time</th>
              <th>Serving Areas</th>
              <th>Total Reviews</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="operator in filteredMetrics" :key="operator._id" class="metrics-row">
              <td class="business-cell">{{ operator.profile?.business_name || 'N/A' }}</td>
              <td class="owner-cell">{{ operator.full_name }}</td>
              <td class="rating-cell">
                <span class="rating-badge">⭐ {{ (operator.profile?.average_rating || 0).toFixed(1) }}</span>
              </td>
              <td class="responses-cell">{{ operator.total_responses || 0 }}</td>
              <td class="response-time-cell">{{ operator.avg_response_time_hours || 0 }}h</td>
              <td class="areas-cell">{{ operator.serving_areas_count || 0 }}</td>
              <td class="reviews-cell">{{ operator.profile?.total_reviews || 0 }}</td>
              <td class="action-cell">
                <button @click="viewDetails(operator)" class="view-btn">
                  View
                </button>
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- Details Modal -->
    <div v-if="showDetailsModal" class="modal-overlay" @click.self="closeDetailsModal">
      <div class="modal-content">
        <div class="modal-header">
          <h2>Performance Details</h2>
          <button @click="closeDetailsModal" class="close-btn">✕</button>
        </div>

        <div v-if="selectedOperatorDetails" class="modal-body">
          <!-- Header -->
          <div class="details-header">
            <div class="business-info">
              <h3>{{ selectedOperatorDetails.profile?.business_name || selectedOperatorDetails.full_name }}</h3>
              <p class="owner-name">{{ selectedOperatorDetails.full_name }}</p>
            </div>
            <div class="rating-display">
              <div class="large-rating">⭐ {{ (selectedOperatorDetails.profile?.average_rating || 0).toFixed(1) }}</div>
              <p class="rating-count">{{ selectedOperatorDetails.profile?.total_reviews || 0 }} reviews</p>
            </div>
          </div>

          <!-- Key Metrics -->
          <div class="metrics-section">
            <h3>Key Performance Indicators</h3>
            <div class="kpi-grid">
              <div class="kpi-card">
                <span class="kpi-label">Total Responses</span>
                <span class="kpi-value">{{ selectedOperatorDetails.total_responses || 0 }}</span>
              </div>
              <div class="kpi-card">
                <span class="kpi-label">Avg Response Time</span>
                <span class="kpi-value">{{ selectedOperatorDetails.avg_response_time_hours || 0 }}h</span>
              </div>
              <div class="kpi-card">
                <span class="kpi-label">Serving Areas</span>
                <span class="kpi-value">{{ selectedOperatorDetails.serving_areas_count || 0 }}</span>
              </div>
              <div class="kpi-card">
                <span class="kpi-label">Experience</span>
                <span class="kpi-value">{{ selectedOperatorDetails.profile?.years_of_experience || 0 }} yrs</span>
              </div>
            </div>
          </div>

          <!-- Business Info -->
          <div class="info-section">
            <h3>Business Information</h3>
            <div class="info-grid">
              <div class="info-item">
                <span class="label">Email:</span>
                <span class="value email">{{ selectedOperatorDetails.email }}</span>
              </div>
              <div class="info-item">
                <span class="label">Phone:</span>
                <span class="value">{{ selectedOperatorDetails.phone || 'N/A' }}</span>
              </div>
              <div class="info-item">
                <span class="label">Status:</span>
                <span :class="['value', selectedOperatorDetails.is_active ? 'active' : 'inactive']">
                  {{ selectedOperatorDetails.is_active ? 'Active' : 'Inactive' }}
                </span>
              </div>
              <div class="info-item">
                <span class="label">Member Since:</span>
                <span class="value">{{ formatDate(selectedOperatorDetails.created_at) }}</span>
              </div>
            </div>
          </div>

          <!-- Description -->
          <div v-if="selectedOperatorDetails.profile?.description" class="info-section">
            <h3>Description</h3>
            <p class="description">{{ selectedOperatorDetails.profile.description }}</p>
          </div>

          <!-- Specializations -->
          <div v-if="selectedOperatorDetails.profile?.specializations?.length" class="info-section">
            <h3>Specializations</h3>
            <div class="specializations">
              <span v-for="spec in selectedOperatorDetails.profile.specializations" :key="spec" class="spec-tag">
                {{ spec }}
              </span>
            </div>
          </div>

          <!-- Serving Areas -->
          <div v-if="selectedOperatorDetails.profile?.serving_areas?.length" class="info-section">
            <h3>Serving Areas</h3>
            <div class="serving-areas">
              <span v-for="area in selectedOperatorDetails.profile.serving_areas" :key="area" class="area-tag">
                📍 {{ formatServingArea(area) }}
              </span>
            </div>
          </div>
        </div>

        <div class="modal-footer">
          <button @click="closeDetailsModal" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import api from '../services/api'

const loading = ref(true)
const activeTab = ref('leaderboard')
const sortBy = ref('rating')
const operatorSearchQuery = ref('')
const leaderboardData = ref([])
const metricsData = ref([])
const selectedOperatorDetails = ref(null)
const showDetailsModal = ref(false)

const filteredMetrics = computed(() => {
  let filtered = metricsData.value

  if (operatorSearchQuery.value) {
    const query = operatorSearchQuery.value.toLowerCase()
    filtered = filtered.filter(o =>
      (o.profile?.business_name || '').toLowerCase().includes(query) ||
      o.full_name.toLowerCase().includes(query)
    )
  }

  return filtered
})

const formatDate = (date) => {
  if (!date) return 'N/A'
  return new Date(date).toLocaleDateString('en-IN')
}

const formatServingArea = (area) => {
  if (!area) return 'N/A'
  if (typeof area === 'string') return area
  return area.area_name || area.name || area.state || area.country || 'N/A'
}

const fetchPerformanceData = async () => {
  try {
    loading.value = true
    const token = localStorage.getItem('adminToken')

    // Fetch leaderboard
    const leaderboardRes = await api.get('/admin/operators/leaderboard', {
      params: { metric: sortBy.value },
      headers: { Authorization: `Bearer ${token}` }
    })
    leaderboardData.value = leaderboardRes.data.operators || leaderboardRes.data.leaderboard || []

    // Fetch metrics
    const metricsRes = await api.get('/admin/operators/performance', {
      params: { sort_by: 'rating' },
      headers: { Authorization: `Bearer ${token}` }
    })
    metricsData.value = metricsRes.data.operators || []
  } catch (error) {
    console.error('Error fetching performance data:', error)
  } finally {
    loading.value = false
  }
}

const viewDetails = async (operator) => {
  try {
    const token = localStorage.getItem('adminToken')
    const response = await api.get(`/admin/operators/${operator.profile?._id || operator._id}/performance`, {
      headers: { Authorization: `Bearer ${token}` }
    })
    const performance = response.data.performance || {}
    selectedOperatorDetails.value = {
      ...operator,
      total_responses: performance.total_responses ?? operator.total_responses ?? 0,
      avg_response_time_hours: performance.average_response_time_hours ?? operator.avg_response_time_hours ?? 0,
      serving_areas_count: performance.serving_areas_count ?? operator.serving_areas_count ?? 0,
      profile: {
        ...(operator.profile || {}),
        average_rating: performance.average_rating ?? operator.profile?.average_rating ?? 0,
        total_reviews: performance.total_reviews ?? operator.profile?.total_reviews ?? 0
      },
      performance
    }
    showDetailsModal.value = true
  } catch (error) {
    console.error('Error fetching operator details:', error)
  }
}

const closeDetailsModal = () => {
  showDetailsModal.value = false
  selectedOperatorDetails.value = null
}

onMounted(() => {
  fetchPerformanceData()
})

watch(sortBy, () => {
  fetchPerformanceData()
})
</script>

<style scoped>
.admin-performance {
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
  gap: 1rem;
  margin-bottom: 2rem;
  border-bottom: 2px solid #e2e8f0;
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
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

/* Loading State */
.loading-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
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

/* Empty State */
.empty-state {
  text-align: center;
  padding: 3rem 2rem;
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  color: #718096;
}

.empty-state p {
  margin: 0;
  font-size: 1.1rem;
}

/* Leaderboard */
.leaderboard-filters {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.filter-select {
  padding: 0.75rem 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
  background: white;
  cursor: pointer;
}

.leaderboard-container {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(350px, 1fr));
  gap: 1.5rem;
}

.leaderboard-card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  position: relative;
  transition: all 0.3s;
}

.leaderboard-card:hover {
  border-color: #667eea;
  box-shadow: 0 10px 30px rgba(102, 126, 234, 0.1);
  transform: translateY(-4px);
}

.rank-badge {
  position: absolute;
  top: 1rem;
  right: 1rem;
  width: 3rem;
  height: 3rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border-radius: 50%;
  font-weight: 700;
  font-size: 1.3rem;
}

.operator-info {
  margin-bottom: 1.5rem;
}

.operator-info h3 {
  margin: 0 0 0.5rem 0;
  color: #1a202c;
  font-size: 1.2rem;
  font-weight: 600;
}

.operator-info .owner {
  margin: 0;
  color: #718096;
  font-size: 0.9rem;
}

.metrics-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.metric-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
  padding: 0.75rem;
  background: #f7fafc;
  border-radius: 8px;
}

.metric-label {
  font-size: 0.75rem;
  font-weight: 600;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.metric-value {
  font-size: 1.3rem;
  font-weight: 700;
  color: #667eea;
}

.details-btn {
  width: 100%;
  padding: 0.75rem;
  border: none;
  border-radius: 8px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.details-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 5px 15px rgba(102, 126, 234, 0.3);
}

/* Metrics Toolbar */
.metrics-toolbar {
  display: flex;
  gap: 1rem;
  margin-bottom: 2rem;
}

.search-box {
  flex: 1;
  min-width: 250px;
  position: relative;
  display: flex;
  align-items: center;
}

.search-input {
  width: 100%;
  padding: 0.75rem 1rem 0.75rem 2.5rem;
  border: 2px solid #e2e8f0;
  border-radius: 8px;
  font-size: 0.95rem;
}

.search-input:focus {
  outline: none;
  border-color: #667eea;
}

.search-icon {
  position: absolute;
  left: 0.75rem;
  color: #a0aec0;
}

/* Metrics Table */
.metrics-table-container {
  background: white;
  border-radius: 12px;
  border: 1px solid #e2e8f0;
  overflow: hidden;
}

.metrics-table {
  width: 100%;
  border-collapse: collapse;
}

.metrics-table thead {
  background: #f7fafc;
  border-bottom: 2px solid #e2e8f0;
}

.metrics-table th {
  padding: 1rem;
  text-align: left;
  font-weight: 600;
  color: #2d3748;
  font-size: 0.9rem;
}

.metrics-table tbody tr {
  border-bottom: 1px solid #e2e8f0;
  transition: background 0.2s;
}

.metrics-table tbody tr:hover {
  background: #f7fafc;
}

.metrics-table td {
  padding: 1rem;
  font-size: 0.9rem;
  color: #2d3748;
}

.business-cell {
  font-weight: 600;
}

.owner-cell {
  color: #667eea;
}

.rating-cell {
  text-align: center;
}

.rating-badge {
  display: inline-block;
  padding: 0.5rem 0.75rem;
  background: #fef3c7;
  color: #92400e;
  border-radius: 6px;
  font-weight: 600;
  font-size: 0.9rem;
}

.responses-cell,
.areas-cell,
.reviews-cell {
  text-align: center;
}

.response-time-cell {
  text-align: center;
  color: #667eea;
  font-weight: 500;
}

.action-cell {
  text-align: center;
}

.view-btn {
  padding: 0.5rem 1rem;
  border: none;
  border-radius: 6px;
  background: #dbeafe;
  color: #0284c7;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.view-btn:hover {
  background: #bfdbfe;
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
  max-width: 700px;
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

.details-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 2rem;
  padding-bottom: 1.5rem;
  border-bottom: 2px solid #e2e8f0;
}

.business-info h3 {
  margin: 0 0 0.5rem 0;
  color: #1a202c;
  font-size: 1.3rem;
  font-weight: 600;
}

.owner-name {
  margin: 0;
  color: #718096;
  font-size: 0.95rem;
}

.rating-display {
  text-align: center;
}

.large-rating {
  font-size: 2rem;
  font-weight: 700;
  color: #f59e0b;
  margin-bottom: 0.5rem;
}

.rating-count {
  margin: 0;
  color: #718096;
  font-size: 0.9rem;
}

.metrics-section {
  margin-bottom: 2rem;
}

.metrics-section h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 1rem 0;
}

.kpi-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
  gap: 1rem;
}

.kpi-card {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  padding: 1.5rem;
  background: linear-gradient(135deg, #f7fafc 0%, #edf2f7 100%);
  border-radius: 8px;
  border: 1px solid #e2e8f0;
}

.kpi-label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.kpi-value {
  font-size: 2rem;
  font-weight: 700;
  color: #667eea;
}

.info-section {
  margin-bottom: 2rem;
}

.info-section h3 {
  font-size: 1.1rem;
  font-weight: 600;
  color: #1a202c;
  margin: 0 0 1rem 0;
  padding-bottom: 0.5rem;
  border-bottom: 2px solid #e2e8f0;
}

.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 1rem;
}

.info-item {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.info-item .label {
  font-size: 0.85rem;
  font-weight: 600;
  color: #718096;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.info-item .value {
  font-size: 1rem;
  color: #2d3748;
  font-weight: 500;
}

.info-item .value.email {
  color: #667eea;
}

.info-item .value.active {
  color: #166534;
  font-weight: 600;
}

.info-item .value.inactive {
  color: #991b1b;
  font-weight: 600;
}

.description {
  color: #4b5563;
  line-height: 1.6;
  margin: 0;
  padding: 1rem;
  background: #f7fafc;
  border-radius: 8px;
  border-left: 4px solid #667eea;
}

.specializations,
.serving-areas {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.spec-tag,
.area-tag {
  display: inline-block;
  padding: 0.5rem 0.75rem;
  background: #f0fdf4;
  color: #166534;
  border-radius: 20px;
  font-size: 0.85rem;
  font-weight: 500;
  border: 1px solid #bbf7d0;
}

.area-tag {
  background: #e0f2fe;
  color: #0284c7;
  border-color: #bae6fd;
}

.modal-footer {
  display: flex;
  gap: 1rem;
  justify-content: flex-end;
  padding: 1.5rem;
  border-top: 1px solid #e2e8f0;
  background: #f7fafc;
}

.btn {
  padding: 0.75rem 1.5rem;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-secondary {
  background: #e2e8f0;
  color: #2d3748;
}

.btn-secondary:hover {
  background: #cbd5e0;
}

/* Responsive */
@media (max-width: 768px) {
  .tabs {
    flex-direction: column;
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

  .leaderboard-container {
    grid-template-columns: 1fr;
  }

  .details-header {
    flex-direction: column;
    gap: 1rem;
  }

  .metrics-grid {
    grid-template-columns: 1fr;
  }

  .metrics-table {
    font-size: 0.85rem;
  }

  .metrics-table th,
  .metrics-table td {
    padding: 0.75rem;
  }

  .kpi-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
