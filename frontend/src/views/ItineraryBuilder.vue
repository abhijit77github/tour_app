<template>
  <div class="it-page">
    <section class="hero">
      <div class="hero-inner">
        <div>
          <span class="eyebrow">Trip design</span>
          <h1>Create your itinerary first, then attach it to a quote when ready</h1>
          <p>Browse operator-curated itinerary templates, save one as your starting point, edit it, and later share it with operators as optional context.</p>
        </div>
        <div class="hero-stats">
          <div class="stat-box">
            <strong>{{ templates.length }}</strong>
            <span>Matching templates</span>
          </div>
          <div class="stat-box">
            <strong>{{ itineraries.length }}</strong>
            <span>Saved itineraries</span>
          </div>
        </div>
      </div>
    </section>

    <div class="container">
      <div v-if="notice.text" :class="['notice', notice.type]">{{ notice.text }}</div>

      <StepGuidePanel
        class="journey-panel"
        variant="itinerary"
        eyebrow="How It Works"
        title="Turn rough trip ideas into reusable itinerary drafts"
        description="Start from grounded templates or a blank draft, shape the day-by-day flow, then decide whether operators can see it when you publish a quote request."
        :steps="itinerarySteps"
      />

      <div class="grid">
        <section class="card search-card">
          <div class="card-head">
            <div>
              <p class="card-label">Retrieve templates</p>
              <h2>Find matching itinerary ideas</h2>
            </div>
            <button class="btn-light" @click="searchTemplates" :disabled="searching">{{ searching ? 'Searching…' : 'Search' }}</button>
          </div>

          <div class="filters">
            <input v-model="filters.area_name" type="text" placeholder="Destination" />
            <input v-model="filters.state" type="text" placeholder="State / region" />
            <input v-model.number="filters.duration_days" type="number" min="1" max="30" placeholder="Duration days" />
            <input v-model="filters.trip_styles" type="text" placeholder="Styles: family, cultural" />
          </div>

          <div v-if="!templates.length" class="empty-box small">Search by destination and duration to load operator-curated itinerary templates.</div>
          <div v-else class="template-list">
            <article v-for="item in templates" :key="item._id" class="template-card">
              <div class="template-top">
                <div>
                  <h3>{{ item.title }}</h3>
                  <p>{{ item.summary || 'No summary provided.' }}</p>
                </div>
                <span class="operator-chip">{{ item.operator_name }}</span>
              </div>
              <div class="meta-row">
                <span>{{ item.primary_location?.area_name }}</span>
                <span>{{ item.duration_days }} days</span>
                <span v-if="item.budget_band">{{ item.budget_band }}</span>
                <span>Score {{ Number(item.score || 0).toFixed(1) }}</span>
              </div>
              <div class="tag-row">
                <span v-for="style in item.trip_styles || []" :key="style" class="tag">{{ style }}</span>
              </div>
              <div class="list-actions">
                <button class="btn-primary" @click="createFromTemplate(item._id)">Use as base</button>
              </div>
            </article>
          </div>
        </section>

        <section class="card form-card">
          <div class="card-head">
            <div>
              <p class="card-label">Your draft</p>
              <h2>{{ editingId ? 'Edit itinerary' : 'New itinerary' }}</h2>
              <p class="card-subhead">Build a clean route summary first, then add the day-level pacing that operators or future-you can actually reuse.</p>
            </div>
            <div class="header-actions">
              <router-link to="/quote-builder" class="btn-light">Open Quote Builder</router-link>
              <button v-if="editingId" class="btn-light" @click="resetForm">Cancel edit</button>
            </div>
          </div>

          <form class="form-grid" @submit.prevent="saveItinerary">
            <div class="draft-overview span-2">
              <article class="draft-metric">
                <span class="draft-kicker">Mode</span>
                <strong>{{ editingId ? 'Updating existing plan' : 'Creating a fresh draft' }}</strong>
                <p>{{ editingId ? 'Polish what you already saved without rebuilding the route.' : 'Use this as your base before you talk to operators.' }}</p>
              </article>
              <article class="draft-metric">
                <span class="draft-kicker">Coverage</span>
                <strong>{{ form.days.length }} structured day{{ form.days.length !== 1 ? 's' : '' }}</strong>
                <p>{{ form.days.length ? 'Each day helps explain pacing, stops, and overnight flow.' : 'Add days once the route and duration feel right.' }}</p>
              </article>
              <article class="draft-metric">
                <span class="draft-kicker">Sharing</span>
                <strong>{{ form.shareable_to_quote ? 'Ready for quote context' : 'Private draft only' }}</strong>
                <p>{{ form.shareable_to_quote ? 'Operators can see the itinerary snapshot when you attach it to a quote.' : 'Keep this saved only for your own planning until it is ready.' }}</p>
              </article>
            </div>

            <div class="section-intro span-2">
              <span class="section-index">01</span>
              <div>
                <h3>Core trip frame</h3>
                <p>Give the itinerary a clear name, summary, destination anchor, and duration before filling the deeper preferences.</p>
              </div>
            </div>

            <label class="field span-2">
              <span>Title</span>
              <input v-model="form.title" type="text" placeholder="My 5-day Manali trip" required />
            </label>

            <label class="field span-2">
              <span>Summary</span>
              <textarea v-model="form.summary" rows="3" placeholder="Short summary of the trip"></textarea>
            </label>

            <label class="field">
              <span>Primary destination</span>
              <input v-model="form.primary_area_name" type="text" placeholder="Manali" />
            </label>

            <label class="field">
              <span>State</span>
              <input v-model="form.primary_state" type="text" placeholder="Himachal Pradesh" />
            </label>

            <label class="field">
              <span>Country</span>
              <input v-model="form.primary_country" type="text" placeholder="India" />
            </label>

            <label class="field">
              <span>Duration</span>
              <input v-model.number="form.duration_days" type="number" min="1" max="30" required />
            </label>

            <label class="field">
              <span>Travelers</span>
              <input v-model.number="form.travelers" type="number" min="1" placeholder="2" />
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

            <div class="section-intro span-2 muted">
              <span class="section-index">02</span>
              <div>
                <h3>Trip style and share rules</h3>
                <p>These details make the itinerary easier to retrieve later and safer to attach to quote requests without extra explanation.</p>
              </div>
            </div>

            <label class="field span-2">
              <span>Trip styles</span>
              <input v-model="tripStylesInput" type="text" placeholder="relaxed, family, scenic" />
            </label>

            <label class="field span-2">
              <span>Notes</span>
              <textarea v-model="form.notes" rows="3" placeholder="Anything operators should know if you share this later?"></textarea>
            </label>

            <label class="toggle-row span-2">
              <input v-model="form.shareable_to_quote" type="checkbox" />
              <div>
                <strong>Allow attaching this itinerary to quote requests</strong>
                <p>Turn this off if the route is still experimental or too incomplete for operator review.</p>
              </div>
            </label>

            <div class="section-intro span-2 muted">
              <span class="section-index">03</span>
              <div>
                <h3>Day-by-day route</h3>
                <p>Use day cards for arrivals, transfer days, and meaningful highlights. Keep it structured enough that another person can understand the pacing instantly.</p>
              </div>
            </div>

            <div class="days-panel span-2">
              <div class="days-head">
                <div>
                  <p class="card-label">Day-wise plan</p>
                  <h3>{{ form.days.length }} day entries</h3>
                </div>
                <button type="button" class="btn-light" @click="addDay">+ Add day</button>
              </div>

              <div v-if="!form.days.length" class="empty-box small">Add day entries to make this itinerary useful to operators later.</div>
              <div v-for="(day, index) in form.days" :key="index" class="day-card">
                <div class="day-row">
                  <strong>Day {{ index + 1 }}</strong>
                  <button type="button" class="remove-btn" @click="removeDay(index)">Remove</button>
                </div>
                <input v-model="day.title" type="text" placeholder="Arrival and local walk" />
                <textarea v-model="day.summary" rows="2" placeholder="What happens on this day?"></textarea>
                <input v-model="day.overnight_location" type="text" placeholder="Overnight location" />
                <input v-model="day.highlightsInput" type="text" placeholder="Highlights separated by commas" />
              </div>
            </div>

            <div class="actions span-2">
              <button class="btn-primary" type="submit" :disabled="saving">
                {{ saving ? 'Saving…' : editingId ? 'Update itinerary' : 'Save itinerary' }}
              </button>
            </div>
          </form>
        </section>
      </div>

      <section class="card saved-card">
        <div class="card-head">
          <div>
            <p class="card-label">Saved itineraries</p>
            <h2>Your reusable drafts</h2>
          </div>
        </div>

        <div v-if="loading && !itineraries.length" class="empty-box">Loading itineraries…</div>
        <div v-else-if="!itineraries.length" class="empty-box">No saved itineraries yet.</div>
        <div v-else class="saved-list">
          <article v-for="item in itineraries" :key="item._id" class="saved-item">
            <div class="template-top">
              <div class="saved-copy">
                <h3>{{ item.title }}</h3>
                <p>{{ item.summary || 'No summary provided.' }}</p>
              </div>
              <span :class="['status-pill', item.shareable_to_quote ? 'published' : 'draft']">
                {{ item.shareable_to_quote ? 'Shareable' : 'Private' }}
              </span>
            </div>
            <div class="meta-row">
              <span>{{ item.primary_location?.area_name || 'No destination' }}</span>
              <span>{{ item.duration_days }} days</span>
              <span v-if="item.budget_band">{{ item.budget_band }}</span>
              <span>{{ item.source_type }}</span>
            </div>
            <div class="list-actions">
              <button class="btn-light" @click="editItinerary(item)">Edit</button>
              <button class="btn-light danger" @click="deleteItinerary(item._id)">Delete</button>
            </div>
          </article>
        </div>
      </section>
    </div>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute } from 'vue-router'
