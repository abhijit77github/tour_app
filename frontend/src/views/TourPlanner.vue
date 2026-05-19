<template>
  <div class="planner-shell">
    <div class="planner-page">
      <aside class="planner-sidebar">
        <div class="sidebar-glow"></div>
        <div class="sidebar-header">
          <div class="eyebrow">AI trip concierge</div>
          <h2>Plan smarter, pick faster.</h2>
          <p class="sidebar-sub">
            Describe the trip once. Compare the best matches and add individually.
          </p>
        </div>

        <div v-if="hasRequirements" class="req-card glass-card" v-show="showTripBrief">
          <div class="card-title-row compact-title-row">
            <h3>Your trip brief</h3>
            <span class="mini-pill">In progress</span>
          </div>

          <div class="req-grid">
            <div class="req-item" v-if="requirements.locations?.length">
              <span class="req-label">Destinations</span>
              <span>{{ requirements.locations.join(', ') }}</span>
            </div>
            <div class="req-item" v-if="requirements.travel_dates">
              <span class="req-label">Travel window</span>
              <span>{{ requirements.travel_dates }}</span>
            </div>
            <div class="req-item" v-if="requirements.group_size">
              <span class="req-label">Group size</span>
              <span>{{ requirements.group_size }} people</span>
            </div>
            <div class="req-item" v-if="requirements.budget_usd">
              <span class="req-label">Budget</span>
              <span>${{ requirements.budget_usd }}</span>
            </div>
            <div class="req-item" v-if="requirements.duration_days">
              <span class="req-label">Duration</span>
              <span>{{ requirements.duration_days }} days</span>
            </div>
            <div class="req-item" v-if="requirements.preferences?.length">
              <span class="req-label">Style</span>
              <span>{{ requirements.preferences.join(', ') }}</span>
            </div>
          </div>
        </div>

        <div class="operator-header" v-if="suggestedOperators.length">
          <div>
            <h3>Matched operators</h3>
            <p>Choose any operator you want to keep in the cart.</p>
          </div>
          <div class="header-actions">
            <span class="mini-pill count-pill">{{ suggestedOperators.length }}</span>
            <button class="mini-toggle" type="button" @click="showOperators = !showOperators">
              {{ showOperators ? 'Hide' : 'Show' }}
            </button>
          </div>
        </div>

        <div v-if="suggestedOperators.length && showOperators" class="operators-panel">
          <div
            v-for="op in suggestedOperators"
            :key="op.id"
            class="operator-card glass-card"
            :class="{ added: addedIds.has(op.id) }"
          >
            <div class="op-topline">
              <div class="op-avatar">{{ op.business_name?.charAt(0)?.toUpperCase() || 'T' }}</div>
              <div class="op-meta">
                <h4>{{ op.business_name }}</h4>
                <div class="op-match-row">
                  <span class="match-pill" :class="matchClass(op)">{{ matchLabel(op) }}</span>
                  <span v-if="op.budget_fit" class="match-pill budget-pill">Budget fit</span>
                  <span class="match-score">Score {{ Number(op.score || 0).toFixed(1) }}</span>
                </div>
                <div class="op-rating-row">
                  <span class="op-rating">★ {{ Number(op.average_rating || 0).toFixed(1) }}</span>
                  <span class="op-reviews">{{ op.total_reviews || 0 }} reviews</span>
                </div>
              </div>
            </div>

            <p v-if="op.match_reason" class="op-match-reason">{{ op.match_reason }}</p>

            <p v-if="op.description" class="op-description">{{ op.description }}</p>

            <div class="op-areas">
              <span v-for="area in op.serving_areas.slice(0, 3)" :key="area" class="area-tag">
                {{ area }}
              </span>
            </div>

            <div class="op-footer">
              <p v-if="op.price_range" class="op-price">{{ op.price_range }}</p>
              <div class="op-actions">
                <button
                  v-if="!addedIds.has(op.id)"
                  class="btn-add"
                  :disabled="addingId === op.id"
                  @click="addToCart(op)"
                >
                  {{ addingId === op.id ? 'Adding...' : 'Add to Cart' }}
                </button>
                <span v-else class="added-label">Added</span>
                <router-link :to="`/operator/${op.user_id}`" class="btn-view" target="_blank">
                  Profile
                </router-link>
              </div>
            </div>
          </div>
        </div>

        <button class="btn-new-session" @click="startNewSession">
          + Start fresh itinerary
        </button>
      </aside>

      <main class="chat-area">
        <section class="planner-toolbar glass-card">
          <div class="toolbar-main">
            <strong>Tour Planner</strong>
            <span class="toolbar-sub">Live assistant with ranked operator matching</span>
          </div>
          <div class="toolbar-stats">
            <div>
              <strong>{{ suggestedOperators.length }}</strong>
              <span>Recommendations</span>
            </div>
            <div>
              <strong>{{ addedIds.size }}</strong>
              <span>Added to cart</span>
            </div>
            <div>
              <strong>{{ messages.length }}</strong>
              <span>Messages</span>
            </div>
          </div>
        </section>

        <div class="messages glass-card" ref="messagesEl">
          <div v-if="!messages.length" class="welcome-state">
            <div class="welcome-badge">Tell me the destination, budget, and vibe</div>
            <div class="welcome-icon">🧭</div>
            <h2>Start with a plain-English trip request</h2>
            <p>
              For example: “I want Coorg for 4 days with my family, mid-range budget, and a relaxed itinerary.”
            </p>
            <div class="starter-chips">
              <button
                v-for="prompt in starterPrompts"
                :key="prompt"
                class="chip"
                @click="sendStarter(prompt)"
              >
                {{ prompt }}
              </button>
            </div>
          </div>

          <div
            v-for="(msg, idx) in messages"
            :key="idx"
            class="message"
            :class="msg.role"
          >
            <div class="bubble">
              <span class="msg-role">{{ msg.role === 'user' ? 'You' : 'Tour Planner' }}</span>
              <p class="msg-text" v-html="formatText(msg.text)"></p>
            </div>
          </div>

          <div v-if="streamingText" class="message assistant streaming">
            <div class="bubble">
              <span class="msg-role">Tour Planner</span>
              <p class="msg-text" v-html="formatText(streamingText)"></p>
              <span class="cursor">▍</span>
            </div>
          </div>

          <div v-if="statusText && !streamingText" class="status-line">
            <span class="status-dot"></span>
            <span>{{ statusText }}</span>
          </div>
        </div>

        <form class="chat-input-area glass-card" @submit.prevent="sendMessage">
          <div class="input-wrap">
            <textarea
              ref="inputEl"
              v-model="input"
              :disabled="streaming"
              placeholder="Describe your trip..."
              rows="1"
              @keydown.enter.exact.prevent="sendMessage"
              @input="autoResize"
            ></textarea>
            <p class="input-hint">Include destination, dates, travelers, budget, and preferences.</p>
          </div>
          <button type="submit" :disabled="streaming || !input.trim()" class="btn-send">
            <span v-if="!streaming">Send</span>
            <span v-else class="sending-dots"><span></span><span></span><span></span></span>
          </button>
        </form>
      </main>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import api from '../services/api'
