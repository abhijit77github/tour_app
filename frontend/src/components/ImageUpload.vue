<template>
  <div class="image-upload">
    <div class="upload-area" :class="{ 'drag-over': isDragOver }" @dragover.prevent="isDragOver = true" @dragleave.prevent="isDragOver = false" @drop.prevent="handleDrop">
      <input type="file" :id="inputId" :accept="accept" :multiple="multiple" @change="handleFileSelect" ref="fileInput" class="file-input" />

      <label :for="inputId" class="upload-label">
        <div class="upload-icon">📁</div>
        <p class="upload-text">
          {{ multiple ? 'Click to upload or drag and drop images' : 'Click to upload or drag and drop an image' }}
        </p>
        <p class="upload-hint">{{ acceptText }} (Max {{ maxSizeMB }}MB{{ multiple ? ' each' : '' }})</p>
      </label>
    </div>

    <!-- Preview existing images -->
    <div v-if="existingImages.length > 0" class="image-preview-grid">
      <div v-for="(image, index) in existingImages" :key="`existing-${index}`" class="image-preview-item">
        <img :src="getImageUrl(image)" :alt="`Image ${index + 1}`" class="preview-image" />
        <button @click="removeExistingImage(index)" class="remove-btn" type="button">✕</button>
      </div>
    </div>

    <!-- Preview new uploads -->
    <div v-if="previewUrls.length > 0" class="image-preview-grid">
      <div v-for="(url, index) in previewUrls" :key="`new-${index}`" class="image-preview-item">
        <img :src="url" :alt="`Preview ${index + 1}`" class="preview-image" />
        <button @click="removeNewImage(index)" class="remove-btn" type="button">✕</button>
        <div class="upload-status">
          <span v-if="uploadStatuses[index] === 'uploading'">⏳ Uploading...</span>
          <span v-if="uploadStatuses[index] === 'success'" class="success">✓ Uploaded</span>
          <span v-if="uploadStatuses[index] === 'error'" class="error">✗ Failed</span>
        </div>
      </div>
    </div>

    <!-- Upload button for new files -->
    <button v-if="newFiles.length > 0 && !autoUpload" @click="uploadFiles" :disabled="uploading" class="upload-btn" type="button">
      {{ uploading ? 'Uploading...' : `Upload ${newFiles.length} ${newFiles.length === 1 ? 'Image' : 'Images'}` }}
    </button>

    <p v-if="error" class="error-message">{{ error }}</p>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue';
import api from '../services/api';

const props = defineProps({
  modelValue: {
    type: [String, Array],
    default: () => []
  },
  multiple: {
    type: Boolean,
    default: false
  },
  accept: {
    type: String,
    default: 'image/jpeg,image/png,image/gif,image/webp'
  },
  maxSizeMB: {
    type: Number,
    default: 5
  },
  uploadEndpoint: {
    type: String,
    default: '/upload/profile-image' // or '/upload/location-images'
  },
  autoUpload: {
    type: Boolean,
    default: true
  }
});

const emit = defineEmits(['update:modelValue', 'upload-success', 'upload-error']);

const inputId = `file-input-${Math.random().toString(36).substr(2, 9)}`;
const fileInput = ref(null);
const isDragOver = ref(false);
const newFiles = ref([]);
const previewUrls = ref([]);
const uploadStatuses = ref([]);
const uploading = ref(false);
const error = ref('');

const existingImages = computed(() => {
  if (props.multiple) {
    return Array.isArray(props.modelValue) ? props.modelValue : [];
  }
  return props.modelValue ? [props.modelValue] : [];
});

const acceptText = computed(() => {
  const types = props.accept.split(',').map(t => t.split('/')[1].toUpperCase());
  return types.join(', ');
});

const getImageUrl = (url) => {
  if (url.startsWith('http')) return url;
  return `http://localhost:8808${url}`;
};

const handleFileSelect = (event) => {
  const files = Array.from(event.target.files);
  processFiles(files);
};

const handleDrop = (event) => {
  isDragOver.value = false;
  const files = Array.from(event.dataTransfer.files);
  processFiles(files);
};

const processFiles = (files) => {
  error.value = '';

  // Validate file types
  const validFiles = files.filter(file => {
    if (!file.type.startsWith('image/')) {
      error.value = 'Only image files are allowed';
      return false;
    }
    if (file.size > props.maxSizeMB * 1024 * 1024) {
      error.value = `File size must be less than ${props.maxSizeMB}MB`;
      return false;
    }
    return true;
  });

  if (validFiles.length === 0) return;

  // If not multiple, replace existing
  if (!props.multiple) {
    newFiles.value = [validFiles[0]];
    previewUrls.value = [];
    uploadStatuses.value = [];
  } else {
    newFiles.value.push(...validFiles);
  }

  // Create preview URLs
  validFiles.forEach(file => {
    const reader = new FileReader();
    reader.onload = (e) => {
      previewUrls.value.push(e.target.result);
      uploadStatuses.value.push('pending');
    };
    reader.readAsDataURL(file);
  });

  if (props.autoUpload) {
    uploadFiles();
  }
};

