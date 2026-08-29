# Quote Builder Refinement Plan - Production Ready

**Date:** August 7, 2026  
**Feature:** Tourist Quote Request Builder Enhancement  
**Status:** Ready for Review  
**Focus:** Production readiness, intuitive UX, step-by-step flow

---

## 📋 Current Implementation Analysis

### Strengths ✅
- **Solid foundation**: Working search with operator-featured and global locations
- **Map integration**: Leaflet map with marker support
- **Bucket system**: LocalStorage persistence for location collection
- **Dual search modes**: Text search + manual pin drop
- **Quote publishing**: Full API integration with itinerary attachment
- **Recent quotes view**: Tracking and response management

### Pain Points ❌
- **No clear step progression**: Everything visible at once, overwhelming
- **Search UX issues**:
  - Autocomplete suggestions not prominent enough
  - No hover highlight on suggestions
  - Selecting suggestion doesn't feel snappy
  - No keyboard navigation (arrow keys, enter)
- **Map selection hidden**: Manual pin section feels like secondary feature
- **No visual feedback**: Adding to bucket lacks celebration/confirmation
- **Form scattered**: Publish form not clearly separated as "Step 2"
- **Mobile unfriendly**: 2-column grid doesn't adapt well
- **No progress indicator**: Can't tell how far along they are

---

## 🎯 Refinement Goals

### Primary Objectives
1. **Clear step-by-step flow** with visual progress indicator
2. **Intuitive location selection** with enhanced autocomplete and bucket management
3. **Convenient map integration** with expandable/collapsible interface
4. **Streamlined publishing** with all details grouped in Step 2
5. **Mobile-first responsive** design that works on all devices
6. **Production-grade polish** with animations, loading states, and validation

---

## 🏗️ Architecture Plan

### Component Structure

```
QuoteBuilder.vue (Main orchestrator)
├── QuoteBuilderSteps.vue (NEW - Step indicator with progress)
├── Step1LocationSelection.vue (NEW)
│   ├── LocationSearchBar.vue (ENHANCED)
│   │   ├── Search input with icon
│   │   ├── Live autocomplete dropdown (ENHANCED)
│   │   │   ├── Keyboard navigation (↑ ↓ Enter Esc)
│   │   │   ├── Hover highlight effect
│   │   │   ├── Category badges (Featured/Global)
│   │   │   └── Selection animation
│   │   └── Search button
│   ├── LocationBucket.vue (NEW - Enhanced bucket list)
│   │   ├── Bucket header with count
│   │   ├── Live map preview
│   │   ├── Location cards (draggable reorder)
│   │   ├── Inline notes editing
│   │   ├── Remove with undo snackbar
│   │   └── Clear all with confirmation
│   └── MapSelector.vue (NEW - Expandable map interface)
│       ├── Expand/collapse button (default closed)
│       ├── Fullscreen map modal
│       ├── Click to select coordinates
│       ├── Search within map
│       ├── Add to bucket directly from map
│       └── Visual pin drop animation
└── Step2PublishQuote.vue (NEW)
    ├── Form header with required field indicator
    ├── Travel window input (date picker)
    ├── Traveler count (stepper input)
    ├── Budget input (currency formatted)
    ├── Notes textarea (rich text optional)
    ├── Itinerary attachment selector
    ├── Preview card (summary of quote)
    └── Publish button (prominent, sticky on mobile)
```

### State Management Enhancement

```javascript
// stores/quotes.js - Enhanced
{
  // Existing
  bucket: [],
  recentQuotes: [],
  loading: false,
  
  // NEW additions
  currentStep: 1, // 1 or 2
  stepValidation: {
    step1: false, // true when bucket.length > 0
    step2: false  // true when required fields filled
  },
  searchHistory: [], // Recent searches
  mapExpanded: false, // Map modal open/closed
  bucketChangeAnimation: null, // Track animations
  formDraft: {}, // Auto-save form progress
}
```

---

## 📐 Detailed Feature Specifications

### Feature 1: Step Progress Indicator

**Component:** `QuoteBuilderSteps.vue`

**Design:**
```
┌─────────────────────────────────────────────────────┐
│  [●━━━━━━━━━━━━━━━━━━━━━━━○]                       │
│   ↑                         ↑                        │
│  Step 1: Select Locations   Step 2: Publish Quote   │
│  ✓ Add at least 1 location  ○ Fill travel details   │
└─────────────────────────────────────────────────────┘
```

**Behavior:**
- Sticky header, always visible while scrolling
- Step 1 active by default
- Progress bar fills as bucket grows (0 locations = 0%, 1+ = 50%, on Step 2 = 100%)
- Click on Step 2 requires Step 1 completion (bucket.length > 0)
- Smooth scroll to relevant section when step clicked
- Tailwind: `bg-gradient-to-r from-cyan-500 to-teal-500` for active progress

**Validation:**
- Step 1 complete when: `bucket.length > 0`
- Step 2 accessible when: Step 1 complete
- Visual checkmark (✓) when step complete
- Disabled state (○) when step not accessible

---

### Feature 2: Enhanced Location Search with Autocomplete

**Component:** `LocationSearchBar.vue`

**Design Elements:**

1. **Search Input:**
   - Icon: Magnifying glass (left)
   - Placeholder: "Search destinations (try: Manali, Bali, Paris...)"
   - Clear button (×) when text entered
   - Loading spinner when searching
   - Tailwind: `focus:ring-2 focus:ring-cyan-500 focus:border-transparent`

