<template>
  <div class="qb-page">

    <!-- Page header -->
    <div class="qb-hero">
      <div class="qb-hero-inner">
        <span class="eyebrow">Trip Quote Builder</span>
        <h1>Build your bucket, get custom quotes</h1>
        <p>Add destinations, drop custom pins, then publish — operators will respond with tailored offers.</p>
        <div class="hero-stats">
          <div class="hstat">
            <strong>{{ quoteStore.bucketCount }}</strong>
            <span>Locations</span>
          </div>
          <div class="hstat-div"></div>
          <div class="hstat">
            <strong>{{ quoteStore.quota.remaining }}</strong>
            <span>Quotes left</span>
          </div>
          <div class="hstat-div"></div>
          <div class="hstat">
            <strong>{{ quoteStore.pagination.total }}</strong>
            <span>Total requests</span>
          </div>
        </div>
        
        <!-- Quota Info Badge -->
        <div class="quota-info" :class="quotaStatusClass">
          <span class="quota-icon">{{ quotaIcon }}</span>
          <span class="quota-text">
            <strong>{{ quoteStore.quota.open_count }} of {{ quoteStore.quota.limit }}</strong> open quotes
            ({{ quoteStore.quota.tier_name }} member)
          </span>
          <button v-if="quoteStore.quota.tier === 'free'" class="btn-upgrade-mini" @click="showUpgradeModal = true">
            ⚡ Upgrade
          </button>
        </div>
      </div>
    </div>

    <div class="qb-container">
      <!-- Step Indicator -->
      <QuoteBuilderSteps
        :current-step="quoteStore.currentStep"
        :step1-completed="quoteStore.step1Completed"
        :step2-completed="quoteStore.step2Completed"
        @step-change="handleStepChange"
      />

      <!-- STEP 1: Location Selection -->
      <div id="location-selection" class="step-section">
        <div class="step-section-header">
          <div class="step-badge">Step 1</div>
          <h2 class="step-title">Select Your Destinations</h2>
          <p class="step-description">Search for places or drop custom pins to build your travel bucket</p>
        </div>

        <!-- Main 2-column layout for Step 1 -->
        <div class="qb-grid">

          <!-- LEFT: Search + manual pin -->
          <div class="qb-col">

            <!-- Search card -->
            <div class="qb-card">
              <div class="card-label">Search destinations</div>
              <h2 class="card-title">Find a place to add</h2>
              <p class="card-sub">Type any city, landmark, or beach — we'll show operator-featured and worldwide results.</p>

            <div class="search-wrap">
              <div class="search-bar">
                <svg class="search-ico" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
                <input
                  v-model="searchQuery"
                  type="text"
                  placeholder="Manali, Santorini, Angkor Wat…"
                  @keyup="handleSearchInput"
                  @keydown="handleKeyDown"
                  @keyup.enter="handleSearch"
                  @focus="showSuggestions = true"
                  @blur="setTimeout(() => { showSuggestions = false; highlightedIndex = -1 }, 200)"
                  aria-label="Search for locations"
                  aria-autocomplete="list"
                  :aria-activedescendant="highlightedIndex >= 0 ? `suggestion-${highlightedIndex}` : undefined"
                />
                <button class="btn-search" @click="handleSearch" :disabled="quoteStore.searching">
                  {{ quoteStore.searching ? '…' : 'Search' }}
                </button>
              </div>

              <!-- Autocomplete -->
              <div v-if="showSuggestions && searchQuery.length >= 2" class="suggestions" role="listbox">
                <div v-if="suggestedLocations.from_operators.length" class="sug-group">
                  <div class="sug-label"><span class="sug-badge op-badge">✈️ Featured</span></div>
                  <div
                    v-for="(r, idx) in suggestedLocations.from_operators.slice(0, 5)"
                    :key="r.id"
                    :id="`suggestion-${idx}`"
                    class="sug-item op-item"
                    :class="{ 
                      'is-highlighted': idx === highlightedIndex,
                      'is-added': isLocationInBucket(r)
                    }"
                    @click="selectSuggestion(r)"
                    @mouseenter="highlightedIndex = idx"
                    role="option"
                    :aria-selected="idx === highlightedIndex"
                  >
                    <div class="sug-content">
                      <div class="sug-name">{{ r.name }}</div>
                      <div class="sug-meta">{{ [r.state, r.country].filter(Boolean).join(', ') }} · {{ r.operator_name }}</div>
                    </div>
                    <div v-if="isLocationInBucket(r)" class="sug-added">✓ Added</div>
                  </div>
                </div>
                <div v-if="suggestedLocations.global.length" class="sug-group">
                  <div class="sug-label"><span class="sug-badge gl-badge">🌍 Worldwide</span></div>
                  <div
                    v-for="(r, idx) in suggestedLocations.global.slice(0, 5)"
                    :key="r.id"
                    :id="`suggestion-${suggestedLocations.from_operators.length + idx}`"
                    class="sug-item gl-item"
                    :class="{ 
                      'is-highlighted': (suggestedLocations.from_operators.length + idx) === highlightedIndex,
                      'is-added': isLocationInBucket(r)
                    }"
                    @click="selectSuggestion(r)"
                    @mouseenter="highlightedIndex = suggestedLocations.from_operators.length + idx"
                    role="option"
                    :aria-selected="(suggestedLocations.from_operators.length + idx) === highlightedIndex"
                  >
                    <div class="sug-content">
                      <div class="sug-name">{{ r.name.split(',')[0] }}</div>
                      <div class="sug-meta">{{ [r.state, r.country].filter(Boolean).join(', ') }}</div>
                    </div>
                    <div v-if="isLocationInBucket(r)" class="sug-added">✓ Added</div>
                  </div>
                </div>
                <div v-if="!suggestedLocations.from_operators.length && !suggestedLocations.global.length" class="sug-empty">
                  No results yet…
                </div>
              </div>
            </div>

            <div v-if="searchError" class="msg-error">
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
              <span>{{ searchError }}</span>
            </div>

            <!-- Loading skeleton -->
            <div v-if="quoteStore.searching" class="results-list">
              <div class="skeleton-item" v-for="n in 3" :key="'skeleton-' + n">
                <div class="skeleton-content">
                  <div class="skeleton-title"></div>
                  <div class="skeleton-text"></div>
                  <div class="skeleton-text skeleton-text-short"></div>
                </div>
                <div class="skeleton-button"></div>
              </div>
            </div>

            <!-- Search results list -->
            <div v-if="!quoteStore.searching && (searchResults.from_operators?.length || searchResults.global?.length)" class="results-list">

              <div v-if="searchResults.from_operators?.length">
                <div class="res-group-label"><span class="sug-badge op-badge">✈️ Operator featured</span></div>
                <div v-for="r in searchResults.from_operators" :key="r.id" class="res-item op-res">
                  <div class="res-left">
                    <div class="res-name">{{ r.name }}</div>
                    <div class="res-meta">{{ [r.state, r.country].filter(Boolean).join(' · ') }}</div>
                    <div class="res-op">by {{ r.operator_name }}</div>
                    <div v-if="r.sub_locations?.length" class="res-subs">Includes: {{ r.sub_locations.join(', ') }}</div>
                  </div>
                  <button class="btn-add" @click="addSearchResult(r)">+ Add</button>
                </div>
              </div>

              <div v-if="searchResults.global?.length" class="mt-12">
                <div class="res-group-label"><span class="sug-badge gl-badge">🌍 Worldwide</span></div>
                <div v-for="r in searchResults.global" :key="r.id" class="res-item gl-res">
                  <div class="res-left">
                    <div class="res-name">{{ r.name }}</div>
                    <div class="res-meta">{{ [r.state, r.country].filter(Boolean).join(' · ') }}</div>
                    <div class="res-coords">{{ r.lat?.toFixed(4) }}, {{ r.lng?.toFixed(4) }}</div>
                  </div>
                  <button class="btn-add" @click="addSearchResult(r)">+ Add</button>
                </div>
              </div>

            </div>
          </div>

          <!-- Map Selector (Expandable) -->
          <div class="qb-card mt-14">
            <div class="card-label">Custom pin</div>
            <h2 class="card-title">Drop a pin manually</h2>
            <p class="card-sub">Open the interactive map to select exact coordinates and add custom locations.</p>

            <MapSelector
              :default-center="defaultCenter"
              @add-location="handleMapSelectorLocation"
            />
          </div>

          </div>
          <!-- END LEFT COLUMN -->

          <!-- RIGHT: Location Bucket -->
          <div class="qb-col">
            <LocationBucket
              :bucket="quoteStore.bucket"
              :last-added-id="quoteStore.lastAddedId"
              :allow-map-expand="true"
              @remove="handleRemoveLocation"
              @clear-all="handleClearAll"
              @undo="handleUndo"
              @reorder="handleReorder"
              @update-notes="handleUpdateNotes"
              @expand-map="expandMapView"
            />
          </div>

        </div><!-- /qb-grid -->
      </div><!-- /step-section -->

      <!-- STEP 2: Publish Quote -->
      <div id="publish-section" class="step-section">
        <div class="step-section-header">
          <div class="step-badge">Step 2</div>
          <h2 class="step-title">Publish Your Quote Request</h2>
          <p class="step-description">Fill in your travel details and get tailored offers from operators</p>
        </div>

          <!-- Publish section -->
        <div class="qb-card publish-card">
          <div class="publish-head">
            <div>
              <div class="card-label">Final step</div>
              <h2 class="card-title">Request quotes from operators</h2>
              <p class="card-sub">Fill in your travel details and operators will reply with tailored offers.</p>
            </div>
            <button
              class="btn-publish"
              @click="publishQuote"
              :disabled="quoteStore.loading || !quoteStore.step1Completed"
            >
              <svg v-if="!quoteStore.loading" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="22" y1="2" x2="11" y2="13"/><polygon points="22 2 15 22 11 13 2 9 22 2"/></svg>
              <svg v-else class="spinner" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle></svg>
              {{ quoteStore.loading ? 'Publishing…' : 'Get quotes' }}
            </button>
          </div>

          <div class="pub-form-grid">
            <div class="pub-field">
              <label><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="3" y="4" width="18" height="18" rx="2" ry="2"></rect><line x1="16" y1="2" x2="16" y2="6"></line><line x1="8" y1="2" x2="8" y2="6"></line><line x1="3" y1="10" x2="21" y2="10"></line></svg> Travel window</label>
              <VueDatePicker 
                v-model="dateRange"
                @update:model-value="handleDateRangeChange"
                range
                :min-date="new Date()"
                :enable-time-picker="false"
                placeholder="Select your travel dates"
                format="dd MMM yyyy"
                :auto-apply="true"
                class="custom-datepicker"
              />
              <p class="field-hint">Select start and end dates for your trip</p>
            </div>
            
            <div class="pub-field">
              <label><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg> Number of travelers *</label>
              <div class="stepper-input">
                <button 
                  type="button" 
                  @click="decrementTravelers" 
                  class="stepper-btn"
                  :disabled="(quoteStore.formDraft.travelers || 1) <= 1"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                </button>
                <input 
                  v-model.number="quoteStore.formDraft.travelers" 
                  @input="handleFormUpdate" 
                  type="number" 
                  min="1" 
                  max="50"
                  class="stepper-value"
                  readonly
                />
                <button 
                  type="button" 
                  @click="incrementTravelers" 
                  class="stepper-btn"
                  :disabled="(quoteStore.formDraft.travelers || 1) >= 50"
                >
                  <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
                </button>
              </div>
              <p class="field-hint">Adults and children combined</p>
            </div>
            
            <div class="pub-field">
              <label><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="12" y1="1" x2="12" y2="23"></line><path d="M17 5H9.5a3.5 3.5 0 0 0 0 7h5a3.5 3.5 0 0 1 0 7H6"></path></svg> Budget (optional)</label>
              <div class="budget-input-wrapper">
                <span class="budget-currency">$</span>
                <input 
                  v-model="budgetInput" 
                  @input="handleBudgetInput" 
                  @blur="formatBudget"
                  type="text" 
                  placeholder="2,500"
                  class="form-input budget-input"
                />
                <span class="budget-label">USD</span>
              </div>
              <p class="field-hint">Estimated budget per person</p>
            </div>
          </div>
          <div class="pub-field mt-12">
            <label><svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg> Notes to operators</label>
            <textarea 
              v-model="quoteStore.formDraft.notes" 
              @input="handleFormUpdate" 
              rows="4" 
              placeholder="Share your interests, special requirements, must-do experiences, dietary needs, accessibility requirements, or any other details that will help operators create the perfect itinerary for you..."
              class="form-textarea"
            ></textarea>
            <p class="field-hint">{{ (quoteStore.formDraft.notes || '').length }} characters</p>
          </div>

        <div class="itinerary-share mt-12">
          <div class="itinerary-share-head">
            <div>
                <label>🗓️ Attach saved itinerary (optional)</label>
                <p>Share a saved itinerary so operators understand your preferred route and pacing.</p>
              </div>
              <router-link to="/itineraries" class="btn-manage-itineraries">Manage itineraries</router-link>
            </div>
            <select v-model="quoteStore.formDraft.attached_itinerary_id" @change="handleFormUpdate" class="itinerary-select" :disabled="itineraryLoading">
              <option value="">No itinerary attached</option>
              <option v-for="item in savedItineraries" :key="item._id" :value="item._id">
                {{ item.title }} · {{ item.duration_days }} days
              </option>
            </select>
            <div v-if="selectedItinerary" class="itinerary-preview">
              <strong>{{ selectedItinerary.title }}</strong>
              <span>{{ selectedItinerary.primary_location?.area_name || 'Custom trip' }} · {{ selectedItinerary.duration_days }} days</span>
              <p>{{ selectedItinerary.summary || 'This itinerary will be snapshot into the quote request.' }}</p>
            </div>
          </div>

          <div v-if="successMessage" class="msg-success mt-12">
            <svg class="success-icon" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path><polyline points="22 4 12 14.01 9 11.01"></polyline></svg>
            <span>{{ successMessage }}</span>
          </div>
          <div v-if="quoteStore.error" class="msg-error mt-12">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
            <span>{{ quoteStore.error }}</span>
          </div>
        </div>
      </div><!-- /step-section -->

      <!-- My Requests -->
      <div v-if="quoteStore.recentQuotes.length > 0" class="qb-card mt-14">
        <div class="card-label">Sent requests</div>
        <div class="requests-header">
          <div>
            <h2 class="card-title">My quote requests</h2>
            <p class="card-sub">Track operator responses and open chats.</p>
          </div>
          <div v-if="quoteStore.pagination.total > 0" class="pagination-info">
            Showing {{ (quoteStore.pagination.page - 1) * quoteStore.pagination.page_size + 1 }}-{{ Math.min(quoteStore.pagination.page * quoteStore.pagination.page_size, quoteStore.pagination.total) }} of {{ quoteStore.pagination.total }}
          </div>
        </div>

        <div class="quotes-grid">
          <div v-for="quote in quoteStore.recentQuotes" :key="quote._id" class="quote-row">

            <div class="quote-top">
              <div class="quote-meta-left">
                <span class="qbadge" :class="quote.status === 'closed' ? 'closed' : 'open'">{{ quote.status }}</span>
                <span class="q-locs">{{ quote.locations.length }} location{{ quote.locations.length !== 1 ? 's' : '' }}</span>
              </div>
              <span class="q-date">{{ new Date(quote.created_at).toLocaleDateString() }}</span>
            </div>

            <ul class="q-loc-list">
              <li v-for="(loc, i) in quote.locations" :key="i">📍 {{ loc.name }} — {{ loc.state || 'N/A' }}, {{ loc.country || 'N/A' }}</li>
            </ul>

            <div class="q-details">
              <span v-if="quote.travel_window">📅 {{ quote.travel_window }}</span>
              <span v-if="quote.budget">💰 ${{ quote.budget }}</span>
              <span v-if="quote.travelers">👥 {{ quote.travelers }}</span>
            </div>

            <div v-if="quote.attached_itinerary_snapshot" class="q-itinerary">
              <strong>Attached itinerary:</strong>
              <span>{{ quote.attached_itinerary_snapshot.title }}</span>
            </div>

            <div v-if="quote.notes" class="q-note">{{ quote.notes }}</div>

            <div v-if="quote.responses?.length" class="q-responses">
              <div class="q-resp-label">Responses ({{ quote.responses.length }})</div>
              <div v-for="(resp, ri) in quote.responses" :key="ri" class="q-resp-item">
                <div class="q-resp-name">{{ resp.operator_name || 'Operator' }}</div>
                <div v-if="resp.amount" class="q-resp-amt">${{ resp.amount }}</div>
                <div v-if="resp.message" class="q-resp-msg">{{ resp.message }}</div>
                <div v-if="resp.proposed_itinerary_snapshot" class="q-resp-itinerary">
                  <strong>{{ resp.proposed_itinerary_snapshot.title }}</strong>
                  <span>
                    {{ resp.proposed_itinerary_snapshot.duration_days }} days ·
                    {{ resp.proposed_itinerary_snapshot.primary_location?.area_name || 'Custom route' }}
                  </span>
                  <p>{{ resp.proposed_itinerary_snapshot.summary || 'Operator shared an itinerary proposal for this quote.' }}</p>
                  <button
                    class="btn-save-proposal"
                    :disabled="savingProposalKey === `${quote._id}-${ri}`"
                    @click="saveProposalToItineraries(quote._id, ri)"
                  >
                    {{ savingProposalKey === `${quote._id}-${ri}` ? 'Saving…' : 'Save to my itineraries' }}
                  </button>
                </div>
              </div>
            </div>
            <div v-else class="q-no-resp">No responses yet — operators are reviewing your request.</div>

            <div class="q-actions">
              <button v-if="quote.status !== 'closed'" class="btn-remove-quote" @click="removeQuote(quote._id)">Remove request</button>
              <span v-else class="q-closed-tag">Closed</span>
            </div>
          </div>
        </div>
        
        <!-- Pagination Controls -->
        <div v-if="quoteStore.recentQuotes.length > 0" class="pagination-controls">
          <button 
            class="btn-pagination" 
            :disabled="quoteStore.pagination.page <= 1 || quoteStore.loading"
            @click="loadPreviousPage"
          >
            ← Previous
          </button>
          <span class="pagination-current">
            Page {{ quoteStore.pagination.page || 1 }} of {{ quoteStore.pagination.total_pages || 1 }}
          </span>
          <button 
            class="btn-pagination" 
            :disabled="!quoteStore.pagination.has_more || quoteStore.loading"
            @click="loadNextPage"
          >
            Next →
          </button>
        </div>
      </div>

    </div><!-- /qb-container -->
    
    <!-- Limit Reached Modal -->
    <div v-if="quoteStore.limitReached" class="modal-overlay" @click="closeLimitModal">
      <div class="modal-content limit-modal" @click.stop>
        <div class="modal-header">
          <div class="modal-icon">🚫</div>
          <h2>Quote Limit Reached</h2>
        </div>
        <div class="modal-body">
          <p class="limit-message">{{ quoteStore.limitErrorMessage }}</p>
          
          <div class="limit-stats">
            <div class="limit-stat">
              <span class="stat-label">Your Current Tier</span>
              <span class="stat-value">{{ quoteStore.quota.tier_name }}</span>
            </div>
            <div class="limit-stat">
              <span class="stat-label">Open Quotes</span>
              <span class="stat-value">{{ quoteStore.quota.open_count }} / {{ quoteStore.quota.limit }}</span>
            </div>
          </div>
          
          <div class="upgrade-options">
            <h3>Get More Quotes</h3>
            <div class="upgrade-tiers">
              <div class="upgrade-tier" v-if="quoteStore.quota.tier === 'free'">
                <div class="tier-badge premium">⭐ Premium</div>
                <div class="tier-limit">Up to 20 open quotes</div>
                <button class="btn-upgrade" @click="handleUpgrade('premium')">
                  Upgrade to Premium
                </button>
              </div>
              <div class="upgrade-tier" v-if="quoteStore.quota.tier === 'free' || quoteStore.quota.tier === 'premium'">
                <div class="tier-badge enterprise">💎 Enterprise</div>
                <div class="tier-limit">Up to 100 open quotes</div>
                <button class="btn-upgrade" @click="handleUpgrade('enterprise')">
                  Upgrade to Enterprise
                </button>
              </div>
            </div>
          </div>
          
          <div class="modal-alternative">
            <p>Or you can close some existing quote requests to free up space.</p>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-close" @click="closeLimitModal">Close</button>
        </div>
      </div>
    </div>
    
    <!-- Upgrade Modal -->
    <div v-if="showUpgradeModal" class="modal-overlay" @click="showUpgradeModal = false">
      <div class="modal-content upgrade-modal" @click.stop>
        <div class="modal-header">
          <div class="modal-icon">⚡</div>
          <h2>Upgrade Your Membership</h2>
        </div>
        <div class="modal-body">
          <p>Get more quote requests and unlock additional features.</p>
          
          <div class="membership-tiers">
            <div class="tier-card current" v-if="quoteStore.quota.tier === 'free'">
              <div class="tier-header">
                <span class="tier-icon">🆓</span>
                <h3>Free</h3>
                <span class="tier-badge-current">Current</span>
              </div>
              <div class="tier-limit-big">{{ quoteStore.quota.limit }} open quotes</div>
            </div>
            
            <div class="tier-card" :class="{ current: quoteStore.quota.tier === 'premium' }">
              <div class="tier-header">
                <span class="tier-icon">⭐</span>
                <h3>Premium</h3>
                <span v-if="quoteStore.quota.tier === 'premium'" class="tier-badge-current">Current</span>
              </div>
              <div class="tier-limit-big">20 open quotes</div>
              <div class="tier-features">
                <div>✓ Priority support</div>
                <div>✓ Advanced search</div>
                <div>✓ Exclusive deals</div>
              </div>
              <button v-if="quoteStore.quota.tier !== 'premium'" class="btn-select-tier" @click="handleUpgrade('premium')">
                Upgrade to Premium
              </button>
            </div>
            
            <div class="tier-card" :class="{ current: quoteStore.quota.tier === 'enterprise' }">
              <div class="tier-header">
                <span class="tier-icon">💎</span>
                <h3>Enterprise</h3>
                <span v-if="quoteStore.quota.tier === 'enterprise'" class="tier-badge-current">Current</span>
              </div>
              <div class="tier-limit-big">100 open quotes</div>
              <div class="tier-features">
                <div>✓ All Premium features</div>
                <div>✓ Dedicated account manager</div>
                <div>✓ Custom SLA</div>
              </div>
              <button v-if="quoteStore.quota.tier !== 'enterprise'" class="btn-select-tier" @click="handleUpgrade('enterprise')">
                Upgrade to Enterprise
              </button>
            </div>
          </div>
        </div>
        <div class="modal-footer">
          <button class="btn-close" @click="showUpgradeModal = false">Maybe Later</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import QuoteBuilderSteps from '../components/QuoteBuilderSteps.vue'
