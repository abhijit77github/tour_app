<template>
  <Teleport to="body">
    <Transition name="toast-slide">
      <div v-if="visible" class="toast-container" :class="`toast-${type}`">
        <div class="toast-icon">
          {{ iconMap[type] }}
        </div>
        <div class="toast-content">
          <p class="toast-title" v-if="title">{{ title }}</p>
          <p class="toast-message">{{ message }}</p>
        </div>
        <button class="toast-close" @click="close" aria-label="Close">×</button>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  type: {
    type: String,
    default: 'info',
    validator: (value) => ['success', 'error', 'warning', 'info'].includes(value)
  },
  title: {
    type: String,
    default: ''
  },
  message: {
    type: String,
    required: true
  },
  duration: {
    type: Number,
    default: 3000
  }
})

const emit = defineEmits(['close'])

const visible = ref(false)
let timer = null

const iconMap = {
  success: '✓',
  error: '✕',
  warning: '⚠',
  info: 'ℹ'
}

onMounted(() => {
  visible.value = true
  
  if (props.duration > 0) {
    timer = setTimeout(() => {
      close()
    }, props.duration)
  }
})

function close() {
  visible.value = false
  setTimeout(() => {
    emit('close')
  }, 300) // Wait for animation
}
</script>

<style scoped>
.toast-container {
  position: fixed;
  top: 80px;
  right: 20px;
  z-index: 9999;
  display: flex;
  align-items: flex-start;
  gap: 12px;
  min-width: 320px;
  max-width: 420px;
  padding: 16px;
  border-radius: 12px;
  background: white;
  box-shadow: 0 8px 24px rgba(0, 0, 0, 0.12), 0 2px 8px rgba(0, 0, 0, 0.08);
  backdrop-filter: blur(16px);
  border: 1px solid rgba(255, 255, 255, 0.8);
}

.toast-icon {
  flex-shrink: 0;
  width: 32px;
  height: 32px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 50%;
  font-size: 18px;
  font-weight: 700;
}

.toast-content {
  flex: 1;
  min-width: 0;
}

.toast-title {
  font-size: 15px;
  font-weight: 600;
  margin: 0 0 4px 0;
  color: #1e293b;
}

.toast-message {
  font-size: 14px;
  margin: 0;
  color: #475569;
  line-height: 1.5;
}

.toast-close {
  flex-shrink: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: none;
  border: none;
  border-radius: 50%;
  font-size: 20px;
  color: #64748b;
  cursor: pointer;
  transition: all 0.2s ease;
}

.toast-close:hover {
  background: rgba(100, 116, 139, 0.1);
  color: #334155;
}

/* Toast type variants */
.toast-success .toast-icon {
  background: linear-gradient(135deg, #10b981 0%, #059669 100%);
  color: white;
}

.toast-error .toast-icon {
  background: linear-gradient(135deg, #ef4444 0%, #dc2626 100%);
  color: white;
}

.toast-warning .toast-icon {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  color: white;
}

.toast-info .toast-icon {
  background: linear-gradient(135deg, #3b82f6 0%, #2563eb 100%);
  color: white;
}

/* Animation */
.toast-slide-enter-active,
.toast-slide-leave-active {
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.toast-slide-enter-from {
  opacity: 0;
  transform: translateX(100px) scale(0.95);
}

.toast-slide-leave-to {
  opacity: 0;
  transform: translateX(100px) scale(0.95);
}

/* Mobile responsive */
@media (max-width: 768px) {
  .toast-container {
    left: 16px;
    right: 16px;
    min-width: auto;
    max-width: none;
    top: 20px;
  }
  
  .toast-slide-enter-from,
  .toast-slide-leave-to {
    transform: translateY(-50px) scale(0.95);
  }
}
</style>
