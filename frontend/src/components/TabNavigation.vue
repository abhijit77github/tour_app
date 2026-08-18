<template>
  <div class="tab-navigation">
    <div class="tab-container">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="$emit('update:activeTab', tab.id)"
      >
        <span class="tab-icon">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
        <span v-if="tab.count > 0" class="tab-badge">{{ tab.count }}</span>
        <span v-if="tab.hasCheck" class="tab-check">✓</span>
      </button>
    </div>
  </div>
</template>

<script setup>
defineProps({
  activeTab: {
    type: String,
    required: true
  },
  tabs: {
    type: Array,
    required: true
  }
})

defineEmits(['update:activeTab'])
</script>

<style scoped>
.tab-navigation {
  width: 100%;
  background: rgba(255, 255, 255, 0.05);
  backdrop-filter: blur(12px);
  border-radius: 16px;
  padding: 8px;
  margin-bottom: 24px;
  border: 1px solid rgba(255, 255, 255, 0.1);
}

.tab-container {
  display: flex;
  gap: 8px;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 12px 20px;
  background: transparent;
  border: none;
  border-radius: 12px;
  color: rgba(255, 255, 255, 0.7);
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.3s ease;
  position: relative;
}

.tab-btn:hover {
  background: rgba(255, 255, 255, 0.05);
  color: rgba(255, 255, 255, 0.9);
}

.tab-btn.active {
  background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
  color: white;
  box-shadow: 0 4px 12px rgba(8, 145, 178, 0.3);
}

.tab-icon {
  font-size: 18px;
  line-height: 1;
}

.tab-label {
  font-weight: 600;
}

.tab-badge {
  min-width: 20px;
  height: 20px;
  padding: 0 6px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.2);
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
}

.tab-btn.active .tab-badge {
  background: rgba(255, 255, 255, 0.3);
}

.tab-check {
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(16, 185, 129, 0.2);
  border-radius: 50%;
  font-size: 12px;
  color: #10b981;
}

.tab-btn.active .tab-check {
  background: rgba(255, 255, 255, 0.3);
  color: white;
}

/* Mobile styles */
@media (max-width: 768px) {
  .tab-navigation {
    position: fixed;
    bottom: 0;
    left: 0;
    right: 0;
    z-index: 1000;
    background: rgba(15, 23, 42, 0.95);
    backdrop-filter: blur(20px);
    border-radius: 0;
    border: none;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
    padding: 8px 8px calc(env(safe-area-inset-bottom) + 8px);
    margin-bottom: 0;
  }

  .tab-btn {
    flex-direction: column;
    gap: 4px;
    padding: 8px 12px;
  }

  .tab-icon {
    font-size: 20px;
  }

  .tab-label {
    font-size: 11px;
    font-weight: 600;
  }

  .tab-badge {
    position: absolute;
    top: 4px;
    right: 8px;
    min-width: 16px;
    height: 16px;
    padding: 0 4px;
    font-size: 10px;
  }

  .tab-check {
    position: absolute;
    top: 4px;
    right: 8px;
    width: 16px;
    height: 16px;
    font-size: 10px;
  }
}
</style>