import LocationBucket from '../components/LocationBucket.vue'
import MapSelector from '../components/MapSelector.vue'
import { VueDatePicker } from '@vuepic/vue-datepicker'
import '@vuepic/vue-datepicker/dist/main.css'
import api from '../services/api'
import { useQuoteStore } from '../stores/quotes'

const quoteStore = useQuoteStore()
const searchQuery = ref('')
const searchResults = ref({ global: [], from_operators: [] })
const suggestedLocations = ref({ global: [], from_operators: [] })
const showSuggestions = ref(false)
const searchError = ref(null)
const searchTimeout = ref(null)
const successMessage = ref('')
const savingProposalKey = ref('')
const savedItineraries = ref([])
const itineraryLoading = ref(false)
const highlightedIndex = ref(-1) // For keyboard navigation in autocomplete
const dateRange = ref(null) // For date range picker

const defaultCenter = computed(() => ({ lat: 20.5937, lng: 78.9629 }))
const selectedItinerary = computed(() => 
  savedItineraries.value.find(item => item._id === quoteStore.formDraft.attached_itinerary_id) || null
)

/**
 * Flattened list of all suggestions for keyboard navigation
 * @returns {Array} All suggestions in order (operators first, then global)
 */
const flattenedSuggestions = computed(() => {
  return [
    ...suggestedLocations.value.from_operators.slice(0, 5),
    ...suggestedLocations.value.global.slice(0, 5)
  ]
})

