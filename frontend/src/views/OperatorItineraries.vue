<template>
  <div class="op-it-page">
    <section class="hero">
      <div class="hero-inner">
        <div>
          <span class="eyebrow">Operator templates</span>
          <h1>Publish general-purpose itineraries for planner retrieval</h1>
          <p>Create reusable trip structures tied to locations you already serve so tourists can start from grounded plans instead of blind AI guesses.</p>
        </div>
        <div class="hero-stats">
          <div class="stat-box">
            <strong>{{ totalTemplates }}</strong>
            <span>Templates</span>
          </div>
          <div class="stat-box">
            <strong>{{ servingAreas.length }}</strong>
            <span>Serving areas</span>
          </div>
        </div>
      </div>
    </section>

    <div class="container">
      <div v-if="notice.text" :class="['notice', notice.type]">{{ notice.text }}</div>

      <div class="grid">
        <section class="card form-card">
          <div class="card-head">
            <div>
              <p class="card-label">Template editor</p>
              <h2>{{ editingId ? 'Edit itinerary template' : 'New itinerary template' }}</h2>
            </div>
            <button v-if="editingId" class="btn-light" @click="resetForm">Cancel edit</button>
          </div>

          <form class="form-grid" @submit.prevent="saveTemplate">
            <label class="field span-2">
              <span>Title</span>
              <input v-model="form.title" type="text" placeholder="4D3N Manali family getaway" required />
            </label>

            <label class="field span-2">
              <span>Summary</span>
              <textarea v-model="form.summary" rows="3" placeholder="What makes this itinerary useful for tourists?"></textarea>
            </label>

            <label class="field">
              <span>Primary location</span>
              <select v-model="selectedAreaIndex" required>
                <option value="">Select serving area</option>
                <option v-for="(area, index) in servingAreas" :key="`${area.area_name}-${index}`" :value="String(index)">
                  {{ formatArea(area) }}
                </option>
              </select>
            </label>

            <label class="field">
              <span>Duration</span>
              <input v-model.number="form.duration_days" type="number" min="1" max="30" required />
            </label>

            <label class="field">
              <span>Budget band</span>
              <select v-model="form.budget_band">
                <option value="">Optional</option>
                <option value="budget">Budget</option>
                <option value="mid">Mid</option>
                <option value="premium">Premium</option>
              </select>
            </label>

            <label class="field">
              <span>Status</span>
              <select v-model="form.status">
                <option value="draft">Draft</option>
                <option value="published">Published</option>
                <option value="archived">Archived</option>
              </select>
            </label>

            <label class="field span-2">
              <span>Trip styles</span>
              <input v-model="tripStylesInput" type="text" placeholder="family, scenic, cultural" />
            </label>

            <label class="field span-2">
              <span>Traveler types</span>
              <input v-model="travelerTypesInput" type="text" placeholder="family, couple, friends" />
            </label>

            <label class="field span-2">
              <span>Notes for planner</span>
              <textarea v-model="form.notes_for_planner" rows="3" placeholder="Internal explanation the planner can surface to tourists"></textarea>
            </label>

            <div class="days-panel span-2">
              <div class="days-head">
                <div>
                  <p class="card-label">Day plan</p>
                  <h3>{{ form.days.length }} day entries</h3>
                </div>
                <button type="button" class="btn-light" @click="addDay">+ Add day</button>
              </div>

              <div v-if="!form.days.length" class="empty-box small">Add at least one day so tourists get a usable draft.</div>

              <div v-for="(day, index) in form.days" :key="index" class="day-card">
                <div class="day-row">
                  <strong>Day {{ index + 1 }}</strong>
                  <button type="button" class="remove-btn" @click="removeDay(index)">Remove</button>
                </div>
                <input v-model="day.title" type="text" placeholder="Arrival and local sightseeing" />
                <textarea v-model="day.summary" rows="2" placeholder="What happens on this day?"></textarea>
                <input v-model="day.overnight_location" type="text" placeholder="Overnight location" />
                <input v-model="day.highlightsInput" type="text" placeholder="Highlights separated by commas" />
              </div>
            </div>

            <div class="actions span-2">
              <button class="btn-primary" type="submit" :disabled="saving">
                {{ saving ? 'Saving…' : editingId ? 'Update template' : 'Create template' }}
              </button>
              <button class="btn-light" type="button" @click="loadAll()" :disabled="loading">Refresh list</button>
            </div>
          </form>
        </section>

        <section class="card list-card">
          <div class="card-head">
            <div>
              <p class="card-label">Published content</p>
              <h2>Your itinerary templates</h2>
              <p class="list-context-copy">{{ listContextCopy }}</p>
            </div>
          </div>

          <div class="list-toolbar">
            <div class="toolbar-filter-row">
              <label class="toolbar-filter">
                <span class="toolbar-label">Filter Name</span>
                <select v-model="selectedFilterKey">
                  <option value="">No filter</option>
                  <option v-for="filter in filterDefinitions" :key="filter.key" :value="filter.key">
                    {{ filter.label }}
                  </option>
                </select>
              </label>

              <label class="toolbar-filter toolbar-filter-wide">
                <span class="toolbar-label">Filter Value</span>
                <select v-model="selectedFilterValue" :disabled="!selectedFilterKey || loadingFilterOptions || !activeFilterValueOptions.length">
                  <option value="">{{ filterValuePlaceholder }}</option>
                  <option v-for="option in activeFilterValueOptions" :key="`${selectedFilterKey}-${option.value}`" :value="option.value">
                    {{ option.label }}<template v-if="typeof option.count === 'number'"> ({{ option.count }})</template>
                  </option>
                </select>
              </label>

              <button v-if="hasActiveListFilters" class="btn-light toolbar-clear" type="button" @click="clearListFilters" :disabled="loading">
                Clear
              </button>
            </div>

            <label class="toolbar-search toolbar-search-full">
              <span class="toolbar-label">Search Title</span>
              <input
                v-model="templateSearch"
                type="search"
                placeholder="Search by itinerary title"
                autocomplete="off"
                spellcheck="false"
              />
            </label>
          </div>

          <div v-if="loading && !templates.length" class="empty-box">Loading templates…</div>
          <div v-else-if="!templates.length" class="empty-box">{{ listEmptyMessage }}</div>
          <div v-else class="template-list">
            <article v-for="item in templates" :key="item._id" class="template-card">
              <div class="template-top">
                <div>
                  <h3>{{ item.title }}</h3>
                  <p>{{ item.summary || 'No summary provided.' }}</p>
                </div>
                <span :class="['status-pill', item.status]">{{ item.status }}</span>
              </div>
              <div class="meta-row">
                <span>{{ item.primary_location?.area_name }}</span>
                <span>{{ item.duration_days }} days</span>
                <span v-if="item.budget_band">{{ item.budget_band }}</span>
              </div>
              <div class="tag-row">
                <span v-for="style in item.trip_styles || []" :key="style" class="tag">{{ style }}</span>
              </div>
              <div class="list-actions">
                <button class="btn-light" @click="editTemplate(item)">Edit</button>
                <button class="btn-light danger" @click="deleteTemplate(item._id)">Delete</button>
              </div>
            </article>
          </div>
          <div class="pager-row">
            <span class="pager-copy">{{ templateRangeLabel }}</span>
            <div class="pager-controls">
              <button class="btn-light" type="button" @click="previousPage" :disabled="currentPage === 1 || loading">Prev</button>
              <span>Page {{ currentPage }} / {{ totalPages }}</span>
              <button class="btn-light" type="button" @click="nextPage" :disabled="!templatePagination.hasMore || loading">Next</button>
            </div>
          </div>
        </section>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue'
