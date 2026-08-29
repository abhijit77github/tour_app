<template>
  <div class="planner-shell" role="main">
    <!-- Sprint 6: Skip Links for Accessibility -->
    <a href="#main-content" class="skip-link">Skip to main content</a>
    <a href="#chat-input" class="skip-link">Skip to chat input</a>
    
    <div 
      class="planner-page-new"
      @touchstart="handleTouchStart"
      @touchmove="handleTouchMove"
      @touchend="handleTouchEnd"
    >
      
      <!-- Sprint 4: Pull-to-refresh indicator -->
      <div 
        v-if="pullDistance > 0" 
        class="pull-refresh-indicator"
        :style="{ height: pullDistance + 'px', opacity: pullDistance / 80 }"
        role="status"
        aria-live="polite"
        aria-label="Pull to refresh indicator"
      >
        <div class="refresh-icon" :class="{ spinning: isRefreshing }">
          {{ isRefreshing ? '⟳' : '↓' }}
        </div>
        <span v-if="!isRefreshing">{{ pullDistance > 60 ? 'Release to refresh' : 'Pull to refresh' }}</span>
        <span v-else>Refreshing...</span>
      </div>
      
      <!-- New Header -->
      <header class="planner-header glass-card" role="banner">
        <div class="header-left">
          <h1 class="planner-title">
            <span class="title-icon" aria-hidden="true">🧭</span>
            Tour Planner
          </h1>
          <p class="planner-subtitle">AI-powered trip planning</p>
        </div>
        <div class="header-right">
          <QuotaBadge 
            :quota="plannerQuota" 
            :loading="plannerQuotaLoading" 
            :error="plannerQuotaError" 
          />
          <router-link 
            to="/cart" 
            class="cart-button"
            aria-label="View cart"
            :aria-describedby="cartStore.itemCount > 0 ? 'cart-count' : null"
          >
            <span aria-hidden="true">🛒</span>
            <span v-if="cartStore.itemCount > 0" id="cart-count">
              ({{ cartStore.itemCount }} {{ cartStore.itemCount === 1 ? 'item' : 'items' }})
            </span>
          </router-link>
        </div>
      </header>

      <!-- Tab Navigation -->
      <TabNavigation
        :activeTab="activeTab"
        :tabs="tabs"
        @update:activeTab="activeTab = $event"
      />

      <div v-show="activeTab === 'chat'" class="planner-page">

      <main class="chat-area">
        <section class="planner-toolbar glass-card">
          <div class="toolbar-main">
            <strong>Tour Planner</strong>
            <span class="toolbar-sub">Live assistant with ranked operator matching</span>
            <div class="service-switch">
              <button
                type="button"
                class="service-btn"
                :class="{ active: serviceMode === 'tour' }"
                @click="serviceMode = 'tour'"
              >Tours</button>
              <button
                type="button"
                class="service-btn"
                :class="{ active: serviceMode === 'car' }"
                @click="serviceMode = 'car'"
              >Cars</button>
              <button
                type="button"
                class="service-btn"
                :class="{ active: serviceMode === 'both' }"
                @click="serviceMode = 'both'"
              >Both</button>
            </div>
            <button
              type="button"
              class="btn-car-only"
              @click="quickCarMode"
              title="Quick filter for car services only"
            >
              🚗 Car Services
            </button>
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
            <div>
              <strong>{{ plannerQuota?.daily_remaining ?? '—' }}</strong>
              <span>Planner requests left today</span>
            </div>
          </div>
        </section>

        <!-- Sprint 6: Screen Reader Announcements -->
        <div 
          class="sr-only" 
          role="status" 
          aria-live="polite" 
          aria-atomic="true"
        >
          {{ screenReaderAnnouncement }}
        </div>

        <div 
          id="main-content"
          class="messages glass-card" 
          ref="messagesEl"
          role="log"
          aria-label="Chat conversation"
          aria-live="polite"
          aria-relevant="additions"
        >
          <div v-if="!messages.length" class="welcome-state">
            <div class="welcome-badge" role="status">Tell me the destination, budget, and vibe</div>
            <div class="welcome-icon" aria-hidden="true">🧭</div>
            <h2>Start with a plain-English trip request</h2>
            <p>
              For example: “I want Coorg for 4 days with my family, mid-range budget, and a relaxed itinerary.”
            </p>
            <div class="starter-chips" role="group" aria-label="Quick start prompts">
              <button
                v-for="prompt in starterPrompts"
                :key="prompt"
                class="chip"
                @click="sendStarter(prompt)"
                :aria-label="`Quick start: ${prompt}`"
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
              
              <!-- Inline Operator Cards (Sprint 2) -->
              <div v-if="getInlineOperators(msg, idx).length" class="inline-operators">
                <div class="inline-operators-header">
                  <span class="operators-badge">{{ getInlineOperators(msg, idx).length }} matches found</span>
                </div>
                <div class="inline-operator-grid">
                  <div 
                    v-for="op in getInlineOperators(msg, idx).slice(0, 3)" 
                    :key="op.id" 
                    class="inline-op-card"
                    :class="{ added: addedIds.has(op.id) }"
                  >
                    <div class="inline-op-header">
                      <div class="inline-op-avatar">{{ op.business_name?.charAt(0)?.toUpperCase() }}</div>
                      <div class="inline-op-info">
                        <h5>{{ op.business_name }}</h5>
                        <div class="inline-op-meta">
                          <span class="op-rating">★ {{ Number(op.average_rating || 0).toFixed(1) }}</span>
                          <span class="op-score">{{ Number(op.score || 0).toFixed(0) }}% match</span>
                        </div>
                      </div>
                    </div>
                    <p v-if="op.match_reason" class="inline-op-reason">{{ op.match_reason }}</p>
                    <div class="inline-op-tags">
                      <span v-if="op.budget_fit" class="op-tag budget">Budget fit</span>
                      <span class="op-tag service">{{ op.recommended_service === 'car' ? '🚗 Car' : '🗺️ Tour' }}</span>
                    </div>
                    <div class="inline-op-actions">
                      <button 
                        v-if="!addedIds.has(op.id)"
                        class="btn-inline-add" 
                        :disabled="addingId === op.id"
                        @click="addToCart(op)"
                        :aria-label="`Add ${op.name} to cart`"
                        :aria-busy="addingId === op.id"
                      >
                        {{ addingId === op.id ? 'Adding...' : 'Add to Cart' }}
                      </button>
                      <span v-else class="inline-added" role="status" aria-live="polite">
                        <span aria-hidden="true">✓</span> Added
                      </span>
                      <button 
                        class="btn-inline-view" 
                        @click="activeTab = 'matches'"
                        aria-label="View all matches"
                      >
                        View All
                      </button>
                    </div>
                  </div>
                </div>
                <p v-if="getInlineOperators(msg, idx).length > 3" class="inline-operators-more">
                  + {{ getInlineOperators(msg, idx).length - 3 }} more in <button @click="activeTab = 'matches'" class="link-button">Matches tab</button>
                </p>
              </div>

              <!-- Quick Reply Buttons (Sprint 2) -->
              <div v-if="msg.quickReplies && msg.quickReplies.length" class="quick-replies" role="group" aria-label="Quick reply options">
                <button 
                  v-for="(reply, ridx) in msg.quickReplies" 
                  :key="ridx"
                  class="quick-reply-btn"
                  @click="sendQuickReply(reply)"
                  :aria-label="`Quick reply: ${reply.text}`"
                >
                  <span aria-hidden="true">{{ reply.icon }}</span> {{ reply.text }}
                </button>
              </div>
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
            <span class="status-text">{{ statusText }}</span>
            <div class="status-progress">
              <div class="progress-bar" :class="statusProgressClass"></div>
            </div>
          </div>

          <!-- Enhanced typing indicator (Sprint 2) -->
          <div v-if="streaming && !streamingText && !statusText" class="typing-indicator">
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-dot"></span>
            <span class="typing-text">Tour Planner is thinking...</span>
          </div>
        </div>

        <form 
          class="chat-input-area glass-card" 
          @submit.prevent="sendMessage"
          role="form"
          aria-label="Chat message input"
        >
          <div class="input-wrap">
            <label for="chat-input" class="sr-only">Enter your trip description</label>
            <textarea
              id="chat-input"
              ref="inputEl"
              v-model="input"
              :disabled="streaming"
              placeholder="Describe your trip..."
              rows="1"
              @keydown.enter.exact.prevent="sendMessage"
              @input="autoResize"
              aria-label="Trip description input"
              aria-describedby="input-hint"
              :aria-disabled="streaming"
            ></textarea>
            <p id="input-hint" class="input-hint">Include destination, dates, travelers, budget, and preferences.</p>
          </div>
          <button 
            type="submit" 
            :disabled="streaming || !input.trim()" 
            class="btn-send"
            aria-label="Send message"
            :aria-busy="streaming"
          >
            <span v-if="!streaming">Send</span>
            <span v-else class="sending-dots" aria-label="Sending message">
              <span></span><span></span><span></span>
            </span>
          </button>
        </form>
      </main>
    </div>
      
      <!-- Placeholder tabs -->
      <div v-show="activeTab === 'matches'" class="tab-panel matches-panel" role="tabpanel" aria-labelledby="matches-tab">
        <div class="matches-container">
          
          <!-- Filters & Sort Bar -->
          <div class="matches-controls glass-card" role="region" aria-label="Filter and sort controls">
            <div class="controls-row">
              
              <!-- Service Type Filter -->
              <div class="control-group">
                <label class="control-label" id="service-filter-label">Service</label>
                <div class="filter-buttons" role="group" aria-labelledby="service-filter-label">
                  <button 
                    class="filter-btn" 
                    :class="{ active: matchesFilter.service === 'all' }"
                    @click="matchesFilter.service = 'all'"
                    aria-label="Show all services"
                    :aria-pressed="matchesFilter.service === 'all'"
                  >
                    All
                  </button>
                  <button 
                    class="filter-btn" 
                    :class="{ active: matchesFilter.service === 'tour' }"
                    @click="matchesFilter.service = 'tour'"
                    aria-label="Show tours only"
                    :aria-pressed="matchesFilter.service === 'tour'"
                  >
                    <span aria-hidden="true">🗺️</span> Tours
                  </button>
                  <button 
                    class="filter-btn" 
                    :class="{ active: matchesFilter.service === 'car' }"
                    @click="matchesFilter.service = 'car'"
                    aria-label="Show car rentals only"
                    :aria-pressed="matchesFilter.service === 'car'"
                  >
                    <span aria-hidden="true">🚗</span> Cars
                  </button>
                </div>
              </div>

              <!-- Rating Filter -->
              <div class="control-group">
                <label for="rating-filter" class="control-label">Min Rating</label>
                <select 
                  id="rating-filter"
                  v-model="matchesFilter.rating" 
                  class="filter-select"
                  aria-label="Filter by minimum rating"
                >
                  <option value="0">Any</option>
                  <option value="3">3+ ⭐</option>
                  <option value="3.5">3.5+ ⭐</option>
                  <option value="4">4+ ⭐</option>
                  <option value="4.5">4.5+ ⭐</option>
                </select>
              </div>

              <!-- Sort Control -->
              <div class="control-group">
                <label for="sort-select" class="control-label">Sort by</label>
                <select 
                  id="sort-select"
                  v-model="matchesSort" 
                  class="filter-select"
                  aria-label="Sort results by"
                >
                  <option value="score">Best Match</option>
                  <option value="rating">Highest Rated</option>
                  <option value="price-low">Price: Low to High</option>
                  <option value="price-high">Price: High to Low</option>
                </select>
              </div>

              <!-- Result Count -->
              <div class="control-group result-count">
                <span class="count-label" role="status" aria-live="polite">{{ filteredOperators.length }} results</span>
              </div>

            </div>
          </div>

          <!-- Operators Grid -->
          <div v-if="filteredOperators.length > 0" class="matches-grid">
            <div 
              v-for="op in filteredOperators" 
              :key="op.id" 
              class="match-card glass-card"
              :class="{ 'match-added': addedIds.has(op.id) }"
            >
              
              <!-- Card Header -->
              <div class="match-header">
                <div class="match-avatar">{{ op.business_name?.charAt(0)?.toUpperCase() }}</div>
                <div class="match-info">
                  <h3 class="match-name">{{ op.business_name }}</h3>
                  <div class="match-meta">
                    <span class="match-rating">⭐ {{ Number(op.average_rating || 0).toFixed(1) }}</span>
                    <span v-if="op.score" class="match-score">{{ Number(op.score).toFixed(0) }}% match</span>
                  </div>
                </div>
                <div v-if="addedIds.has(op.id)" class="match-badge added-badge">✓ Added</div>
              </div>

              <!-- Match Reason -->
              <p v-if="op.match_reason" class="match-reason">{{ op.match_reason }}</p>

              <!-- Service Info -->
              <div class="match-service">
                <span class="service-badge" :class="op.recommended_service === 'car' ? 'badge-car' : 'badge-tour'">
                  {{ op.recommended_service === 'car' ? '🚗 Car Service' : '🗺️ Tour Packages' }}
                </span>
                <span v-if="op.budget_fit" class="service-badge badge-budget">💰 Budget fit</span>
              </div>

              <!-- Serving Areas -->
              <div v-if="op.serving_areas?.length" class="match-areas">
                <span class="areas-label">Serves:</span>
                <span 
                  v-for="area in op.serving_areas.slice(0, 4)" 
                  :key="area" 
                  class="area-tag"
                >
                  {{ area }}
                </span>
                <span v-if="op.serving_areas.length > 4" class="area-more">
                  +{{ op.serving_areas.length - 4 }} more
                </span>
              </div>

              <!-- Description -->
              <p v-if="op.description" class="match-description">{{ op.description }}</p>

              <!-- Price Range -->
              <div v-if="op.price_range" class="match-price">
                <span class="price-label">Pricing:</span>
                <span class="price-value">{{ op.price_range }}</span>
              </div>

              <!-- Actions -->
              <div class="match-actions">
                <button 
                  v-if="!addedIds.has(op.id)"
                  class="btn-match-add" 
                  :disabled="addingId === op.id"
                  @click="addToCart(op)"
                  :aria-label="`Add ${op.name} to cart`"
                  :aria-busy="addingId === op.id"
                >
                  {{ addingId === op.id ? 'Adding...' : 'Add to Cart' }}
                </button>
                <span v-else class="match-added-label" role="status" aria-live="polite">
                  <span aria-hidden="true">✓</span> Added to cart
                </span>
                <router-link 
                  :to="`/operator/${op.user_id}`" 
                  class="btn-match-view" 
                  target="_blank"
                >
                  View Profile
                </router-link>
              </div>

            </div>
          </div>

          <!-- Empty State -->
          <div v-else class="matches-empty">
            <div class="empty-icon">🔍</div>
            <h3>No operators matched yet</h3>
            <p v-if="suggestedOperators.length === 0">
              Start chatting to find tour operators and car services that match your needs.
            </p>
            <p v-else>
              No operators match your current filters. Try adjusting the filters above.
            </p>
            <button 
              v-if="suggestedOperators.length === 0"
              class="btn-empty-action" 
              @click="activeTab = 'chat'"
            >
              Go to Chat
            </button>
            <button 
              v-else
              class="btn-empty-action" 
              @click="resetFilters"
            >
              Reset Filters
            </button>
          </div>

        </div>
      </div>
      
      <div v-show="activeTab === 'itinerary'" class="tab-panel" role="tabpanel" aria-labelledby="itinerary-tab">
        <div class="matches-container">
          <div class="itinerary-card glass-card">
            <div class="card-title-row compact-title-row">
              <h3>Itinerary ideas</h3>
              <div class="header-actions">
                <button class="mini-toggle" type="button" @click="loadItineraryIdeas" :disabled="itineraryLoading">
                  {{ itineraryLoading ? 'Loading...' : 'Refresh' }}
                </button>
                <router-link
                  class="mini-link"
                  :to="{ path: '/itineraries', query: { area_name: requirements.locations?.[0] || '', state: requirements.states?.[0] || '', duration_days: requirements.duration_days || '' } }"
                >
                  Open builder
                </router-link>
              </div>
            </div>

            <div v-if="!hasRequirements" class="itinerary-empty">
              Add destination and duration in Chat first to generate itinerary ideas.
            </div>
            <div v-else-if="itineraryError" class="itinerary-empty">{{ itineraryError }}</div>
            <div v-else-if="itineraryLoading && !itineraryIdeas.length" class="itinerary-empty">
              Finding grounded itinerary options...
            </div>
            <div v-else-if="!itineraryIdeas.length" class="itinerary-empty">
              No itinerary ideas yet. Try refining your request in Chat.
            </div>
            <div v-else class="itinerary-list">
              <article v-for="item in itineraryIdeas" :key="item._id" class="itinerary-item">
                <div class="itinerary-top">
                  <div>
                    <h4>{{ item.title }}</h4>
                    <p>{{ item.summary || 'Operator-curated template' }}</p>
                  </div>
                  <span class="mini-pill count-pill">{{ item.duration_days }}d</span>
                </div>
                <div class="itinerary-meta">
                  <span>{{ item.primary_location?.area_name }}</span>
                  <span v-if="item.operator_name">{{ item.operator_name }}</span>
                  <span>Score {{ Number(item.score || 0).toFixed(1) }}</span>
                </div>
              </article>
            </div>
          </div>
        </div>
      </div>

      <div v-show="activeTab === 'requirements'" class="tab-panel" role="tabpanel" aria-labelledby="requirements-tab">
        <div class="matches-container">
          <div class="req-card glass-card">
            <div class="card-title-row compact-title-row">
              <h3>Trip requirements</h3>
              <span class="mini-pill">{{ hasRequirements ? 'Captured' : 'Awaiting details' }}</span>
            </div>

            <div v-if="hasRequirements" class="req-actions" role="group" aria-label="Refine requirements in chat">
              <button class="mini-toggle" type="button" @click="editRequirementInChat('dates')">Edit Dates</button>
              <button class="mini-toggle" type="button" @click="editRequirementInChat('budget')">Edit Budget</button>
              <button class="mini-toggle" type="button" @click="editRequirementInChat('refine')">Refine Search</button>
            </div>

            <div v-if="!hasRequirements" class="itinerary-empty">
              Share destination, dates, traveler count, budget, and preferences in Chat to populate this tab.
            </div>

            <div v-else class="req-grid">
              <div class="req-item" v-if="requirements.locations?.length">
                <span class="req-label">Destinations</span>
                <span>{{ requirements.locations.join(', ') }}</span>
              </div>
              <div class="req-item" v-if="requirements.states?.length">
                <span class="req-label">States</span>
                <span>{{ requirements.states.join(', ') }}</span>
              </div>
              <div class="req-item" v-if="requirements.travel_dates">
                <span class="req-label">Travel window</span>
                <span>{{ requirements.travel_dates }}</span>
              </div>
              <div class="req-item" v-if="requirements.group_size">
                <span class="req-label">Group size</span>
                <span>{{ requirements.group_size }} people</span>
              </div>
              <div class="req-item" v-if="requirements.duration_days">
                <span class="req-label">Duration</span>
                <span>{{ requirements.duration_days }} days</span>
              </div>
              <div class="req-item" v-if="requirements.budget_usd">
                <span class="req-label">Budget</span>
                <span>${{ requirements.budget_usd }}</span>
              </div>
              <div class="req-item" v-if="requirements.service_mode">
                <span class="req-label">Service mode</span>
                <span>{{ requirements.service_mode }}</span>
              </div>
              <div class="req-item" v-if="requirements.preferences?.length">
                <span class="req-label">Preferences</span>
                <span>{{ requirements.preferences.join(', ') }}</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      <!-- Sprint 4: Floating Action Buttons (Mobile) -->
      <div class="fab-container">
        <!-- Cart FAB -->
        <router-link 
          to="/cart" 
          class="fab fab-cart"
          :class="{ 'has-items': cartStore.itemCount > 0 }"
          @click="hapticFeedback('medium')"
          role="button"
          aria-label="View cart"
          :aria-describedby="cartStore.itemCount > 0 ? 'fab-cart-count' : null"
        >
          <span aria-hidden="true">🛒</span>
          <span v-if="cartStore.itemCount > 0" id="fab-cart-count" class="fab-badge">{{ cartStore.itemCount }}</span>
        </router-link>
        
        <!-- Scroll to bottom FAB (only when scrolled down) -->
        <button 
          v-if="showFAB && activeTab === 'chat'" 
          class="fab fab-scroll"
          @click="scrollToBottom"
          aria-label="Scroll to bottom"
        >
          <span aria-hidden="true">↓</span>
        </button>
        
        <!-- New session FAB -->
        <button 
          class="fab fab-new-session"
          @click="startNewSessionFAB"
          aria-label="Start new session"
        >
          <span aria-hidden="true">✨</span>
        </button>
      </div>

    </div><!-- end planner-page-new -->
  </div><!-- end planner-shell -->
