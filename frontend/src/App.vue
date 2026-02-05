<template>
  <div id="app">
    <Header />
    <main class="main-content">
      <router-view />
    </main>
    <Footer />
    <ChatWidget v-if="isAuthenticated" />
  </div>
</template>

<script>
import { computed, onMounted } from 'vue'
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
    
    const isAuthenticated = computed(() => authStore.isAuthenticated && authStore.user)
    
    onMounted(async () => {
      await authStore.initAuth()
    })

    return {
      isAuthenticated
    }
  }
}
</script>

<style scoped>
.main-content {
  min-height: calc(100vh - 160px);
  padding: 20px 0;
}
</style>
