<template>
  <div class="map-selector">
    <!-- Collapsed State: Expand Button -->
    <div v-if="!isExpanded" class="map-selector-collapsed">
      <button @click="expandMap" class="btn-expand-map">
        <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
          <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
          <circle cx="12" cy="10" r="3"></circle>
        </svg>
        <span>Drop a pin on the map</span>
        <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
          <polyline points="9 18 15 12 9 6"></polyline>
        </svg>
      </button>
      <p class="map-selector-hint">Click to open interactive map and select coordinates</p>
    </div>

    <!-- Expanded State: Full-Screen Modal -->
    <Teleport to="body">
      <Transition name="modal">
        <div v-if="isExpanded" class="map-modal-overlay" @click.self="closeMap">
          <div class="map-modal-container">
            <!-- Modal Header -->
            <div class="map-modal-header">
              <div class="map-modal-title">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M21 10c0 7-9 13-9 13s-9-6-9-13a9 9 0 0 1 18 0z"></path>
                  <circle cx="12" cy="10" r="3"></circle>
                </svg>
                <h3>Select Location on Map</h3>
                <span v-if="locationsAdded > 0" class="header-badge">{{ locationsAdded }} added</span>
              </div>
              <button @click="closeMap" class="btn-close-modal" aria-label="Close map">
                <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <line x1="18" y1="6" x2="6" y2="18"></line>
                  <line x1="6" y1="6" x2="18" y2="18"></line>
                </svg>
              </button>
            </div>

            <!-- Map -->
            <div class="map-modal-map">
              <!-- Loading Spinner -->
              <div v-if="!showMap" class="map-loading">
                <div class="spinner"></div>
                <p>Initializing map...</p>
              </div>

              <MapView
                v-show="showMap"
                v-model="selectedCoordinates"
                :allow-selection="true"
                :show-coordinates="true"
                :center="mapCenter"
                :zoom="12"
                height="100%"
                @location-selected="handleLocationSelected"
              />
              
              <!-- Instructions Overlay -->
              <div v-if="showMap && !selectedCoordinates" class="map-instructions">
                <div class="map-instructions-content">
                  <svg width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"></path>
                    <polyline points="9 22 9 12 15 12 15 22"></polyline>
                  </svg>
                  <p>Click anywhere on the map to drop a pin</p>
                </div>
              </div>
            </div>

            <!-- Success Message (shown after adding location) -->
            <Transition name="fade">
              <div v-if="successMessage && !selectedCoordinates" class="success-banner">
                <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                  <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"></path>
                  <polyline points="22 4 12 14.01 9 11.01"></polyline>
                </svg>
                <span>{{ successMessage }}</span>
                <span class="success-count" v-if="locationsAdded > 0">{{ locationsAdded }} added</span>
              </div>
            </Transition>

            <!-- Location Form (shown after selecting coordinates) -->
            <Transition name="slide-up">
              <div v-if="selectedCoordinates" class="map-modal-form">
                <div class="form-header">
                  <h4>Location Details</h4>
                  <p>Fill in the details for your selected location</p>
                </div>

                <div class="form-grid">
                  <div class="form-field form-field-full">
                    <label for="location-name">Location Name *</label>
                    <input
                      id="location-name"
                      v-model="locationForm.name"
                      type="text"
                      placeholder="e.g., Eiffel Tower, My Hotel, Beach Resort"
                      @keyup.enter="handleAddLocation"
                    />
                  </div>

                  <div class="form-field">
                    <label for="location-state">State / Region</label>
                    <input
                      id="location-state"
                      v-model="locationForm.state"
                      type="text"
                      placeholder="e.g., California, Île-de-France"
                    />
                  </div>

                  <div class="form-field">
                    <label for="location-country">Country</label>
                    <input
                      id="location-country"
                      v-model="locationForm.country"
                      type="text"
                      placeholder="e.g., USA, France, India"
                    />
                  </div>

                  <div class="form-field form-field-full">
                    <label for="location-notes">Notes (Optional)</label>
                    <textarea
                      id="location-notes"
                      v-model="locationForm.notes"
                      rows="2"
                      placeholder="Add any notes for operators..."
                    ></textarea>
                  </div>
                </div>

                <div v-if="formError" class="form-error">{{ formError }}</div>

                <div class="form-actions">
                  <button @click="resetSelection" class="btn-reset">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="1 4 1 10 7 10"></polyline>
                      <path d="M3.51 15a9 9 0 1 0 2.13-9.36L1 10"></path>
                    </svg>
                    Reset Selection
                  </button>
                  <button @click="handleAddLocation" class="btn-add-location" :disabled="!locationForm.name.trim()">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <line x1="12" y1="5" x2="12" y2="19"></line>
                      <line x1="5" y1="12" x2="19" y2="12"></line>
                    </svg>
                    Add & Continue
                  </button>
                  <button @click="handleDone" class="btn-done">
                    <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round">
                      <polyline points="20 6 9 17 4 12"></polyline>
                    </svg>
                    {{ selectedCoordinates && locationForm.name.trim() ? 'Add & Done' : 'Done' }}
                  </button>
                </div>
              </div>
            </Transition>
          </div>
        </div>
      </Transition>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, computed, nextTick } from 'vue'