import api from '../services/api'
import { resolveRequestedPage } from '../utils/operatorItinerariesPagination'

const filterDefinitions = [
  { key: 'status', label: 'Status' },
  { key: 'budget', label: 'Budget' },
  { key: 'location', label: 'Location' },
  { key: 'duration', label: 'Duration' },
  { key: 'trip_style', label: 'Trip Style' },
]

const loading = ref(false)
const saving = ref(false)
const editingId = ref('')
const profile = ref(null)
const templates = ref([])
const selectedAreaIndex = ref('')
const tripStylesInput = ref('')
const travelerTypesInput = ref('')
const templateSearch = ref('')
const selectedFilterKey = ref('')
const selectedFilterValue = ref('')
const filterOptions = ref({
  status: [],
  budget: [],
  location: [],
  duration: [],
  trip_style: [],
})
const notice = ref({ type: 'info', text: '' })
const currentPage = ref(1)
const pageCursors = ref([null])
const PAGE_SIZE = 8
const templatePagination = ref({ totalItems: 0, hasMore: false, nextCursor: null })
const loadingFilterOptions = ref(false)
let searchDebounceId = 0
let activeLoadRequestId = 0
let suppressFilterReload = false

const emptyForm = () => ({
  title: '',
  summary: '',
  duration_days: 3,
  budget_band: '',
  status: 'draft',
  notes_for_planner: '',
  days: []
})