import { useCartStore } from '../stores/cart'

// ─── State ───────────────────────────────────────────────────────────────────
const sessionId = ref(localStorage.getItem('plannerSessionId') || uuidv4())
const messages = ref([])
const suggestedOperators = ref([])
const requirements = ref({})
const input = ref('')
const streaming = ref(false)
const streamingText = ref('')
const statusText = ref('')
const addedIds = ref(new Set())
const addingId = ref(null)
const showTripBrief = ref(true)
const showOperators = ref(true)
const messagesEl = ref(null)
const inputEl = ref(null)
const cartStore = useCartStore()

const hasRequirements = computed(() =>
  requirements.value.locations?.length ||
  requirements.value.travel_dates ||
  requirements.value.group_size
)

const starterPrompts = [
  'I want to visit Coorg for 4 days with family',
  'Planning a trip to Goa next month, budget $500',
  'Adventure trip to Himalayas for 2 people',
  'Cultural tour of Rajasthan for 5 days',
]

// ─── Lifecycle ────────────────────────────────────────────────────────────────
onMounted(async () => {
  localStorage.setItem('plannerSessionId', sessionId.value)
  cartStore.initCart()
  await loadSession()
})

// ─── Load existing session ────────────────────────────────────────────────────
async function loadSession() {
  try {
    const res = await api.get(`/tour-planner/session/${sessionId.value}`)
    if (res.data.messages?.length) {
      messages.value = res.data.messages
      suggestedOperators.value = res.data.suggested_operators || []
      requirements.value = res.data.requirements || {}
      scrollBottom()
    }
  } catch (e) {
    // new session, ignore
  }
}

