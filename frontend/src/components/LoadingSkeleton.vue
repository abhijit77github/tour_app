<template>
  <div class="skeleton" :class="[`skeleton-${type}`, { 'skeleton-animated': animated }]">
    <!-- Operator Card Skeleton -->
    <div v-if="type === 'operator-card'" class="skeleton-card">
      <div class="skeleton-avatar"></div>
      <div class="skeleton-content">
        <div class="skeleton-line skeleton-title"></div>
        <div class="skeleton-line skeleton-subtitle"></div>
        <div class="skeleton-badges">
          <div class="skeleton-badge"></div>
          <div class="skeleton-badge"></div>
        </div>
        <div class="skeleton-line skeleton-description"></div>
        <div class="skeleton-line skeleton-description short"></div>
        <div class="skeleton-actions">
          <div class="skeleton-button"></div>
          <div class="skeleton-button"></div>
        </div>
      </div>
    </div>

    <!-- Message Skeleton -->
    <div v-else-if="type === 'message'" class="skeleton-message">
      <div class="skeleton-line skeleton-text"></div>
      <div class="skeleton-line skeleton-text"></div>
      <div class="skeleton-line skeleton-text short"></div>
    </div>

    <!-- Inline Operator Skeleton -->
    <div v-else-if="type === 'inline-operator'" class="skeleton-inline-op">
      <div class="skeleton-avatar small"></div>
      <div class="skeleton-inline-content">
        <div class="skeleton-line skeleton-name"></div>
        <div class="skeleton-line skeleton-rating"></div>
      </div>
    </div>

    <!-- Generic Line -->
    <div v-else-if="type === 'line'" class="skeleton-line" :style="{ width: width }"></div>

    <!-- Generic Circle -->
    <div v-else-if="type === 'circle'" class="skeleton-circle" :style="{ width: size, height: size }"></div>

    <!-- Generic Rectangle -->
    <div v-else-if="type === 'rectangle'" class="skeleton-rectangle" :style="{ width: width, height: height }"></div>
  </div>
</template>

<script setup>
defineProps({
  type: {
    type: String,
    default: 'line',
    validator: (value) => ['operator-card', 'message', 'inline-operator', 'line', 'circle', 'rectangle'].includes(value)
  },
  animated: {
    type: Boolean,
    default: true
  },
  width: {
    type: String,
    default: '100%'
  },
  height: {
    type: String,
    default: '20px'
  },
  size: {
    type: String,
    default: '40px'
  }
})
</script>

<style scoped>
.skeleton {
  display: block;
}

.skeleton-animated::before {
  content: '';
  position: absolute;
  top: 0;
  left: -100%;
  width: 100%;
  height: 100%;
  background: linear-gradient(
    90deg,
    transparent 0%,
    rgba(255, 255, 255, 0.3) 50%,
    transparent 100%
  );
  animation: skeleton-shimmer 1.5s infinite;
}

@keyframes skeleton-shimmer {
  0% {
    left: -100%;
  }
  100% {
    left: 100%;
  }
}

/* Base skeleton elements */
.skeleton-line,
.skeleton-circle,
.skeleton-rectangle,
.skeleton-avatar,
.skeleton-badge,
.skeleton-button {
  background: linear-gradient(90deg, #e2e8f0 0%, #f1f5f9 50%, #e2e8f0 100%);
  background-size: 200% 100%;
  position: relative;
  overflow: hidden;
}

.skeleton-animated .skeleton-line,
.skeleton-animated .skeleton-circle,
.skeleton-animated .skeleton-rectangle,
.skeleton-animated .skeleton-avatar,
.skeleton-animated .skeleton-badge,
.skeleton-animated .skeleton-button {
  animation: skeleton-pulse 1.5s ease-in-out infinite;
}

@keyframes skeleton-pulse {
  0%, 100% {
    background-position: 0% 0%;
  }
  50% {
    background-position: 100% 0%;
  }
}

/* Operator Card Skeleton */
.skeleton-card {
  background: rgba(255, 255, 255, 0.8);
  border-radius: 14px;
  padding: 18px;
  display: flex;
  gap: 14px;
}

.skeleton-avatar {
  width: 48px;
  height: 48px;
  border-radius: 50%;
  flex-shrink: 0;
}

.skeleton-avatar.small {
  width: 32px;
  height: 32px;
}

.skeleton-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.skeleton-line {
  height: 12px;
  border-radius: 6px;
}

.skeleton-title {
  width: 60%;
  height: 16px;
}

.skeleton-subtitle {
  width: 40%;
  height: 12px;
}

.skeleton-description {
  width: 100%;
  height: 10px;
}

.skeleton-description.short {
  width: 70%;
}

.skeleton-badges {
  display: flex;
  gap: 8px;
}

.skeleton-badge {
  width: 80px;
  height: 24px;
  border-radius: 12px;
}

.skeleton-actions {
  display: flex;
  gap: 10px;
  margin-top: 4px;
}

.skeleton-button {
  flex: 1;
  height: 36px;
  border-radius: 8px;
}

/* Message Skeleton */
.skeleton-message {
  padding: 12px 16px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.skeleton-text {
  width: 100%;
  height: 14px;
}

.skeleton-text.short {
  width: 65%;
}

/* Inline Operator Skeleton */
.skeleton-inline-op {
  display: flex;
  gap: 10px;
  align-items: center;
  padding: 10px;
  background: rgba(255, 255, 255, 0.6);
  border-radius: 10px;
}

.skeleton-inline-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.skeleton-name {
  width: 120px;
  height: 14px;
}

.skeleton-rating {
  width: 80px;
  height: 10px;
}

/* Generic shapes */
.skeleton-circle {
  border-radius: 50%;
}

.skeleton-rectangle {
  border-radius: 8px;
}
</style>