import MapView from './MapView.vue'

/**
 * @typedef {Object} Props
 * @property {Object} defaultCenter - Default map center { lat, lng }
 */

const props = defineProps({
  defaultCenter: {
    type: Object,
    default: () => ({ lat: 28.6139, lng: 77.2090 }) // Default: New Delhi
  }
})

const emit = defineEmits(['add-location'])

const isExpanded = ref(false)
const showMap = ref(false) // Control when MapView renders
const selectedCoordinates = ref(null)
const formError = ref('')
const successMessage = ref('')
const locationsAdded = ref(0) // Track how many locations added in this session

const locationForm = reactive({
  name: '',
  state: '',
  country: '',
  notes: ''
})

const mapCenter = computed(() => props.defaultCenter)

/**
 * Expand the map modal
 */
const expandMap = () => {
  console.log('Expanding map modal...');
  isExpanded.value = true
  showMap.value = false // Start with map hidden
  // Lock body scroll
  document.body.style.overflow = 'hidden'
  // Wait for modal to be fully rendered, then show map
  setTimeout(() => {
    console.log('Showing map after modal transition');
    showMap.value = true
  }, 600)
}

/**
 * Close the map modal
 */
const closeMap = () => {
  isExpanded.value = false
  showMap.value = false // Hide map immediately on close
  resetSelection()
  locationsAdded.value = 0
  successMessage.value = ''
  // Unlock body scroll
  document.body.style.overflow = ''
}

/**
 * Handle Done button - adds pending location if exists, then closes
 */
const handleDone = () => {
  // If there's a pending location with a name, add it first
  if (selectedCoordinates.value && locationForm.name.trim()) {
    console.log('Adding pending location before closing...');
    
    // Try to add the location
    handleAddLocation();
    
    // Check if there was a validation error
    if (!formError.value) {
      // Successfully added, close the modal after brief delay
      setTimeout(() => {
        closeMap();
      }, 150);
    }
    // If there was an error, keep modal open so user can fix it
  } else {
    // No pending location, just close
    closeMap();
  }
}

/**
 * Handle location selected on map
 * @param {Object} location - { lat, lng }
 */
const handleLocationSelected = (location) => {
  console.log('Location selected:', location);
  selectedCoordinates.value = {
    latitude: location.lat,
    longitude: location.lng
  }
  console.log('selectedCoordinates set to:', selectedCoordinates.value);
}

/**
 * Reset selection and form
 */
const resetSelection = () => {
  selectedCoordinates.value = null
  locationForm.name = ''
  locationForm.state = ''
  locationForm.country = ''
  locationForm.notes = ''
  formError.value = ''
  successMessage.value = ''
}

/**
 * Add location to bucket
 */
const handleAddLocation = () => {
  console.log('handleAddLocation called');
  formError.value = ''

  if (!locationForm.name.trim()) {
    formError.value = 'Please enter a location name'
    console.log('Validation failed: no name');
    return
  }

  if (!selectedCoordinates.value) {
    formError.value = 'Please select coordinates on the map'
    console.log('Validation failed: no coordinates');
    return
  }

  const locationData = {
    name: locationForm.name.trim(),
    state: locationForm.state.trim(),
    country: locationForm.country.trim(),
    notes: locationForm.notes.trim(),
    coordinates: selectedCoordinates.value,
    type: 'custom_pin'
  };

  console.log('Emitting add-location with data:', locationData);
  
  // Emit the location to parent
  emit('add-location', locationData);

  // Show success message and increment counter
  locationsAdded.value++;
  successMessage.value = `Location "${locationData.name}" added successfully!`;
  
  // Reset form for next location but keep modal open
  resetSelection();
  
  // Hide success message after 3 seconds
  setTimeout(() => {
    successMessage.value = '';
  }, 3000);
}
</script>