2. **Autocomplete Dropdown:**
   ```
   ┌─────────────────────────────────────────┐
   │ ✈️ FEATURED BY OPERATORS                │
   │ ┌─────────────────────────────────────┐ │
   │ │ > Manali, Himachal Pradesh, India   │ │ (hovered - bg-cyan-50)
   │ │   by Himalayan Adventures            │ │
   │ └─────────────────────────────────────┘ │
   │   Shimla, Himachal Pradesh, India      │
   │   by Mountain Explorers                 │
   ├─────────────────────────────────────────┤
   │ 🌍 WORLDWIDE RESULTS                    │
   │   Manali, Australia                     │
   │   Manila, Philippines                   │
   └─────────────────────────────────────────┘
   ```

   **Hover Effects:**
   - Subtle background change: `hover:bg-cyan-50 transition-colors duration-150`
   - Slight scale: `hover:scale-[1.02]`
   - Cursor: `cursor-pointer`
   - Border left accent: `hover:border-l-4 hover:border-cyan-500`

   **Keyboard Navigation:**
   - ↑/↓ arrows: Navigate suggestions
   - Enter: Select highlighted suggestion
   - Esc: Close dropdown
   - Tab: Cycle through suggestions
   - Visual highlight: `ring-2 ring-cyan-500` for keyboard-selected item

3. **Selection Animation:**
   - When item selected:
     - Dropdown fades out: `opacity-0 transition-opacity duration-200`
     - Search input briefly shows checkmark: ✓
     - Success feedback: Green pulse animation
     - Auto-clear input after 500ms
   - Bucket card pulses to draw attention: `animate-pulse`

4. **Search Results (Full Results Below):**
   - Card-based layout with better spacing
   - Thumbnail images (if available)
   - "Add to bucket" button with icon: `+ Add`
   - Button state changes: `Added ✓` (disabled, green)
   - Loading skeleton for async results

**Implementation Details:**
```vue
<script setup>
const suggestions = ref([])
const highlightedIndex = ref(-1)
const searchLoading = ref(false)

const handleKeyDown = (e) => {
  if (!showSuggestions.value) return
  
  switch(e.key) {
    case 'ArrowDown':
      e.preventDefault()
      highlightedIndex.value = Math.min(
        highlightedIndex.value + 1,
        suggestions.value.length - 1
      )
      break
    case 'ArrowUp':
      e.preventDefault()
      highlightedIndex.value = Math.max(highlightedIndex.value - 1, 0)
      break
    case 'Enter':
      e.preventDefault()
      if (highlightedIndex.value >= 0) {
        selectSuggestion(suggestions.value[highlightedIndex.value])
      }
      break
    case 'Escape':
      showSuggestions.value = false
      break
  }
}

const selectSuggestion = (location) => {
  // Add to bucket with animation
  quoteStore.addLocation(location, { animate: true })
  
  // Show success feedback
  showSuccessCheck()
  
  // Clear and close
  setTimeout(() => {
    searchQuery.value = ''
    showSuggestions.value = false
    highlightedIndex.value = -1
  }, 500)
}
</script>
```

**Accessibility:**
- ARIA labels for screen readers
- Focus trap in dropdown
- High contrast mode support
- Touch-friendly (48px min tap target)

---

### Feature 3: Enhanced Location Bucket

**Component:** `LocationBucket.vue`

**Design:**
```
┌────────────────────────────────────────────────┐
│  YOUR DESTINATIONS                      Clear All│
│  3 locations selected                           │
├────────────────────────────────────────────────┤
│  [Interactive Map Preview - shows all pins]    │
│  (Click to expand full map)                     │
├────────────────────────────────────────────────┤
│  1. [📍] Manali, Himachal Pradesh, India       │
│     [                                      ] [×]│
│     └─ Add note for operators...               │
│                                                 │
│  2. [📍] Shimla, Himachal Pradesh, India       │
│     [Weekend getaway, budget hotels       ] [×]│
│                                                 │
│  3. [📍] Dharamshala, Himachal Pradesh         │
│     [Trekking focus                       ] [×]│
└────────────────────────────────────────────────┘
```

**Features:**

1. **Drag-to-Reorder:**
   - Use `@vueuse/motion` or `vue-draggable-next`
   - Visual drag handle: `⋮⋮` on left side
   - Ghost preview during drag
   - Smooth animations when items reorder
   - Auto-save order to localStorage

2. **Location Cards:**
   - Numbered badges (1, 2, 3...)
   - Location icon matching type (featured ✈️ vs global 🌍)
   - Primary text: Location name (bold, 16px)
   - Secondary text: State, Country (gray, 14px)
   - Inline notes input (shows on hover or always on mobile)
   - Remove button (×) on right

3. **Interactive Map Preview:**
   - Small map (200px height) showing all bucket locations
   - Pins numbered to match bucket order
   - Click to expand full map modal
   - Animated pin additions
   - Auto-zoom to fit all pins

4. **Remove with Undo:**
   - Click ×: Item fades out with slide animation
   - Snackbar appears: "Location removed. Undo?"
   - 5-second undo window
   - Auto-dismiss after timeout

5. **Empty State:**
   ```
   ┌────────────────────────────────────┐
   │         🗺️                         │
   │                                    │
   │   No destinations yet              │
   │                                    │
   │   Search or drop a pin to start    │
   │   building your trip               │
   └────────────────────────────────────┘
   ```