import StepGuidePanel from '../components/StepGuidePanel.vue'
import api from '../services/api'

const route = useRoute()
const loading = ref(false)
const searching = ref(false)
const saving = ref(false)
const templates = ref([])
const itineraries = ref([])
const editingId = ref('')
const tripStylesInput = ref('')
const notice = ref({ type: 'info', text: '' })
const itinerarySteps = [
  { title: 'Scan template ideas', detail: 'Search grounded itinerary templates by destination, state, and duration so you start from something realistic.' },
  { title: 'Shape your own draft', detail: 'Rename it, tighten the summary, set budget and traveler fit, and decide whether it should stay private or be shareable.' },
  { title: 'Save for future quotes', detail: 'Once the route is clean, keep it in My Itineraries and attach it only when it helps operators respond with better offers.' }
]
const filters = ref({
  area_name: route.query.area_name || '',
  state: route.query.state || '',
  duration_days: route.query.duration_days ? Number(route.query.duration_days) : '',
  trip_styles: route.query.trip_styles || ''
})

const emptyForm = () => ({
  title: '',
  summary: '',
  primary_area_name: '',
  primary_state: '',
  primary_country: '',
  duration_days: 3,
  travelers: null,
  budget_band: '',
  notes: '',
  shareable_to_quote: true,
  days: []
})