<style scoped>
/* Collapsed State */
.map-selector-collapsed {
  text-align: center;
  padding: 1.5rem;
}

.btn-expand-map {
  display: inline-flex;
  align-items: center;
  gap: 0.75rem;
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  color: white;
  border: none;
  border-radius: 12px;
  padding: 1rem 1.5rem;
  font-size: 0.95rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.25);
}

.btn-expand-map:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(6, 182, 212, 0.35);
}

.btn-expand-map:active {
  transform: translateY(0);
}

.map-selector-hint {
  margin-top: 0.75rem;
  font-size: 0.8rem;
  color: #64748b;
}

/* Modal Overlay */
.map-modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.75);
  backdrop-filter: blur(4px);
  z-index: 9999;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1rem;
}

.map-modal-container {
  width: 100%;
  max-width: 1200px;
  max-height: 90vh;
  background: white;
  border-radius: 20px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  position: relative;
}

/* Modal Header */
.map-modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.5rem 2rem;
  border-bottom: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
}

.map-modal-title {
  display: flex;
  align-items: center;
  gap: 0.75rem;
}

.map-modal-title svg {
  color: #06b6d4;
}

.map-modal-title h3 {
  font-size: 1.25rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
}

.header-badge {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  padding: 0.375rem 0.875rem;
  border-radius: 20px;
  font-size: 0.8rem;
  font-weight: 700;
  letter-spacing: 0.025em;
  box-shadow: 0 2px 8px rgba(16, 185, 129, 0.25);
}

.btn-close-modal {
  width: 2.5rem;
  height: 2.5rem;
  display: flex;
  align-items: center;
  justify-content: center;
  background: transparent;
  border: none;
  border-radius: 50%;
  cursor: pointer;
  color: #64748b;
  transition: all 0.2s ease;
}

.btn-close-modal:hover {
  background: #f1f5f9;
  color: #0f172a;
}

/* Map Container */
.map-modal-map {
  flex: 1;
  position: relative;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}

/* Loading Spinner */
.map-loading {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #f8fafc;
  gap: 1rem;
  z-index: 10;
}

.map-loading p {
  margin: 0;
  font-size: 0.95rem;
  font-weight: 600;
  color: #64748b;
}

.spinner {
  width: 48px;
  height: 48px;
  border: 4px solid #e2e8f0;
  border-top-color: #06b6d4;
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}

@keyframes spin {
  to { transform: rotate(360deg); }
}

