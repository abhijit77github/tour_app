<template>
  <div class="tab-navigation" role="tablist" aria-label="Tour planner navigation">
    <div class="tab-container">
      <button
        v-for="tab in tabs"
        :key="tab.id"
        :id="`${tab.id}-tab`"
        class="tab-btn"
        :class="{ active: activeTab === tab.id }"
        @click="$emit('update:activeTab', tab.id)"
        role="tab"
        :aria-selected="activeTab === tab.id"
        :aria-controls="`${tab.id}-panel`"
        :tabindex="activeTab === tab.id ? 0 : -1"
      >
        <span class="tab-icon" aria-hidden="true">{{ tab.icon }}</span>
        <span class="tab-label">{{ tab.label }}</span>
        <span v-if="tab.count > 0" class="tab-badge" :aria-label="`${tab.count} items`">{{ tab.count }}</span>
        <span v-if="tab.hasCheck" class="tab-check" aria-label="Completed">✓</span>
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
  background: linear-gradient(180deg, #eef2f7 0%, #e2e8f0 100%);
  border-radius: 16px 16px 0 0;
  padding: 8px 10px 0;
  margin-bottom: 0;
  border: 1px solid rgba(148, 163, 184, 0.45);
  border-bottom: 1px solid rgba(203, 213, 225, 0.9);
  box-shadow: inset 0 -1px 0 rgba(255, 255, 255, 0.65);
}

.tab-container {
  display: flex;
  gap: 0;
  align-items: flex-end;
  overflow: hidden;
}

.tab-btn {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 11px 18px;
  background: linear-gradient(180deg, #e2e8f0 0%, #cbd5e1 100%);
  border: 1px solid rgba(148, 163, 184, 0.65);
  border-bottom: none;
  border-radius: 14px 14px 0 0;
  color: #334155;
  font-size: 14px;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
  margin-right: -1px;
  min-height: 44px;
}

.tab-btn:hover {
  color: #0f172a;
  background: linear-gradient(180deg, #f8fafc 0%, #e2e8f0 100%);
}

.tab-btn.active {
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  color: #0f172a;
  border-color: rgba(100, 116, 139, 0.7);
  transform: translateY(1px);
  z-index: 2;
  box-shadow: 0 -2px 8px rgba(15, 23, 42, 0.06);
}

.tab-btn.active::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: -1px;
  height: 3px;
  background: #f8fafc;
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
  background: rgba(71, 85, 105, 0.12);
  border-radius: 10px;
  font-size: 11px;
  font-weight: 700;
  color: #0f172a;
}

.tab-btn.active .tab-badge {
  background: rgba(8, 145, 178, 0.15);
  color: #0f172a;
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
  background: rgba(16, 185, 129, 0.22);
  color: #047857;
}

.tab-btn:focus-visible {
  outline: 3px solid #0891b2;
  outline-offset: 2px;
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
    box-shadow: none;
  }

  .tab-btn {
    flex-direction: column;
    gap: 4px;
    padding: 8px 12px;
    border: none;
    border-radius: 10px;
    background: transparent;
    color: rgba(226, 232, 240, 0.9);
    margin-right: 0;
    min-height: auto;
    transform: none;
    z-index: auto;
  }

  .tab-btn.active {
    background: linear-gradient(135deg, #0891b2 0%, #0f766e 100%);
    color: #ffffff;
    box-shadow: 0 6px 12px rgba(8, 145, 178, 0.35);
  }

  .tab-btn.active::after {
    display: none;
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