**Tailwind Styling:**
```vue
<template>
  <div class="bg-white rounded-2xl shadow-lg border border-gray-100 p-6">
    <!-- Header -->
    <div class="flex justify-between items-center mb-4">
      <div>
        <h3 class="text-lg font-bold text-gray-900">Your Destinations</h3>
        <p class="text-sm text-gray-500">{{ bucket.length }} location{{ bucket.length !== 1 ? 's' : '' }} selected</p>
      </div>
      <button
        v-if="bucket.length > 0"
        @click="clearAll"
        class="text-sm text-red-600 hover:text-red-700 font-medium"
      >
        Clear All
      </button>
    </div>

    <!-- Map Preview -->
    <div
      @click="expandMap"
      class="h-48 rounded-xl overflow-hidden border-2 border-gray-200 cursor-pointer hover:border-cyan-500 transition-colors mb-4"
    >
      <MapView :locations="mapLocations" :interactive="false" />
    </div>

    <!-- Bucket Items -->
    <TransitionGroup name="bucket" tag="div" class="space-y-3">
      <div
        v-for="(item, idx) in bucket"
        :key="item.id"
        class="flex items-start gap-3 p-4 rounded-xl border-2 border-gray-200 hover:border-cyan-300 transition-all duration-200 group"
      >
        <!-- Drag Handle -->
        <div class="text-gray-400 cursor-move">⋮⋮</div>
        
        <!-- Number Badge -->
        <div class="flex-shrink-0 w-8 h-8 rounded-full bg-cyan-500 text-white flex items-center justify-center font-bold text-sm">
          {{ idx + 1 }}
        </div>
        
        <!-- Content -->
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 mb-1">
            <span>{{ item.type === 'operator' ? '✈️' : '🌍' }}</span>
            <h4 class="font-semibold text-gray-900">{{ item.name }}</h4>
          </div>
          <p class="text-sm text-gray-600 mb-2">{{ item.state }}, {{ item.country }}</p>
          <input
            v-model="item.notes"
            placeholder="Add note for operators..."
            class="w-full text-sm px-3 py-2 border border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          />
        </div>
        
        <!-- Remove Button -->
        <button
          @click="removeItem(idx)"
          class="flex-shrink-0 w-8 h-8 rounded-full hover:bg-red-50 text-gray-400 hover:text-red-600 flex items-center justify-center transition-colors"
          title="Remove"
        >
          ×
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.bucket-move,
.bucket-enter-active,
.bucket-leave-active {
  transition: all 0.3s ease;
}

.bucket-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.bucket-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.bucket-leave-active {
  position: absolute;
}
</style>
```

---

### Feature 4: Map Selector (Default Closed, Expandable)

**Component:** `MapSelector.vue`

**Default State (Collapsed):**
```
┌────────────────────────────────────────────┐
│  📍 Or select from map                      │
│  Drop custom pins directly on the map      │
│                                             │
│  [🗺️ Open Map Selector] (Button)          │
└────────────────────────────────────────────┘
```

**Expanded State (Modal):**
```
┌─────────────────────────────────────────────────────┐
│  Select Location on Map                       [× Close]│
├─────────────────────────────────────────────────────┤
│  [Search within map...         ] [My Location 📍]   │
├─────────────────────────────────────────────────────┤
│                                                      │
│                                                      │
│              [FULL SCREEN MAP]                       │
│              Click anywhere to select                │
│                                                      │
│                                                      │
├─────────────────────────────────────────────────────┤
│  Selected: 28.6139°N, 77.2090°E                    │
│  Location name: [                          ]         │
│  [Add to Bucket]                                     │
└─────────────────────────────────────────────────────┘
```

**Behavior:**

1. **Expand Button:**
   - Secondary style button with map icon
   - Expands to full-screen modal overlay
   - Backdrop blur effect
   - Smooth zoom-in animation

2. **Map Interface:**
   - Leaflet map with OpenStreetMap tiles
   - Click anywhere to drop pin
   - Pin animates with bounce effect
   - Shows coordinates of selected point
   - Search bar for finding locations by name
   - "My Location" button (requires permission)

3. **Selection Flow:**
   - Click map → Pin drops → Coordinates shown
   - Name input appears (with suggestion from reverse geocoding)
   - "Add to Bucket" button becomes enabled
   - Adding triggers success animation
   - Modal closes automatically after adding
   - Bucket card pulses to show new addition

4. **Advanced Features:**
   - **Reverse Geocoding:** Auto-fill location name from coordinates
   - **Drawing Tools:** Draw radius around area of interest (future)
   - **Satellite View Toggle:** Switch between map and satellite
   - **Zoom Controls:** +/- buttons, scroll zoom
   - **Fullscreen:** Native fullscreen API support