/* Instructions Overlay */
.map-instructions {
  position: absolute;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(15, 23, 42, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  pointer-events: none;
  z-index: 100;
}

.map-instructions-content {
  background: white;
  padding: 2rem 3rem;
  border-radius: 16px;
  box-shadow: 0 10px 40px rgba(0, 0, 0, 0.2);
  text-align: center;
  pointer-events: none;
}

.map-instructions-content svg {
  color: #06b6d4;
  margin-bottom: 1rem;
  pointer-events: none;
}

.map-instructions-content p {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
  pointer-events: none;
}

/* Success Banner */
.success-banner {
  position: absolute;
  top: 1rem;
  left: 50%;
  transform: translateX(-50%);
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
  padding: 0.875rem 1.5rem;
  border-radius: 12px;
  box-shadow: 0 4px 20px rgba(16, 185, 129, 0.4);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  z-index: 200;
  font-weight: 600;
  font-size: 0.95rem;
  backdrop-filter: blur(8px);
}

.success-banner svg {
  flex-shrink: 0;
}

.success-count {
  background: rgba(255, 255, 255, 0.25);
  padding: 0.25rem 0.625rem;
  border-radius: 20px;
  font-size: 0.85rem;
  margin-left: auto;
}

/* Location Form */
.map-modal-form {
  padding: 2rem 2.5rem;
  border-top: 2px solid #e2e8f0;
  background: linear-gradient(to bottom, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 -4px 12px rgba(0, 0, 0, 0.05);
  max-height: 50vh;
  overflow-y: auto;
  flex-shrink: 0;
}

.form-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 1px solid #e2e8f0;
}

.form-header h4 {
  font-size: 1.1rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0 0 0.5rem;
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.form-header h4::before {
  content: '📍';
  font-size: 1.2rem;
}

.form-header p {
  font-size: 0.9rem;
  color: #64748b;
  margin: 0;
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.25rem;
  margin-bottom: 1.5rem;
}

.form-field {
  display: flex;
  flex-direction: column;
  gap: 0.625rem;
}

.form-field-full {
  grid-column: 1 / -1;
}

.form-field label {
  font-size: 0.875rem;
  font-weight: 700;
  color: #475569;
  letter-spacing: 0.01em;
}

.form-field input,
.form-field textarea {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.95rem;
  color: #0f172a;
  font-family: inherit;
  background: white;
  transition: all 0.2s ease;
}

.form-field input:focus,
.form-field textarea:focus {
  outline: none;
  border-color: #06b6d4;
  background: #ffffff;
  box-shadow: 0 0 0 4px rgba(6, 182, 212, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08);
  transform: translateY(-1px);
}

.form-field input::placeholder,
.form-field textarea::placeholder {
  color: #cbd5e1;
}

.form-field textarea {
  resize: vertical;
  min-height: 60px;
}

.form-error {
  background: linear-gradient(135deg, #fee2e2 0%, #fecaca 100%);
  border: 2px solid #fca5a5;
  border-radius: 10px;
  padding: 1rem;
  margin-bottom: 1rem;
  color: #dc2626;
  font-size: 0.9rem;
  font-weight: 600;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  box-shadow: 0 2px 8px rgba(220, 38, 38, 0.1);
}

.form-error::before {
  content: '⚠️';
  font-size: 1.2rem;
}

.form-actions {
  display: flex;
  gap: 0.75rem;
  align-items: center;
  flex-wrap: wrap;
}

.btn-reset {
  margin-right: auto;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.5rem;
  background: white;
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 600;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.btn-reset:hover {
  background: #f8fafc;
  border-color: #cbd5e1;
  color: #475569;
  transform: translateY(-1px);
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.08);
}

.btn-add-location {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 2rem;
  background: linear-gradient(135deg, #06b6d4 0%, #0891b2 100%);
  border: none;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 700;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
}

.btn-add-location:hover:not(:disabled) {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(6, 182, 212, 0.4);
  background: linear-gradient(135deg, #0891b2 0%, #0e7490 100%);
}

.btn-add-location:active:not(:disabled) {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.3);
}

.btn-add-location:disabled {
  opacity: 0.5;
  cursor: not-allowed;
  transform: none;
  box-shadow: 0 2px 8px rgba(6, 182, 212, 0.2);
}

.btn-done {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  padding: 0.875rem 1.75rem;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 100%);
  border: none;
  border-radius: 10px;
  font-size: 0.95rem;
  font-weight: 700;
  color: white;
  cursor: pointer;
  transition: all 0.2s ease;
  box-shadow: 0 4px 12px rgba(15, 23, 42, 0.3);
}

.btn-done:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 20px rgba(15, 23, 42, 0.4);
  background: linear-gradient(135deg, #1e293b 0%, #334155 100%);
}

.btn-done:active {
  transform: translateY(0);
  box-shadow: 0 2px 8px rgba(15, 23, 42, 0.3);
}

/* Animations */
.modal-enter-active,
.modal-leave-active {
  transition: opacity 0.3s ease;
}

.modal-enter-from,
.modal-leave-to {
  opacity: 0;
}

.modal-enter-active .map-modal-container,
.modal-leave-active .map-modal-container {
  transition: transform 0.3s ease;
}

.modal-enter-from .map-modal-container,
.modal-leave-to .map-modal-container {
  transform: scale(0.95) translateY(20px);
}

.slide-up-enter-active,
.slide-up-leave-active {
  transition: all 0.3s ease;
}

.slide-up-enter-from,
.slide-up-leave-to {
  opacity: 0;
  transform: translateY(20px);
}

.fade-enter-active,
.fade-leave-active {
  transition: all 0.3s ease;
}

.fade-enter-from,
.fade-leave-to {
  opacity: 0;
  transform: translateX(-50%) translateY(-10px);
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .map-modal-overlay {
    padding: 0;
  }

  .map-modal-container {
    max-height: 100vh;
    border-radius: 0;
    max-width: none;
  }

  .map-modal-header {
    padding: 1rem 1.5rem;
  }

  .map-modal-title h3 {
    font-size: 1rem;
  }

  .map-modal-form {
    padding: 1.25rem 1.5rem;
  }

  .form-grid {
    grid-template-columns: 1fr;
  }

  .form-actions {
    flex-direction: column;
    gap: 0.75rem;
  }

  .btn-reset,
  .btn-add-location,
  .btn-done {
    width: 100%;
    justify-content: center;
  }

  .success-banner {
    left: 1rem;
    right: 1rem;
    transform: none;
    font-size: 0.875rem;
    padding: 0.75rem 1rem;
  }
}
</style>