const form = ref(emptyForm())
const servingAreas = computed(() => profile.value?.serving_areas || [])
const totalTemplates = computed(() => templatePagination.value.totalItems || templates.value.length)
const totalPages = computed(() => Math.max(1, Math.ceil((templatePagination.value.totalItems || 0) / PAGE_SIZE)))
const hasActiveListFilters = computed(() => Boolean(
  templateSearch.value.trim() || (selectedFilterKey.value && selectedFilterValue.value)
))
const activeFilterDefinition = computed(() => filterDefinitions.find((filter) => filter.key === selectedFilterKey.value) || null)
const activeFilterValueOptions = computed(() => {
  if (!selectedFilterKey.value) return []
  return filterOptions.value[selectedFilterKey.value] || []
})
const filterValuePlaceholder = computed(() => {
  if (!selectedFilterKey.value) return 'Select a filter first'
  if (loadingFilterOptions.value) return 'Loading values...'
  if (!activeFilterValueOptions.value.length) return 'No values available'
  return `All ${activeFilterDefinition.value?.label?.toLowerCase() || 'values'}`
})
const listContextCopy = computed(() => {
  if (hasActiveListFilters.value) {
    return `${templatePagination.value.totalItems || templates.value.length} matching templates`
  }
  return 'Search by title and narrow results with one filter selector for status, budget, location, duration, or trip style.'
})
const listEmptyMessage = computed(() => (
  hasActiveListFilters.value
    ? 'No templates match the current search and filters.'
    : 'No templates yet. Create one to make planner retrieval useful.'
))
const templateRangeLabel = computed(() => {
  const totalItems = templatePagination.value.totalItems || 0
  if (!totalItems || !templates.value.length) return '0-0 of 0'
  const start = (currentPage.value - 1) * PAGE_SIZE + 1
  const end = start + templates.value.length - 1
  return `${start}-${end} of ${totalItems}`
})

const setNotice = (type, text) => {
  notice.value = { type, text }
  window.clearTimeout(setNotice.timeoutId)
  setNotice.timeoutId = window.setTimeout(() => {
    notice.value = { type: 'info', text: '' }
  }, 3500)
}

const parseCsv = (value) => value.split(',').map(item => item.trim()).filter(Boolean)
const formatArea = (area) => [area.area_name, area.state, area.country].filter(Boolean).join(', ')
const buildAreaKey = (area) => [area.area_name || '', area.state || '', area.country || ''].join('||')

const parseAreaFilter = (value) => {
  const [area_name, state, country] = value.split('||')
  return {
    area_name: area_name || undefined,
    state: state || undefined,
    country: country || undefined,
  }
}

const addDay = () => {
  form.value.days.push({
    day_number: form.value.days.length + 1,
    title: '',
    summary: '',
    highlightsInput: '',
    overnight_location: ''
  })
}

const removeDay = (index) => {
  form.value.days.splice(index, 1)
  form.value.days.forEach((day, idx) => {
    day.day_number = idx + 1
  })
}

const resetForm = () => {
  editingId.value = ''
  selectedAreaIndex.value = ''
  tripStylesInput.value = ''
  travelerTypesInput.value = ''
  form.value = emptyForm()
}

const normalizeDays = () => form.value.days.map((day, index) => ({
  day_number: index + 1,
  title: day.title,
  summary: day.summary || null,
  overnight_location: day.overnight_location || null,
  highlights: parseCsv(day.highlightsInput || '')
}))

const resetPagination = () => {
  currentPage.value = 1
  pageCursors.value = [null]
}

const clearListFilters = async () => {
  suppressFilterReload = true
  templateSearch.value = ''
  selectedFilterKey.value = ''
  selectedFilterValue.value = ''
  window.clearTimeout(searchDebounceId)
  resetPagination()
  suppressFilterReload = false
  await loadAll(1)
}

