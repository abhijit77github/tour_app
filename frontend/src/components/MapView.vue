<template>
  <div class="map-view-container" :style="{ height: height }">
    <div ref="mapContainer" class="map-container" :style="{ height: '100%' }"></div>
    
    <div v-if="showCoordinates && selectedLocation" class="coordinates-display">
      <strong>Selected Location:</strong>
      <span>Lat: {{ selectedLocation.lat.toFixed(6) }}, Lng: {{ selectedLocation.lng.toFixed(6) }}</span>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted, watch, nextTick } from 'vue';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';

const props = defineProps({
  modelValue: {
    type: Object,
    default: null // { latitude, longitude }
  },
  locations: {
    type: Array,
    default: () => [] // [{ lat, lng, title, description }]
  },
  center: {
    type: Object,
    default: () => ({ lat: 28.6139, lng: 77.2090 }) // Default: New Delhi
  },
  zoom: {
    type: Number,
    default: 12
  },
  height: {
    type: String,
    default: '400px'
  },
  allowSelection: {
    type: Boolean,
    default: false
  },
  showCoordinates: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['update:modelValue', 'location-selected']);

const mapContainer = ref(null);
const map = ref(null);
const markers = ref([]);
const selectedLocation = ref(null);

// Fix Leaflet default marker icon issue
delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png'
});

onMounted(() => {
  console.log('MapView mounted, waiting before initializing...');
  // Delay initialization to ensure container is visible and has dimensions
  setTimeout(() => {
    initializeMap();
  }, 100);
});

const initializeMap = () => {
  if (!mapContainer.value) {
    console.error('Map container ref is null');
    return;
  }

  console.log('Map container dimensions:', {
    width: mapContainer.value.offsetWidth,
    height: mapContainer.value.offsetHeight,
    clientWidth: mapContainer.value.clientWidth,
    clientHeight: mapContainer.value.clientHeight
  });

  if (mapContainer.value.offsetHeight === 0) {
    console.warn('Map container has zero height, retrying...');
    setTimeout(initializeMap, 200);
    return;
  }

  // Initialize map
  const initialCenter = props.modelValue 
    ? [props.modelValue.latitude, props.modelValue.longitude]
    : [props.center.lat, props.center.lng];

  try {
    map.value = L.map(mapContainer.value).setView(initialCenter, props.zoom);
    console.log('Map instance created successfully');

    // Add tile layer
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
      attribution: '© OpenStreetMap contributors',
      maxZoom: 19
    }).addTo(map.value);

    console.log('Tiles added to map');

    // Add click handler for selection
    if (props.allowSelection) {
      map.value.on('click', handleMapClick);
      console.log('Click handler registered for map selection');
    }

    // Force map to recalculate size after rendering
    setTimeout(() => {
      if (map.value) {
        map.value.invalidateSize();
        console.log('Map size invalidated');
      }
    }, 200);

    // Add existing locations
    if (props.locations.length > 0) {
      addLocationMarkers();
    }

    // Add initial marker if model value exists
    if (props.modelValue) {
      addMarker(props.modelValue.latitude, props.modelValue.longitude, 'Selected Location');
    }
  } catch (error) {
    console.error('Error initializing map:', error);
  }
};

const handleMapClick = (e) => {
  const { lat, lng } = e.latlng;
  selectedLocation.value = { lat, lng };
  console.log('Map clicked at:', { lat, lng });
  
  // Clear existing markers and add new marker at clicked location
  clearMarkers();
  addMarker(lat, lng, 'Selected Location', true);
  
  // Immediately set the model value; saving is handled by parent form
  const coordinates = { latitude: lat, longitude: lng };
  emit('update:modelValue', coordinates);
  emit('location-selected', { lat, lng }); // Emit with lat/lng for consistency
};

const addMarker = (lat, lng, title = '', isSelected = false) => {
  let icon;
  
  if (isSelected) {
    // Create a custom red marker using SVG data URL
    const redMarkerSvg = `
      <svg width="25" height="41" viewBox="0 0 25 41" xmlns="http://www.w3.org/2000/svg">
        <path d="M12.5 0C5.6 0 0 5.6 0 12.5c0 8.4 12.5 28.5 12.5 28.5S25 20.9 25 12.5C25 5.6 19.4 0 12.5 0z" 
              fill="#DC2626" stroke="#991B1B" stroke-width="1"/>
        <circle cx="12.5" cy="12.5" r="4" fill="white"/>
      </svg>
    `;
    const redMarkerUrl = 'data:image/svg+xml;base64,' + btoa(redMarkerSvg);
    
    icon = L.icon({
      iconUrl: redMarkerUrl,
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41],
      popupAnchor: [1, -34],
      shadowSize: [41, 41]
    });
  } else {
    icon = L.icon({
      iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
      iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
      shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
      iconSize: [25, 41],
      iconAnchor: [12, 41],
      popupAnchor: [1, -34],
      shadowSize: [41, 41]
    });
  }

  const marker = L.marker([lat, lng], { icon })
    .addTo(map.value)
    .bindPopup(title);

  markers.value.push(marker);
  return marker;
};

const addLocationMarkers = () => {
  props.locations.forEach(location => {
    const marker = addMarker(
      location.lat,
      location.lng,
      location.title || 'Location',
      false
    );
    
    if (location.description) {
      marker.bindPopup(`<strong>${location.title || 'Location'}</strong><br>${location.description}`);
    }
  });

  // Fit bounds to show all markers
  if (markers.value.length > 0) {
    const group = L.featureGroup(markers.value);
    map.value.fitBounds(group.getBounds().pad(0.1));
  }
};

const clearMarkers = () => {
  markers.value.forEach(marker => map.value.removeLayer(marker));
  markers.value = [];
};

// Confirm button removed; selection is immediate on map click

// Watch for location changes
watch(() => props.locations, () => {
  if (map.value) {
    clearMarkers();
    addLocationMarkers();
  }
}, { deep: true });

// Watch for model value changes
watch(() => props.modelValue, (newVal) => {
  if (map.value && newVal) {
    clearMarkers();
    addMarker(newVal.latitude, newVal.longitude, 'Selected Location', true);
    map.value.setView([newVal.latitude, newVal.longitude], props.zoom);
  }
}, { deep: true });
</script>

<style scoped>
.map-view-container {
  position: relative;
  width: 100%;
  height: 100%;
  min-height: 400px;
  display: flex;
  flex-direction: column;
  z-index: 1;
}

.map-container {
  width: 100%;
  height: 100%;
  min-height: 400px;
  flex: 1;
  border-radius: 0;
  overflow: hidden;
  border: none;
  z-index: 1;
  background: #e5e7eb;
}

.coordinates-display {
  position: absolute;
  bottom: 1rem;
  left: 50%;
  transform: translateX(-50%);
  padding: 0.75rem 1.25rem;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border-radius: 8px;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.15);
  display: flex;
  align-items: center;
  gap: 0.75rem;
  z-index: 1000;
  pointer-events: none;
}

.coordinates-display strong {
  color: #333;
}

.coordinates-display span {
  color: #666;
  font-family: monospace;
}

.confirm-btn {
  padding: 6px 12px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.9em;
  transition: background 0.3s;
}

.confirm-btn:hover {
  background: #45a049;
}
</style>