</template>

<script setup>
import { ref, computed, nextTick, onMounted } from 'vue'
import { v4 as uuidv4 } from 'uuid'
import TabNavigation from '../components/TabNavigation.vue'
import QuotaBadge from '../components/QuotaBadge.vue'
import LoadingSkeleton from '../components/LoadingSkeleton.vue'
import api from '../services/api'
import { useCartStore } from '../stores/cart'
import { useToast } from '../composables/useToast'

// Sprint 5: Toast system
const toast = useToast()

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
const serviceMode = ref('tour')
const itineraryIdeas = ref([])
const itineraryLoading = ref(false)
const itineraryError = ref('')
const plannerQuota = ref(null)
const plannerQuotaLoading = ref(false)
const plannerQuotaError = ref('')
const messagesEl = ref(null)
const inputEl = ref(null)
const cartStore = useCartStore()

// New tab state for refactored layout
const activeTab = ref('chat')

// Sprint 2: Status progress tracking
const statusProgressClass = ref('progress-searching')

// Sprint 3: Matches tab filtering & sorting
const matchesFilter = ref({
  service: 'all',  // 'all', 'tour', 'car'
  rating: 0        // minimum rating filter
})
const matchesSort = ref('score')  // 'score', 'rating', 'price-low', 'price-high'