const form = ref(emptyForm())

const setNotice = (type, text) => {
  notice.value = { type, text }
  window.clearTimeout(setNotice.timeoutId)
  setNotice.timeoutId = window.setTimeout(() => {
    notice.value = { type: 'info', text: '' }
  }, 3500)
}

const parseCsv = (value) => value.split(',').map(item => item.trim()).filter(Boolean)
const addDay = () => {
  form.value.days.push({ day_number: form.value.days.length + 1, title: '', summary: '', overnight_location: '', highlightsInput: '' })
}

const removeDay = (index) => {
  form.value.days.splice(index, 1)
  form.value.days.forEach((day, idx) => {
    day.day_number = idx + 1
  })
}

const resetForm = () => {
  editingId.value = ''
  tripStylesInput.value = ''
  form.value = emptyForm()
}

const buildPayload = () => ({
  title: form.value.title,
  summary: form.value.summary || null,
  primary_location: form.value.primary_area_name ? {
    area_name: form.value.primary_area_name,
    state: form.value.primary_state || null,
    country: form.value.primary_country || null,
    coordinates: null
  } : null,
  route_locations: [],
  duration_days: Number(form.value.duration_days),
  trip_styles: parseCsv(tripStylesInput.value),
  travelers: form.value.travelers || null,
  budget_band: form.value.budget_band || null,
  notes: form.value.notes || null,
  days: form.value.days.map((day, index) => ({
    day_number: index + 1,
    title: day.title,
    summary: day.summary || null,
    overnight_location: day.overnight_location || null,
    highlights: parseCsv(day.highlightsInput || '')
  })),
  status: 'saved',
  source_type: 'manual',
  source_template_ids: [],
  shareable_to_quote: form.value.shareable_to_quote
})

