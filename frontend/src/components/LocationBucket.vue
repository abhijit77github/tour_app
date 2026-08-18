<template>
  <div class="location-bucket">
    <!-- Header -->
    <div class="bucket-header">
      <div class="bucket-header-left">
        <h3 class="bucket-title">Your Destinations</h3>
        <p class="bucket-count">{{ bucketCount }} location{{ bucketCount !== 1 ? 's' : '' }} selected</p>
      </div>
      <button
        v-if="bucketCount > 0"
        @click="handleClearAll"
        class="btn-clear-all"
      >
        Clear All
      </button>
    </div>

    <!-- Map Preview -->
    <div
      v-if="bucketCount > 0"
      @click="$emit('expand-map')"
      class="map-preview"
      :class="{ 'is-clickable': allowMapExpand }"
    >
      <MapView
        :locations="mapLocations"
        :zoom="6"
        height="200px"
        :allow-selection="false"
      />
      <div v-if="allowMapExpand" class="map-overlay">
        <span class="map-overlay-text">🗺️ Click to expand map</span>
      </div>
    </div>

    <!-- Empty State -->
    <div v-if="bucketCount === 0" class="bucket-empty">
      <span class="empty-icon">🗺️</span>
      <p class="empty-title">No destinations yet</p>
      <p class="empty-subtitle">Search or drop a pin to start building your trip</p>
    </div>

    <!-- Bucket Items List -->
    <TransitionGroup
      v-else
      name="bucket-list"
      tag="div"
      class="bucket-list"
    >
      <div
        v-for="(item, index) in bucket"
        :key="item.id"
        class="bucket-item"
        :class="{
          'is-new': item.id === lastAddedId,
          'is-dragging': draggingIndex === index
        }"
        draggable="true"
        @dragstart="handleDragStart(index, $event)"
        @dragend="handleDragEnd"
        @dragover.prevent="handleDragOver(index, $event)"
        @drop="handleDrop(index)"
      >
        <!-- Drag Handle -->
        <div class="drag-handle" title="Drag to reorder">
          <span>⋮⋮</span>
        </div>

        <!-- Number Badge -->
        <div class="item-badge">{{ index + 1 }}</div>

        <!-- Content -->
        <div class="item-content">
          <div class="item-header">
            <span class="item-type-icon">{{ item.type === 'operator' ? '✈️' : '🌍' }}</span>
            <h4 class="item-name">{{ item.name }}</h4>
          </div>
          <p class="item-location">
            {{ [item.state, item.country].filter(Boolean).join(', ') || 'No location details' }}
          </p>
          <input
            v-model="item.notes"
            @blur="$emit('update-notes', index, item.notes)"
            type="text"
            placeholder="Add note for operators..."
            class="item-notes-input"
          />
        </div>

        <!-- Remove Button -->
        <button
          @click="handleRemove(index)"
          class="btn-remove"
          title="Remove location"
        >
          ×
        </button>
      </div>
    </TransitionGroup>

    <!-- Undo Snackbar -->
    <Transition name="snackbar">
      <div v-if="showUndoSnackbar" class="undo-snackbar">
        <span class="undo-message">Location removed</span>
        <button @click="handleUndo" class="btn-undo">
          Undo
        </button>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import MapView from './MapView.vue'

/**
 * @typedef {Object} Location
 * @property {string|number} id - Unique identifier
 * @property {string} name - Location name
 * @property {string} state - State/region
 * @property {string} country - Country
 * @property {Object} coordinates - Lat/lng coordinates
 * @property {string} notes - User notes
 * @property {string} type - Location type (operator/global/custom)
 */

/**
 * @typedef {Object} Props
 * @property {Location[]} bucket - Array of locations
 * @property {string|number|null} lastAddedId - ID of last added location for animation
 * @property {boolean} allowMapExpand - Whether map can be expanded
 */

