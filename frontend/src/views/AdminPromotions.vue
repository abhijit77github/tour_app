<template>
  <div class="admin-promotions">
    <div class="page-header">
      <div>
        <h1>Location Promotions</h1>
        <p class="subtitle">Create and manage location-specific promoted placements for operators.</p>
      </div>
      <button class="btn-refresh" @click="loadData" :disabled="loading">
        {{ loading ? 'Refreshing…' : 'Refresh' }}
      </button>
    </div>

    <div v-if="message.text" :class="['message-banner', message.type]">
      {{ message.text }}
    </div>

    <div class="promo-grid">
      <section class="promo-card form-card">
        <div class="section-head">
          <div>
            <p class="eyebrow">Campaign Editor</p>
            <h2>{{ editingPromotionId ? 'Edit Promotion' : 'New Promotion' }}</h2>
          </div>
          <button v-if="editingPromotionId" class="btn-link" @click="resetForm">Cancel edit</button>
        </div>

        <form class="promo-form" @submit.prevent="savePromotion">
          <label class="field field-full">
            <span>Operator</span>
            <select v-model="form.operator_profile_id" required>
              <option value="">Select operator</option>
              <option v-for="operator in operatorOptions" :key="operator.profileId" :value="operator.profileId">
                {{ operator.businessName }}
              </option>
            </select>
          </label>

          <label class="field">
            <span>Area name</span>
            <input v-model="form.location_scope.area_name" type="text" placeholder="Manali" />
          </label>

          <label class="field">
            <span>State</span>
            <input v-model="form.location_scope.state" type="text" placeholder="Himachal Pradesh" />
          </label>

          <label class="field">
            <span>Country</span>
            <input v-model="form.location_scope.country" type="text" placeholder="India" />
          </label>

          <label class="field">
            <span>Service type</span>
            <select v-model="form.service_type">
              <option value="">All supported</option>
              <option value="tour">Tour</option>
              <option value="car">Car</option>
            </select>
          </label>

          <label class="field">
            <span>Status</span>
            <select v-model="form.status">
              <option value="draft">Draft</option>
              <option value="pending_approval">Pending approval</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="ended">Ended</option>
              <option value="rejected">Rejected</option>
            </select>
          </label>

          <label class="field">
            <span>Label</span>
            <input v-model="form.promotion_label" type="text" maxlength="40" placeholder="Promoted" required />
          </label>

          <label class="field">
            <span>Priority</span>
            <input v-model.number="form.priority" type="number" min="0" max="100" required />
          </label>

          <label class="field">
            <span>Bid amount</span>
            <input v-model.number="form.bid_amount" type="number" min="0" step="0.01" placeholder="25" />
          </label>

          <label class="field">
            <span>Daily budget</span>
            <input v-model.number="form.daily_budget" type="number" min="0" step="0.01" placeholder="2000" />
          </label>

          <label class="field">
            <span>Total budget</span>
            <input v-model.number="form.total_budget" type="number" min="0" step="0.01" placeholder="20000" />
          </label>

          <label class="field">
            <span>Start at</span>
            <input v-model="form.start_at" type="datetime-local" required />
          </label>

          <label class="field">
            <span>End at</span>
            <input v-model="form.end_at" type="datetime-local" required />
          </label>

          <div class="form-actions field-full">
            <button class="btn-primary" type="submit" :disabled="saving">
              {{ saving ? 'Saving…' : editingPromotionId ? 'Update promotion' : 'Create promotion' }}
            </button>
            <button class="btn-secondary" type="button" @click="resetForm">Reset</button>
          </div>
        </form>
      </section>

      <section class="promo-card list-card">
        <div class="section-head">
          <div>
            <p class="eyebrow">Live inventory</p>
            <h2>Existing Promotions</h2>
          </div>
          <div class="filter-row">
            <select v-model="filters.status">
              <option value="">All statuses</option>
              <option value="draft">Draft</option>
              <option value="pending_approval">Pending approval</option>
              <option value="active">Active</option>
              <option value="paused">Paused</option>
              <option value="ended">Ended</option>
              <option value="rejected">Rejected</option>
            </select>
            <input v-model="filters.area_name" type="text" placeholder="Filter by area" />
            <button class="btn-link" @click="fetchPromotions">Apply</button>
          </div>
        </div>

        <div v-if="loading" class="empty-box">Loading promotions…</div>
        <div v-else-if="!promotions.length" class="empty-box">No promotions created yet.</div>
        <div v-else class="promo-table-wrap">
          <table class="promo-table">
            <thead>
              <tr>
                <th>Operator</th>
                <th>Location</th>
                <th>Status</th>
                <th>Service</th>
                <th>Metrics</th>
                <th>Spend</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="promotion in promotions" :key="promotion._id">
                <td>
                  <div class="operator-name">{{ promotion.operator_profile?.business_name || 'Unknown operator' }}</div>
                  <div class="subtext">Priority {{ promotion.priority }}</div>
                </td>
                <td>
                  <div>{{ formatLocation(promotion.location_scope) }}</div>
                  <div class="subtext">{{ formatWindow(promotion.start_at, promotion.end_at) }}</div>
                </td>
                <td>
                  <span :class="['status-pill', promotion.status]">{{ readableStatus(promotion.status) }}</span>
                </td>
                <td>{{ promotion.service_type || 'All' }}</td>
                <td>
                  <div>{{ promotion.total_impressions || 0 }} impressions</div>
                  <div class="subtext">{{ promotion.total_clicks || 0 }} clicks</div>
                </td>
                <td>
                  <div>₹{{ formatMoney(promotion.total_spend) }}</div>
                  <div class="subtext">Daily ₹{{ formatMoney(promotion.daily_spend) }}</div>
                </td>
                <td>
                  <div class="table-actions">
                    <button class="icon-btn" @click="startEdit(promotion)">Edit</button>
                    <button class="icon-btn danger" @click="removePromotion(promotion)">Delete</button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import api from '../services/api'