**Implementation:**
```vue
<template>
  <!-- Collapsed State -->
  <div v-if="!expanded" class="bg-gradient-to-br from-cyan-50 to-teal-50 rounded-2xl p-6 border-2 border-dashed border-cyan-300">
    <div class="flex items-center gap-3 mb-2">
      <span class="text-2xl">📍</span>
      <h3 class="font-bold text-gray-900">Or select from map</h3>
    </div>
    <p class="text-sm text-gray-600 mb-4">
      Drop custom pins directly on the map for precise location control
    </p>
    <button
      @click="expanded = true"
      class="w-full bg-white hover:bg-cyan-50 text-cyan-700 font-semibold py-3 px-6 rounded-xl border-2 border-cyan-300 hover:border-cyan-500 transition-all duration-200 flex items-center justify-center gap-2"
    >
      <span class="text-xl">🗺️</span>
      Open Map Selector
    </button>
  </div>

  <!-- Expanded State (Modal) -->
  <Teleport to="body">
    <Transition name="modal">
      <div
        v-if="expanded"
        class="fixed inset-0 z-50 flex items-center justify-center bg-black bg-opacity-50 backdrop-blur-sm p-4"
        @click.self="closeModal"
      >
        <div class="bg-white rounded-2xl shadow-2xl w-full max-w-6xl h-[80vh] flex flex-col">
          <!-- Header -->
          <div class="flex items-center justify-between p-6 border-b">
            <h2 class="text-2xl font-bold text-gray-900">Select Location on Map</h2>
            <button
              @click="closeModal"
              class="text-gray-400 hover:text-gray-600 text-2xl"
            >
              ×
            </button>
          </div>

          <!-- Search Bar -->
          <div class="p-4 border-b flex gap-2">
            <input
              v-model="mapSearch"
              placeholder="Search within map..."
              class="flex-1 px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            />
            <button
              @click="useMyLocation"
              class="px-4 py-2 bg-cyan-500 text-white rounded-lg hover:bg-cyan-600 transition-colors flex items-center gap-2"
            >
              <span>📍</span>
              My Location
            </button>
          </div>

          <!-- Map Container -->
          <div class="flex-1 relative">
            <MapView
              v-model="selectedCoords"
              :allow-selection="true"
              :show-coordinates="true"
              height="100%"
              @location-selected="onLocationSelected"
            />
          </div>

          <!-- Selection Footer -->
          <div v-if="selectedCoords" class="p-6 border-t bg-gray-50">
            <div class="mb-4">
              <label class="block text-sm font-medium text-gray-700 mb-2">
                Selected: {{ selectedCoords.latitude.toFixed(6) }}°N, {{ selectedCoords.longitude.toFixed(6) }}°E
              </label>
              <input
                v-model="locationName"
                placeholder="Location name (auto-filled from map)"
                class="w-full px-4 py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
              />
            </div>
            <button
              @click="addTobucket"
              :disabled="!locationName"
              class="w-full bg-cyan-500 hover:bg-cyan-600 disabled:bg-gray-300 text-white font-bold py-3 px-6 rounded-xl transition-colors"
            >
              Add to Bucket
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref } from 'vue'

const expanded = ref(false)
const selectedCoords = ref(null)
const locationName = ref('')
const mapSearch = ref('')

const onLocationSelected = async (coords) => {
  selectedCoords.value = coords
  
  // Reverse geocode to get location name
  try {
    const response = await fetch(
      `https://nominatim.openstreetmap.org/reverse?lat=${coords.latitude}&lon=${coords.longitude}&format=json`
    )
    const data = await response.json()
    locationName.value = data.display_name?.split(',')[0] || 'Custom Location'
  } catch (err) {
    locationName.value = 'Custom Location'
  }
}

const addToucket = () => {
  // Add logic
  expanded.value = false
  selectedCoords.value = null
  locationName.value = ''
}

const useMyLocation = () => {
  if ('geolocation' in navigator) {
    navigator.geolocation.getCurrentPosition(
      (position) => {
        selectedCoords.value = {
          latitude: position.coords.latitude,
          longitude: position.coords.longitude
        }
        onLocationSelected(selectedCoords.value)
      },
      (error) => {
        alert('Could not get your location. Please enable location access.')
      }
    )
  }
}
</script>

<style scoped>
.modal-enter-active, .modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from, .modal-leave-to {
  opacity: 0;
}

.modal-enter-active .bg-white,
.modal-leave-active .bg-white {
  transition: transform 0.3s ease;
}

.modal-enter-from .bg-white {
  transform: scale(0.9);
}