/**
 * Check if a location is already in the bucket
 * @param {Object} location - Location to check
 * @returns {boolean} True if already added
 */
const isLocationInBucket = (location) => {
  return quoteStore.bucket.some(
    (loc) => loc.name.toLowerCase() === location.name.toLowerCase() &&
      loc.coordinates?.latitude === location.lat &&
      loc.coordinates?.longitude === location.lng
  )
}

// New refs for quota and upgrade modals
const showUpgradeModal = ref(false)

/**
 * Computed property for quota status class
 */
const quotaStatusClass = computed(() => {
  const remaining = quoteStore.quota.remaining
  const limit = quoteStore.quota.limit
  const percentage = (remaining / limit) * 100
  
  if (percentage <= 0) return 'quota-critical'
  if (percentage <= 20) return 'quota-warning'
  return 'quota-ok'
})

/**
 * Computed property for quota icon
 */
const quotaIcon = computed(() => {
  const remaining = quoteStore.quota.remaining
  const limit = quoteStore.quota.limit
  const percentage = (remaining / limit) * 100
  
  if (percentage <= 0) return '🔴'
  if (percentage <= 20) return '⚠️'
  return '✅'
})

/**
 * Close limit reached modal
 */
const closeLimitModal = () => {
  quoteStore.clearLimitError()
}

/**
 * Handle upgrade button click
 */
const handleUpgrade = (tier) => {
  console.log(`Upgrade to ${tier} tier`)
  // TODO: Implement actual upgrade flow (redirect to pricing/payment page)
  alert(`Upgrade to ${tier} tier - This would redirect to the payment page.`)
  showUpgradeModal.value = false
  quoteStore.clearLimitError()
}

/**
 * Load previous page of quotes
 */
const loadPreviousPage = async () => {
  await quoteStore.loadPreviousPage()
}

/**
 * Load next page of quotes
 */
const loadNextPage = async () => {
  await quoteStore.loadNextPage()
}

onMounted(async () => {
  quoteStore.hydrate()
  await Promise.all([quoteStore.loadMyQuotes(), loadSavedItineraries()])
  
  // Initialize budget display
  if (quoteStore.formDraft.budget) {
    budgetInput.value = formatNumberWithCommas(quoteStore.formDraft.budget.toString())
  }
  
  // Ensure travelers has a default value
  if (!quoteStore.formDraft.travelers) {
    quoteStore.formDraft.travelers = 1
  }
  
  // Set to step 2 if step 1 is already complete
  if (quoteStore.step1Completed && quoteStore.currentStep === 1) {
    quoteStore.setStep(1) // Stay on step 1 by default
  }
})

/**
 * Handle step change from QuoteBuilderSteps component
 * @param {number} step - New step number
 */
const handleStepChange = (step) => {
  quoteStore.setStep(step)
}

/**
 * Handle form updates (auto-save draft)
 */
const handleFormUpdate = () => {
  quoteStore.persist()
}

/**
 * Increment travelers count
 */