const buildTemplateParams = (targetPage) => {
  const params = { page_size: PAGE_SIZE }
  const currentCursor = pageCursors.value[targetPage - 1]
  if (currentCursor) params.cursor = currentCursor

  const searchValue = templateSearch.value.trim()
  if (searchValue) params.search = searchValue
  if (selectedFilterKey.value && selectedFilterValue.value) {
    if (selectedFilterKey.value === 'status') params.status = selectedFilterValue.value
    if (selectedFilterKey.value === 'budget') params.budget_band = selectedFilterValue.value
    if (selectedFilterKey.value === 'location') {
      const areaFilter = parseAreaFilter(selectedFilterValue.value)
      if (areaFilter.area_name) params.area_name = areaFilter.area_name
      if (areaFilter.state) params.state = areaFilter.state
      if (areaFilter.country) params.country = areaFilter.country
    }
    if (selectedFilterKey.value === 'duration') params.duration_days = Number(selectedFilterValue.value)
    if (selectedFilterKey.value === 'trip_style') params.trip_style = selectedFilterValue.value
  }
  return params
}

const loadProfile = async () => {
  if (profile.value) return
  const profileRes = await api.get('/operators/profile/me')
  profile.value = profileRes.data
}

const loadFilterOptions = async () => {
  loadingFilterOptions.value = true
  try {
    const response = await api.get('/itineraries/operator/templates/filter-options')
    filterOptions.value = {
      status: response.data.filters?.status || [],
      budget: response.data.filters?.budget || [],
      location: response.data.filters?.location || [],
      duration: response.data.filters?.duration || [],
      trip_style: response.data.filters?.trip_style || [],
    }
  } finally {
    loadingFilterOptions.value = false
  }
}

const loadAll = async (page = currentPage.value) => {
  const requestId = ++activeLoadRequestId
  loading.value = true
  try {
    const targetPage = resolveRequestedPage(page, currentPage.value)
    const templatesRes = await api.get('/itineraries/operator/templates', { params: buildTemplateParams(targetPage) })
    if (requestId !== activeLoadRequestId) return

    templates.value = templatesRes.data.templates || []
    templatePagination.value = {
      totalItems: templatesRes.data.pagination?.total_items || templates.value.length,
      hasMore: Boolean(templatesRes.data.pagination?.has_more),
      nextCursor: templatesRes.data.pagination?.next_cursor || null,
    }
    if (pageCursors.value.length === targetPage) {
      pageCursors.value.push(templatePagination.value.nextCursor)
    } else {
      pageCursors.value[targetPage] = templatePagination.value.nextCursor
    }
    pageCursors.value = pageCursors.value.slice(0, targetPage + 1)
    currentPage.value = targetPage
  } catch (error) {
    if (requestId !== activeLoadRequestId) return
    console.error('Failed to load operator itineraries', error)
    setNotice('error', error.response?.data?.detail || 'Failed to load itinerary data')
  } finally {
    if (requestId === activeLoadRequestId) {
      loading.value = false
    }
  }
}

const reloadFromFilters = () => {
  resetPagination()
  loadAll(1)
}

const saveTemplate = async () => {
  const selectedArea = selectedAreaIndex.value === '' ? null : servingAreas.value[Number(selectedAreaIndex.value)]
  if (!selectedArea) {
    setNotice('error', 'Choose one of your serving areas')
    return
  }

  saving.value = true
  try {
    const payload = {
      title: form.value.title,
      summary: form.value.summary || null,
      primary_location: {
        area_name: selectedArea.area_name,
        state: selectedArea.state || null,
        country: selectedArea.country || null,
        coordinates: selectedArea.coordinates || null
      },
      route_locations: [],
      duration_days: Number(form.value.duration_days),
      trip_styles: parseCsv(tripStylesInput.value),
      traveler_types: parseCsv(travelerTypesInput.value),
      season_tags: [],
      budget_band: form.value.budget_band || null,
      notes_for_planner: form.value.notes_for_planner || null,
      days: normalizeDays(),
      status: form.value.status
    }

    if (editingId.value) {
      await api.patch(`/itineraries/operator/templates/${editingId.value}`, payload)
      setNotice('success', 'Template updated')
    } else {
      await api.post('/itineraries/operator/templates', payload)
      setNotice('success', 'Template created')
    }

    resetForm()
    resetPagination()
    await loadFilterOptions()
    await loadAll(1)
  } catch (error) {
    console.error('Failed to save operator itinerary template', error)
    setNotice('error', error.response?.data?.detail || 'Failed to save template')
  } finally {
    saving.value = false
  }
}

