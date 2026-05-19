<template>
  <div id="app">
    <Header v-if="!isAdminRoute" />
    <main class="main-content" :class="{ 'admin-content': isAdminRoute }">
      <router-view />
    </main>
    <Footer v-if="!isAdminRoute" />
    <ChatWidget v-if="isAuthenticated && !isAdminRoute" />
  </div>
</template>

<script>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'
import Header from './components/Header.vue'
import Footer from './components/Footer.vue'
import ChatWidget from './components/ChatWidget.vue'

export default {
  name: 'App',
  components: {
    Header,
    Footer,
    ChatWidget
  },
  setup() {
    const authStore = useAuthStore()
    const route = useRoute()
    
    const isAuthenticated = computed(() => authStore.isAuthenticated && authStore.user)
    const isAdminRoute = computed(() => route.path.startsWith('/admin'))

    return {
      isAuthenticated,
      isAdminRoute
    }
  }
}
</script>

<style scoped>
.main-content {
  min-height: calc(100vh - 160px);
  padding: 20px 0;
}

.admin-content {
  min-height: 100vh;
  padding: 0;
}
</style>