// Sprint 4: Mobile gestures & interactions
const touchStartX = ref(0)
const touchStartY = ref(0)
const touchEndX = ref(0)
const touchEndY = ref(0)
const showFAB = ref(false)
const pullStartY = ref(0)
const pullDistance = ref(0)
const isRefreshing = ref(false)

// Sprint 6: Accessibility
const screenReaderAnnouncement = ref('')

const tabs = computed(() => [
  {
    id: 'chat',
    label: 'Chat',
    icon: '💬',
    count: 0,
    hasCheck: false
  },
  {
    id: 'matches',
    label: 'Matches',
    icon: '📍',
    count: suggestedOperators.value.length,
    hasCheck: false
  },
  {
    id: 'itinerary',
    label: 'Itinerary',
    icon: '📋',
    count: itineraryIdeas.value.length,
    hasCheck: false
  },
  {
    id: 'requirements',
    label: 'Trip',
    icon: '⚙️',
    count: 0,
    hasCheck: hasRequirements.value
  }
])

const hasRequirements = computed(() =>
  requirements.value.locations?.length ||
  requirements.value.travel_dates ||
  requirements.value.group_size
)

// Sprint 3: Filtered and sorted operators
const filteredOperators = computed(() => {
  let filtered = [...suggestedOperators.value]

  // Filter by service type
  if (matchesFilter.value.service !== 'all') {
    filtered = filtered.filter(op => op.recommended_service === matchesFilter.value.service)
  }

  // Filter by minimum rating
  if (matchesFilter.value.rating > 0) {
    filtered = filtered.filter(op => Number(op.average_rating || 0) >= matchesFilter.value.rating)
  }

  // Sort operators
  filtered.sort((a, b) => {
    switch (matchesSort.value) {
      case 'score':
        return Number(b.score || 0) - Number(a.score || 0)
      case 'rating':
        return Number(b.average_rating || 0) - Number(a.average_rating || 0)
      case 'price-low':
        return getPriceValue(a.price_range) - getPriceValue(b.price_range)
      case 'price-high':
        return getPriceValue(b.price_range) - getPriceValue(a.price_range)
      default:
        return 0
    }
  })

  return filtered
})

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
  await loadPlannerQuota()
  await loadSession()
  
  // Sprint 4: Attach mobile gesture listeners
  if (messagesEl.value) {
    messagesEl.value.addEventListener('scroll', handleScroll)
  }
})

async function loadPlannerQuota() {
  plannerQuotaLoading.value = true
  plannerQuotaError.value = ''
  try {
    const res = await api.get('/tour-planner/quota')
    plannerQuota.value = res.data?.quota || null
  } catch (error) {
    plannerQuotaError.value = error.response?.data?.detail || 'Unable to load planner quota.'
  } finally {
    plannerQuotaLoading.value = false
  }
}

// ─── Load existing session ────────────────────────────────────────────────────
async function loadSession(options = {}) {
  const { preserveEnhancements = false } = options
  try {
    const res = await api.get(`/tour-planner/session/${sessionId.value}`)
    const serverMessages = res.data.messages || []

    if (preserveEnhancements && messages.value.length) {
      // Keep local UI enrichments (inline operators/quick replies) that backend messages may not persist.
      const localEnhancements = new Map()
      for (const msg of messages.value) {
        if (!msg || msg.role !== 'assistant') continue
        if (!msg.operators && !msg.quickReplies) continue
        localEnhancements.set(`${msg.role}::${msg.text}`, msg)
      }

      messages.value = serverMessages.map((msg) => {
        const enhanced = localEnhancements.get(`${msg.role}::${msg.text}`)
        if (!enhanced) return msg
        return {
          ...msg,
          operators: enhanced.operators || msg.operators || null,
          quickReplies: enhanced.quickReplies || msg.quickReplies || null,
        }
      })
    } else {
      messages.value = serverMessages
    }

    suggestedOperators.value = res.data.suggested_operators || []
    requirements.value = res.data.requirements || {}
    if (Object.keys(requirements.value || {}).length) {
      await loadItineraryIdeas()
    } else {
      itineraryIdeas.value = []
      itineraryError.value = ''
    }
    scrollBottom()
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
        body: JSON.stringify({
          session_id: sessionId.value,
          message: text,
          service_mode: serviceMode.value,
        }),
      }
    )

    if (!response.ok) {
      const err = await response.json()
      if (response.status === 429 && err?.detail?.quota) {
        plannerQuota.value = err.detail.quota
        messages.value.push({ role: 'assistant', text: `⚠️ ${err.detail.message || 'Planner request limit reached.'}` })
      } else {
        messages.value.push({ role: 'assistant', text: `⚠️ ${typeof err.detail === 'string' ? err.detail : 'Something went wrong'}` })
      }
      return
    }

    const reader = response.body.getReader()
    const decoder = new TextDecoder()
    let sseBuffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      const raw = decoder.decode(value, { stream: true })
      sseBuffer += raw
      const lines = sseBuffer.split('\n')
      sseBuffer = lines.pop() || ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        try {
          const event = JSON.parse(line.slice(6))
          if (event.type === 'text') {
            streamingText.value += event.text
            scrollBottom()
          } else if (event.type === 'status') {
            statusText.value = event.text
            // Update progress class based on status (Sprint 2)
            if (event.text.includes('Searching') || event.text.includes('Finding')) {
              statusProgressClass.value = 'progress-searching'
            } else if (event.text.includes('Analyzing') || event.text.includes('Matching')) {
              statusProgressClass.value = 'progress-analyzing'
            } else if (event.text.includes('Ranking') || event.text.includes('Sorting')) {
              statusProgressClass.value = 'progress-ranking'
            }
          } else if (event.type === 'operators') {
            suggestedOperators.value = event.operators
          } else if (event.type === 'itineraries') {
            itineraryIdeas.value = event.itineraries || []
            itineraryError.value = ''
          } else if (event.type === 'error') {
            streamingText.value = ''
            messages.value.push({ role: 'assistant', text: `⚠️ ${event.text}` })
          } else if (event.type === 'done') {
            if (streamingText.value) {
              // Create enhanced message with operators and quick replies (Sprint 2)
              const enhancedMessage = {
                role: 'assistant',
                text: streamingText.value,
                operators: suggestedOperators.value.length > 0 ? [...suggestedOperators.value] : null,
                quickReplies: generateQuickReplies(streamingText.value, suggestedOperators.value)
              }
              messages.value.push(enhancedMessage)
              streamingText.value = ''
            }
            statusText.value = ''
          }
        } catch {}
      }
    }

    // Flush any remaining buffered SSE data line after stream ends.
    const tailLine = sseBuffer.trim()
    if (tailLine.startsWith('data: ')) {
      try {
        const event = JSON.parse(tailLine.slice(6))
        if (event.type === 'text') {
          streamingText.value += event.text
        } else if (event.type === 'status') {
          statusText.value = event.text
        } else if (event.type === 'operators') {
          suggestedOperators.value = event.operators || []
        } else if (event.type === 'itineraries') {
          itineraryIdeas.value = event.itineraries || []
          itineraryError.value = ''
        } else if (event.type === 'error') {
          streamingText.value = ''
          messages.value.push({ role: 'assistant', text: `⚠️ ${event.text}` })
        } else if (event.type === 'done') {
          if (streamingText.value) {
            const enhancedMessage = {
              role: 'assistant',
              text: streamingText.value,
              operators: suggestedOperators.value.length > 0 ? [...suggestedOperators.value] : null,
              quickReplies: generateQuickReplies(streamingText.value, suggestedOperators.value)
            }
            messages.value.push(enhancedMessage)
            streamingText.value = ''
          }
          statusText.value = ''
        }
      } catch {}
    }
  } catch (err) {
    messages.value.push({ role: 'assistant', text: '⚠️ Connection error. Please try again.' })
  } finally {
    streaming.value = false
    streamingText.value = ''
    await loadSession({ preserveEnhancements: true })
    await loadPlannerQuota()
    scrollBottom()
    await nextTick()
    inputEl.value?.focus()
  }
}