const editTemplate = (item) => {
  editingId.value = item._id
  const areaIndex = servingAreas.value.findIndex(area =>
    area.area_name === item.primary_location?.area_name &&
    (area.state || '') === (item.primary_location?.state || '') &&
    (area.country || '') === (item.primary_location?.country || '')
  )
  selectedAreaIndex.value = areaIndex >= 0 ? String(areaIndex) : ''
  tripStylesInput.value = (item.trip_styles || []).join(', ')
  travelerTypesInput.value = (item.traveler_types || []).join(', ')
  form.value = {
    title: item.title,
    summary: item.summary || '',
    duration_days: item.duration_days || 3,
    budget_band: item.budget_band || '',
    status: item.status || 'draft',
    notes_for_planner: item.notes_for_planner || '',
    days: (item.days || []).map(day => ({
      day_number: day.day_number,
      title: day.title,
      summary: day.summary || '',
      overnight_location: day.overnight_location || '',
      highlightsInput: (day.highlights || []).join(', ')
    }))
  }
  window.scrollTo({ top: 0, behavior: 'smooth' })
}

const deleteTemplate = async (templateId) => {
  if (!window.confirm('Delete this itinerary template?')) return
  try {
    await api.delete(`/itineraries/operator/templates/${templateId}`)
    resetPagination()
    await loadFilterOptions()
    await loadAll(1)
    setNotice('success', 'Template deleted')
  } catch (error) {
    console.error('Failed to delete itinerary template', error)
    setNotice('error', error.response?.data?.detail || 'Failed to delete template')
  }
}

const previousPage = async () => {
  if (currentPage.value === 1 || loading.value) return
  await loadAll(currentPage.value - 1)
}

const nextPage = async () => {
  if (!templatePagination.value.hasMore || loading.value) return
  await loadAll(currentPage.value + 1)
}

onMounted(() => {
  loadProfile().then(() => {
    resetPagination()
    loadFilterOptions()
    loadAll(1)
  }).catch((error) => {
    console.error('Failed to load operator profile', error)
    setNotice('error', error.response?.data?.detail || 'Failed to load itinerary data')
  })
})

watch(selectedFilterKey, () => {
  if (suppressFilterReload) return
  suppressFilterReload = true
  selectedFilterValue.value = ''
  window.clearTimeout(searchDebounceId)
  suppressFilterReload = false
  reloadFromFilters()
})

watch(selectedFilterValue, () => {
  if (suppressFilterReload) return
  reloadFromFilters()
})

watch(templateSearch, () => {
  if (suppressFilterReload) return
  window.clearTimeout(searchDebounceId)
  searchDebounceId = window.setTimeout(() => {
    reloadFromFilters()
  }, 250)
})

onBeforeUnmount(() => {
  window.clearTimeout(searchDebounceId)
})
</script>