.modal-leave-to .bg-white {
  transform: scale(0.9);
}
</style>
```

---

### Feature 5: Step 2 - Publish Quote (Enhanced Form)

**Component:** `Step2PublishQuote.vue`

**Design:**
```
┌──────────────────────────────────────────────────────┐
│  STEP 2: PUBLISH YOUR QUOTE REQUEST                  │
│  Fill in travel details to get accurate quotes       │
├──────────────────────────────────────────────────────┤
│  📅 Travel Window *                                   │
│  [March 15-22, 2026         ] [📅 Pick Dates]       │
│  or "Flexible in April"                              │
├──────────────────────────────────────────────────────┤
│  👥 Number of Travelers *                            │
│  [ - ]  2  [ + ]                                     │
├──────────────────────────────────────────────────────┤
│  💰 Budget (Optional)                                │
│  [$] [                    ] per person / total       │
│  (helps operators tailor their offers)               │
├──────────────────────────────────────────────────────┤
│  📝 Notes for Operators                              │
│  [                                                   ]│
│  [  Tell operators about your interests,            ]│
│  [  special requirements, must-do experiences...    ]│
│  [                                                   ]│
├──────────────────────────────────────────────────────┤
│  🗓️ Attach Saved Itinerary (Optional)               │
│  Share your planned route with operators             │
│                                                       │
│  [Select Itinerary ▼]                                │
│  ○ No itinerary attached                             │
│  ○ Himalayan Adventure - 7 days                      │
│  ○ Weekend Getaway - 3 days                          │
│                                                       │
│  [Preview Selected] [Manage Itineraries →]          │
├──────────────────────────────────────────────────────┤
│  PREVIEW YOUR REQUEST                                │
│  ┌────────────────────────────────────────────────┐ │
│  │ • 3 destinations: Manali, Shimla, Dharamshala │ │
│  │ • Travel: March 15-22, 2026                    │ │
│  │ • Travelers: 2 adults                          │ │
│  │ • Budget: $1,500 total                         │ │
│  │ • Itinerary: Himalayan Adventure (attached)    │ │
│  └────────────────────────────────────────────────┘ │
├──────────────────────────────────────────────────────┤
│                 [📨 Publish Quote Request]           │
│          Operators will respond within 24-48 hours   │
└──────────────────────────────────────────────────────┘
```

**Key Features:**

1. **Date Picker Integration:**
   - Use `@vuepic/vue-datepicker` or similar
   - Calendar popup for visual date selection
   - Range selection support
   - "Flexible dates" toggle option
   - Quick presets: "Next weekend", "Next month", "Summer 2026"

2. **Traveler Stepper:**
   - Visual +/- buttons
   - Separate inputs for adults and children (with ages)
   - Group discount indicator if applicable
   - Max travelers validation (e.g., 20)

3. **Budget Input:**
   - Currency selector (USD, EUR, INR, etc.)
   - Per person vs total toggle
   - Budget range slider as alternative
   - Tooltip: "Typical range: $500-$2000 per person"

4. **Rich Text Notes:**
   - Optional: Integrate basic rich text editor (bold, lists)
   - Or: Simple textarea with character counter (max 500)
   - Suggestions chips: "Adventure activities", "Cultural experiences", "Luxury accommodations"
   - Click chip to insert into notes

5. **Itinerary Selector:**
   - Dropdown with preview cards
   - Each option shows: Title, Duration, Primary location
   - "Preview" button opens modal with full itinerary details
   - "Manage Itineraries" link to /itineraries page
   - Clear selection button (×)

6. **Request Preview Card:**
   - Summary of all inputs
   - Visual checklist style
   - Edit buttons to jump back to specific field
   - Shows validation errors (red highlights)

7. **Publish Button:**
   - Large, prominent button (full width on mobile)
   - Sticky on mobile when scrolling
   - Loading state with spinner
   - Success animation on publish
   - Disabled when required fields missing
   - Validation messages above button

**Validation Rules:**
```javascript
const validation = {
  step1: {
    locations: {
      required: true,
      min: 1,
      message: 'Add at least one destination'
    }
  },
  step2: {
    travel_window: {
      required: true,
      message: 'Travel dates help operators provide accurate quotes'
    },
    travelers: {
      required: true,
      min: 1,
      message: 'Number of travelers is required'
    },
    budget: {
      required: false,
      min: 0,
      message: 'Budget must be a positive number'
    },
    notes: {
      required: false,
      maxLength: 500
    }
  }
}
```

**Implementation:**
```vue
<template>
  <div class="bg-white rounded-2xl shadow-lg border border-gray-100 p-8">
    <!-- Header -->
    <div class="mb-8">
      <div class="flex items-center gap-3 mb-2">
        <span class="text-3xl">📨</span>
        <h2 class="text-2xl font-bold text-gray-900">Publish Your Quote Request</h2>
      </div>
      <p class="text-gray-600">Fill in travel details to get accurate, tailored quotes from operators</p>
    </div>

    <!-- Form Fields -->
    <div class="space-y-6">
      <!-- Travel Window -->
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          📅 Travel Window <span class="text-red-500">*</span>
        </label>
        <div class="flex gap-2">
          <input
            v-model="form.travel_window"
            type="text"
            placeholder="March 15-22, 2026 or Flexible in April"
            class="flex-1 px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
            :class="{ 'border-red-500': errors.travel_window }"
          />
          <button
            @click="showDatePicker = true"
            class="px-4 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors"
          >
            📅 Pick Dates
          </button>
        </div>
        <p v-if="errors.travel_window" class="mt-1 text-sm text-red-600">{{ errors.travel_window }}</p>
        <p class="mt-1 text-xs text-gray-500">Help operators check availability and seasonal pricing</p>
      </div>

      <!-- Travelers -->
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          👥 Number of Travelers <span class="text-red-500">*</span>
        </label>
        <div class="flex items-center gap-4">
          <button
            @click="form.travelers = Math.max(1, form.travelers - 1)"
            class="w-10 h-10 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-xl font-bold"
          >
            −
          </button>
          <input
            v-model.number="form.travelers"
            type="number"
            min="1"
            class="w-20 text-center text-xl font-bold py-2 border-2 border-gray-300 rounded-lg focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          />
          <button
            @click="form.travelers++"
            class="w-10 h-10 rounded-lg bg-gray-100 hover:bg-gray-200 flex items-center justify-center text-xl font-bold"
          >
            +
          </button>
          <span class="text-gray-600">{{ form.travelers === 1 ? 'traveler' : 'travelers' }}</span>
        </div>
        <p v-if="errors.travelers" class="mt-1 text-sm text-red-600">{{ errors.travelers }}</p>
      </div>

      <!-- Budget -->
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          💰 Budget (Optional)
        </label>
        <div class="flex gap-2">
          <span class="flex items-center px-4 py-3 bg-gray-100 border-2 border-gray-300 rounded-l-xl text-gray-600 font-semibold">
            $
          </span>
          <input
            v-model.number="form.budget"
            type="number"
            min="0"
            step="50"
            placeholder="1500"
            class="flex-1 px-4 py-3 border-2 border-gray-300 border-l-0 rounded-r-xl focus:ring-2 focus:ring-cyan-500 focus:border-transparent"
          />
          <select
            v-model="budgetType"
            class="px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-cyan-500"
          >
            <option value="total">Total</option>
            <option value="per-person">Per Person</option>
          </select>
        </div>
        <p class="mt-1 text-xs text-gray-500">Helps operators tailor their offers to your budget range</p>
      </div>

      <!-- Notes -->
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          📝 Notes for Operators
        </label>
        <textarea
          v-model="form.notes"
          rows="4"
          placeholder="Tell operators about your interests, special requirements, must-do experiences..."
          class="w-full px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-cyan-500 focus:border-transparent resize-none"
          maxlength="500"
        ></textarea>
        <div class="flex justify-between mt-1">
          <p class="text-xs text-gray-500">Share preferences, dietary restrictions, accessibility needs, etc.</p>
          <p class="text-xs text-gray-400">{{ form.notes.length }}/500</p>
        </div>
      </div>

      <!-- Itinerary Attachment -->
      <div>
        <label class="block text-sm font-semibold text-gray-700 mb-2">
          🗓️ Attach Saved Itinerary (Optional)
        </label>
        <p class="text-sm text-gray-600 mb-3">Share your planned route to help operators understand your vision</p>
        <div class="flex gap-2">
          <select
            v-model="selectedItineraryId"
            class="flex-1 px-4 py-3 border-2 border-gray-300 rounded-xl focus:ring-2 focus:ring-cyan-500"
          >
            <option value="">No itinerary attached</option>
            <option v-for="itin in savedItineraries" :key="itin._id" :value="itin._id">
              {{ itin.title }} · {{ itin.duration_days }} days
            </option>
          </select>
          <router-link
            to="/itineraries"
            class="px-4 py-3 bg-gray-100 hover:bg-gray-200 rounded-xl transition-colors text-gray-700 font-medium whitespace-nowrap"
          >
            Manage →
          </router-link>
        </div>
        <div v-if="selectedItinerary" class="mt-3 p-4 bg-cyan-50 border-2 border-cyan-200 rounded-xl">
          <h4 class="font-bold text-gray-900 mb-1">{{ selectedItinerary.title }}</h4>
          <p class="text-sm text-gray-600">
            {{ selectedItinerary.duration_days }} days · {{ selectedItinerary.primary_location?.area_name }}
          </p>
        </div>
      </div>
    </div>

    <!-- Preview Card -->
    <div class="mt-8 p-6 bg-gradient-to-br from-cyan-50 to-teal-50 rounded-xl border-2 border-cyan-200">
      <h3 class="font-bold text-gray-900 mb-3">Request Preview</h3>
      <ul class="space-y-2 text-sm">
        <li class="flex items-start gap-2">
          <span>📍</span>
          <span><strong>Destinations:</strong> {{ bucketCount }} location{{ bucketCount !== 1 ? 's' : '' }}</span>
        </li>
        <li v-if="form.travel_window" class="flex items-start gap-2">
          <span>📅</span>
          <span><strong>Travel:</strong> {{ form.travel_window }}</span>
        </li>
        <li v-if="form.travelers" class="flex items-start gap-2">
          <span>👥</span>
          <span><strong>Travelers:</strong> {{ form.travelers }}</span>
        </li>
        <li v-if="form.budget" class="flex items-start gap-2">
          <span>💰</span>
          <span><strong>Budget:</strong> ${{ form.budget }} {{ budgetType }}</span>
        </li>
        <li v-if="selectedItinerary" class="flex items-start gap-2">
          <span>🗓️</span>
          <span><strong>Itinerary:</strong> {{ selectedItinerary.title }} (attached)</span>
        </li>
      </ul>
    </div>

    <!-- Validation Errors -->
    <div v-if="Object.keys(errors).length > 0" class="mt-6 p-4 bg-red-50 border-2 border-red-200 rounded-xl">
      <p class="font-semibold text-red-900 mb-2">Please fix the following errors:</p>
      <ul class="text-sm text-red-700 space-y-1">
        <li v-for="(error, field) in errors" :key="field">• {{ error }}</li>
      </ul>
    </div>

    <!-- Publish Button -->
    <button
      @click="publishQuote"
      :disabled="!canPublish || publishing"
      class="mt-6 w-full bg-gradient-to-r from-cyan-500 to-teal-500 hover:from-cyan-600 hover:to-teal-600 disabled:from-gray-300 disabled:to-gray-400 text-white font-bold py-4 px-8 rounded-xl text-lg transition-all duration-200 flex items-center justify-center gap-3 shadow-lg hover:shadow-xl disabled:cursor-not-allowed"
    >
      <span v-if="publishing" class="animate-spin">⏳</span>
      <span v-else>📨</span>
      {{ publishing ? 'Publishing...' : 'Publish Quote Request' }}
    </button>
    <p class="text-center text-sm text-gray-500 mt-3">
      Operators will respond within 24-48 hours
    </p>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const form = ref({
  travel_window: '',
  travelers: 2,
  budget: null,
  notes: ''
})

