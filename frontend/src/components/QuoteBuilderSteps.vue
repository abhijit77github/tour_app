<template>
  <div class="steps-container" :class="{ 'is-sticky': isSticky }">
    <div class="steps-inner">
      <!-- Progress Bar -->
      <div class="progress-track">
        <div class="progress-bar" :style="{ width: progressPercent + '%' }"></div>
      </div>

      <!-- Step Indicators -->
      <div class="steps-list">
        <!-- Step 1 -->
        <button
          class="step-item"
          :class="{
            'is-active': currentStep === 1,
            'is-completed': step1Completed
          }"
          @click="goToStep(1)"
        >
          <div class="step-icon">
            <span v-if="step1Completed" class="checkmark">✓</span>
            <span v-else class="step-number">1</span>
          </div>
          <div class="step-content">
            <div class="step-title">Select Locations</div>
            <div class="step-subtitle">
              {{ step1Completed ? '✓ Locations added' : 'Add at least 1 location' }}
            </div>
          </div>
        </button>

        <!-- Step Connector -->
        <div class="step-connector"></div>

        <!-- Step 2 -->
        <button
          class="step-item"
          :class="{
            'is-active': currentStep === 2,
            'is-completed': step2Completed,
            'is-disabled': !step1Completed
          }"
          @click="goToStep(2)"
          :disabled="!step1Completed"
        >
          <div class="step-icon">
            <span v-if="step2Completed" class="checkmark">✓</span>
            <span v-else class="step-number">2</span>
          </div>
          <div class="step-content">
            <div class="step-title">Publish Quote</div>
            <div class="step-subtitle">
              {{ step2Completed ? '✓ Ready to publish' : step1Completed ? 'Fill travel details' : 'Complete Step 1 first' }}
            </div>
          </div>
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, onMounted, onUnmounted } from 'vue'

/**
 * @typedef {Object} Props
 * @property {number} currentStep - Current active step (1 or 2)
 * @property {boolean} step1Completed - Whether step 1 validation passed
 * @property {boolean} step2Completed - Whether step 2 validation passed
 */

const props = defineProps({
  currentStep: {
    type: Number,
    required: true,
    default: 1,
    validator: (value) => [1, 2].includes(value)
  },
  step1Completed: {
    type: Boolean,
    default: false
  },
  step2Completed: {
    type: Boolean,
    default: false
  }
})

const emit = defineEmits(['step-change'])

const isSticky = ref(false)

/**
 * Calculate progress percentage based on current step and completion status
 * @returns {number} Progress percentage (0-100)
 */
const progressPercent = computed(() => {
  if (props.currentStep === 1) {
    return props.step1Completed ? 50 : 25
  } else if (props.currentStep === 2) {
    return props.step2Completed ? 100 : 75
  }
  return 0
})

/**
 * Navigate to a specific step
 * @param {number} step - Step number to navigate to (1 or 2)
 */
const goToStep = (step) => {
  // Don't allow going to step 2 if step 1 not completed
  if (step === 2 && !props.step1Completed) {
    return
  }

  if (step !== props.currentStep) {
    emit('step-change', step)
    
    // Smooth scroll to the relevant section
    const targetSection = step === 1 ? 'location-selection' : 'publish-section'
    const element = document.getElementById(targetSection)
    if (element) {
      element.scrollIntoView({ behavior: 'smooth', block: 'start' })
    }
  }
}

/**
 * Handle scroll event to make steps sticky
 */
const handleScroll = () => {
  const scrollTop = window.pageYOffset || document.documentElement.scrollTop
  isSticky.value = scrollTop > 200
}

onMounted(() => {
  window.addEventListener('scroll', handleScroll)
})

onUnmounted(() => {
  window.removeEventListener('scroll', handleScroll)
})
</script>

<style scoped>
/* Container */
.steps-container {
  background: white;
  border-radius: 1rem;
  box-shadow: 0 4px 16px rgba(15, 23, 42, 0.08);
  border: 1px solid #f1f5f9;
  padding: 1.5rem;
  margin-bottom: 2rem;
  transition: all 0.3s ease;
}

.steps-container.is-sticky {
  position: sticky;
  top: 1rem;
  z-index: 40;
  box-shadow: 0 10px 40px rgba(15, 23, 42, 0.15);
}

.steps-inner {
  max-width: 800px;
  margin: 0 auto;
}

/* Progress Bar */
.progress-track {
  height: 6px;
  background: #e2e8f0;
  border-radius: 999px;
  margin-bottom: 1.5rem;
  overflow: hidden;
}

.progress-bar {
  height: 100%;
  background: linear-gradient(90deg, #06b6d4 0%, #14b8a6 100%);
  border-radius: 999px;
  transition: width 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

/* Steps List */
.steps-list {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
}

/* Step Item */
.step-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 1rem;
  background: transparent;
  border: 2px solid transparent;
  border-radius: 0.75rem;
  cursor: pointer;
  transition: all 0.2s ease;
  flex: 1;
  max-width: 300px;
}

.step-item:hover:not(.is-disabled) {
  background: #f0fdfa;
  border-color: #99f6e4;
}

.step-item.is-active {
  background: linear-gradient(135deg, #ecfeff 0%, #d1fae5 100%);
  border-color: #14b8a6;
}

.step-item.is-completed {
  background: #f0fdf4;
  border-color: #bbf7d0;
}

.step-item.is-disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

/* Step Icon */
.step-icon {
  flex-shrink: 0;
  width: 2.5rem;
  height: 2.5rem;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
  font-size: 1rem;
  background: #e2e8f0;
  color: #475569;
  transition: all 0.2s ease;
}

.step-item.is-active .step-icon {
  background: linear-gradient(135deg, #06b6d4 0%, #14b8a6 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(6, 182, 212, 0.3);
}

.step-item.is-completed .step-icon {
  background: #10b981;
  color: white;
}

.step-icon .checkmark {
  font-size: 1.25rem;
}

.step-icon .step-number {
  font-size: 1.1rem;
}

/* Step Content */
.step-content {
  text-align: left;
  flex: 1;
  min-width: 0;
}

.step-title {
  font-size: 0.95rem;
  font-weight: 700;
  color: #0f172a;
  margin-bottom: 0.15rem;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.step-subtitle {
  font-size: 0.75rem;
  color: #64748b;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.step-item.is-active .step-title {
  color: #0891b2;
}

.step-item.is-completed .step-title {
  color: #059669;
}

/* Step Connector */
.step-connector {
  width: 2rem;
  height: 2px;
  background: #cbd5e1;
  flex-shrink: 0;
}

/* Mobile Responsive */
@media (max-width: 768px) {
  .steps-container {
    padding: 1rem;
  }

  .steps-list {
    flex-direction: column;
    gap: 0.5rem;
  }

  .step-connector {
    width: 2px;
    height: 1rem;
    margin: 0 auto;
  }

  .step-item {
    width: 100%;
    max-width: none;
  }

  .step-title {
    font-size: 0.875rem;
  }

  .step-subtitle {
    font-size: 0.7rem;
  }
}

/* Smooth animations */
@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(-10px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.steps-container {
  animation: slideIn 0.3s ease-out;
}
</style>
