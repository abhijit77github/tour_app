<template>
  <div class="map-view-container">
    <div ref="mapContainer" class="map-container" :style="{ height: height }"></div>
    
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
  initializeMap();
});

const initializeMap = () => {
  if (!mapContainer.value) return;

  // Initialize map
  const initialCenter = props.modelValue 
    ? [props.modelValue.latitude, props.modelValue.longitude]
    : [props.center.lat, props.center.lng];

  map.value = L.map(mapContainer.value).setView(initialCenter, props.zoom);

  // Add tile layer
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    attribution: '© OpenStreetMap contributors',
    maxZoom: 19
  }).addTo(map.value);

  // Add click handler for selection
  if (props.allowSelection) {
    map.value.on('click', handleMapClick);
  }

  // Add existing locations
  if (props.locations.length > 0) {
    addLocationMarkers();
  }

  // Add initial marker if model value exists
  if (props.modelValue) {
    addMarker(props.modelValue.latitude, props.modelValue.longitude, 'Selected Location');
  }
};

const handleMapClick = (e) => {
  const { lat, lng } = e.latlng;
  selectedLocation.value = { lat, lng };
  // Immediately set the model value; saving is handled by parent form
  const coordinates = { latitude: lat, longitude: lng };
  emit('update:modelValue', coordinates);
  emit('location-selected', coordinates);
};

const addMarker = (lat, lng, title = '', isSelected = false) => {
  const icon = isSelected ? L.icon({
    iconUrl: 'https://raw.githubusercontent.com/pointhi/leaflet-color-markers/master/img/marker-icon-2x-red.png',
    shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.7.1/images/marker-shadow.png',
    iconSize: [25, 41],
    iconAnchor: [12, 41],
    popupAnchor: [1, -34],
    shadowSize: [41, 41]
  }) : null;

  const options = icon ? { icon } : {};

  const marker = L.marker([lat, lng], options)
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
  z-index: 1;
}

.map-container {
  width: 100%;
  border-radius: 8px;
  overflow: hidden;
  border: 1px solid #ddd;
  z-index: 1;
}

.coordinates-display {
  margin-top: 10px;
  padding: 10px;
  background: #f5f5f5;
  border-radius: 5px;
  display: flex;
  align-items: center;
  gap: 15px;
  flex-wrap: wrap;
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