const errors = ref({})
const publishing = ref(false)
const budgetType = ref('total')

const canPublish = computed(() => {
  return form.value.travel_window && form.value.travelers >= 1
})

const validateForm = () => {
  errors.value = {}
  
  if (!form.value.travel_window) {
    errors.value.travel_window = 'Travel dates are required'
  }
  
  if (!form.value.travelers || form.value.travelers < 1) {
    errors.value.travelers = 'At least 1 traveler is required'
  }
  
  return Object.keys(errors.value).length === 0
}

const publishQuote = async () => {
  if (!validateForm()) return
  
  publishing.value = true
  try {
    // Publish logic
    await quoteStore.publishQuote(form.value)
    // Success handling
  } catch (err) {
    // Error handling
  } finally {
    publishing.value = false
  }
}
</script>
```

---

## 📱 Mobile Responsiveness

### Breakpoints Strategy

```javascript
// Tailwind breakpoints
sm: '640px'  // Small devices
md: '768px'  // Tablets
lg: '1024px' // Desktops
xl: '1280px' // Large screens
```

### Mobile-Specific Adaptations

1. **Step Indicator:**
   - Horizontal scrollable steps on mobile
   - Sticky at top with reduced padding
   - Progress bar more prominent

2. **Location Search:**
   - Full-width input
   - Autocomplete as bottom sheet (not dropdown)
   - Larger touch targets (48px min)

3. **Bucket List:**
   - Vertical stack (no grid)
   - Swipe-to-delete gestures
   - Collapsible map preview

4. **Map Selector:**
   - Full-screen modal (no padding)
   - Bottom sheet for location details
   - Larger add button

5. **Form Fields:**
   - Full-width inputs
   - Stepper with larger touch areas
   - Sticky publish button at bottom

### Responsive Classes Example

```vue
<div class="
  grid grid-cols-1 lg:grid-cols-2
  gap-4 lg:gap-6
  p-4 lg:p-8
">
  <button class="
    text-sm lg:text-base
    py-2 lg:py-3
    px-4 lg:px-6
  ">
    Button Text
  </button>
</div>
```

---

## 🎨 Design System

### Color Palette

```css
/* Primary - Cyan/Teal gradient */
--primary-50: #ecfeff;
--primary-500: #06b6d4; /* Cyan */
--primary-600: #0891b2;
--primary-700: #0e7490;
--teal-500: #14b8a6;
--teal-600: #0d9488;