// ─── Streaming send ───────────────────────────────────────────────────────────
async function sendMessage() {
  const text = input.value.trim()
  if (!text || streaming.value) return

  messages.value.push({ role: 'user', text })
  input.value = ''
  autoResize()
  streaming.value = true
  streamingText.value = ''
  statusText.value = ''
  scrollBottom()

  try {
    const token = localStorage.getItem('token')
    const response = await fetch(
      `${import.meta.env.VITE_API_URL || 'http://localhost:8808'}/tour-planner/chat`,
      {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          Authorization: `Bearer ${token}`,
        },
        body: JSON.stringify({ session_id: sessionId.value, message: text }),
      }
    )

    if (!response.ok) {
      const err = await response.json()
      messages.value.push({ role: 'assistant', text: `⚠️ ${err.detail || 'Something went wrong'}` })
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const raw = decoder.decode(value)
      const lines = raw.split('\n')

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'text') {
            streamingText.value += event.text
            scrollBottom()
          } else if (event.type === 'status') {
            statusText.value = event.text
          } else if (event.type === 'operators') {
            suggestedOperators.value = event.operators
          } else if (event.type === 'error') {
            streamingText.value = ''
            messages.value.push({ role: 'assistant', text: `⚠️ ${event.text}` })
          } else if (event.type === 'done') {
            if (streamingText.value) {
              messages.value.push({ role: 'assistant', text: streamingText.value })
              streamingText.value = ''
            }
            statusText.value = ''
          }
        } catch {}
      }
    }
  } catch (err) {
    messages.value.push({ role: 'assistant', text: '⚠️ Connection error. Please try again.' })
  } finally {
    streaming.value = false
    streamingText.value = ''
    scrollBottom()
    await nextTick()
    inputEl.value?.focus()
  }
}

function sendStarter(prompt) {
  input.value = prompt
  sendMessage()
}

// ─── Cart confirm ─────────────────────────────────────────────────────────────
async function addToCart(op) {
  addingId.value = op.id
  try {
    await api.post('/tour-planner/confirm', {
      session_id: sessionId.value,
      operator_id: op.id,
    })

    const primaryArea = op.serving_areas?.[0] || requirements.value.locations?.[0] || 'Selected destination'
    const matchedAreaDetail = (op.serving_area_details || []).find((detail) => detail.area_name === primaryArea)
      || (op.serving_area_details || [])[0]
      || null
    const primaryState = matchedAreaDetail?.state || requirements.value.states?.[0] || 'N/A'
    const primaryCountry = matchedAreaDetail?.country || 'N/A'
    const plannerCartItem = {
      operator_id: op.id,
      operator_name: op.business_name,
      area_name: primaryArea,
      state: primaryState,
      country: primaryCountry,
      sub_location_name: `Planner shortlist: ${op.business_name}`,
      description: op.match_reason || op.description || 'Added from Tour Planner recommendations',
      coordinates: matchedAreaDetail?.coordinates || null,
      images: [],
    }
    cartStore.addToCart(plannerCartItem)

    addedIds.value = new Set([...addedIds.value, op.id])
    messages.value.push({
      role: 'assistant',
      text: `✅ **${op.business_name}** has been added to your cart. You can view and book it from the Cart page.`,
    })
    scrollBottom()
  } catch (err) {
    messages.value.push({
      role: 'assistant',
      text: `⚠️ Could not add to cart: ${err.response?.data?.detail || 'Unknown error'}`,
    })
  } finally {
    addingId.value = null
  }
}