const loading = ref(false)
const saving = ref(false)
const promotions = ref([])
const operators = ref([])
const editingPromotionId = ref('')
const message = ref({ type: 'info', text: '' })
const filters = ref({ status: '', area_name: '' })

const createEmptyForm = () => ({
  operator_profile_id: '',
  location_scope: {
    area_name: '',
    state: '',
    country: ''
  },
  service_type: '',
  status: 'draft',
  promotion_label: 'Promoted',
  priority: 50,
  bid_amount: null,
  daily_budget: null,
  total_budget: null,
  start_at: '',
  end_at: ''
})

const form = ref(createEmptyForm())

const adminHeaders = computed(() => ({
  Authorization: `Bearer ${localStorage.getItem('adminToken') || ''}`
}))

const operatorOptions = computed(() =>
  operators.value
    .filter(operator => operator.profile?._id)
    .map(operator => ({
      profileId: operator.profile._id,
      businessName: operator.profile.business_name || operator.full_name
    }))
)

const showMessage = (type, text) => {
  message.value = { type, text }
  window.clearTimeout(showMessage.timeoutId)
  showMessage.timeoutId = window.setTimeout(() => {
    message.value = { type: 'info', text: '' }
  }, 3500)
}

const toDateTimeLocal = (value) => {
  if (!value) return ''
  return new Date(value).toISOString().slice(0, 16)
}

const toPayload = () => ({
  operator_profile_id: form.value.operator_profile_id,
  location_scope: {
    area_name: form.value.location_scope.area_name || null,
    state: form.value.location_scope.state || null,
    country: form.value.location_scope.country || null
  },
  service_type: form.value.service_type || null,
  status: form.value.status,
  promotion_label: form.value.promotion_label,
  priority: Number(form.value.priority || 0),
  bid_amount: form.value.bid_amount == null || form.value.bid_amount === '' ? null : Number(form.value.bid_amount),
  daily_budget: form.value.daily_budget == null || form.value.daily_budget === '' ? null : Number(form.value.daily_budget),
  total_budget: form.value.total_budget == null || form.value.total_budget === '' ? null : Number(form.value.total_budget),
  start_at: new Date(form.value.start_at).toISOString(),
  end_at: new Date(form.value.end_at).toISOString()
})