/* Accent - Orange for operators */
--accent-500: #f97316;
--accent-600: #ea580c;

/* Neutrals */
--gray-50: #f8fafc;
--gray-100: #f1f5f9;
--gray-300: #cbd5e1;
--gray-600: #475569;
--gray-900: #0f172a;

/* Status */
--success: #10b981;
--error: #ef4444;
--warning: #f59e0b;
```

### Typography

```css
/* Headings */
h1: 2.5rem (40px) font-bold
h2: 2rem (32px) font-bold
h3: 1.5rem (24px) font-semibold
h4: 1.25rem (20px) font-semibold

/* Body */
body: 1rem (16px) normal
small: 0.875rem (14px) normal
xs: 0.75rem (12px) normal
```

### Spacing System

```javascript
// Tailwind spacing scale
0.5 = 0.125rem (2px)
1 = 0.25rem (4px)
2 = 0.5rem (8px)
3 = 0.75rem (12px)
4 = 1rem (16px)
6 = 1.5rem (24px)
8 = 2rem (32px)
12 = 3rem (48px)
```

### Border Radius

```css
rounded-lg: 0.5rem (8px)
rounded-xl: 0.75rem (12px)
rounded-2xl: 1rem (16px)
rounded-full: 9999px (circle)
```

---

## ⚡ Performance Optimization

### Code Splitting

```javascript
// Lazy load heavy components
const MapSelector = defineAsyncComponent(() =>
  import('./components/MapSelector.vue')
)

const DatePicker = defineAsyncComponent(() =>
  import('@vuepic/vue-datepicker')
)
```

### Debouncing Search

```javascript
// Debounce autocomplete search
const debouncedSearch = useDebounceFn(async (query) => {
  const results = await searchPlaces(query)
  suggestions.value = results
}, 300)
```

### Virtual Scrolling

```javascript
// For large bucket lists (100+ items)
import { useVirtualList } from '@vueuse/core'

const { list, containerProps, wrapperProps } = useVirtualList(
  bucketItems,
  { itemHeight: 80 }
)
```

### Image Optimization

- Lazy load map tiles
- Use progressive JPEGs for location images
- Implement blur-up technique for thumbnails

---

## 🔒 Security & Validation

### Input Sanitization

```javascript
// Sanitize user inputs
import DOMPurify from 'dompurify'

const sanitizeInput = (input) => {
  return DOMPurify.sanitize(input, {
    ALLOWED_TAGS: [], // No HTML tags
    KEEP_CONTENT: true
  })
}
```

### Rate Limiting

```javascript
// Limit search requests
const searchRateLimit = useRateLimit(
  5, // requests
  60000 // per 60 seconds
)

const handleSearch = async () => {
  if (!searchRateLimit.check()) {
    toast.error('Too many searches. Please wait.')
    return
  }
  // Proceed with search
}
```

### XSS Protection

- Never use `v-html` with user content
- Sanitize all text inputs
- Escape special characters in notes field

---

## 🧪 Testing Strategy

### Unit Tests

```javascript
// LocationSearchBar.spec.js
describe('LocationSearchBar', () => {
  it('shows autocomplete after 2 characters', async () => {
    const wrapper = mount(LocationSearchBar)
    await wrapper.find('input').setValue('Ma')
    expect(wrapper.find('.autocomplete').exists()).toBe(true)
  })

  it('highlights item on hover', async () => {
    const wrapper = mount(LocationSearchBar)
    await wrapper.find('.suggestion-item').trigger('mouseenter')
    expect(wrapper.find('.suggestion-item').classes()).toContain('highlighted')
  })

  it('navigates suggestions with arrow keys', async () => {
    const wrapper = mount(LocationSearchBar)
    await wrapper.find('input').trigger('keydown.down')
    expect(wrapper.vm.highlightedIndex).toBe(0)
  })
})
```

### E2E Tests (Playwright)

```javascript
// quote-builder.spec.ts
test('complete quote request flow', async ({ page }) => {
  await page.goto('/quote-builder')
  
  // Step 1: Add location
  await page.fill('[placeholder*="Search"]', 'Manali')
  await page.click('text=Manali, Himachal Pradesh')
  await expect(page.locator('.bucket-item')).toHaveCount(1)
  
  // Navigate to Step 2
  await page.click('text=Step 2')
  
  // Fill form
  await page.fill('[placeholder*="Travel window"]', 'March 15-22')
  await page.fill('[type="number"]', '2')
  await page.fill('textarea', 'Looking for adventure activities')
  
  // Publish
  await page.click('text=Publish Quote Request')
  await expect(page.locator('text=Quote request published')).toBeVisible()
})
```

### Accessibility Tests

```javascript
// a11y.spec.js
import { axe } from 'jest-axe'

test('QuoteBuilder has no accessibility violations', async () => {
  const wrapper = mount(QuoteBuilder)
  const results = await axe(wrapper.element)
  expect(results).toHaveNoViolations()
})
```

---

## 📊 Analytics & Tracking

### Event Tracking

```javascript
// Track user interactions
const trackEvent = (category, action, label) => {
  // Google Analytics
  gtag('event', action, {
    event_category: category,
    event_label: label
  })
  
  // Mixpanel
  mixpanel.track(action, {
    category,
    label
  })
}