// ─── New session ──────────────────────────────────────────────────────────────
function startNewSession() {
  const newId = uuidv4()
  sessionId.value = newId
  localStorage.setItem('plannerSessionId', newId)
  messages.value = []
  suggestedOperators.value = []
  requirements.value = {}
  streamingText.value = ''
  statusText.value = ''
  addedIds.value = new Set()
}

// ─── Helpers ──────────────────────────────────────────────────────────────────
function scrollBottom() {
  nextTick(() => {
    if (messagesEl.value) {
      messagesEl.value.scrollTop = messagesEl.value.scrollHeight
    }
  })
}

function autoResize() {
  if (!inputEl.value) return
  inputEl.value.style.height = 'auto'
  inputEl.value.style.height = Math.min(inputEl.value.scrollHeight, 160) + 'px'
}

function formatText(text) {
  if (!text) return ''
  return text
    .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
    .replace(/\n/g, '<br>')
}

function matchLabel(op) {
  if (op.match_type === 'exact') return 'Exact match'
  if (op.match_type === 'similar') return 'Similar match'
  return 'Suggested match'
}

function matchClass(op) {
  if (op.match_type === 'exact') return 'match-exact'
  if (op.match_type === 'similar') return 'match-similar'
  return 'match-fallback'
}
</script>

<style scoped>
.planner-shell {
  min-height: calc(100vh - 70px);
  padding: 0.8rem;
  background:
    radial-gradient(circle at top left, rgba(15, 118, 110, 0.12), transparent 30%),
    radial-gradient(circle at top right, rgba(14, 165, 233, 0.12), transparent 28%),
    linear-gradient(180deg, #f7fbfa 0%, #eef4f4 100%);
}

.planner-page {
  display: grid;
  grid-template-columns: 320px minmax(0, 1fr);
  gap: 0.75rem;
  height: calc(100vh - 94px);
  min-height: calc(100vh - 94px);
}

.glass-card {
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(16px);
}

.planner-sidebar {
  position: relative;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  padding: 0.95rem;
  overflow-y: auto;
  border-radius: 28px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(245, 250, 249, 0.9));
  box-shadow: 0 20px 60px rgba(15, 23, 42, 0.08);
  min-height: 0;
}

.sidebar-glow {
  position: absolute;
  inset: -80px auto auto -80px;
  width: 180px;
  height: 180px;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(15, 118, 110, 0.16), transparent 68%);
  pointer-events: none;
}

.sidebar-header h2 {
  font-family: 'Fraunces', serif;
  font-size: 1.35rem;
  line-height: 1.1;
  color: #0f172a;
  margin: 0.25rem 0 0.4rem;
}

.eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 0.4rem;
  width: fit-content;
  padding: 0.35rem 0.7rem;
  border-radius: 999px;
  font-size: 0.72rem;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  font-weight: 800;
  color: #0f766e;
  background: rgba(15, 118, 110, 0.1);
}

.sidebar-sub {
  color: #475569;
  font-size: 0.86rem;
  margin: 0;
  line-height: 1.45;
}

.req-card {
  border-radius: 24px;
  padding: 0.8rem;
}

.compact-title-row {
  margin-bottom: 0.2rem;
}

.card-title-row,
.operator-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.card-title-row h3,
.operator-header h3 {
  font-size: 0.95rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.05em;
}

.operator-header p {
  margin: 0.1rem 0 0;
  color: #64748b;
  font-size: 0.78rem;
}

.header-actions {
  display: flex;
  align-items: center;
  gap: 0.35rem;
}

.mini-toggle {
  border: 1px solid rgba(148, 163, 184, 0.25);
  background: rgba(255, 255, 255, 0.86);
  color: #334155;
  border-radius: 999px;
  padding: 0.25rem 0.55rem;
  font-size: 0.72rem;
  font-weight: 700;
  cursor: pointer;
}

.mini-toggle:hover {
  border-color: rgba(15, 118, 110, 0.38);
  color: #0f766e;
}