const props = defineProps({
  bucket: {
    type: Array,
    required: true,
    default: () => []
  },
  lastAddedId: {
    type: [String, Number],
    default: null
  },
  allowMapExpand: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits(['remove', 'clear-all', 'undo', 'reorder', 'update-notes', 'expand-map'])

const draggingIndex = ref(null)
const dragOverIndex = ref(null)
const showUndoSnackbar = ref(false)
const undoTimer = ref(null)

const bucketCount = computed(() => props.bucket.length)

const mapLocations = computed(() => {
  return props.bucket
    .filter(loc => loc.coordinates)
    .map(loc => ({
      lat: loc.coordinates.latitude,
      lng: loc.coordinates.longitude,
      title: loc.name,
      description: [loc.state, loc.country].filter(Boolean).join(', ')
    }))
})

/**
 * Handle drag start
 * @param {number} index - Item index
 * @param {DragEvent} event - Drag event
 */
const handleDragStart = (index, event) => {
  draggingIndex.value = index
  event.dataTransfer.effectAllowed = 'move'
  event.dataTransfer.setData('text/html', event.target.innerHTML)
}

/**
 * Handle drag end
 */
const handleDragEnd = () => {
  draggingIndex.value = null
  dragOverIndex.value = null
}

/**
 * Handle drag over
 * @param {number} index - Item index being dragged over
 * @param {DragEvent} event - Drag event
 */
const handleDragOver = (index, event) => {
  event.preventDefault()
  dragOverIndex.value = index
}

/**
 * Handle drop
 * @param {number} newIndex - Drop target index
 */
const handleDrop = (newIndex) => {
  if (draggingIndex.value !== null && draggingIndex.value !== newIndex) {
    emit('reorder', draggingIndex.value, newIndex)
  }
  draggingIndex.value = null
  dragOverIndex.value = null
}

/**
 * Handle item removal
 * @param {number} index - Item index to remove
 */
const handleRemove = (index) => {
  emit('remove', index)
  
  // Show undo snackbar
  showUndoSnackbar.value = true
  
  // Clear previous timer
  if (undoTimer.value) {
    clearTimeout(undoTimer.value)
  }
  
  // Hide snackbar after 5 seconds
  undoTimer.value = setTimeout(() => {
    showUndoSnackbar.value = false
  }, 5000)
}

/**
 * Handle undo
 */
const handleUndo = () => {
  emit('undo')
  showUndoSnackbar.value = false
  
  if (undoTimer.value) {
    clearTimeout(undoTimer.value)
    undoTimer.value = null
  }
}

/**
 * Handle clear all
 */
const handleClearAll = () => {
  if (confirm(`Remove all ${bucketCount.value} locations?`)) {
    emit('clear-all')
  }
}

// Watch for undo snackbar to auto-hide
watch(showUndoSnackbar, (newVal) => {
  if (!newVal && undoTimer.value) {
    clearTimeout(undoTimer.value)
    undoTimer.value = null
  }
})
</script>

<style scoped>
/* Container */
.location-bucket {
  background: white;
  border-radius: 1.25rem;
  box-shadow: 0 8px 32px rgba(15, 23, 42, 0.09);
  border: 1px solid #f1f5f9;
  padding: 1.5rem;
}

/* Header */
.bucket-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1.25rem;
}

.bucket-header-left {
  flex: 1;
}

.bucket-title {
  font-size: 1.125rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.25rem;
}

.bucket-count {
  font-size: 0.875rem;
  color: #64748b;
  margin: 0;
}

.btn-clear-all {
  font-size: 0.875rem;
  font-weight: 600;
  color: #ef4444;
  background: transparent;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-clear-all:hover {
  background: #fee2e2;
  color: #dc2626;
}

/* Map Preview */
.map-preview {
  height: 200px;
  border-radius: 0.75rem;
  overflow: hidden;
  border: 2px solid #e2e8f0;
  margin-bottom: 1.25rem;
  position: relative;
  transition: all 0.2s ease;
}

.map-preview.is-clickable {
  cursor: pointer;
}

.map-preview.is-clickable:hover {
  border-color: #06b6d4;
  box-shadow: 0 4px 16px rgba(6, 182, 212, 0.2);
}

.map-overlay {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: linear-gradient(to top, rgba(15, 23, 42, 0.8), transparent);
  padding: 1rem;
  opacity: 0;
  transition: opacity 0.2s ease;
}

.map-preview.is-clickable:hover .map-overlay {
  opacity: 1;
}

.map-overlay-text {
  color: white;
  font-size: 0.875rem;
  font-weight: 600;
  display: block;
  text-align: center;
}

/* Empty State */
.bucket-empty {
  text-align: center;
  padding: 3rem 1rem;
}

.empty-icon {
  font-size: 3rem;
  display: block;
  margin-bottom: 1rem;
  opacity: 0.5;
}

.empty-title {
  font-size: 1rem;
  font-weight: 600;
  color: #475569;
  margin: 0 0 0.5rem;
}

.empty-subtitle {
  font-size: 0.875rem;
  color: #94a3b8;
  margin: 0;
}

/* Bucket List */
.bucket-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

/* Bucket Item */
.bucket-item {
  display: flex;
  align-items: flex-start;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 0.75rem;
  border: 2px solid #e2e8f0;
  background: white;
  transition: all 0.2s ease;
  position: relative;
}

.bucket-item:hover {
  border-color: #a5f3fc;
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.1);
}

.bucket-item.is-new {
  animation: itemAdded 0.5s ease-out;
  border-color: #14b8a6;
  background: linear-gradient(135deg, #ecfeff 0%, #f0fdfa 100%);
}

.bucket-item.is-dragging {
  opacity: 0.5;
  cursor: grabbing;
}

/* Drag Handle */
.drag-handle {
  flex-shrink: 0;
  width: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #cbd5e1;
  cursor: grab;
  transition: color 0.2s ease;
}

.drag-handle:hover {
  color: #64748b;
}

.drag-handle:active {
  cursor: grabbing;
}

/* Item Badge */
.item-badge {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  background: linear-gradient(135deg, #06b6d4 0%, #14b8a6 100%);
  color: white;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 0.875rem;
}

/* Item Content */
.item-content {
  flex: 1;
  min-width: 0;
}

.item-header {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.25rem;
}

.item-type-icon {
  font-size: 1rem;
}

.item-name {
  font-size: 0.95rem;
  font-weight: 600;
  color: #0f172a;
  margin: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-location {
  font-size: 0.8rem;
  color: #64748b;
  margin: 0 0 0.5rem;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.item-notes-input {
  width: 100%;
  padding: 0.5rem 0.75rem;
  border: 1px solid #e2e8f0;
  border-radius: 0.5rem;
  font-size: 0.8rem;
  color: #475569;
  transition: all 0.2s ease;
}

.item-notes-input:focus {
  outline: none;
  border-color: #06b6d4;
  ring: 2px;
  ring-color: rgba(6, 182, 212, 0.2);
}

.item-notes-input::placeholder {
  color: #cbd5e1;
}

/* Remove Button */
.btn-remove {
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border-radius: 50%;
  border: none;
  background: transparent;
  color: #94a3b8;
  font-size: 1.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-remove:hover {
  background: #fee2e2;
  color: #ef4444;
}

/* Undo Snackbar */
.undo-snackbar {
  position: fixed;
  bottom: 2rem;
  left: 50%;
  transform: translateX(-50%);
  background: #0f172a;
  color: white;
  padding: 1rem 1.5rem;
  border-radius: 0.75rem;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.3);
  display: flex;
  align-items: center;
  gap: 1rem;
  z-index: 1000;
}

.undo-message {
  font-size: 0.875rem;
  font-weight: 500;
}

.btn-undo {
  background: #06b6d4;
  color: white;
  border: none;
  padding: 0.5rem 1rem;
  border-radius: 0.5rem;
  font-size: 0.875rem;
  font-weight: 600;
  cursor: pointer;
  transition: background 0.2s ease;
}

.btn-undo:hover {
  background: #0891b2;
}

/* Animations */
@keyframes itemAdded {
  0% {
    opacity: 0;
    transform: translateY(-20px) scale(0.8) rotate(-2deg);
  }
  40% {
    transform: translateY(0) scale(1.08) rotate(1deg);
  }
  60% {
    transform: translateY(-5px) scale(1.05) rotate(-0.5deg);
  }
  80% {
    transform: translateY(0) scale(1.02) rotate(0.2deg);
  }
  100% {
    opacity: 1;
    transform: translateY(0) scale(1) rotate(0deg);
  }
}

/* List Transitions */
.bucket-list-move,
.bucket-list-enter-active,
.bucket-list-leave-active {
  transition: all 0.3s ease;
}

.bucket-list-enter-from {
  opacity: 0;
  transform: translateY(-20px);
}

.bucket-list-leave-to {
  opacity: 0;
  transform: translateX(20px);
}

.bucket-list-leave-active {
  position: absolute;
  width: 100%;
}

/* Snackbar Transitions */
.snackbar-enter-active,
.snackbar-leave-active {
  transition: all 0.3s ease;
}

.snackbar-enter-from,
.snackbar-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(20px);
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .location-bucket {
    padding: 1rem;
  }

  .bucket-title {
    font-size: 1rem;
  }

  .bucket-count {
    font-size: 0.8rem;
  }

  .map-preview {
    height: 150px;
  }

  .bucket-item {
    padding: 0.75rem;
  }

  .drag-handle {
    display: none;
  }

  .item-badge {
    width: 1.75rem;
    height: 1.75rem;
    font-size: 0.75rem;
  }

  .item-name {
    font-size: 0.875rem;
  }

  .item-location {
    font-size: 0.75rem;
  }

  .undo-snackbar {
    bottom: 1rem;
    left: 1rem;
    right: 1rem;
    transform: none;
  }
}
</style>