// Usage
trackEvent('QuoteBuilder', 'location_added', 'search')
trackEvent('QuoteBuilder', 'step_completed', 'step_1')
trackEvent('QuoteBuilder', 'quote_published', 'success')
```

### Funnel Analysis

```javascript
const funnelSteps = [
  { step: 'page_view', label: 'Visited Quote Builder' },
  { step: 'location_added', label: 'Added First Location' },
  { step: 'step_2_viewed', label: 'Viewed Step 2' },
  { step: 'form_filled', label: 'Filled Travel Details' },
  { step: 'quote_published', label: 'Published Quote' }
]
```

---

## 🚀 Implementation Phases

### Phase 1: Foundation (Week 1)
**Goal:** Step indicator and enhanced bucket

- [ ] Create `QuoteBuilderSteps.vue` component
- [ ] Implement step navigation logic
- [ ] Build `LocationBucket.vue` with enhanced design
- [ ] Add drag-to-reorder functionality
- [ ] Implement remove with undo
- [ ] Add animations for bucket operations
- [ ] Update state management in quotes store

**Deliverable:** Working step indicator + polished bucket list

### Phase 2: Search Enhancement (Week 1)
**Goal:** Perfect autocomplete experience

- [ ] Enhance `LocationSearchBar.vue` with keyboard nav
- [ ] Implement hover highlight effects
- [ ] Add selection animations
- [ ] Build search results cards
- [ ] Add "Added ✓" state for results
- [ ] Implement debounced search
- [ ] Add accessibility features

**Deliverable:** Intuitive search with instant feedback

### Phase 3: Map Selector (Week 2)
**Goal:** Expandable map interface

- [ ] Create `MapSelector.vue` modal component
- [ ] Build collapsed state with expand button
- [ ] Implement full-screen map modal
- [ ] Add reverse geocoding
- [ ] Implement "My Location" feature
- [ ] Add pin drop animation
- [ ] Build location details form

**Deliverable:** Complete map selection workflow

### Phase 4: Publish Form (Week 2)
**Goal:** Enhanced Step 2 experience

- [ ] Create `Step2PublishQuote.vue` component
- [ ] Integrate date picker component
- [ ] Build traveler stepper input
- [ ] Implement budget input with formatting
- [ ] Enhance notes textarea
- [ ] Build itinerary selector with previews
- [ ] Create request preview card
- [ ] Add form validation
- [ ] Implement publish logic with success state

**Deliverable:** Production-ready publish form

### Phase 5: Mobile & Polish (Week 3)
**Goal:** Responsive and polished

- [ ] Implement mobile-specific layouts
- [ ] Add touch gestures (swipe-to-delete)
- [ ] Create bottom sheets for mobile
- [ ] Add loading skeletons
- [ ] Implement error handling
- [ ] Add success animations
- [ ] Optimize performance
- [ ] Test on real devices

**Deliverable:** Mobile-optimized experience

### Phase 6: Testing & Launch (Week 3)
**Goal:** Production ready

- [ ] Write unit tests (80% coverage)
- [ ] Write E2E tests (critical paths)
- [ ] Accessibility audit and fixes
- [ ] Performance optimization
- [ ] Security review
- [ ] User acceptance testing
- [ ] Documentation
- [ ] Deploy to production

**Deliverable:** Launched feature

---

## 📦 Dependencies

### New Packages to Add

```json
{
  "dependencies": {
    "@vuepic/vue-datepicker": "^8.0.0",
    "@vueuse/core": "^10.0.0",
    "@vueuse/motion": "^2.0.0",
    "vue-draggable-next": "^2.2.1",
    "dompurify": "^3.0.0"
  },
  "devDependencies": {
    "@playwright/test": "^1.40.0",
    "jest-axe": "^8.0.0",
    "@vue/test-utils": "^2.4.0",
    "vitest": "^1.0.0"
  }
}
```

### Existing Dependencies (Keep)
- Vue 3.x
- Pinia
- Vue Router
- Axios
- Tailwind CSS
- Leaflet

---

## 🎯 Success Metrics

### User Experience Metrics
- **Time to first location added:** < 10 seconds
- **Completion rate:** > 70% (start to publish)
- **Error rate:** < 5% of submissions
- **Mobile usage:** > 40% of sessions

### Technical Metrics
- **Page load time:** < 2 seconds
- **Time to interactive:** < 3 seconds
- **Lighthouse score:** > 90
- **Bundle size:** < 300KB (gzipped)

### Business Metrics
- **Quote request volume:** +30%
- **Operator response rate:** > 80%
- **User satisfaction:** > 4.5/5 stars

---

## 🔄 Future Enhancements (Post-MVP)

### Advanced Features
1. **Multi-day itinerary builder** - Visual day-by-day planning
2. **Budget calculator** - Break down costs by category
3. **Weather forecasts** - Show weather for travel dates
4. **Social sharing** - Share bucket list with friends
5. **Collaborative planning** - Multiple users edit same quote
6. **Voice input** - Dictate notes to operators
7. **AI suggestions** - "People who went to X also visited Y"
8. **Photo upload** - Attach inspiration photos
9. **Video intro** - Record video message for operators
10. **Live chat** - Chat with operators during quote creation

---

## ✅ Review Checklist

Before implementation, confirm:

- [ ] All stakeholders reviewed and approved design
- [ ] UI/UX mockups finalized
- [ ] API endpoints confirmed (no changes needed)
- [ ] Development team capacity available
- [ ] Timeline realistic (3 weeks)
- [ ] Dependencies vetted and approved
- [ ] Security review completed
- [ ] Accessibility requirements met
- [ ] Mobile design approved
- [ ] Success metrics defined
- [ ] Testing strategy agreed upon
- [ ] Rollback plan in place

---

## 🎬 Next Steps

1. **Review this plan** with stakeholders
2. **Create UI mockups** using Figma/Sketch
3. **Get approval** from product owner
4. **Set up project board** (GitHub/Jira)
5. **Assign tasks** to frontend team
6. **Kick off Phase 1** implementation
7. **Weekly demos** to stakeholders
8. **Iterate** based on feedback

---

**Document Version:** 1.0  
**Last Updated:** August 7, 2026  
**Status:** Ready for Review  
**Estimated Effort:** 3 weeks (2 developers)  
**Priority:** High  
**Risk Level:** Low (building on solid foundation)