function sendStarter(prompt) {
  input.value = prompt
  sendMessage()
}

// ─── Quick reply handler (Sprint 2) ──────────────────────────────────────────
function sendQuickReply(reply) {
  const label = (reply?.text || '').toLowerCase()
  let action = reply?.action

  if (!action) {
    if (label.includes('view all matches')) action = 'goto-matches'
    else if (label.includes('add dates')) action = 'prefill-dates'
    else if (label.includes('set budget')) action = 'prefill-budget'
    else if (label.includes('refine search')) action = 'prefill-refine'
  }

  applyQuickAction(action, reply?.message || reply?.text || '')
}

function applyQuickAction(action, fallbackText = '') {
  // Navigation action: jump straight to Matches tab.
  if (action === 'goto-matches') {
    activeTab.value = 'matches'
    return
  }

  // All template actions continue in Chat.
  activeTab.value = 'chat'

  if (action === 'prefill-dates') {
    input.value = [
      'Travel dates:',
      '- Start date: YYYY-MM-DD',
      '- End date: YYYY-MM-DD'
    ].join('\n')
  } else if (action === 'prefill-budget') {
    input.value = [
      'Budget details:',
      '- Total budget: $____',
      '- Currency: USD',
      '- Flexibility: +/- ____%'
    ].join('\n')
  } else if (action === 'prefill-refine') {
    input.value = [
      'Please refine my search with these updates:',
      '- Priority: (price / rating / availability)',
      '- Preferred service: (tour / car / both)',
      '- Must-have preferences: ____'
    ].join('\n')
  } else {
    // Fallback: prefill only, never auto-send.
    input.value = fallbackText
  }

  nextTick(() => {
    inputEl.value?.focus()
    autoResize()
  })
}

function editRequirementInChat(target) {
  if (target === 'dates') {
    applyQuickAction('prefill-dates')
    return
  }
  if (target === 'budget') {
    applyQuickAction('prefill-budget')
    return
  }
  applyQuickAction('prefill-refine')
}

// ─── Generate contextual quick replies (Sprint 2) ────────────────────────────
function generateQuickReplies(messageText, operators) {
  const replies = []
  const text = messageText.toLowerCase()
  
  // If operators found, suggest viewing them
  if (operators && operators.length > 0) {
    replies.push({ icon: '📍', text: 'View All Matches', message: 'Show me all the matched operators', action: 'goto-matches' })
  }
  
  // If no dates mentioned, suggest adding them
  if (!requirements.value.travel_dates && (text.includes('trip') || text.includes('visit'))) {
    replies.push({ icon: '📅', text: 'Add Dates', message: 'I want to travel next month', action: 'prefill-dates' })
  }
  
  // If no budget mentioned
  if (!requirements.value.budget_usd && operators.length > 0) {
    replies.push({ icon: '💰', text: 'Set Budget', message: 'My budget is around $500', action: 'prefill-budget' })
  }
  
  // If requirements exist, offer to refine
  if (hasRequirements.value) {
    replies.push({ icon: '🔍', text: 'Refine Search', message: 'Can you find more options?', action: 'prefill-refine' })
  }
  
  // Always offer to ask more
  replies.push({ icon: '💬', text: 'Ask More', message: 'Tell me more about the best option' })
  
  return replies.slice(0, 4) // Max 4 quick replies
}

// ─── Quick car mode ───────────────────────────────────────────────────────────
function quickCarMode() {
  serviceMode.value = 'car'
  input.value = 'I need car services in the area I mentioned'
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
      service_type: op.recommended_service || 'tour',
      area_name: primaryArea,
      state: primaryState,
      country: primaryCountry,
      sub_location_name: `Planner shortlist: ${op.business_name}`,
      description: op.match_reason || op.description || 'Added from Tour Planner recommendations',
      coordinates: matchedAreaDetail?.coordinates || null,
      vehicle_type: op.car_option?.vehicle_type,
      seats: op.car_option?.seats,
      pricing_model: op.car_option?.pricing_model,
      base_fare: op.car_option?.base_fare,
      images: [],
    }
    cartStore.addToCart(plannerCartItem)

    addedIds.value = new Set([...addedIds.value, op.id])
    
    // Sprint 5: Success toast with confetti
    toast.success(`${op.business_name} added to cart!`, 'Success')
    triggerConfetti()
    hapticFeedback('success')
    
    // Sprint 6: Screen reader announcement
    announceToScreenReader(`${op.business_name} successfully added to cart`)
    
    messages.value.push({
      role: 'assistant',
      text: `✅ **${op.business_name}** has been added to your cart. You can view and book it from the Cart page.`,
    })
    scrollBottom()
  } catch (err) {
    // Sprint 5: Error toast
    const errorMsg = err.response?.data?.detail || 'Unable to add to cart'
    toast.error(errorMsg, 'Error')
    hapticFeedback('error')
    
    // Sprint 6: Screen reader announcement
    announceToScreenReader(`Error: ${errorMsg}`)
    
    messages.value.push({
      role: 'assistant',
      text: `⚠️ Could not add to cart: ${errorMsg}`,
    })
  } finally {
    addingId.value = null
  }
}

