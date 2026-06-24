import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import { adminBrandConfig } from './config/adminBrand'
import './assets/main.css'

async function bootstrap() {
	document.title = adminBrandConfig.browserTitle

	const app = createApp(App)
	const pinia = createPinia()

	app.use(pinia)

	const authStore = useAuthStore(pinia)
	await authStore.initAuth()

	app.use(router)
	await router.isReady()
	app.mount('#app')
}

bootstrap()