const loadMyItineraries = async () => {
  const res = await api.get('/itineraries/my')
  itineraries.value = res.data.itineraries || []
}

const searchTemplates = async () => {
  searching.value = true
  try {
    const params = {}
    if (filters.value.area_name) params.area_name = filters.value.area_name
    if (filters.value.state) params.state = filters.value.state
    if (filters.value.duration_days) params.duration_days = filters.value.duration_days
    if (filters.value.trip_styles) params.trip_styles = filters.value.trip_styles
    const res = await api.get('/itineraries/search', { params })
    templates.value = res.data.itineraries || []
  } catch (error) {
    console.error('Failed to search templates', error)
    setNotice('error', error.response?.data?.detail || 'Failed to search itinerary templates')
  } finally {
    searching.value = false
  }
}

const createFromTemplate = async (templateId) => {
  try {
    const res = await api.post(`/itineraries/my/from-template/${templateId}`)
    itineraries.value = [res.data.itinerary, ...itineraries.value]
    setNotice('success', 'Itinerary created from template')
  } catch (error) {
    console.error('Failed to create itinerary from template', error)
    setNotice('error', error.response?.data?.detail || 'Failed to create itinerary from template')
  }
}

const saveItinerary = async () => {
  saving.value = true
  try {
    const payload = buildPayload()
    if (editingId.value) {
      await api.patch(`/itineraries/my/${editingId.value}`, payload)
      setNotice('success', 'Itinerary updated')
    } else {
      await api.post('/itineraries/my', payload)
      setNotice('success', 'Itinerary saved')
    }
    resetForm()
    await loadMyItineraries()
  } catch (error) {
    console.error('Failed to save itinerary', error)
    setNotice('error', error.response?.data?.detail || 'Failed to save itinerary')
  } finally {
    saving.value = false
  }
}