const incrementTravelers = () => {
  const current = quoteStore.formDraft.travelers || 1
  if (current < 50) {
    quoteStore.formDraft.travelers = current + 1
    handleFormUpdate()
  }
}

/**
 * Decrement travelers count
 */
const decrementTravelers = () => {
  const current = quoteStore.formDraft.travelers || 1
  if (current > 1) {
    quoteStore.formDraft.travelers = current - 1
    handleFormUpdate()
  }
}

/**
 * Handle date range change
 */
const handleDateRangeChange = (value) => {
  dateRange.value = value
  if (value && value.length === 2) {
    // Format dates as "DD Mon - DD Mon YYYY" (e.g., "15 Mar - 22 Mar 2026")
    const startDate = new Date(value[0])
    const endDate = new Date(value[1])
    const formatDate = (date) => {
      const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
      return `${date.getDate()} ${months[date.getMonth()]}`
    }
    const startFormatted = formatDate(startDate)
    const endFormatted = formatDate(endDate)
    const year = endDate.getFullYear()
    quoteStore.formDraft.travel_window = `${startFormatted} - ${endFormatted} ${year}`
  } else if (!value) {
    quoteStore.formDraft.travel_window = ''
  }
  handleFormUpdate()
}

/**
 * Budget input with formatting
 */
const budgetInput = ref('')

/**
 * Handle budget input (remove non-numeric chars except comma)
 */
const handleBudgetInput = (e) => {
  // Remove non-numeric characters except comma
  let value = e.target.value.replace(/[^0-9,]/g, '')
  
  // Remove existing commas for processing
  let numericValue = value.replace(/,/g, '')
  
  // Update the raw number in store
  quoteStore.formDraft.budget = numericValue ? parseInt(numericValue) : null
  
  // Update display value with commas
  budgetInput.value = numericValue ? formatNumberWithCommas(numericValue) : ''
  
  handleFormUpdate()
}

/**
 * Format budget on blur
 */
const formatBudget = () => {
  if (quoteStore.formDraft.budget) {
    budgetInput.value = formatNumberWithCommas(quoteStore.formDraft.budget.toString())
  }
}

/**
 * Format number with commas
 */
const formatNumberWithCommas = (num) => {
  return num.replace(/\B(?=(\d{3})+(?!\d))/g, ',')
}

/**
 * Handle location removal from bucket
 * @param {number} index - Index to remove
 */
const handleRemoveLocation = (index) => {
  quoteStore.removeLocation(index)
}

/**
 * Handle undo last removal
 */
const handleUndo = () => {
  quoteStore.undoRemove()
}

/**
 * Handle bucket reorder
 * @param {number} oldIndex - Original index
 * @param {number} newIndex - New index
 */
const handleReorder = (oldIndex, newIndex) => {
  quoteStore.reorderBucket(oldIndex, newIndex)
}

/**
 * Handle notes update
 * @param {number} index - Location index
 * @param {string} notes - Updated notes
 */
const handleUpdateNotes = (index, notes) => {
  if (quoteStore.bucket[index]) {
    quoteStore.bucket[index].notes = notes
    quoteStore.persist()
  }
}

/**
 * Handle clear all locations
 */
const handleClearAll = () => {
  quoteStore.clearBucket()
}

/**
 * Expand map view (placeholder for future modal)
 */
const expandMapView = () => {
  // TODO: Implement full-screen map modal in future phase
  console.log('Expand map view - to be implemented in Phase 2')
}

/**
 * Handle keyboard navigation in autocomplete
 * @param {KeyboardEvent} event - Keyboard event
 */
const handleKeyDown = (event) => {
  if (!showSuggestions.value || flattenedSuggestions.value.length === 0) {
    return
  }

  switch (event.key) {
    case 'ArrowDown':
      event.preventDefault()
      highlightedIndex.value = (highlightedIndex.value + 1) % flattenedSuggestions.value.length
      break
    
    case 'ArrowUp':
      event.preventDefault()
      highlightedIndex.value = highlightedIndex.value <= 0
        ? flattenedSuggestions.value.length - 1
        : highlightedIndex.value - 1
      break
    
    case 'Enter':
      event.preventDefault()
      if (highlightedIndex.value >= 0 && highlightedIndex.value < flattenedSuggestions.value.length) {
        selectSuggestion(flattenedSuggestions.value[highlightedIndex.value])
      }
      break
    
    case 'Escape':
      event.preventDefault()
      showSuggestions.value = false
      highlightedIndex.value = -1
      break
  }
}

const loadSavedItineraries = async () => {
  itineraryLoading.value = true
  try {
    const res = await api.get('/itineraries/my')
    savedItineraries.value = (res.data.itineraries || []).filter(item => item.shareable_to_quote !== false)
  } catch (err) {
    console.error('Failed to load saved itineraries', err)
  } finally {
    itineraryLoading.value = false
  }
}

const handleSearch = async () => {
  searchError.value = null
  searchResults.value = { global: [], from_operators: [] }
  const results = await quoteStore.searchPlaces(searchQuery.value)
  searchResults.value = results
  
  const totalResults = (results.global?.length || 0) + (results.from_operators?.length || 0)
  if (totalResults === 0) {
    searchError.value = 'No places found. Try refining your query.'
  }
  showSuggestions.value = false
}

const handleSearchInput = async () => {
  searchError.value = null
  highlightedIndex.value = -1 // Reset keyboard navigation
  
  // Clear previous timeout
  if (searchTimeout.value) {
    clearTimeout(searchTimeout.value)
  }
  
  // Show suggestions if query is long enough
  if (searchQuery.value.length >= 2) {
    showSuggestions.value = true
    
    // Debounced search for suggestions
    searchTimeout.value = setTimeout(async () => {
      const results = await quoteStore.searchPlaces(searchQuery.value)
      suggestedLocations.value = results
      highlightedIndex.value = -1 // Reset after new results
    }, 300)
  } else {
    showSuggestions.value = false
  }
}

const selectSuggestion = async (result) => {
  addSearchResult(result)
  searchQuery.value = ''
  showSuggestions.value = false
  suggestedLocations.value = { global: [], from_operators: [] }
  highlightedIndex.value = -1 // Reset keyboard navigation
}

const addSearchResult = (result) => {
  quoteStore.addLocation({
    name: result.name,
    state: result.state,
    country: result.country,
    coordinates: { latitude: result.lat, longitude: result.lng },
    type: result.type || 'global_location'
  }, { animate: true })
}

/**
 * Handle location added from MapSelector
 * @param {Object} location - Location data from MapSelector
 */
const handleMapSelectorLocation = (location) => {
  console.log('QuoteBuilder received location from MapSelector:', location);
  quoteStore.addLocation(location, { animate: true });
  console.log('Location added to store');
}

const publishQuote = async () => {
  successMessage.value = ''
  quoteStore.error = ''
  
  // Validate step 1
  if (!quoteStore.step1Completed) {
    quoteStore.error = '⚠️ Please add at least one location before publishing.'
    // Scroll to step 1
    document.getElementById('location-selection')?.scrollIntoView({ behavior: 'smooth' })
    return
  }
  
  // Validate required fields
  if (!quoteStore.formDraft.travelers || quoteStore.formDraft.travelers < 1) {
    quoteStore.error = '⚠️ Please specify the number of travelers.'
    return
  }
  
  try {
    await quoteStore.publishQuote({
      travel_window: quoteStore.formDraft.travel_window,
      travelers: quoteStore.formDraft.travelers || null,
      budget: quoteStore.formDraft.budget ? Number(quoteStore.formDraft.budget) : null,
      notes: quoteStore.formDraft.notes,
      attached_itinerary_id: quoteStore.formDraft.attached_itinerary_id || null
    })
    
    // Show success with details
    const locationCount = quoteStore.bucket.length
    successMessage.value = `🎉 Quote request published successfully! Your request for ${locationCount} location${locationCount > 1 ? 's' : ''} with ${quoteStore.formDraft.travelers} traveler${quoteStore.formDraft.travelers > 1 ? 's' : ''} has been sent to operators. You'll receive responses soon!`
    
    // Clear the form after success
    setTimeout(() => {
      // Auto-navigate back to step 1 for next quote
      quoteStore.setStep(1)
      
      // Scroll to top
      window.scrollTo({ top: 0, behavior: 'smooth' })
      
      // Clear success message after scrolling
      setTimeout(() => {
        successMessage.value = ''
      }, 3000)
    }, 2000)
  } catch (err) {
    console.error(err)
    // Error message is set by the store
  }
}

const removeQuote = async (quoteId) => {
  if (confirm('Are you sure you want to remove this quote request?')) {
    try {
      await api.post(`/quotes/${quoteId}/close`)
      // Reload quotes after deletion
      await quoteStore.loadMyQuotes()
      successMessage.value = 'Quote request removed successfully.'
    } catch (err) {
      console.error('Failed to remove quote:', err)
      alert('Failed to remove quote request. Please try again.')
    }
  }
}

const saveProposalToItineraries = async (quoteId, responseIndex) => {
  savingProposalKey.value = `${quoteId}-${responseIndex}`
  try {
    await api.post(`/quotes/${quoteId}/responses/${responseIndex}/save-itinerary`)
    successMessage.value = 'Itinerary saved to My Itineraries.'
    await loadSavedItineraries()
  } catch (err) {
    console.error('Failed to save proposed itinerary', err)
    quoteStore.error = err.response?.data?.detail || 'Failed to save itinerary proposal'
  } finally {
    savingProposalKey.value = ''
  }
}
</script>