.mini-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0.35rem 0.6rem;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
  font-size: 0.75rem;
  font-weight: 800;
  letter-spacing: 0.04em;
}

.count-pill {
  min-width: 2rem;
}

.req-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 0.55rem;
}

.req-item {
  padding: 0.55rem 0.65rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.16);
  font-size: 0.78rem;
  color: #334155;
}

.req-label {
  font-weight: 700;
  color: #0f766e;
  font-size: 0.66rem;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  display: block;
  margin-bottom: 0.2rem;
}

.operators-panel {
  overflow-y: auto;
  max-height: 42vh;
  min-height: 0;
  padding-right: 0.2rem;
}

.operators-panel h3 {
  display: none;
}

.pick-hint {
  display: none;
}

.operator-card {
  border-radius: 22px;
  padding: 0.75rem;
  margin-bottom: 0.6rem;
  transition: transform 0.18s ease, border-color 0.2s ease, box-shadow 0.2s ease;
}

.operator-card.added {
  border-color: rgba(15, 118, 110, 0.45);
  background: linear-gradient(180deg, rgba(236, 253, 245, 0.95), rgba(255, 255, 255, 0.9));
}

.operator-card:hover {
  transform: translateY(-2px);
}

.op-topline {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
}

.op-avatar {
  width: 42px;
  height: 42px;
  border-radius: 14px;
  display: grid;
  place-items: center;
  background: linear-gradient(135deg, rgba(15, 118, 110, 0.16), rgba(14, 165, 233, 0.14));
  color: #0f766e;
  font-weight: 900;
  flex-shrink: 0;
}

.op-meta h4 {
  font-size: 0.92rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
  line-height: 1.25;
}

.op-match-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
  flex-wrap: wrap;
  margin-top: 0.35rem;
}

.match-pill {
  display: inline-flex;
  align-items: center;
  border-radius: 999px;
  padding: 0.2rem 0.55rem;
  font-size: 0.72rem;
  font-weight: 800;
  letter-spacing: 0.03em;
}

.match-exact {
  color: #047857;
  background: rgba(16, 185, 129, 0.14);
}

.match-similar {
  color: #0369a1;
  background: rgba(14, 165, 233, 0.14);
}

.match-fallback {
  color: #475569;
  background: rgba(148, 163, 184, 0.16);
}

.budget-pill {
  color: #7c3aed;
  background: rgba(124, 58, 237, 0.14);
}

.match-score {
  font-size: 0.72rem;
  color: #64748b;
  font-weight: 700;
}

.op-rating-row {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex-wrap: wrap;
  margin-top: 0.25rem;
}

.op-rating {
  font-size: 0.82rem;
  font-weight: 700;
  color: #b45309;
}

.op-reviews {
  font-size: 0.78rem;
  color: #94a3b8;
}

.op-description {
  margin: 0.55rem 0 0;
  color: #475569;
  font-size: 0.82rem;
  line-height: 1.45;
}

.op-match-reason {
  margin: 0.45rem 0 0;
  color: #0f766e;
  font-size: 0.75rem;
  line-height: 1.5;
  font-weight: 700;
}

.op-areas {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin: 0.55rem 0 0;
}

.area-tag {
  background: rgba(14, 165, 233, 0.08);
  color: #0369a1;
  border: 1px solid rgba(14, 165, 233, 0.12);
  border-radius: 999px;
  padding: 0.28rem 0.6rem;
  font-size: 0.76rem;
  font-weight: 700;
}

.op-footer {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 0.75rem;
  margin-top: 0.55rem;
  flex-wrap: wrap;
}

.op-actions {
  display: flex;
  align-items: center;
  gap: 0.6rem;
  flex-wrap: wrap;
}

.op-price {
  font-size: 0.8rem;
  color: #64748b;
  margin: 0;
}