<style scoped>
.op-it-page {
  min-height: 100vh;
  background: #f0f4f8;
  padding-bottom: 4rem;
}
.hero {
  background: linear-gradient(135deg, #0f172a 0%, #1d3557 55%, #0f766e 100%);
  padding: 4rem 2rem 6rem;
}
.hero-inner {
  max-width: 1180px;
  margin: 0 auto;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 1rem;
  color: #fff;
}
.eyebrow, .card-label {
  display: inline-block;
  font-size: 0.72rem;
  font-weight: 700;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #94a3b8;
}
.hero .eyebrow {
  color: #7dd3fc;
  margin-bottom: 0.8rem;
}
.hero h1 {
  margin: 0;
  font-size: clamp(2rem, 4vw, 3rem);
  line-height: 1.1;
}
.hero p {
  color: rgba(255,255,255,0.72);
  line-height: 1.6;
}
.hero-stats {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.8rem;
  align-self: end;
}
.stat-box {
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 16px;
  padding: 1rem;
}
.stat-box strong {
  display: block;
  font-size: 1.5rem;
}
.container {
  max-width: 1180px;
  margin: -3rem auto 0;
  padding: 0 1.5rem;
}
.notice {
  margin-bottom: 1rem;
  padding: 0.9rem 1rem;
  border-radius: 12px;
  font-weight: 600;
}
.notice.success { background: #f0fdf4; border: 1px solid #bbf7d0; color: #166534; }
.notice.error { background: #fef2f2; border: 1px solid #fecaca; color: #b91c1c; }
.grid {
  display: grid;
  grid-template-columns: 1.05fr 0.95fr;
  gap: 1.4rem;
}
.card {
  background: #fff;
  border-radius: 20px;
  border: 1px solid #eef2f7;
  box-shadow: 0 10px 30px rgba(15,23,42,0.08);
  padding: 1.4rem;
}
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  margin-bottom: 1rem;
}
.card-head h2 {
  margin: 0.2rem 0 0;
  color: #0f172a;
  font-size: 1.2rem;
}
.list-context-copy {
  margin: 0.45rem 0 0;
  color: #64748b;
  font-size: 0.92rem;
  line-height: 1.5;
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}
.field {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.field span {
  font-size: 0.8rem;
  font-weight: 700;
  color: #475569;
}
.field input,
.field select,
.field textarea {
  width: 100%;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #f8fafc;
  padding: 0.75rem 0.85rem;
  font: inherit;
}
.span-2 { grid-column: 1 / -1; }
.list-toolbar {
  display: flex;
  flex-direction: column;
  gap: 0.85rem;
  margin-bottom: 1rem;
}
.toolbar-filter-row {
  display: grid;
  grid-template-columns: minmax(180px, 0.8fr) minmax(220px, 1fr) auto;
  gap: 0.75rem;
  align-items: end;
}
.toolbar-search,
.toolbar-filter {
  display: flex;
  flex-direction: column;
  gap: 0.35rem;
}
.toolbar-search-full {
  width: 100%;
}
.toolbar-label {
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #64748b;
}
.toolbar-search input,
.toolbar-filter select {
  width: 100%;
  border: 1px solid #dbe4ee;
  border-radius: 10px;
  background: #f8fafc;
  padding: 0.72rem 0.8rem;
  font: inherit;
}
.toolbar-filter-wide {
  min-width: 0;
}
.toolbar-clear {
  white-space: nowrap;
}
.days-panel {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
}
.days-head, .day-row, .template-top, .list-actions, .actions {
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  align-items: center;
}
.day-card, .template-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  background: #fafcff;
}
.template-card h3 {
  margin: 0;
  color: #0f172a;
}
.template-card p {
  margin: 0.25rem 0 0;
  color: #64748b;
}
.pager-row {
  margin-top: 1rem;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 1rem;
}
.pager-copy {
  color: #64748b;
  font-size: 0.88rem;
}
.pager-controls {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}
.meta-row, .tag-row {
  display: flex;
  gap: 0.5rem;
  flex-wrap: wrap;
}
.meta-row span, .tag, .status-pill {
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 700;
}
.meta-row span, .tag { background: #f1f5f9; color: #475569; }
.status-pill.draft { background: #f8fafc; color: #475569; border: 1px solid #dbe4ee; }
.status-pill.published { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.status-pill.archived { background: #fef2f2; color: #b91c1c; border: 1px solid #fecaca; }
.btn-primary, .btn-light, .remove-btn {
  border: none;
  border-radius: 10px;
  font: inherit;
  cursor: pointer;
}
.btn-primary { background: linear-gradient(135deg, #0ea5e9, #2563eb); color: #fff; padding: 0.8rem 1.1rem; }
.btn-light, .remove-btn { background: #fff; border: 1px solid #dbe4ee; color: #334155; padding: 0.65rem 0.9rem; }
.btn-light.danger { background: #fff5f5; border-color: #fecaca; color: #b91c1c; }
.empty-box {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 220px;
  background: #f8fafc;
  border: 1px dashed #dbe4ee;
  border-radius: 14px;
  text-align: center;
  color: #64748b;
  padding: 1rem;
}
.empty-box.small { min-height: 100px; }
@media (max-width: 960px) {
  .hero-inner, .grid { grid-template-columns: 1fr; }
  .toolbar-filter-row {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
  .toolbar-clear {
    grid-column: 1 / -1;
    justify-self: start;
  }
}
@media (max-width: 640px) {
  .hero { padding: 3rem 1rem 5rem; }
  .container { padding: 0 1rem; }
  .form-grid { grid-template-columns: 1fr; }
  .span-2 { grid-column: auto; }
  .toolbar-filter-row {
    grid-template-columns: 1fr;
  }
  .card-head, .template-top, .actions, .days-head, .day-row, .list-actions { flex-direction: column; align-items: stretch; }
}
</style>