<style scoped>
/* ── Page ────────────────────────────────────────────────────────────────── */
.qb-page {
  min-height: 100vh;
  background: #f0f4f8;
  padding-bottom: 5rem;
}

/* ── Hero ────────────────────────────────────────────────────────────────── */
.qb-hero {
  background: linear-gradient(135deg, #0f172a 0%, #1a2d4a 55%, #0c4a6e 100%);
  padding: 4rem 2rem 6.5rem;
  position: relative;
  overflow: hidden;
}

.qb-hero::before {
  content: '';
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 15% 60%, rgba(56,189,248,0.09), transparent 55%),
    radial-gradient(ellipse at 85% 30%, rgba(99,102,241,0.09), transparent 50%);
  pointer-events: none;
}

.qb-hero-inner {
  position: relative;
  z-index: 1;
  max-width: 760px;
  margin: 0 auto;
  text-align: center;
}

.eyebrow {
  display: inline-block;
  background: rgba(56,189,248,0.15);
  color: #7dd3fc;
  border: 1px solid rgba(56,189,248,0.25);
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.3rem 1rem;
  margin-bottom: 1rem;
}

.qb-hero-inner h1 {
  font-size: 2.5rem;
  font-weight: 800;
  color: #fff;
  line-height: 1.15;
  margin: 0 0 0.8rem;
}

.qb-hero-inner p {
  color: rgba(255,255,255,0.6);
  font-size: 1rem;
  margin: 0 0 1.8rem;
}

.hero-stats {
  display: inline-flex;
  align-items: center;
  gap: 1.2rem;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 16px;
  padding: 0.75rem 1.8rem;
}

.hstat {
  text-align: center;
}

.hstat strong {
  display: block;
  font-size: 1.6rem;
  font-weight: 800;
  color: #fff;
  line-height: 1;
}