const editItinerary = (item) => {
  editingId.value = item._id
  tripStylesInput.value = (item.trip_styles || []).join(', ')
  form.value = {
    title: item.title,
    summary: item.summary || '',
    primary_area_name: item.primary_location?.area_name || '',
    primary_state: item.primary_location?.state || '',
    primary_country: item.primary_location?.country || '',
    duration_days: item.duration_days || 3,
    travelers: item.travelers || null,
    budget_band: item.budget_band || '',
    notes: item.notes || '',
    shareable_to_quote: item.shareable_to_quote !== false,
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

const deleteItinerary = async (id) => {
  if (!window.confirm('Delete this itinerary?')) return
  try {
    await api.delete(`/itineraries/my/${id}`)
    itineraries.value = itineraries.value.filter(item => item._id !== id)
    setNotice('success', 'Itinerary deleted')
  } catch (error) {
    console.error('Failed to delete itinerary', error)
    setNotice('error', error.response?.data?.detail || 'Failed to delete itinerary')
  }
}

onMounted(async () => {
  loading.value = true
  try {
    await Promise.all([loadMyItineraries(), searchTemplates()])
  } finally {
    loading.value = false
  }
})
</script>

<style scoped>
.it-page {
  min-height: 100vh;
  background: #f0f4f8;
  padding-bottom: 4rem;
}
.hero {
  background: linear-gradient(135deg, #0f172a 0%, #1b3150 55%, #0f766e 100%);
  padding: 4rem 2rem 6rem;
}
.hero-inner {
  max-width: 1180px;
  margin: 0 auto;
  color: #fff;
  display: grid;
  grid-template-columns: 1.2fr 0.8fr;
  gap: 1rem;
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
.hero p { color: rgba(255,255,255,0.72); line-height: 1.6; }
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
.stat-box strong { display: block; font-size: 1.5rem; }
.container {
  max-width: 1180px;
  margin: -3rem auto 0;
  padding: 0 1.5rem;
}
.journey-panel {
  margin-bottom: 1.4rem;
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
  grid-template-columns: 0.9fr 1.1fr;
  gap: 1.4rem;
}
.card {
  background: #fff;
  border-radius: 20px;
  border: 1px solid #eef2f7;
  box-shadow: 0 10px 30px rgba(15,23,42,0.08);
  padding: 1.4rem;
}
.saved-card { margin-top: 1.4rem; }
.card-head {
  display: flex;
  justify-content: space-between;
  gap: 1rem;
  align-items: flex-start;
  margin-bottom: 1rem;
}
.card-subhead {
  margin: 0.45rem 0 0;
  color: #64748b;
  line-height: 1.55;
  max-width: 52ch;
}
.card-head h2 { margin: 0.2rem 0 0; color: #0f172a; font-size: 1.2rem; }
.header-actions, .filters, .actions, .days-head, .day-row, .template-top, .meta-row, .tag-row, .list-actions {
  display: flex;
  gap: 0.8rem;
  flex-wrap: wrap;
}
.filters { margin-bottom: 1rem; }
.filters input {
  flex: 1;
  min-width: 160px;
}
.form-card {
  background:
    radial-gradient(circle at top right, rgba(14,165,233,0.08), transparent 28%),
    linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
}
.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.9rem;
}
.draft-overview {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.8rem;
}
.draft-metric {
  padding: 1rem;
  border-radius: 18px;
  background: rgba(255,255,255,0.88);
  border: 1px solid #dbeafe;
  box-shadow: inset 0 1px 0 rgba(255,255,255,0.7);
}
.draft-kicker {
  display: inline-block;
  margin-bottom: 0.35rem;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  color: #0284c7;
}
.draft-metric strong {
  display: block;
  color: #0f172a;
  font-size: 1rem;
}
.draft-metric p {
  margin: 0.35rem 0 0;
  color: #64748b;
  font-size: 0.85rem;
  line-height: 1.55;
}
.section-intro {
  display: grid;
  grid-template-columns: auto 1fr;
  gap: 0.8rem;
  align-items: start;
  padding: 0.95rem 1rem;
  border-radius: 18px;
  background: #eff6ff;
  border: 1px solid #dbeafe;
}
.section-intro.muted {
  background: #f8fafc;
  border-color: #e2e8f0;
}
.section-index {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 14px;
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: #fff;
  font-size: 0.82rem;
  font-weight: 800;
}
.section-intro.muted .section-index {
  background: linear-gradient(135deg, #64748b, #334155);
}
.section-intro h3 {
  margin: 0;
  color: #0f172a;
  font-size: 1rem;
}
.section-intro p {
  margin: 0.25rem 0 0;
  color: #64748b;
  line-height: 1.55;
  font-size: 0.86rem;
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
.field input, .field select, .field textarea, .filters input {
  width: 100%;
  border: 1px solid #dbe4ee;
  border-radius: 14px;
  background: rgba(255,255,255,0.96);
  padding: 0.85rem 0.95rem;
  font: inherit;
  color: #0f172a;
  transition: border-color 0.2s, box-shadow 0.2s, transform 0.15s;
}
.field input:focus, .field select:focus, .field textarea:focus, .filters input:focus {
  outline: none;
  border-color: #60a5fa;
  box-shadow: 0 0 0 4px rgba(96, 165, 250, 0.14);
}
.span-2 { grid-column: 1 / -1; }
.toggle-row {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  padding: 0.95rem 1rem;
  border-radius: 18px;
  background: rgba(255,255,255,0.88);
  border: 1px solid #e2e8f0;
  color: #334155;
}
.toggle-row input {
  margin-top: 0.2rem;
}
.toggle-row strong {
  display: block;
  font-size: 0.92rem;
}
.toggle-row p {
  margin: 0.22rem 0 0;
  font-size: 0.84rem;
  color: #64748b;
  line-height: 1.5;
}
.days-panel {
  display: flex;
  flex-direction: column;
  gap: 0.8rem;
  padding: 1rem;
  border-radius: 22px;
  background: linear-gradient(180deg, #f8fbff 0%, #f8fafc 100%);
  border: 1px solid #dbeafe;
}
.template-list, .saved-list { display: flex; flex-direction: column; gap: 0.9rem; }
.template-card, .saved-item, .day-card {
  border: 1px solid #e2e8f0;
  border-radius: 14px;
  padding: 0.9rem;
  display: flex;
  flex-direction: column;
  gap: 0.6rem;
  background: #fafcff;
}
.day-card {
  background: rgba(255,255,255,0.94);
  border-radius: 20px;
  padding: 1rem;
  box-shadow: 0 8px 22px rgba(15,23,42,0.05);
}
.day-card input,
.day-card textarea {
  width: 100%;
  border: 1px solid #dbe4ee;
  border-radius: 12px;
  background: #fff;
  padding: 0.78rem 0.85rem;
  font: inherit;
}
.day-card input:focus,
.day-card textarea:focus {
  outline: none;
  border-color: #60a5fa;
  box-shadow: 0 0 0 4px rgba(96, 165, 250, 0.12);
}
.template-card h3, .saved-item h3 { margin: 0; color: #0f172a; }
.template-card p, .saved-item p { margin: 0.25rem 0 0; color: #64748b; }
.meta-row span, .tag, .status-pill, .operator-chip {
  border-radius: 999px;
  padding: 0.2rem 0.6rem;
  font-size: 0.75rem;
  font-weight: 700;
}
.saved-copy {
  min-width: 0;
  flex: 1;
}
.saved-item .template-top {
  align-items: flex-start;
}
.meta-row span, .tag { background: #f1f5f9; color: #475569; }
.operator-chip { background: #eff6ff; color: #1d4ed8; }
.status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  align-self: flex-start;
  flex-shrink: 0;
  min-height: 2rem;
  padding: 0.32rem 0.82rem;
  font-size: 0.78rem;
  line-height: 1;
  white-space: nowrap;
}
.status-pill.published { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.status-pill.draft { background: #f8fafc; color: #475569; border: 1px solid #dbe4ee; }
.btn-primary, .btn-light, .remove-btn {
  border: none;
  border-radius: 10px;
  font: inherit;
  cursor: pointer;
}
.btn-primary { background: linear-gradient(135deg, #0ea5e9, #2563eb); color: #fff; padding: 0.8rem 1.1rem; }
.btn-light, .remove-btn { background: #fff; border: 1px solid #dbe4ee; color: #334155; padding: 0.65rem 0.9rem; text-decoration: none; }
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
  .draft-overview { grid-template-columns: 1fr; }
}
@media (max-width: 640px) {
  .hero { padding: 3rem 1rem 5rem; }
  .container { padding: 0 1rem; }
  .form-grid { grid-template-columns: 1fr; }
  .span-2 { grid-column: auto; }
  .card-head, .header-actions, .template-top, .list-actions, .actions, .days-head, .day-row, .toggle-row { flex-direction: column; align-items: stretch; }
  .section-intro { grid-template-columns: 1fr; }
  .saved-item .template-top {
    align-items: stretch;
  }
  .status-pill {
    width: fit-content;
  }
}
</style>
