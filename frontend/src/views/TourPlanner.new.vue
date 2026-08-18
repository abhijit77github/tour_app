<template>
  <div class="planner-shell">
    <div class="planner-page">
      <!-- Header with Title and Quota Badge -->
      <header class="planner-header glass-card">
        <div class="header-left">
          <h1 class="planner-title">
            <span class="title-icon">🧭</span>
            Tour Planner
          </h1>
          <p class="planner-subtitle">AI-powered trip planning with smart operator matching</p>
        </div>
        <div class="header-right">
          <QuotaBadge 
            :quota="plannerQuota" 
            :loading="plannerQuotaLoading" 
            :error="plannerQuotaError" 
          />
          <router-link to="/cart" class="cart-button">
            <span class="cart-icon">🛒</span>
            <span class="cart-count" v-if="cartStore.itemCount > 0">{{ cartStore.itemCount }}</span>
          </router-link>
        </div>
      </header>

      <!-- Tab Navigation -->
      <TabNavigation
        :activeTab="activeTab"
        :tabs="tabs"
        @update:activeTab="activeTab = $event"
      />