async function loadItineraryIdeas() {
  if (!sessionId.value) return
  itineraryLoading.value = true
  itineraryError.value = ''
  try {
    const res = await api.get(`/tour-planner/session/${sessionId.value}/itineraries`)
    itineraryIdeas.value = res.data.itineraries || []
  } catch (err) {
    itineraryIdeas.value = []
    itineraryError.value = err.response?.data?.detail || 'Unable to load itinerary ideas right now.'
  } finally {
    itineraryLoading.value = false
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
  itineraryIdeas.value = []
  itineraryError.value = ''
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

function getInlineOperators(msg, idx) {
  if (msg?.operators?.length) return msg.operators

  const isLatestAssistantMessage =
    msg?.role === 'assistant' && idx === messages.value.length - 1

  if (isLatestAssistantMessage && suggestedOperators.value?.length) {
    return suggestedOperators.value
  }

  return []
}

// Sprint 3: Helper functions for Matches tab
function getPriceValue(priceRange) {
  if (!priceRange) return 0
  // Extract first number from price range (e.g., "$500 - $1000" -> 500)
  const match = priceRange.match(/\$?(\d+)/)
  return match ? parseInt(match[1]) : 0
}

// Sprint 4: Mobile gesture & interaction handlers

// Haptic feedback for touch interactions
function hapticFeedback(type = 'light') {
  if (navigator.vibrate) {
    const patterns = {
      light: 10,
      medium: 20,
      heavy: 30,
      success: [10, 50, 10],
      error: [20, 100, 20]
    }
    navigator.vibrate(patterns[type] || 10)
  }
}

// Swipe gesture detection for tab navigation
function handleTouchStart(e) {
  touchStartX.value = e.touches[0].clientX
  touchStartY.value = e.touches[0].clientY
}

function handleTouchMove(e) {
  touchEndX.value = e.touches[0].clientX
  touchEndY.value = e.touches[0].clientY
}

function handleTouchEnd() {
  const deltaX = touchStartX.value - touchEndX.value
  const deltaY = touchStartY.value - touchEndY.value
  
  // Require horizontal swipe to be more prominent than vertical
  if (Math.abs(deltaX) > Math.abs(deltaY) && Math.abs(deltaX) > 50) {
    const tabOrder = ['chat', 'matches', 'itinerary', 'requirements']
    const currentIndex = tabOrder.indexOf(activeTab.value)
    
    if (deltaX > 0 && currentIndex < tabOrder.length - 1) {
      // Swipe left - next tab
      activeTab.value = tabOrder[currentIndex + 1]
      hapticFeedback('light')
    } else if (deltaX < 0 && currentIndex > 0) {
      // Swipe right - previous tab
      activeTab.value = tabOrder[currentIndex - 1]
      hapticFeedback('light')
    }
  }
}

// Pull-to-refresh functionality
function handlePullStart(e) {
  if (messagesEl.value && messagesEl.value.scrollTop === 0) {
    pullStartY.value = e.touches[0].clientY
  }
}

function handlePullMove(e) {
  if (pullStartY.value > 0) {
    const currentY = e.touches[0].clientY
    pullDistance.value = Math.min(Math.max(currentY - pullStartY.value, 0), 100)
  }
}

async function handlePullEnd() {
  if (pullDistance.value > 60) {
    isRefreshing.value = true
    hapticFeedback('medium')
    await loadPlannerQuota()
    await loadSession()
    setTimeout(() => {
      isRefreshing.value = false
      pullDistance.value = 0
      pullStartY.value = 0
      hapticFeedback('success')
    }, 500)
  } else {
    pullDistance.value = 0
    pullStartY.value = 0
  }
}

// Toggle FAB visibility based on scroll
function handleScroll() {
  if (messagesEl.value) {
    showFAB.value = messagesEl.value.scrollTop > 200
  }
}

// FAB action - scroll to bottom
function scrollToBottom() {
  hapticFeedback('light')
  scrollBottom()
}

// FAB action - new session
function startNewSessionFAB() {
  hapticFeedback('medium')
  startNewSession()
}

// Sprint 5: Confetti animation for cart additions
function triggerConfetti() {
  const confettiCount = 30
  const colors = ['#10b981', '#3b82f6', '#f59e0b', '#ec4899', '#8b5cf6']
  const confettiContainer = document.createElement('div')
  confettiContainer.style.position = 'fixed'
  confettiContainer.style.top = '0'
  confettiContainer.style.left = '0'
  confettiContainer.style.width = '100%'
  confettiContainer.style.height = '100%'
  confettiContainer.style.pointerEvents = 'none'
  confettiContainer.style.zIndex = '9998'
  document.body.appendChild(confettiContainer)
  
  for (let i = 0; i < confettiCount; i++) {
    const confetti = document.createElement('div')
    const color = colors[Math.floor(Math.random() * colors.length)]
    const size = Math.random() * 10 + 5
    const startX = Math.random() * window.innerWidth
    const endX = startX + (Math.random() - 0.5) * 200
    const rotation = Math.random() * 360
    const duration = Math.random() * 2 + 1
    
    confetti.style.position = 'absolute'
    confetti.style.width = size + 'px'
    confetti.style.height = size + 'px'
    confetti.style.background = color
    confetti.style.top = '-20px'
    confetti.style.left = startX + 'px'
    confetti.style.borderRadius = Math.random() > 0.5 ? '50%' : '0'
    confetti.style.opacity = '1'
    confetti.style.transform = `rotate(${rotation}deg)`
    
    confettiContainer.appendChild(confetti)
    
    confetti.animate([
      {
        top: '-20px',
        left: startX + 'px',
        opacity: 1,
        transform: `rotate(${rotation}deg)`
      },
      {
        top: window.innerHeight + 'px',
        left: endX + 'px',
        opacity: 0,
        transform: `rotate(${rotation + 720}deg)`
      }
    ], {
      duration: duration * 1000,
      easing: 'cubic-bezier(0.25, 0.46, 0.45, 0.94)'
    })
  }
  
  setTimeout(() => {
    document.body.removeChild(confettiContainer)
  }, 3000)
}

// Sprint 6: Accessibility - Screen reader announcements
function announceToScreenReader(message) {
  screenReaderAnnouncement.value = message
  // Clear after a brief moment so repeated messages are re-announced
  setTimeout(() => {
    screenReaderAnnouncement.value = ''
  }, 1000)
}

// Sprint 6: Accessibility - Keyboard navigation helpers
function handleEscapeKey(event) {
  if (event.key === 'Escape') {
    // Close any open modals or reset focus
    event.preventDefault()
  }
}

// Sprint 6: Accessibility - Focus management
function trapFocus(event, container) {
  const focusableElements = container.querySelectorAll(
    'button:not([disabled]), a[href], input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'
  )
  const firstElement = focusableElements[0]
  const lastElement = focusableElements[focusableElements.length - 1]
  
  if (event.key === 'Tab') {
    if (event.shiftKey && document.activeElement === firstElement) {
      event.preventDefault()
      lastElement.focus()
    } else if (!event.shiftKey && document.activeElement === lastElement) {
      event.preventDefault()
      firstElement.focus()
    }
  }
}

// Sprint 5: Smooth scroll behavior
function smoothScrollTo(element, offset = 0) {
  if (!element) return
  const top = element.offsetTop - offset
  window.scrollTo({
    top,
    behavior: 'smooth'
  })
}

</script>

<style scoped>
/* Sprint 6: Accessibility Styles */

/* Skip Links - Hidden until focused */
.skip-link {
  position: absolute;
  top: -40px;
  left: 0;
  background: #0891b2;
  color: white;
  padding: 8px 16px;
  text-decoration: none;
  border-radius: 0 0 4px 0;
  z-index: 10000;
  font-weight: 600;
  transition: top 0.2s ease;
}

.skip-link:focus {
  top: 0;
  outline: 3px solid #fbbf24;
  outline-offset: 2px;
}

/* Screen Reader Only - Visually hidden but accessible to screen readers */
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border-width: 0;
}

/* Enhanced Focus Styles - WCAG AA compliant */
*:focus {
  outline: 2px solid #0891b2;
  outline-offset: 2px;
}

button:focus,
a:focus,
input:focus,
select:focus,
textarea:focus {
  outline: 3px solid #0891b2;
  outline-offset: 2px;
}

/* Reduced Motion Support */
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 0.01ms !important;
    animation-iteration-count: 1 !important;
    transition-duration: 0.01ms !important;
  }
}

/* NEW LAYOUT STYLES */
.planner-page-new {
  max-width: 1400px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.planner-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 20px 28px;
  border-radius: 16px;
  margin-bottom: 0;
}

.header-left {
  flex: 1;
}

.planner-title {
  display: flex;
  align-items: center;
  gap: 12px;
  margin: 0;
  font-size: 26px;
  font-weight: 700;
  color: #0f172a;
}

.title-icon {
  font-size: 28px;
}

.planner-subtitle {
  margin: 4px 0 0 40px;
  font-size: 14px;
  color: #64748b;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: nowrap;
}

.cart-button {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  min-height: 42px;
  padding: 10px 14px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid rgba(100, 116, 139, 0.35);
  border-radius: 12px;
  text-decoration: none;
  color: #0f172a;
  font-size: 15px;
  font-weight: 700;
  transition: all 0.2s ease;
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.08);
  white-space: nowrap;
}

.cart-button:hover {
  background: linear-gradient(180deg, #ffffff 0%, #f1f5f9 100%);
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(15, 23, 42, 0.14);
}

.cart-button:focus-visible {
  outline: 3px solid #0891b2;
  outline-offset: 2px;
}

/* Keep a single cart entry point on touch layouts (FAB cart) */
@media (max-width: 1024px) {
  .header-right .cart-button {
    display: none;
  }
}

@media (max-width: 768px) {
  .planner-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 10px;
    padding: 14px 16px;
  }

  .planner-title {
    font-size: 22px;
  }

  .planner-subtitle {
    margin-left: 36px;
    font-size: 13px;
  }

  .header-right {
    width: 100%;
    justify-content: flex-start;
  }
}

.tab-panel {
  background: rgba(255, 255, 255, 0.78);
  border-radius: 0 0 16px 16px;
  margin-top: -17px;
  padding-top: 17px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-top: none;
  min-height: 400px;
}

/* ORIGINAL STYLES */
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
  grid-template-columns: minmax(0, 1fr);
  gap: 0.75rem;
  height: calc(100vh - 94px);
  min-height: calc(100vh - 94px);
  border-radius: 0 0 16px 16px;
  margin-top: -17px;
  padding: 17px 16px 16px;
  border: 1px solid rgba(148, 163, 184, 0.28);
  border-top: none;
  background: rgba(255, 255, 255, 0.78);
}

.glass-card {
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 18px 50px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(16px);
}

.req-card {
  border-radius: 24px;
  padding: 0.8rem;
}

.quota-card {
  border-radius: 24px;
  padding: 0.8rem;
}

.itinerary-card {
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

.mini-link {
  color: #0369a1;
  font-size: 0.74rem;
  font-weight: 700;
  text-decoration: none;
}

.mini-link:hover {
  text-decoration: underline;
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

.req-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.45rem;
  margin-top: 0.55rem;
}

.quota-grid-panel {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.5rem;
  margin-top: 0.55rem;
}

.quota-stat {
  padding: 0.55rem 0.65rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.16);
  display: grid;
  gap: 0.15rem;
}

.quota-stat strong {
  font-size: 1.08rem;
  color: #0f172a;
}

.quota-stat span:last-child {
  font-size: 0.76rem;
  color: #64748b;
}

.quota-meta {
  margin: 0.55rem 0 0;
  color: #64748b;
  font-size: 0.75rem;
  line-height: 1.45;
}

.quota-pill.danger {
  background: rgba(239, 68, 68, 0.12);
  color: #b91c1c;
}

.quota-lock-panel {
  margin-top: 0.65rem;
  padding: 0.75rem;
  border-radius: 14px;
  background: rgba(15, 23, 42, 0.04);
  border: 1px dashed rgba(148, 163, 184, 0.28);
  display: grid;
  gap: 0.5rem;
}

.quota-lock-copy,
.quota-lock-note {
  margin: 0;
  color: #475569;
  font-size: 0.78rem;
  line-height: 1.45;
}

.quota-lock-note {
  color: #64748b;
}

.btn-reward-locked {
  border: none;
  border-radius: 14px;
  padding: 0.72rem 0.9rem;
  background: linear-gradient(135deg, #cbd5e1, #94a3b8);
  color: #0f172a;
  font-weight: 800;
  opacity: 0.72;
  cursor: not-allowed;
}

.error-text {
  color: #b91c1c;
}

.itinerary-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-top: 0.55rem;
}

.itinerary-item {
  padding: 0.65rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.75);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.itinerary-top {
  display: flex;
  justify-content: space-between;
  gap: 0.65rem;
  align-items: flex-start;
}