const uploadFiles = async () => {
  if (newFiles.value.length === 0) return;

  uploading.value = true;
  error.value = '';

  try {
    if (props.multiple) {
      // Upload multiple files
      const formData = new FormData();
      newFiles.value.forEach(file => {
        formData.append('files', file);
      });

      uploadStatuses.value = uploadStatuses.value.map(() => 'uploading');

      const response = await api.post(props.uploadEndpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      const uploadedUrls = response.data.files.map(f => f.url);
      uploadStatuses.value = uploadStatuses.value.map(() => 'success');

      // Emit updated value
      const newValue = [...existingImages.value, ...uploadedUrls];
      emit('update:modelValue', newValue);
      emit('upload-success', uploadedUrls);

      // Clear new files
      setTimeout(() => {
        newFiles.value = [];
        previewUrls.value = [];
        uploadStatuses.value = [];
      }, 1000);

    } else {
      // Upload single file
      const formData = new FormData();
      formData.append('file', newFiles.value[0]);

      uploadStatuses.value[0] = 'uploading';

      const response = await api.post(props.uploadEndpoint, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      });

      uploadStatuses.value[0] = 'success';

      emit('update:modelValue', response.data.url);
      emit('upload-success', response.data.url);

      // Clear after a moment
      setTimeout(() => {
        newFiles.value = [];
        previewUrls.value = [];
        uploadStatuses.value = [];
      }, 1000);
    }
  } catch (err) {
    console.error('Upload failed:', err);
    error.value = err.response?.data?.detail || 'Upload failed';
    uploadStatuses.value = uploadStatuses.value.map(() => 'error');
    emit('upload-error', err);
  } finally {
    uploading.value = false;
    if (fileInput.value) {
      fileInput.value.value = '';
    }
  }
};

const removeExistingImage = (index) => {
  const newImages = [...existingImages.value];
  newImages.splice(index, 1);

  if (props.multiple) {
    emit('update:modelValue', newImages);
  } else {
    emit('update:modelValue', '');
  }
};

const removeNewImage = (index) => {
  newFiles.value.splice(index, 1);
  previewUrls.value.splice(index, 1);
  uploadStatuses.value.splice(index, 1);
};
</script>

<style scoped>
.image-upload {
  width: 100%;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 30px;
  text-align: center;
  transition: all 0.3s ease;
  background: #fafafa;
}

.upload-area.drag-over {
  border-color: #4CAF50;
  background: #f0f9f0;
}

.file-input {
  display: none;
}

.upload-label {
  cursor: pointer;
  display: block;
}

.upload-icon {
  font-size: 48px;
  margin-bottom: 10px;
}

.upload-text {
  margin: 10px 0;
  color: #333;
  font-weight: 500;
}

.upload-hint {
  margin: 5px 0 0;
  color: #666;
  font-size: 0.9em;
}

.image-preview-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 20px;
}

.image-preview-item {
  position: relative;
  aspect-ratio: 1;
  border-radius: 8px;
  overflow: hidden;
  border: 2px solid #eee;
}

.preview-image {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.remove-btn {
  position: absolute;
  top: 5px;
  right: 5px;
  background: rgba(255, 0, 0, 0.8);
  color: white;
  border: none;
  border-radius: 50%;
  width: 24px;
  height: 24px;
  cursor: pointer;
  font-size: 14px;
  display: flex;
  align-items: center;
  justify-content: center;
  transition: background 0.3s;
}

.remove-btn:hover {
  background: rgba(255, 0, 0, 1);
}

.upload-status {
  position: absolute;
  bottom: 0;
  left: 0;
  right: 0;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 5px;
  font-size: 0.8em;
  text-align: center;
}

.upload-status .success {
  color: #4CAF50;
}

.upload-status .error {
  color: #f44336;
}

.upload-btn {
  margin-top: 15px;
  padding: 10px 20px;
  background: #4CAF50;
  color: white;
  border: none;
  border-radius: 5px;
  cursor: pointer;
  font-size: 1em;
  transition: background 0.3s;
}

.upload-btn:hover:not(:disabled) {
  background: #45a049;
}

.upload-btn:disabled {
  background: #ccc;
  cursor: not-allowed;
}

.error-message {
  margin-top: 10px;
  color: #f44336;
  font-size: 0.9em;
}
</style>