.btn-add {
  background: linear-gradient(135deg, #0f766e, #115e59);
  color: white;
  border: none;
  border-radius: 999px;
  padding: 0.55rem 0.95rem;
  font-size: 0.82rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.15s ease, box-shadow 0.2s ease, opacity 0.2s ease;
  box-shadow: 0 10px 24px rgba(15, 118, 110, 0.2);
}

.btn-add:hover:not(:disabled) {
  transform: translateY(-1px);
}

.btn-add:disabled { opacity: 0.6; cursor: not-allowed; }

.added-label {
  font-size: 0.82rem;
  font-weight: 700;
  color: #0f766e;
}

.btn-view {
  color: #0369a1;
  font-size: 0.8rem;
  font-weight: 700;
  text-decoration: none;
}

.btn-view:hover { text-decoration: underline; }

.btn-new-session {
  margin-top: auto;
  border: 1.5px solid rgba(15, 118, 110, 0.18);
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.9), rgba(240, 253, 250, 0.9));
  color: #0f766e;
  border-radius: 14px;
  padding: 0.7rem 0.8rem;
  font-weight: 800;
  cursor: pointer;
  transition: all 0.2s;
  font-size: 0.88rem;
}

.btn-new-session:hover {
  transform: translateY(-1px);
  box-shadow: 0 12px 24px rgba(15, 118, 110, 0.12);
}

.chat-area {
  display: flex;
  flex-direction: column;
  overflow: hidden;
  gap: 0.6rem;
  min-height: 0;
}

.planner-toolbar {
  border-radius: 18px;
  padding: 0.7rem 0.9rem;
  display: flex;
  justify-content: space-between;
  gap: 0.8rem;
  align-items: center;
}

.toolbar-main strong {
  display: block;
  font-size: 0.98rem;
  color: #0f172a;
}

.toolbar-sub {
  display: block;
  margin-top: 0.1rem;
  color: #64748b;
  font-size: 0.76rem;
}

.toolbar-stats {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 0.45rem;
  min-width: 255px;
}