.itinerary-top h4 {
  margin: 0;
  font-size: 0.88rem;
  color: #0f172a;
}

.itinerary-top p {
  margin: 0.2rem 0 0;
  color: #64748b;
  font-size: 0.78rem;
  line-height: 1.4;
}

.itinerary-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
  margin-top: 0.45rem;
}

.itinerary-meta span {
  background: rgba(241, 245, 249, 0.9);
  border-radius: 999px;
  padding: 0.2rem 0.5rem;
  font-size: 0.74rem;
  color: #475569;
  font-weight: 700;
}

.itinerary-empty {
  margin-top: 0.55rem;
  padding: 0.65rem;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.7);
  border: 1px dashed rgba(148, 163, 184, 0.22);
  font-size: 0.74rem;
  color: #475569;
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

.service-pill {
  color: #1e293b;
  background: rgba(148, 163, 184, 0.18);
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

.car-quick-specs {
  margin-top: 0.45rem;
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem;
}

.car-quick-specs span {
  font-size: 0.7rem;
  color: #334155;
  background: rgba(226, 232, 240, 0.7);
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  padding: 0.2rem 0.45rem;
  font-weight: 700;
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

.service-switch {
  margin-top: 0.45rem;
  display: inline-flex;
  border: 1px solid rgba(148, 163, 184, 0.3);
  border-radius: 10px;
  padding: 0.15rem;
  gap: 0.15rem;
}

.service-btn {
  border: none;
  background: transparent;
  color: #475569;
  font-size: 0.72rem;
  font-weight: 800;
  padding: 0.3rem 0.55rem;
  border-radius: 8px;
  cursor: pointer;
}

.service-btn.active {
  background: rgba(15, 118, 110, 0.14);
  color: #0f766e;
}

.btn-car-only {
  margin-left: 0.8rem;
  border: 1px solid rgba(220, 38, 38, 0.3);
  background: rgba(220, 38, 38, 0.06);
  color: #991b1b;
  font-size: 0.75rem;
  font-weight: 700;
  padding: 0.35rem 0.7rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s ease;
  display: inline-flex;
  align-items: center;
  gap: 0.3rem;
}

.btn-car-only:hover {
  background: rgba(220, 38, 38, 0.12);
  border-color: rgba(220, 38, 38, 0.5);
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
    grid-template-rows: 1fr;
    height: calc(100vh - 88px);
    min-height: calc(100vh - 88px);
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

  .req-grid,
  .quota-grid-panel {
    grid-template-columns: 1fr;
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   SPRINT 2: CHAT ENHANCEMENTS - Inline Operator Cards & Quick Replies
   ═══════════════════════════════════════════════════════════════════════════ */

/* Inline Operator Cards */
.inline-operators {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.15);
}

.inline-operators-header {
  margin-bottom: 12px;
}

.operators-badge {
  display: inline-block;
  padding: 4px 12px;
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  color: white;
  border-radius: 12px;
  font-size: 12px;
  font-weight: 700;
}

.inline-operator-grid {
  display: grid;
  gap: 12px;
  margin-bottom: 12px;
}

.inline-op-card {
  padding: 14px;
  background: rgba(255, 255, 255, 0.6);
  border: 1px solid rgba(148, 163, 184, 0.15);
  border-radius: 12px;
  transition: all 0.2s ease;
}

.inline-op-card:hover {
  background: rgba(255, 255, 255, 0.9);
  border-color: rgba(15, 118, 110, 0.3);
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
}

.inline-op-card.added {
  background: rgba(16, 185, 129, 0.05);
  border-color: rgba(16, 185, 129, 0.3);
}

.inline-op-header {
  display: flex;
  gap: 10px;
  margin-bottom: 8px;
}

.inline-op-avatar {
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  color: white;
  border-radius: 8px;
  font-size: 16px;
  font-weight: 700;
  flex-shrink: 0;
}

.inline-op-info {
  flex: 1;
  min-width: 0;
}

.inline-op-info h5 {
  margin: 0 0 4px 0;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.inline-op-meta {
  display: flex;
  gap: 10px;
  font-size: 12px;
}

.op-rating {
  color: #f59e0b;
  font-weight: 600;
}

.op-score {
  color: #10b981;
  font-weight: 600;
}

.inline-op-reason {
  margin: 0 0 8px 0;
  font-size: 12px;
  line-height: 1.4;
  color: #475569;
  font-style: italic;
  overflow: hidden;
  text-overflow: ellipsis;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
}

.inline-op-tags {
  display: flex;
  gap: 6px;
  margin-bottom: 10px;
  flex-wrap: wrap;
}

.op-tag {
  padding: 3px 8px;
  border-radius: 6px;
  font-size: 11px;
  font-weight: 600;
}

.op-tag.budget {
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}

.op-tag.service {
  background: rgba(8, 145, 178, 0.1);
  color: #0891b2;
}

.inline-op-actions {
  display: flex;
  gap: 8px;
}

.btn-inline-add {
  flex: 1;
  padding: 8px 14px;
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  border: none;
  border-radius: 8px;
  color: white;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-inline-add:hover:not(:disabled) {
  transform: translateY(-1px);
  box-shadow: 0 4px 8px rgba(8, 145, 178, 0.3);
}

.btn-inline-add:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.inline-added {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 8px 14px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 8px;
  color: #10b981;
  font-size: 12px;
  font-weight: 600;
}

.btn-inline-view {
  padding: 8px 14px;
  background: white;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 8px;
  color: #334155;
  font-size: 12px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-inline-view:hover {
  border-color: rgba(15, 118, 110, 0.4);
  color: #0f766e;
}

.inline-operators-more {
  margin: 0;
  font-size: 12px;
  color: #64748b;
  text-align: center;
}

.link-button {
  background: none;
  border: none;
  color: #0891b2;
  font-weight: 600;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
  font-size: inherit;
}

.link-button:hover {
  color: #0f766e;
}

/* Quick Reply Buttons */
.quick-replies {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
}

.quick-reply-btn {
  padding: 8px 14px;
  background: rgba(255, 255, 255, 0.8);
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 999px;
  color: #334155;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-reply-btn:hover {
  background: white;
  border-color: rgba(15, 118, 110, 0.4);
  color: #0f766e;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

/* Enhanced Status Line */
.status-line {
  gap: 8px;
}

.status-text {
  font-size: 13px;
  color: #0891b2;
  font-weight: 500;
}

.status-progress {
  height: 4px;
  background: rgba(8, 145, 178, 0.1);
  border-radius: 2px;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  border-radius: 2px;
  animation: progress-slide 2s ease-in-out infinite;
}

.progress-searching {
  background: linear-gradient(90deg, #0891b2, #0ea5e9);
  animation-duration: 1.5s;
}

.progress-analyzing {
  background: linear-gradient(90deg, #8b5cf6, #a78bfa);
  animation-duration: 2s;
}

.progress-ranking {
  background: linear-gradient(90deg, #10b981, #34d399);
  animation-duration: 1s;
}

@keyframes progress-slide {
  0% { transform: translateX(-100%); }
  100% { transform: translateX(300%); }
}

/* Typing Indicator */
.typing-indicator {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 14px 18px;
  background: rgba(255, 255, 255, 0.8);
  border-radius: 18px;
  width: fit-content;
  border: 1px solid rgba(148, 163, 184, 0.15);
}

.typing-dot {
  width: 8px;
  height: 8px;
  background: #94a3b8;
  border-radius: 50%;
  animation: typing-bounce 1.4s ease-in-out infinite;
}

.typing-dot:nth-child(1) {
  animation-delay: 0s;
}

.typing-dot:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dot:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing-bounce {
  0%, 60%, 100% {
    transform: translateY(0);
  }
  30% {
    transform: translateY(-10px);
  }
}

.typing-text {
  font-size: 13px;
  color: #64748b;
  font-style: italic;
}

/* ═══════════════════════════════════════════════════════════════════════════
   SPRINT 3: MATCHES TAB CONTENT
   ═══════════════════════════════════════════════════════════════════════════ */

/* Matches Panel Container */
.matches-panel {
  padding: 0;
}

.matches-container {
  max-width: 1400px;
  margin: 0 auto;
  padding: 24px;
}

/* Filters & Sort Controls */
.matches-controls {
  padding: 20px 24px;
  margin-bottom: 24px;
  border-radius: 16px;
}

.controls-row {
  display: flex;
  align-items: flex-end;
  gap: 20px;
  flex-wrap: wrap;
}

.control-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.control-label {
  font-size: 13px;
  font-weight: 600;
  color: #334155;
}

.filter-buttons {
  display: flex;
  gap: 8px;
}

.filter-btn {
  padding: 8px 16px;
  background: white;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  color: #334155;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
}

.filter-btn:hover {
  border-color: rgba(15, 118, 110, 0.3);
  background: rgba(15, 118, 110, 0.05);
}

.filter-btn.active {
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  border-color: #0891b2;
  color: white;
}

.filter-select {
  padding: 8px 14px;
  background: white;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  color: #334155;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.2s ease;
  min-width: 180px;
}

.filter-select:hover {
  border-color: rgba(15, 118, 110, 0.3);
}

.filter-select:focus {
  outline: none;
  border-color: #0891b2;
  box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.1);
}

.result-count {
  margin-left: auto;
  justify-content: flex-end;
}

.count-label {
  font-size: 14px;
  font-weight: 600;
  color: #0891b2;
}

/* Matches Grid */
.matches-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(380px, 1fr));
  gap: 20px;
}

/* Match Card */
.match-card {
  padding: 20px;
  border-radius: 16px;
  transition: all 0.3s ease;
  border: 1px solid rgba(148, 163, 184, 0.1);
}

.match-card:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.1);
  border-color: rgba(15, 118, 110, 0.2);
}

.match-card.match-added {
  background: rgba(16, 185, 129, 0.03);
  border-color: rgba(16, 185, 129, 0.2);
}

/* Card Header */
.match-header {
  display: flex;
  gap: 14px;
  margin-bottom: 14px;
  align-items: flex-start;
}

.match-avatar {
  width: 48px;
  height: 48px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  color: white;
  border-radius: 12px;
  font-size: 20px;
  font-weight: 700;
  flex-shrink: 0;
}

.match-info {
  flex: 1;
  min-width: 0;
}

.match-name {
  margin: 0 0 6px 0;
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.match-meta {
  display: flex;
  gap: 12px;
  font-size: 14px;
}

.match-rating {
  color: #f59e0b;
  font-weight: 600;
}

.match-score {
  color: #10b981;
  font-weight: 600;
}

.match-badge {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.added-badge {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

/* Match Reason */
.match-reason {
  margin: 0 0 14px 0;
  font-size: 14px;
  line-height: 1.5;
  color: #475569;
  font-style: italic;
  background: rgba(8, 145, 178, 0.05);
  padding: 10px 12px;
  border-radius: 10px;
  border-left: 3px solid #0891b2;
}

/* Service Badges */
.match-service {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}

.service-badge {
  padding: 6px 12px;
  border-radius: 8px;
  font-size: 12px;
  font-weight: 600;
}

.badge-tour {
  background: rgba(8, 145, 178, 0.1);
  color: #0891b2;
}

.badge-car {
  background: rgba(139, 92, 246, 0.1);
  color: #8b5cf6;
}

.badge-budget {
  background: rgba(16, 185, 129, 0.1);
  color: #10b981;
}

/* Serving Areas */
.match-areas {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
  margin-bottom: 12px;
  align-items: center;
}

.areas-label {
  font-size: 12px;
  font-weight: 600;
  color: #64748b;
}

.area-tag {
  padding: 4px 10px;
  background: rgba(148, 163, 184, 0.1);
  border-radius: 6px;
  font-size: 12px;
  color: #475569;
}

.area-more {
  font-size: 12px;
  color: #64748b;
  font-style: italic;
}

/* Description */
.match-description {
  margin: 0 0 14px 0;
  font-size: 14px;
  line-height: 1.6;
  color: #475569;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Price */
.match-price {
  margin-bottom: 16px;
  padding: 10px 12px;
  background: rgba(139, 92, 246, 0.05);
  border-radius: 8px;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.price-label {
  font-size: 13px;
  font-weight: 600;
  color: #64748b;
}

.price-value {
  font-size: 15px;
  font-weight: 700;
  color: #8b5cf6;
}

/* Actions */
.match-actions {
  display: flex;
  gap: 10px;
  padding-top: 16px;
  border-top: 1px solid rgba(148, 163, 184, 0.1);
}

.btn-match-add {
  flex: 1;
  padding: 10px 18px;
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  border: none;
  border-radius: 10px;
  color: white;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-match-add:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(8, 145, 178, 0.3);
}

.btn-match-add:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.match-added-label {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 10px 18px;
  background: rgba(16, 185, 129, 0.1);
  border-radius: 10px;
  color: #10b981;
  font-size: 14px;
  font-weight: 600;
}

.btn-match-view {
  padding: 10px 18px;
  background: white;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-radius: 10px;
  color: #334155;
  font-size: 14px;
  font-weight: 600;
  text-decoration: none;
  transition: all 0.2s ease;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-match-view:hover {
  border-color: #0891b2;
  color: #0891b2;
  background: rgba(8, 145, 178, 0.05);
}

/* Empty State */
.matches-empty {
  text-align: center;
  padding: 80px 40px;
  background: rgba(255, 255, 255, 0.5);
  border-radius: 20px;
  border: 2px dashed rgba(148, 163, 184, 0.2);
}

.empty-icon {
  font-size: 64px;
  margin-bottom: 20px;
  opacity: 0.5;
}

.matches-empty h3 {
  margin: 0 0 12px 0;
  font-size: 22px;
  color: #334155;
}

.matches-empty p {
  margin: 0 0 24px 0;
  font-size: 15px;
  color: #64748b;
  max-width: 500px;
  margin-left: auto;
  margin-right: auto;
}

.btn-empty-action {
  padding: 12px 32px;
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  border: none;
  border-radius: 12px;
  color: white;
  font-size: 15px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-empty-action:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(8, 145, 178, 0.3);
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .matches-container {
    padding: 16px;
  }

  .controls-row {
    flex-direction: column;
    align-items: stretch;
  }

  .control-group {
    width: 100%;
  }

  .filter-buttons {
    width: 100%;
  }

  .filter-btn {
    flex: 1;
  }

  .filter-select {
    width: 100%;
  }

  .result-count {
    margin-left: 0;
  }

  .matches-grid {
    grid-template-columns: 1fr;
  }

  .match-header {
    flex-wrap: wrap;
  }

  .match-badge {
    width: 100%;
    text-align: center;
  }
}

/* ═══════════════════════════════════════════════════════════════════════════
   SPRINT 4: MOBILE OPTIMIZATION STYLES
   ═══════════════════════════════════════════════════════════════════════════ */

/* Pull-to-refresh indicator */
.pull-refresh-indicator {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  z-index: 9999;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  color: white;
  font-size: 13px;
  font-weight: 600;
  transition: height 0.1s ease, opacity 0.1s ease;
  overflow: hidden;
}

.refresh-icon {
  font-size: 20px;
  margin-bottom: 4px;
  transition: transform 0.3s ease;
}

.refresh-icon.spinning {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

/* Floating Action Buttons */
.fab-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  z-index: 1000;
}

.fab {
  width: 56px;
  height: 56px;
  border-radius: 50%;
  border: none;
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  color: white;
  font-size: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 4px 12px rgba(8, 145, 178, 0.3);
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  text-decoration: none;
}

.fab:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(8, 145, 178, 0.4);
}

.fab:active {
  transform: translateY(0) scale(0.95);
}

.fab-cart {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  box-shadow: 0 4px 12px rgba(245, 158, 11, 0.3);
}

.fab-cart:hover {
  box-shadow: 0 6px 20px rgba(245, 158, 11, 0.4);
}

.fab-cart.has-items {
  animation: pulse-cart 2s infinite;
}

@keyframes pulse-cart {
  0%, 100% { transform: scale(1); }
  50% { transform: scale(1.05); }
}

.fab-badge {
  position: absolute;
  top: -4px;
  right: -4px;
  background: #ef4444;
  color: white;
  font-size: 12px;
  font-weight: 700;
  min-width: 20px;
  height: 20px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 0 6px;
  border: 2px solid white;
}

.fab-scroll {
  background: linear-gradient(135deg, #8b5cf6 0%, #7c3aed 100%);
  box-shadow: 0 4px 12px rgba(139, 92, 246, 0.3);
  animation: fadeInUp 0.3s ease;
}

.fab-scroll:hover {
  box-shadow: 0 6px 20px rgba(139, 92, 246, 0.4);
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.fab-new-session {
  width: 48px;
  height: 48px;
  font-size: 20px;
  background: linear-gradient(135deg, #ec4899 0%, #db2777 100%);
  box-shadow: 0 4px 12px rgba(236, 72, 153, 0.3);
}

.fab-new-session:hover {
  box-shadow: 0 6px 20px rgba(236, 72, 153, 0.4);
}

/* Mobile optimizations */
@media (max-width: 768px) {
  
  /* Hide FABs on mobile when TabNavigation bottom bar is visible */
  .fab-container {
    bottom: 90px; /* Above the bottom tab bar */
    right: 16px;
  }
  
  .fab {
    width: 48px;
    height: 48px;
    font-size: 20px;
  }
  
  .fab-new-session {
    width: 44px;
    height: 44px;
    font-size: 18px;
  }
  
  /* Enhanced touch targets for all interactive elements */
  .filter-btn,
  .sort-btn,
  .btn-add,
  .btn-view,
  .btn-empty-action {
    min-height: 44px;
    padding: 12px 20px;
    font-size: 15px;
  }
  
  /* Quick reply buttons larger on mobile */
  .quick-reply-btn {
    min-height: 44px;
    padding: 10px 18px;
    font-size: 15px;
  }
  
  /* Inline operator card actions */
  .inline-op-actions .btn-add-inline,
  .inline-op-actions .btn-view-all {
    min-height: 44px;
    padding: 10px 18px;
  }
  
  /* Chat input area optimization */
  .input-row {
    padding: 16px;
    gap: 12px;
  }
  
  .input-box {
    min-height: 48px;
    font-size: 16px; /* Prevents auto-zoom on iOS */
    padding: 14px 16px;
  }
  
  .send-btn {
    min-width: 48px;
    min-height: 48px;
    font-size: 20px;
  }
  
  /* Service mode buttons larger touch targets */
  .service-btn {
    min-height: 44px;
    padding: 10px 16px;
    font-size: 15px;
  }
  
  /* Matches grid cards - better spacing on mobile */
  .matches-grid {
    gap: 16px;
  }
  
  .match-card {
    padding: 18px;
  }
  
  /* Swipe gesture feedback */
  .planner-page-new {
    -webkit-user-select: none;
    user-select: none;
    touch-action: pan-y; /* Allow vertical scrolling, detect horizontal swipes */
  }
  
  .tab-panel {
    transition: transform 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  }
}

/* Tablet optimizations */
@media (min-width: 769px) and (max-width: 1024px) {
  .fab-container {
    bottom: 24px;
    right: 24px;
  }
}

/* Desktop - hide mobile-specific features */
@media (min-width: 1025px) {
  .pull-refresh-indicator {
    display: none;
  }
  
  .fab-container {
    display: none; /* Desktop users use header cart button */
  }
  
  .planner-page-new {
    touch-action: auto;
  }
}

/* High DPI displays */
@media (-webkit-min-device-pixel-ratio: 2), (min-resolution: 192dpi) {
  .fab {
    box-shadow: 0 4px 16px rgba(8, 145, 178, 0.35);
  }
  
  .fab:hover {
    box-shadow: 0 6px 24px rgba(8, 145, 178, 0.45);
  }
}

/* Reduced motion preference */
@media (prefers-reduced-motion: reduce) {
  .fab,
  .refresh-icon,
  .tab-panel {
    transition: none !important;
    animation: none !important;
  }
}

/* Dark mode support (future-proofing) */
@media (prefers-color-scheme: dark) {
  .fab {
    box-shadow: 0 4px 12px rgba(8, 145, 178, 0.5);
  }
  
  .fab-badge {
    border-color: #1e293b;
  }
}

/* END SPRINT 4 STYLES */

/* ═══════════════════════════════════════════════════════════════════════════
   SPRINT 5: VISUAL POLISH & MICRO-INTERACTIONS
   ═══════════════════════════════════════════════════════════════════════════ */

/* Global smooth scroll */
html {
  scroll-behavior: smooth;
}

.planner-shell *,
.planner-page-new * {
  scroll-behavior: smooth;
}

/* Enhanced card hover animations */
.glass-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.glass-card:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 32px rgba(0, 0, 0, 0.12), 0 4px 12px rgba(0, 0, 0, 0.08);
}

/* Button press micro-interaction */
button:not(.fab):active,
.btn-add:active,
.btn-view:active,
.filter-btn:active,
.sort-btn:active {
  transform: scale(0.96);
  transition: transform 0.1s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Enhanced button hover states */
.btn-add,
.btn-view,
.filter-btn,
.sort-btn,
.quick-reply-btn {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.btn-add::before,
.btn-view::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.2);
  transform: translate(-50%, -50%);
  transition: width 0.6s, height 0.6s;
}

.btn-add:hover::before,
.btn-view:hover::before {
  width: 300px;
  height: 300px;
}

/* Match card enhanced animations */
.match-card {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.match-card::before {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 14px;
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  opacity: 0;
  transition: opacity 0.3s ease;
  z-index: -1;
}

.match-card:hover {
  transform: translateY(-6px) scale(1.02);
  box-shadow: 0 16px 48px rgba(8, 145, 178, 0.2), 0 8px 16px rgba(0, 0, 0, 0.12);
}

.match-card:hover::before {
  opacity: 0.05;
}

/* Inline operator card animations */
.inline-operator-card {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
}

.inline-operator-card:hover {
  transform: translateY(-3px);
  box-shadow: 0 8px 20px rgba(8, 145, 178, 0.15);
}

/* Quick reply button ripple effect */
.quick-reply-btn {
  position: relative;
  overflow: hidden;
}

.quick-reply-btn::after {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(8, 145, 178, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.4s ease, height 0.4s ease;
}

.quick-reply-btn:active::after {
  width: 200px;
  height: 200px;
  transition: width 0s, height 0s;
}

/* Tab transition animations */
.tab-panel {
  animation: fadeSlideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes fadeSlideIn {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Enhanced message bubble animations */
.message {
  animation: messageSlideIn 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes messageSlideIn {
  from {
    opacity: 0;
    transform: translateX(-20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

.message.assistant {
  animation-name: messageSlideInRight;
}

@keyframes messageSlideInRight {
  from {
    opacity: 0;
    transform: translateX(20px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

/* Streaming cursor pulse */
.cursor {
  animation: cursorPulse 0.8s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes cursorPulse {
  0%, 100% {
    opacity: 1;
  }
  50% {
    opacity: 0.3;
  }
}

/* Status progress enhanced animation */
.status-progress {
  overflow: hidden;
}

.progress-bar {
  animation: progressSlide 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes progressSlide {
  0% {
    transform: translateX(-100%);
  }
  50% {
    transform: translateX(0%);
  }
  100% {
    transform: translateX(100%);
  }
}

/* Filter button selection animation */
.filter-btn.active,
.sort-btn.active {
  animation: buttonActivate 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes buttonActivate {
  0% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
  100% {
    transform: scale(1);
  }
}

/* Badge pulse animation */
.fab-badge {
  animation: badgePulse 2s cubic-bezier(0.4, 0, 0.2, 1) infinite;
}

@keyframes badgePulse {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.15);
  }
}

/* Operators badge entrance */
.operators-badge {
  animation: badgeSlideDown 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes badgeSlideDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

/* Match reason box enhanced */
.match-reason {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.match-card:hover .match-reason {
  background: linear-gradient(135deg, #ecfdf5 0%, #d1fae5 100%);
  transform: scale(1.02);
}

/* Avatar glow effect on hover */
.match-avatar {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.match-avatar::after {
  content: '';
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  border-radius: 50%;
  background: radial-gradient(circle, rgba(8, 145, 178, 0.4) 0%, transparent 70%);
  opacity: 0;
  transition: opacity 0.3s ease;
}

.match-card:hover .match-avatar::after {
  opacity: 1;
}

/* Loading skeleton shimmer enhanced */
@keyframes skeletonShimmer {
  0% {
    background-position: -200% 0;
  }
  100% {
    background-position: 200% 0;
  }
}

/* Input focus glow */
.input-box:focus {
  box-shadow: 0 0 0 3px rgba(8, 145, 178, 0.1), 0 4px 12px rgba(0, 0, 0, 0.08);
  border-color: #0891b2;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Send button enhanced interaction */
.send-btn {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.send-btn::before {
  content: '';
  position: absolute;
  top: 50%;
  left: 50%;
  width: 0;
  height: 0;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.3);
  transform: translate(-50%, -50%);
  transition: width 0.5s ease, height 0.5s ease;
}

.send-btn:hover::before {
  width: 120px;
  height: 120px;
}

.send-btn:hover {
  transform: scale(1.05) rotate(-5deg);
}

.send-btn:active {
  transform: scale(0.95) rotate(0deg);
}

/* Cart button badge animation */
.cart-button {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.cart-button:hover {
  transform: translateY(-2px);
}

.cart-button span {
  display: inline-block;
  animation: cartBadgeBounce 0.5s cubic-bezier(0.4, 0, 0.2, 1);
}

@keyframes cartBadgeBounce {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.2);
  }
}

/* Empty state animations */
.empty-state,
.welcome-state {
  animation: emptyStateFloat 3s ease-in-out infinite;
}

@keyframes emptyStateFloat {
  0%, 100% {
    transform: translateY(0);
  }
  50% {
    transform: translateY(-10px);
  }
}

.empty-icon,
.welcome-icon {
  animation: iconSpin 20s linear infinite;
}

@keyframes iconSpin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}

/* Starter chips hover effect */
.chip {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.chip::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.3), transparent);
  transition: left 0.5s ease;
}

.chip:hover::before {
  left: 100%;
}

.chip:hover {
  transform: translateY(-3px) scale(1.05);
  box-shadow: 0 8px 20px rgba(8, 145, 178, 0.2);
}

/* Service button enhanced states */
.service-btn {
  transition: all 0.25s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
}

.service-btn::after {
  content: '';
  position: absolute;
  bottom: 0;
  left: 50%;
  width: 0;
  height: 2px;
  background: linear-gradient(90deg, #0891b2, #0f766e);
  transform: translateX(-50%);
  transition: width 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.service-btn.active::after {
  width: 80%;
}

.service-btn:hover {
  transform: translateY(-2px);
}

/* Responsive micro-interactions */
@media (max-width: 768px) {
  /* Reduce animations on mobile for performance */
  .glass-card:hover {
    transform: translateY(-1px);
  }
  
  .match-card:hover {
    transform: translateY(-3px) scale(1.01);
  }
  
  /* Disable some decorative animations on mobile */
  .empty-state,
  .welcome-state {
    animation: none;
  }
  
  .empty-icon,
  .welcome-icon {
    animation: iconSpin 40s linear infinite; /* Slower spin */
  }
}

/* High contrast mode support */
@media (prefers-contrast: high) {
  .btn-add,
  .btn-view,
  .filter-btn,
  .sort-btn {
    border: 2px solid currentColor;
  }
  
  .fab {
    border: 2px solid white;
  }
}

/* Print styles */
@media print {
  .fab-container,
  .chat-input-area,
  .pull-refresh-indicator,
  .toast-container {
    display: none !important;
  }
  
  .planner-page-new {
    max-width: 100%;
  }
}

/* Focus visible for keyboard navigation */
button:focus-visible,
a:focus-visible,
input:focus-visible,
textarea:focus-visible {
  outline: 3px solid #0891b2;
  outline-offset: 2px;
  border-radius: 4px;
}

/* Selection styling */
::selection {
  background: rgba(8, 145, 178, 0.2);
  color: inherit;
}

::-moz-selection {
  background: rgba(8, 145, 178, 0.2);
  color: inherit;
}

/* Scrollbar styling (webkit only) */
.messages::-webkit-scrollbar {
  width: 8px;
}

.messages::-webkit-scrollbar-track {
  background: rgba(0, 0, 0, 0.05);
  border-radius: 4px;
}

.messages::-webkit-scrollbar-thumb {
  background: rgba(8, 145, 178, 0.3);
  border-radius: 4px;
  transition: background 0.3s ease;
}

.messages::-webkit-scrollbar-thumb:hover {
  background: rgba(8, 145, 178, 0.5);
}

/* END SPRINT 5 STYLES */

</style>