.hstat span {
  font-size: 0.75rem;
  color: rgba(255,255,255,0.55);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.hstat-div {
  width: 1px;
  height: 36px;
  background: rgba(255,255,255,0.15);
}

/* ── Container ───────────────────────────────────────────────────────────── */
.qb-container {
  max-width: 1200px;
  margin: -3.5rem auto 0;
  padding: 0 1.5rem;
  position: relative;
  z-index: 10;
}

/* ── Step Sections ───────────────────────────────────────────────────────── */
.step-section {
  margin-bottom: 2.5rem;
}

.step-section-header {
  text-align: center;
  margin-bottom: 2rem;
}

.step-badge {
  display: inline-block;
  background: linear-gradient(135deg, #06b6d4 0%, #14b8a6 100%);
  color: white;
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  padding: 0.4rem 1rem;
  border-radius: 999px;
  margin-bottom: 0.75rem;
}

.step-title {
  font-size: 1.75rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0 0 0.5rem;
}

.step-description {
  font-size: 1rem;
  color: #64748b;
  margin: 0;
  max-width: 600px;
  margin-left: auto;
  margin-right: auto;
}

/* ── Grid ───────────────────────────────────────────────────────────────── */

/* ── Cards ───────────────────────────────────────────────────────────────── */
.qb-card {
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(15,23,42,0.09);
  border: 1px solid #f1f5f9;
  padding: 1.8rem;
}

.mt-14 { margin-top: 1.4rem; }
.mt-12 { margin-top: 1.2rem; }
.mt-8  { margin-top: 0.8rem; }

.card-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #94a3b8;
  margin-bottom: 0.35rem;
}

.card-title {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.35rem;
}

.card-sub {
  font-size: 0.875rem;
  color: #64748b;
  margin: 0 0 1.2rem;
  line-height: 1.5;
}

/* ── 2-col grid ──────────────────────────────────────────────────────────── */
.qb-grid {
  display: grid;
  grid-template-columns: 1.1fr 0.9fr;
  gap: 1.4rem;
  margin-bottom: 1.4rem;
}

.qb-col {
  display: flex;
  flex-direction: column;
}

/* ── Search bar ──────────────────────────────────────────────────────────── */
.search-wrap { position: relative; }

.search-bar {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  background: #f8fafc;
  border: 1.5px solid #e2e8f0;
  border-radius: 12px;
  padding: 0.5rem 0.5rem 0.5rem 1rem;
}

.search-ico {
  width: 16px;
  height: 16px;
  color: #94a3b8;
  flex-shrink: 0;
}

.search-bar input {
  flex: 1;
  border: none;
  background: transparent;
  font-size: 0.9rem;
  color: #0f172a;
  outline: none;
  font-family: inherit;
}

.search-bar input::placeholder { color: #cbd5e1; }

.btn-search {
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: #fff;
  border: none;
  border-radius: 9px;
  font-size: 0.85rem;
  font-weight: 700;
  padding: 0.55rem 1.2rem;
  cursor: pointer;
  white-space: nowrap;
  transition: all 0.2s;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.btn-search:disabled { opacity: 0.6; cursor: not-allowed; }
.btn-search:not(:disabled):hover { 
  opacity: 0.88;
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.3);
}

.btn-search:not(:disabled):active {
  transform: translateY(0);
  box-shadow: none;
}

/* Autocomplete */
.suggestions {
  position: absolute;
  top: calc(100% + 6px);
  left: 0;
  right: 0;
  background: #fff;
  border: 1.5px solid #e2e8f0;
  border-radius: 14px;
  box-shadow: 0 16px 40px rgba(15,23,42,0.12);
  z-index: 200;
  overflow: hidden;
}

.sug-group { padding: 0.6rem 0; border-bottom: 1px solid #f1f5f9; }
.sug-group:last-child { border-bottom: none; }

.sug-label { padding: 0.4rem 1rem 0.2rem; }

.sug-badge {
  font-size: 0.7rem;
  font-weight: 700;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
}

.op-badge { background: #faf5ff; color: #7c3aed; border: 1px solid #ede9fe; }
.gl-badge { background: #eff6ff; color: #1d4ed8; border: 1px solid #bfdbfe; }

.sug-item {
  padding: 0.65rem 1rem;
  cursor: pointer;
  transition: background 0.15s, border-color 0.15s;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 0.75rem;
}

.sug-item:hover { background: #f8fafc; }
.sug-item.is-highlighted {
  background: linear-gradient(135deg, #ecfeff 0%, #e0f2fe 100%);
  border-left-color: #06b6d4 !important;
}

.sug-item.is-added {
  opacity: 0.6;
  cursor: default;
}

.sug-item.is-added:hover {
  background: transparent;
}

.op-item { border-left: 3px solid #8b5cf6; }
.gl-item { border-left: 3px solid #0ea5e9; }

.sug-content {
  flex: 1;
  min-width: 0;
}

.sug-name { font-size: 0.88rem; font-weight: 600; color: #0f172a; }
.sug-meta { font-size: 0.78rem; color: #94a3b8; margin-top: 0.1rem; }

.sug-added {
  font-size: 0.75rem;
  font-weight: 700;
  color: #10b981;
  white-space: nowrap;
}

.sug-empty { padding: 1rem; text-align: center; color: #94a3b8; font-size: 0.85rem; }

/* ── Results list ────────────────────────────────────────────────────────── */
.results-list { margin-top: 1.2rem; display: flex; flex-direction: column; gap: 0.7rem; }

.res-group-label { margin-bottom: 0.5rem; }

/* Skeleton Loader */
.skeleton-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  background: #fafafa;
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  padding: 0.9rem 1rem;
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.skeleton-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.skeleton-title {
  height: 18px;
  width: 60%;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 4px;
}

.skeleton-text {
  height: 14px;
  width: 80%;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 4px;
}

.skeleton-text-short {
  width: 40%;
}

.skeleton-button {
  height: 32px;
  width: 80px;
  background: linear-gradient(90deg, #e2e8f0 25%, #f1f5f9 50%, #e2e8f0 75%);
  background-size: 200% 100%;
  animation: skeleton-shimmer 1.5s ease-in-out infinite;
  border-radius: 8px;
  flex-shrink: 0;
}

@keyframes skeleton-shimmer {
  0% { background-position: 200% 0; }
  100% { background-position: -200% 0; }
}

.res-item {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  background: #fafafa;
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  padding: 0.9rem 1rem;
  transition: box-shadow 0.2s, transform 0.15s;
}

.res-item:hover { box-shadow: 0 4px 16px rgba(15,23,42,0.08); transform: translateY(-1px); }
.op-res { border-left: 3px solid #8b5cf6; }
.gl-res { border-left: 3px solid #0ea5e9; }

.res-name { font-size: 0.95rem; font-weight: 700; color: #0f172a; }
.res-meta { font-size: 0.8rem; color: #64748b; margin-top: 0.15rem; }
.res-op   { font-size: 0.78rem; color: #7c3aed; font-weight: 600; margin-top: 0.15rem; }
.res-subs { font-size: 0.75rem; color: #94a3b8; font-style: italic; margin-top: 0.1rem; }
.res-coords { font-size: 0.75rem; color: #94a3b8; margin-top: 0.1rem; }

.btn-add {
  border: 1.5px solid #0ea5e9;
  background: #eff9ff;
  color: #0369a1;
  font-size: 0.8rem;
  font-weight: 700;
  padding: 0.4rem 0.85rem;
  border-radius: 8px;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.18s;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.btn-add:hover { 
  background: #0ea5e9; 
  color: #fff; 
  border-color: #0ea5e9;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(14, 165, 233, 0.3);
}

.btn-add:active {
  transform: translateY(0);
  box-shadow: none;
}

/* ── Bucket card ─────────────────────────────────────────────────────────── */
.bucket-card { flex: 1; }

.bucket-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
}

.btn-clear {
  border: 1px solid #fecaca;
  background: #fef2f2;
  color: #b91c1c;
  font-size: 0.78rem;
  font-weight: 700;
  padding: 0.35rem 0.8rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.18s;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.btn-clear:hover { 
  background: #dc2626; 
  color: #fff; 
  border-color: #dc2626;
  transform: translateY(-1px);
}

.btn-clear:active {
  transform: translateY(0);
}

.bucket-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 2rem 1rem;
  color: #94a3b8;
  font-size: 0.9rem;
  text-align: center;
}

.bucket-empty span { font-size: 2rem; }

.bucket-items { margin-top: 1rem; display: flex; flex-direction: column; gap: 0.65rem; }

.bucket-row {
  display: flex;
  align-items: flex-start;
  gap: 0.8rem;
  background: #f8fafc;
  border: 1px solid #f1f5f9;
  border-radius: 12px;
  padding: 0.8rem 0.9rem;
}

.bucket-row-left { display: flex; gap: 0.7rem; flex: 1; min-width: 0; }

.bucket-num {
  width: 24px;
  height: 24px;
  background: #0f172a;
  color: #fff;
  border-radius: 6px;
  font-size: 0.72rem;
  font-weight: 800;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  margin-top: 1px;
}

.bucket-info { flex: 1; min-width: 0; }
.bucket-name { font-size: 0.9rem; font-weight: 700; color: #0f172a; }
.bucket-loc  { font-size: 0.78rem; color: #64748b; margin-top: 0.1rem; }

.bucket-note {
  width: 100%;
  margin-top: 0.5rem;
  border: 1px solid #e2e8f0;
  border-radius: 7px;
  padding: 0.4rem 0.65rem;
  font-size: 0.8rem;
  font-family: inherit;
  color: #475569;
  background: #fff;
  outline: none;
}

.bucket-note:focus { border-color: #0ea5e9; }

.btn-remove {
  background: none;
  border: 1px solid #e2e8f0;
  color: #94a3b8;
  width: 28px;
  height: 28px;
  border-radius: 7px;
  cursor: pointer;
  font-size: 0.8rem;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  transition: all 0.18s;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.btn-remove:hover { 
  background: #fef2f2; 
  border-color: #fecaca; 
  color: #dc2626;
  transform: scale(1.1);
}

.btn-remove:active {
  transform: scale(0.95);
}

/* ── Publish card ────────────────────────────────────────────────────────── */
.publish-card { margin-bottom: 1.4rem; }

.publish-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1.5rem;
  margin-bottom: 1.5rem;
  flex-wrap: wrap;
}

.btn-publish {
  display: inline-flex;
  align-items: center;
  gap: 0.5rem;
  background: linear-gradient(135deg, #10b981, #059669);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 0.9rem;
  font-weight: 700;
  padding: 0.75rem 1.5rem;
  cursor: pointer;
  white-space: nowrap;
  flex-shrink: 0;
  transition: all 0.2s;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.btn-publish:disabled { opacity: 0.55; cursor: not-allowed; }
.btn-publish:not(:disabled):hover { 
  opacity: 0.9; 
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(16, 185, 129, 0.3);
}

.btn-publish:not(:disabled):active {
  transform: translateY(0);
  box-shadow: none;
}

.btn-publish .spinner {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.pub-form-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
}

.pub-field {
  display: flex;
  flex-direction: column;
  gap: 0.4rem;
}

.pub-field label {
  font-size: 0.82rem;
  font-weight: 700;
  color: #475569;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.pub-field label svg {
  color: #06b6d4;
  flex-shrink: 0;
}

.pub-field input,
.pub-field textarea,
.form-input,
.form-textarea {
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
  font-family: inherit;
  color: #0f172a;
  outline: none;
  transition: all 0.2s;
  resize: vertical;
}

.pub-field input:focus,
.pub-field textarea:focus,
.form-input:focus,
.form-textarea:focus { 
  border-color: #06b6d4; 
  background: #fff;
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
  transform: translateY(-1px);
}

.field-hint {
  font-size: 0.8rem;
  color: #94a3b8;
  margin: 0;
}

/* Traveler Stepper */
.stepper-input {
  display: flex;
  align-items: center;
  gap: 0;
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.25rem;
  transition: all 0.2s;
}

.stepper-input:focus-within {
  border-color: #06b6d4;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
}

.stepper-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 36px;
  height: 36px;
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.2s;
  color: #64748b;
  user-select: none;
  -webkit-tap-highlight-color: transparent;
}

.stepper-btn:hover:not(:disabled) {
  background: #06b6d4;
  border-color: #06b6d4;
  color: white;
  transform: scale(1.05);
}

.stepper-btn:active:not(:disabled) {
  transform: scale(0.95);
}

.stepper-btn:disabled {
  opacity: 0.4;
  cursor: not-allowed;
}

.stepper-value {
  flex: 1;
  text-align: center;
  font-size: 1.1rem;
  font-weight: 700;
  color: #0f172a;
  background: transparent;
  border: none;
  outline: none;
  padding: 0.5rem;
  min-width: 60px;
}

/* Budget Input */
.budget-input-wrapper {
  position: relative;
  display: flex;
  align-items: center;
}

.budget-currency {
  position: absolute;
  left: 1rem;
  font-size: 1rem;
  font-weight: 700;
  color: #06b6d4;
  pointer-events: none;
}

.budget-input {
  padding-left: 2.5rem !important;
  padding-right: 4rem !important;
  font-weight: 600;
}

.budget-label {
  position: absolute;
  right: 1rem;
  font-size: 0.85rem;
  font-weight: 600;
  color: #94a3b8;
  pointer-events: none;
}

/* Date Range Picker Customization */
.custom-datepicker {
  --dp-font-family: inherit;
  --dp-border-radius: 10px;
  --dp-input-padding: 0.75rem 1rem;
  --dp-font-size: 0.95rem;
  --dp-border-color: #e2e8f0;
  --dp-border-color-hover: #06b6d4;
  --dp-primary-color: #06b6d4;
  --dp-primary-text-color: #fff;
  --dp-background-color: #f8fafc;
  --dp-text-color: #0f172a;
  --dp-hover-color: #e0f2fe;
  --dp-hover-text-color: #0c4a6e;
  --dp-menu-border-color: #e2e8f0;
}

.custom-datepicker :deep(.dp__input) {
  background: #f8fafc;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  padding: 0.75rem 1rem;
  font-size: 0.95rem;
  color: #0f172a;
  transition: all 0.2s;
  min-height: 46px;
}

.custom-datepicker :deep(.dp__input:hover) {
  border-color: #cbd5e1;
}

.custom-datepicker :deep(.dp__input:focus) {
  border-color: #06b6d4;
  background: #fff;
  box-shadow: 0 0 0 3px rgba(6, 182, 212, 0.1);
  transform: translateY(-1px);
}

.custom-datepicker :deep(.dp__input_icon) {
  color: #06b6d4;
}

.custom-datepicker :deep(.dp__calendar_header) {
  font-weight: 700;
}

.custom-datepicker :deep(.dp__calendar_header_item) {
  font-weight: 600;
  color: #64748b;
}

.custom-datepicker :deep(.dp__range_start),
.custom-datepicker :deep(.dp__range_end) {
  background: #06b6d4 !important;
  color: white !important;
}

.custom-datepicker :deep(.dp__range_between) {
  background: #e0f2fe !important;
  color: #0c4a6e !important;
}

.custom-datepicker :deep(.dp__today) {
  border-color: #06b6d4;
}

.custom-datepicker :deep(.dp__action_button) {
  background: #06b6d4;
  color: white;
  font-weight: 600;
  border-radius: 8px;
  padding: 0.5rem 1rem;
  transition: all 0.2s;
}

.custom-datepicker :deep(.dp__action_button:hover) {
  background: #0891b2;
  transform: translateY(-1px);
}

.custom-datepicker :deep(.dp__clear_icon),
.custom-datepicker :deep(.dp__input_icon_pad) {
  color: #06b6d4;
}

.itinerary-share {
  border: 1px solid #e2e8f0;
  background: #f8fafc;
  border-radius: 14px;
  padding: 1rem;
}

.itinerary-share-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 1rem;
  margin-bottom: 0.75rem;
}

.itinerary-share-head label {
  display: block;
  font-size: 0.78rem;
  font-weight: 700;
  color: #475569;
}

.itinerary-share-head p {
  margin: 0.25rem 0 0;
  color: #64748b;
  font-size: 0.84rem;
}

.btn-manage-itineraries {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  text-decoration: none;
  background: #fff;
  border: 1px solid #cbd5e1;
  color: #334155;
  border-radius: 10px;
  padding: 0.6rem 0.9rem;
  font-size: 0.82rem;
  font-weight: 700;
}

.itinerary-select {
  width: 100%;
  background: #fff;
  border: 1.5px solid #dbe4ee;
  border-radius: 10px;
  padding: 0.7rem 0.8rem;
  font: inherit;
}

.itinerary-preview {
  margin-top: 0.75rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
}

.itinerary-preview strong {
  color: #0f172a;
}

.itinerary-preview span {
  font-size: 0.82rem;
  color: #0369a1;
  font-weight: 700;
}

.itinerary-preview p {
  margin: 0.2rem 0 0;
  font-size: 0.84rem;
  color: #64748b;
}

/* ── Messages ────────────────────────────────────────────────────────────── */
.msg-error {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border: 2px solid #fca5a5;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  color: #dc2626;
  font-size: 0.95rem;
  font-weight: 600;
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  box-shadow: 0 2px 8px rgba(220, 38, 38, 0.15);
  animation: slideInDown 0.3s ease;
}

.msg-error svg {
  flex-shrink: 0;
  margin-top: 0.1rem;
}

.msg-error span {
  flex: 1;
}

@keyframes slideInDown {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.msg-success {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  border: 2px solid #6ee7b7;
  border-radius: 12px;
  padding: 1rem 1.25rem;
  color: #059669;
  font-size: 0.95rem;
  font-weight: 600;
  line-height: 1.6;
  box-shadow: 0 2px 8px rgba(5, 150, 105, 0.15);
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  animation: slideInUp 0.4s ease, successPulse 0.6s ease;
}

.msg-success svg {
  flex-shrink: 0;
}

.msg-success span {
  flex: 1;
}

.success-icon {
  animation: successCheck 0.6s ease;
}

@keyframes successCheck {
  0% {
    opacity: 0;
    transform: scale(0) rotate(-45deg);
  }
  50% {
    transform: scale(1.2) rotate(5deg);
  }
  100% {
    opacity: 1;
    transform: scale(1) rotate(0deg);
  }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

@keyframes successPulse {
  0%, 100% {
    box-shadow: 0 2px 8px rgba(5, 150, 105, 0.15);
  }
  50% {
    box-shadow: 0 4px 20px rgba(5, 150, 105, 0.3);
  }
}

/* ── Quotes grid ─────────────────────────────────────────────────────────── */
.quotes-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 1.2rem; margin-top: 1.2rem; }

.quote-row {
  border: 1px solid #f1f5f9;
  border-radius: 16px;
  padding: 1.2rem;
  background: #fafbfe;
  display: flex;
  flex-direction: column;
  gap: 0.7rem;
}

.quote-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.quote-meta-left { display: flex; align-items: center; gap: 0.6rem; }

.qbadge {
  font-size: 0.72rem;
  font-weight: 700;
  padding: 0.2rem 0.65rem;
  border-radius: 999px;
  text-transform: capitalize;
}

.qbadge.open   { background: #f0fdf4; color: #166534; border: 1px solid #bbf7d0; }
.qbadge.closed { background: #f1f5f9; color: #64748b; border: 1px solid #e2e8f0; }

.q-locs { font-size: 0.82rem; font-weight: 600; color: #334155; }
.q-date { font-size: 0.75rem; color: #94a3b8; }

.q-loc-list {
  margin: 0;
  padding-left: 1.2rem;
  font-size: 0.82rem;
  color: #475569;
  line-height: 1.7;
}

.q-details {
  display: flex;
  gap: 0.8rem;
  flex-wrap: wrap;
}

.q-details span {
  font-size: 0.78rem;
  color: #64748b;
  background: #f1f5f9;
  border-radius: 6px;
  padding: 0.2rem 0.55rem;
}

.q-note {
  font-size: 0.82rem;
  color: #64748b;
  font-style: italic;
  background: #f8fafc;
  border-left: 3px solid #e2e8f0;
  padding: 0.5rem 0.7rem;
  border-radius: 0 8px 8px 0;
}

.q-itinerary {
  display: flex;
  gap: 0.45rem;
  flex-wrap: wrap;
  align-items: center;
  font-size: 0.82rem;
  color: #334155;
}

.q-itinerary strong {
  color: #0369a1;
}

.q-responses { border-top: 1px solid #f1f5f9; padding-top: 0.7rem; }

.q-resp-label { font-size: 0.72rem; font-weight: 700; text-transform: uppercase; color: #94a3b8; margin-bottom: 0.5rem; }

.q-resp-item {
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
  border-radius: 10px;
  padding: 0.65rem 0.85rem;
  margin-bottom: 0.5rem;
}

.q-resp-name { font-size: 0.85rem; font-weight: 700; color: #0f172a; }
.q-resp-amt  { font-size: 0.85rem; color: #059669; font-weight: 700; margin-top: 0.15rem; }
.q-resp-msg  { font-size: 0.8rem; color: #64748b; margin-top: 0.2rem; }
.q-resp-itinerary {
  margin-top: 0.55rem;
  padding: 0.7rem 0.8rem;
  border-radius: 10px;
  background: #f0fdf4;
  border: 1px solid #bbf7d0;
}
.q-resp-itinerary span {
  display: block;
  margin-top: 0.2rem;
  font-size: 0.8rem;
  color: #166534;
}
.q-resp-itinerary p {
  margin: 0.35rem 0 0;
  font-size: 0.82rem;
  color: #166534;
}
.btn-save-proposal {
  margin-top: 0.55rem;
  border: none;
  background: #166534;
  color: #fff;
  border-radius: 999px;
  padding: 0.45rem 0.8rem;
  font-size: 0.78rem;
  font-weight: 700;
  cursor: pointer;
}
.btn-save-proposal:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.q-no-resp { font-size: 0.82rem; color: #94a3b8; font-style: italic; }

.q-actions { border-top: 1px solid #f1f5f9; padding-top: 0.7rem; }

.btn-remove-quote {
  background: #fef2f2;
  border: 1px solid #fecaca;
  color: #b91c1c;
  font-size: 0.82rem;
  font-weight: 600;
  padding: 0.45rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  transition: all 0.18s;
}

.btn-remove-quote:hover { background: #dc2626; color: #fff; border-color: #dc2626; }

.q-closed-tag {
  font-size: 0.8rem;
  color: #64748b;
  background: #f1f5f9;
  padding: 0.3rem 0.8rem;
  border-radius: 8px;
  font-weight: 600;
}

/* ── Quota Display ──────────────────────────────────────────────────────── */

.quota-info {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 0.75rem;
  margin-top: 1.5rem;
  padding: 0.75rem 1.5rem;
  border-radius: 12px;
  font-size: 0.95rem;
  transition: all 0.3s;
}

.quota-info.quota-ok {
  background: linear-gradient(135deg, #d1fae5 0%, #a7f3d0 100%);
  border: 2px solid #6ee7b7;
}

.quota-info.quota-warning {
  background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
  border: 2px solid #fbbf24;
}

.quota-info.quota-critical {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border: 2px solid #f87171;
}

.quota-icon {
  font-size: 1.25rem;
}

.quota-text {
  font-weight: 500;
  color: #1f2937;
}

.quota-text strong {
  font-weight: 700;
  color: #111827;
}

.btn-upgrade-mini {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.4rem 1rem;
  border-radius: 8px;
  font-size: 0.85rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-upgrade-mini:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* ── Pagination ──────────────────────────────────────────────────────────── */

.requests-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1.5rem;
}

.pagination-info {
  font-size: 0.9rem;
  color: #64748b;
  font-weight: 500;
}

.pagination-controls {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1.5rem;
  margin-top: 2rem;
  padding-top: 1.5rem;
  border-top: 1px solid #e2e8f0;
}

.btn-pagination {
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  color: white;
  border: none;
  padding: 0.65rem 1.5rem;
  border-radius: 10px;
  font-size: 0.9rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-pagination:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
}

.btn-pagination:disabled {
  opacity: 0.4;
  cursor: not-allowed;
  transform: none;
}

.pagination-current {
  font-size: 0.95rem;
  font-weight: 600;
  color: #334155;
}

/* ── Modals ──────────────────────────────────────────────────────────────── */

.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.6);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 9999;
  padding: 1rem;
  animation: fadeIn 0.3s ease-out;
}

@keyframes fadeIn {
  from {
    opacity: 0;
  }
  to {
    opacity: 1;
  }
}

.modal-content {
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  max-width: 600px;
  width: 100%;
  max-height: 90vh;
  overflow-y: auto;
  animation: slideUp 0.3s ease-out;
}

@keyframes slideUp {
  from {
    opacity: 0;
    transform: translateY(30px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.modal-header {
  padding: 2rem 2rem 1rem;
  text-align: center;
}

.modal-icon {
  font-size: 3rem;
  margin-bottom: 0.75rem;
}

.modal-header h2 {
  font-size: 1.75rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0;
}

.modal-body {
  padding: 1rem 2rem 2rem;
}

.limit-message {
  font-size: 1rem;
  color: #4a5568;
  text-align: center;
  margin: 0 0 1.5rem 0;
  line-height: 1.6;
}

.limit-stats {
  display: flex;
  gap: 1rem;
  margin: 1.5rem 0;
}

.limit-stat {
  flex: 1;
  background: #f7fafc;
  border-radius: 12px;
  padding: 1rem;
  text-align: center;
}

.stat-label {
  display: block;
  font-size: 0.85rem;
  color: #718096;
  font-weight: 600;
  margin-bottom: 0.5rem;
}

.stat-value {
  display: block;
  font-size: 1.5rem;
  font-weight: 700;
  color: #2d3748;
}

.upgrade-options h3 {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0 0 1rem 0;
  text-align: center;
}

.upgrade-tiers {
  display: flex;
  flex-direction: column;
  gap: 1rem;
}

.upgrade-tier {
  background: linear-gradient(135deg, #fef5e7 0%, #fff 100%);
  border: 2px solid #fbbf24;
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
}

.tier-badge {
  display: inline-block;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 700;
  margin-bottom: 0.75rem;
}

.tier-badge.premium {
  background: linear-gradient(135deg, #fbbf24 0%, #f59e0b 100%);
  color: white;
}

.tier-badge.enterprise {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

.tier-limit {
  font-size: 1.5rem;
  font-weight: 700;
  color: #2d3748;
  margin-bottom: 1rem;
}

.btn-upgrade {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
}

.btn-upgrade:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(102, 126, 234, 0.4);
}

.modal-alternative {
  margin-top: 1.5rem;
  padding: 1rem;
  background: #edf2f7;
  border-radius: 8px;
  text-align: center;
}

.modal-alternative p {
  margin: 0;
  font-size: 0.9rem;
  color: #4a5568;
}

.modal-footer {
  padding: 1rem 2rem 2rem;
  text-align: center;
}

.btn-close {
  background: #e2e8f0;
  color: #475569;
  border: none;
  padding: 0.75rem 2rem;
  border-radius: 10px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-close:hover {
  background: #cbd5e1;
}

/* Upgrade Modal Specific Styles */

.upgrade-modal .modal-body {
  padding: 1rem 1.5rem 2rem;
}

.membership-tiers {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
  gap: 1rem;
  margin-top: 1.5rem;
}

.tier-card {
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
  transition: all 0.3s;
}

.tier-card:hover {
  border-color: #667eea;
  transform: translateY(-4px);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.2);
}

.tier-card.current {
  border-color: #667eea;
  background: linear-gradient(135deg, #f0f4ff 0%, #fff 100%);
}

.tier-header {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.tier-icon {
  font-size: 2.5rem;
}

.tier-header h3 {
  font-size: 1.25rem;
  font-weight: 700;
  color: #1a202c;
  margin: 0;
}

.tier-badge-current {
  display: inline-block;
  padding: 0.25rem 0.75rem;
  background: #667eea;
  color: white;
  border-radius: 12px;
  font-size: 0.75rem;
  font-weight: 700;
}

.tier-limit-big {
  font-size: 1.5rem;
  font-weight: 700;
  color: #2d3748;
  margin-bottom: 1rem;
}

.tier-features {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
  margin-bottom: 1rem;
  text-align: left;
}

.tier-features div {
  font-size: 0.9rem;
  color: #4a5568;
  padding-left: 0.5rem;
}

.btn-select-tier {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  border: none;
  padding: 0.65rem 1.5rem;
  border-radius: 8px;
  font-size: 0.9rem;
  font-weight: 700;
  cursor: pointer;
  transition: all 0.2s;
  width: 100%;
}

.btn-select-tier:hover {
  transform: translateY(-2px);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.4);
}

/* ── Responsive ──────────────────────────────────────────────────────────── */

/* Tablet (768px - 900px) */
@media (max-width: 900px) {
  .qb-hero-inner h1 { font-size: 2rem; }
  .qb-grid { 
    grid-template-columns: 1fr; 
    gap: 2rem;
  }
  .pub-form-grid { grid-template-columns: 1fr 1fr; }
  .qb-container { margin-top: -2.5rem; }
  
  /* Reorder: bucket comes after search on tablet */
  .qb-col:last-child {
    order: 2;
  }
}

/* Mobile (600px - 768px) */
@media (max-width: 768px) {
  .qb-hero { padding: 2.5rem 1.2rem 5rem; }
  .qb-hero-inner h1 { font-size: 1.75rem; }
  
  .hero-stats {
    flex-wrap: wrap;
    gap: 0.8rem;
    padding: 0.6rem 1.2rem;
  }
  
  .hstat strong { font-size: 1.4rem; }
  .hstat span { font-size: 0.7rem; }
  
  .step-title { font-size: 1.5rem; }
  .step-description { font-size: 0.95rem; }
  
  .card-title { font-size: 1.2rem; }
  .card-sub { font-size: 0.9rem; }
  
  .pub-form-grid { 
    grid-template-columns: 1fr;
    gap: 1.2rem;
  }
}

/* Small Mobile (< 600px) */
@media (max-width: 600px) {
  .qb-hero { padding: 2rem 1rem 4.5rem; }
  .qb-hero-inner h1 { font-size: 1.5rem; }
  .qb-hero-inner p { font-size: 0.9rem; }
  
  .eyebrow { 
    font-size: 0.65rem;
    padding: 0.25rem 0.8rem;
  }
  
  .qb-container { 
    padding: 0 1rem;
    margin-top: -2rem;
  }
  
  .qb-card { 
    padding: 1.2rem; 
    border-radius: 14px;
  }
  
  .step-section { margin-bottom: 2rem; }
  .step-title { font-size: 1.3rem; }
  .step-description { font-size: 0.85rem; }
  
  .card-title { font-size: 1.1rem; }
  .card-sub { font-size: 0.85rem; }
  
  /* Touch-friendly search bar */
  .search-bar {
    padding: 0.6rem 0.6rem 0.6rem 1rem;
  }
  
  .search-bar input {
    font-size: 1rem; /* Prevent zoom on iOS */
    min-height: 44px; /* Touch-friendly */
  }
  
  .btn-search {
    padding: 0.7rem 1.3rem;
    font-size: 0.9rem;
    min-height: 44px;
  }
  
  /* Touch-friendly form inputs */
  .pub-field input,
  .pub-field textarea,
  .form-input,
  .form-textarea {
    font-size: 1rem; /* Prevent zoom on iOS */
    padding: 0.85rem 1rem;
    min-height: 44px;
  }
  
  .pub-field textarea,
  .form-textarea {
    min-height: 100px;
  }
  
  /* Stepper buttons touch-friendly */
  .stepper-btn {
    width: 44px;
    height: 44px;
  }
  
  .stepper-value {
    font-size: 1.1rem;
    padding: 0 0.8rem;
  }
  
  /* Date picker touch-friendly */
  .custom-datepicker :deep(.dp__input) {
    font-size: 1rem;
    padding: 0.85rem 1rem;
    min-height: 48px;
  }
  
  /* Publish button sticky on mobile */
  .publish-head {
    position: sticky;
    top: 0;
    z-index: 50;
    background: white;
    padding: 1rem;
    margin: -1.2rem -1.2rem 1rem;
    border-bottom: 1px solid #e2e8f0;
    flex-direction: column;
    gap: 1rem;
  }
  
  .btn-publish { 
    width: 100%; 
    justify-content: center;
    min-height: 50px;
    font-size: 1rem;
    padding: 0 1.5rem;
  }
  
  /* Forms */
  .pub-form-grid { 
    grid-template-columns: 1fr;
    gap: 1rem;
  }
  
  .pin-form { grid-template-columns: 1fr; }
  
  .itinerary-share-head { 
    flex-direction: column;
    gap: 1rem;
  }
  
  .btn-manage-itineraries {
    width: 100%;
    justify-content: center;
  }
  
  /* Results */
  .res-item {
    flex-direction: column;
    align-items: stretch;
    gap: 1rem;
  }
  
  .btn-add {
    width: 100%;
    justify-content: center;
    min-height: 44px;
  }
  
  /* Bucket items */
  .bucket-item {
    flex-direction: column;
    gap: 0.8rem;
  }
  
  .bucket-item-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 0.5rem;
  }
  
  /* Quote cards */
  .quote-row {
    padding: 1rem;
  }
  
  .quote-top {
    flex-direction: column;
    gap: 0.8rem;
  }
  
  .quote-actions {
    width: 100%;
    justify-content: stretch;
  }
  
  .quote-actions button {
    flex: 1;
    min-height: 44px;
  }
  
  /* Suggestions dropdown */
  .suggestions {
    position: fixed;
    top: auto;
    left: 1rem;
    right: 1rem;
    bottom: 1rem;
    max-height: 60vh;
    overflow-y: auto;
    border-radius: 16px;
  }
  
  .sug-item {
    padding: 1rem;
    min-height: 60px;
  }
  
  /* Hide elements on mobile to reduce clutter */
  .hero-stats { display: none; }
  .card-label { font-size: 0.65rem; }
}

/* Extra Small Mobile (< 400px) */
@media (max-width: 400px) {
  .qb-hero-inner h1 { font-size: 1.3rem; }
  .step-title { font-size: 1.2rem; }
  .qb-card { padding: 1rem; }
  
  .search-bar {
    flex-direction: column;
    gap: 0.8rem;
    padding: 0.8rem;
  }
  
  .btn-search {
    width: 100%;
    justify-content: center;
  }
}
</style>