.toolbar-stats div {
  border-radius: 10px;
  padding: 0.45rem 0.55rem;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.toolbar-stats strong {
  display: block;
  font-size: 0.84rem;
  color: #0f172a;
}

.toolbar-stats span {
  display: block;
  font-size: 0.68rem;
  color: #64748b;
  margin-top: 0.1rem;
}

.messages {
  flex: 1;
  overflow-y: auto;
  min-height: 0;
  padding: 0.85rem;
  display: flex;
  flex-direction: column;
  gap: 1.2rem;
  scroll-behavior: smooth;
  border-radius: 28px;
  overscroll-behavior: contain;
  scrollbar-gutter: stable;
}

.welcome-state {
  margin: auto;
  text-align: center;
  max-width: 620px;
  padding: 2rem 1rem;
}

.welcome-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.welcome-state h2 {
  font-family: 'Fraunces', serif;
  font-size: clamp(1.7rem, 2vw, 2.4rem);
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.75rem;
}

.welcome-state p {
  color: #475569;
  line-height: 1.65;
  margin: 0 0 1.5rem;
  font-size: 1rem;
}

.welcome-badge {
  display: inline-flex;
  margin-bottom: 1rem;
  padding: 0.4rem 0.8rem;
  border-radius: 999px;
  background: rgba(15, 118, 110, 0.1);
  color: #0f766e;
  font-size: 0.78rem;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.starter-chips {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
  justify-content: center;
}

.chip {
  background: rgba(255, 255, 255, 0.8);
  border: 1.5px solid rgba(148, 163, 184, 0.22);
  border-radius: 999px;
  padding: 0.6rem 1rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #334155;
  cursor: pointer;
  transition: all 0.2s;
}

.chip:hover {
  border-color: #0f766e;
  color: #0f766e;
  background: #f0fdfb;
}

/* Messages */
.message {
  display: flex;
}

.message.user {
  justify-content: flex-end;
}

.message.assistant,
.message.streaming {
  justify-content: flex-start;
}

.bubble {
  max-width: 68%;
  display: flex;
  flex-direction: column;
  gap: 0.3rem;
}

.message.user .bubble {
  background: linear-gradient(135deg, #0f766e, #115e59);
  color: white;
  border-radius: 20px 20px 6px 20px;
  padding: 0.85rem 1.1rem;
  box-shadow: 0 14px 30px rgba(15, 118, 110, 0.18);
}

.message.assistant .bubble,
.message.streaming .bubble {
  background: rgba(255, 255, 255, 0.86);
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 20px 20px 20px 6px;
  padding: 0.85rem 1.1rem;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.05);
}

.msg-role {
  font-size: 0.72rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.06em;
  opacity: 0.6;
}

.msg-text {
  margin: 0;
  font-size: 0.95rem;
  line-height: 1.65;
  white-space: pre-wrap;
  word-break: break-word;
}

.cursor {
  animation: blink 0.9s infinite;
  color: #0f766e;
  font-size: 1rem;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

.status-line {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  color: #475569;
  font-size: 0.88rem;
  font-weight: 600;
  padding-left: 0.25rem;
}

.status-dot {
  width: 8px;
  height: 8px;
  background: #0f766e;
  border-radius: 50%;
  animation: pulse 1.2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; transform: scale(1); }
  50% { opacity: 0.5; transform: scale(1.35); }
}

/* Input */
.chat-input-area {
  display: flex;
  align-items: flex-end;
  gap: 0.9rem;
  padding: 0.72rem 0.85rem;
  border-radius: 18px;
  flex-shrink: 0;
}

.input-wrap {
  flex: 1;
}

.input-hint {
  margin: 0.45rem 0 0;
  color: #64748b;
  font-size: 0.78rem;
}

.chat-input-area textarea {
  flex: 1;
  resize: none;
  width: 100%;
  border: 1.5px solid rgba(148, 163, 184, 0.22);
  border-radius: 14px;
  padding: 0.7rem 0.85rem;
  font-size: 0.95rem;
  font-family: inherit;
  line-height: 1.5;
  outline: none;
  background: rgba(255, 255, 255, 0.72);
  color: #0f172a;
  transition: border-color 0.2s;
  max-height: 130px;
  overflow-y: auto;
}

.chat-input-area textarea:focus {
  border-color: #0f766e;
  box-shadow: 0 0 0 3px rgba(15, 118, 110, 0.12);
}

.btn-send {
  background: linear-gradient(135deg, #0f766e, #115e59);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 0.75rem 0.95rem;
  font-size: 0.88rem;
  font-weight: 700;
  cursor: pointer;
  transition: transform 0.15s, box-shadow 0.2s, opacity 0.2s;
  min-width: 74px;
  align-self: flex-end;
  box-shadow: 0 16px 30px rgba(15, 118, 110, 0.22);
}

.btn-send:hover:not(:disabled) {
  transform: translateY(-1px);
}

.btn-send:disabled {
  opacity: 0.55;
  cursor: not-allowed;
}

/* Sending animation */
.sending-dots {
  display: flex;
  gap: 4px;
  align-items: center;
  justify-content: center;
}

.sending-dots span {
  width: 6px;
  height: 6px;
  background: white;
  border-radius: 50%;
  animation: dotBounce 1.1s infinite;
}

.sending-dots span:nth-child(2) { animation-delay: 0.15s; }
.sending-dots span:nth-child(3) { animation-delay: 0.3s; }

@keyframes dotBounce {
  0%, 80%, 100% { transform: scale(0.7); opacity: 0.5; }
  40% { transform: scale(1); opacity: 1; }
}

/* Responsive */
@media (max-width: 900px) {
  .planner-shell {
    padding: 0.45rem;
  }

  .planner-page {
    grid-template-columns: 1fr;
    grid-template-rows: auto 1fr;
    height: calc(100vh - 88px);
    min-height: calc(100vh - 88px);
  }

  .planner-sidebar {
    border-radius: 24px;
    max-height: 34vh;
  }

  .chat-area {
    min-height: 0;
  }

  .planner-toolbar {
    flex-direction: column;
    align-items: start;
  }

  .toolbar-stats {
    width: 100%;
    min-width: 0;
  }

  .messages {
    min-height: 220px;
    padding: 0.8rem;
  }

  .chat-input-area {
    padding: 1rem;
    flex-direction: column;
    align-items: stretch;
  }

  .bubble {
    max-width: 86%;
  }
}
</style>