const fetchOperators = async () => {
  const response = await api.get('/admin/operators?skip=0&limit=1000', {
    headers: adminHeaders.value
  })
  operators.value = response.data.operators || []
}

const fetchPromotions = async () => {
  const params = {}
  if (filters.value.status) params.status_filter = filters.value.status
  if (filters.value.area_name) params.area_name = filters.value.area_name

  const response = await api.get('/admin/promotions/location', {
    headers: adminHeaders.value,
    params
  })
  promotions.value = response.data.promotions || []
}

const loadData = async () => {
  loading.value = true
  try {
    await Promise.all([fetchOperators(), fetchPromotions()])
  } catch (error) {
    console.error('Failed to load promotions data', error)
    showMessage('error', error.response?.data?.detail || 'Failed to load promotions data')
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  editingPromotionId.value = ''
  form.value = createEmptyForm()
}

const startEdit = (promotion) => {
  editingPromotionId.value = promotion._id
  form.value = {
    operator_profile_id: promotion.operator_profile_id,
    location_scope: {
      area_name: promotion.location_scope?.area_name || '',
      state: promotion.location_scope?.state || '',
      country: promotion.location_scope?.country || ''
    },
    service_type: promotion.service_type || '',
    status: promotion.status,
    promotion_label: promotion.promotion_label || 'Promoted',
    priority: promotion.priority ?? 50,
    bid_amount: promotion.bid_amount,
    daily_budget: promotion.daily_budget,
    total_budget: promotion.total_budget,
    start_at: toDateTimeLocal(promotion.start_at),
    end_at: toDateTimeLocal(promotion.end_at)
  }
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const savePromotion = async () => {
  if (!form.value.location_scope.area_name && !form.value.location_scope.state && !form.value.location_scope.country) {
    showMessage('error', 'At least one location field is required')
    return
  }

  saving.value = true
  try {
    const payload = toPayload()
    if (editingPromotionId.value) {
      await api.patch(`/admin/promotions/location/${editingPromotionId.value}`, payload, {
        headers: adminHeaders.value
      })
      showMessage('success', 'Promotion updated successfully')
    } else {
      await api.post('/admin/promotions/location', payload, {
        headers: adminHeaders.value
      })
      showMessage('success', 'Promotion created successfully')
    }
    resetForm()
    await fetchPromotions()
  } catch (error) {
    console.error('Failed to save promotion', error)
    showMessage('error', error.response?.data?.detail || 'Failed to save promotion')
  } finally {
    saving.value = false
  }
}

const removePromotion = async (promotion) => {
  if (!window.confirm(`Delete promotion for ${promotion.operator_profile?.business_name || 'this operator'}?`)) {
    return
  }

  try {
    await api.delete(`/admin/promotions/location/${promotion._id}`, {
      headers: adminHeaders.value
    })
    showMessage('success', 'Promotion deleted successfully')
    if (editingPromotionId.value === promotion._id) {
      resetForm()
    }
    await fetchPromotions()
  } catch (error) {
    console.error('Failed to delete promotion', error)
    showMessage('error', error.response?.data?.detail || 'Failed to delete promotion')
  }
}

const readableStatus = (value) => value.replaceAll('_', ' ')

const formatLocation = (scope) => {
  return [scope?.area_name, scope?.state, scope?.country].filter(Boolean).join(', ')
}

const formatWindow = (startAt, endAt) => {
  return `${new Date(startAt).toLocaleDateString()} - ${new Date(endAt).toLocaleDateString()}`
}

const formatMoney = (value) => Number(value || 0).toFixed(2)

onMounted(loadData)
</script>

<style scoped>
.admin-promotions {
  display: flex;
  flex-direction: column;
  gap: 1.4rem;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
}

.page-header h1 {
  margin: 0;
  font-size: 2rem;
  color: #0f172a;
}

.subtitle {
  margin: 0.35rem 0 0;
  color: #64748b;
}

.btn-refresh,
.btn-primary,
.btn-secondary,
.btn-link,
.icon-btn {
  border: none;
  border-radius: 10px;
  font: inherit;
  cursor: pointer;
}

.btn-refresh,
.btn-link,
.btn-secondary,
.icon-btn {
  background: #fff;
  border: 1px solid #dbe4ee;
  color: #334155;
  padding: 0.7rem 1rem;
}

.btn-primary {
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: #fff;
  padding: 0.8rem 1.2rem;
}

.message-banner {
  padding: 0.9rem 1rem;
  border-radius: 12px;
  font-weight: 600;
}

.message-banner.success {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  color: #166534;
}

.message-banner.error {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
}

.promo-grid {
  display: grid;
  grid-template-columns: minmax(340px, 420px) minmax(0, 1fr);
  gap: 1.4rem;
}

.promo-card {
  background: #fff;
  border: 1px solid #e2e8f0;
  border-radius: 18px;
  box-shadow: 0 10px 24px rgba(15, 23, 42, 0.06);
  padding: 1.4rem;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 1.2rem;
}

.eyebrow {
  display: inline-block;
  margin: 0 0 0.35rem;
  font-size: 0.72rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  font-weight: 700;
  color: #94a3b8;
}

.section-head h2 {
  margin: 0;
  font-size: 1.2rem;
  color: #0f172a;
}

.promo-form {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}

.field-full {
  grid-column: 1 / -1;
}

.field span {
  font-size: 0.8rem;
  font-weight: 700;
  color: #475569;
}

.field input,
.field select {
  width: 100%;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  padding: 0.75rem 0.85rem;
  font: inherit;
  color: #0f172a;
  background: #f8fafc;
}

.field input:focus,
.field select:focus {
  outline: none;
  border-color: #38bdf8;
  background: #fff;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 0.2rem;
}

.filter-row {
  display: flex;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.filter-row input,
.filter-row select {
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  padding: 0.65rem 0.8rem;
  font: inherit;
  background: #f8fafc;
}

.promo-table-wrap {
  overflow-x: auto;
}

.promo-table {
  width: 100%;
  border-collapse: collapse;
}

.promo-table th,
.promo-table td {
  text-align: left;
  padding: 0.9rem 0.75rem;
  border-bottom: 1px solid #eef2f7;
  vertical-align: top;
}

.promo-table th {
  font-size: 0.78rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.operator-name {
  font-weight: 700;
  color: #0f172a;
}

.subtext {
  font-size: 0.8rem;
  color: #94a3b8;
  margin-top: 0.2rem;
}

.status-pill {
  display: inline-flex;
  align-items: center;
  padding: 0.25rem 0.6rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: capitalize;
}

.status-pill.active {
  background: #f0fdf4;
  color: #166534;
  border: 1px solid #bbf7d0;
}

.status-pill.draft,
.status-pill.paused,
.status-pill.ended,
.status-pill.rejected,
.status-pill.pending_approval {
  background: #f8fafc;
  color: #475569;
  border: 1px solid #dbe4ee;
}

.table-actions {
  display: flex;
  gap: 0.5rem;
}

.icon-btn.danger {
  color: #b91c1c;
  border-color: #fecaca;
  background: #fff5f5;
}

.empty-box {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 220px;
  border: 1px dashed #dbe4ee;
  border-radius: 14px;
  background: #f8fafc;
  color: #64748b;
}

@media (max-width: 1100px) {
  .promo-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 700px) {
  .page-header,
  .section-head {
    flex-direction: column;
  }

  .promo-form {
    grid-template-columns: 1fr;
  }

  .form-actions,
  .filter-row,
  .table-actions {
    flex-direction: column;
  }
}
</style>