<template>
  <div class="tourist-home">
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-background">
        <div class="gradient-blob blob-1"></div>
        <div class="gradient-blob blob-2"></div>
        <div class="gradient-blob blob-3"></div>
      </div>
      <div class="hero-content">
        <div class="hero-text">
          <p class="eyebrow">Explore the World</p>
          <h1>Discover Your Next Adventure</h1>
          <p class="sub">Connect with local experts and create unforgettable memories</p>
        </div>
        <div class="hero-cta">
          <router-link to="/search" class="btn btn-primary">
            <span class="btn-icon">🔍</span> Explore Now
          </router-link>
          <router-link to="/cart" class="btn btn-secondary">
            <span class="btn-icon">🛒</span> Your Cart
          </router-link>
        </div>
      </div>
      <div class="hero-illustration">
        <div class="floating-card card-1">
          <p>🗺️</p>
          <span>800+</span>
          <p>Destinations</p>
        </div>
        <div class="floating-card card-2">
          <p>👥</p>
          <span>5K+</span>
          <p>Operators</p>
        </div>
        <div class="floating-card card-3">
          <p>⭐</p>
          <span>4.8★</span>
          <p>Rating</p>
        </div>
      </div>
    </section>

    <!-- Stats Bar -->
    <section class="stats-bar">
      <div class="stat-item">
        <div class="stat-icon">✈️</div>
        <div class="stat-info">
          <p class="stat-value">50K+</p>
          <p class="stat-label">Happy Travelers</p>
        </div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <div class="stat-icon">🏆</div>
        <div class="stat-info">
          <p class="stat-value">98%</p>
          <p class="stat-label">Satisfaction Rate</p>
        </div>
      </div>
      <div class="stat-divider"></div>
      <div class="stat-item">
        <div class="stat-icon">📍</div>
        <div class="stat-info">
          <p class="stat-value">150+</p>
          <p class="stat-label">Countries</p>
        </div>
      </div>
    </section>

    <!-- For You Section -->
    <section class="for-you-section">
      <div class="section-container">
        <header class="section-header">
          <div class="header-text">
            <p class="eyebrow">Tailored for you</p>
            <h2>Recommended Experiences</h2>
          </div>
          <div class="header-actions">
            <button class="btn-icon-only" @click="refreshRecs" :disabled="loading" :title="loading ? 'Refreshing...' : 'Refresh'">
              <span :class="{ spinning: loading }">🔄</span>
            </button>
            <router-link to="/recommendations" class="btn btn-text">See all →</router-link>
          </div>
        </header>
        <div class="scroll-row-limited">
          <RecommendationCard
            v-for="rec in recommendations.personalized.slice(0, 5)"
            :key="rec.operator_id + rec.area_name"
            :rec="rec"
          />
        </div>
      </div>
    </section>

    <!-- Main Content Grid: Trending Left + Featured Right -->
    <div class="content-grid">
      <!-- Left: Trending Places (Vertical Scroll) -->
      <main class="trending-column">
        <div class="section-container">
          <header class="section-header">
            <div class="header-text">
              <p class="eyebrow">Trending worldwide</p>
              <h2>Popular Destinations</h2>
            </div>
          </header>
          <div class="scroll-column">
            <RecommendationCard
              v-for="rec in recommendations.popular"
              :key="rec.operator_id + rec.area_name + '-pop'"
              :rec="rec"
            />
          </div>
        </div>
      </main>

      <!-- Right: Featured Experiences with Animation -->
      <aside class="featured-column">
        <div class="featured-panel">
          <div class="featured-header">
            <h3>✨ Featured Experiences</h3>
          </div>
          <div class="featured-items">
            <div 
              class="featured-item" 
              v-for="(rec, idx) in recommendations.sponsored.slice(0, 4)" 
              :key="rec.operator_id + rec.area_name + '-spon'"
              @click="selectFeatured(rec)"
            >
              <div class="featured-item-inner">
                <div class="item-image">
                  <img :src="rec.thumbnail" :alt="rec.area_name" v-if="rec.thumbnail" />
                  <div class="image-overlay"></div>
                </div>
                <div class="item-content">
                  <div class="item-header">
                    <p class="item-location">{{ rec.state }}</p>
                    <span class="featured-badge">Featured</span>
                  </div>
                  <h4 class="item-title">{{ rec.area_name }}</h4>
                  <p class="item-operator">By {{ rec.operator_name }}</p>
                  <div class="item-rating">
                    <span class="stars">⭐ {{ rec.average_rating.toFixed(1) }}</span>
                    <span class="reviews">({{ rec.total_reviews }})</span>
                  </div>
                  <router-link :to="`/operator/${rec.operator_id}`" class="btn btn-small">Learn More →</router-link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </aside>
    </div>
  </div>
</template>

<script>
import { ref, onMounted } from 'vue'
import api from '../services/api'
import RecommendationCard from '../components/RecommendationCard.vue'

export default {
  name: 'TouristHome',
  components: { RecommendationCard },
  setup() {
    const recommendations = ref({ personalized: [], popular: [], sponsored: [] })
    const loading = ref(false)
    const selectedFeatured = ref(null)

    const loadRecs = async () => {
      loading.value = true
      try {
        const res = await api.get('/recommendations/custom')
        recommendations.value = res.data
      } catch (error) {
        console.error('Failed to load recommendations', error)
      } finally {
        loading.value = false
      }
    }

    const refreshRecs = async () => {
      await loadRecs()
    }

    const selectFeatured = (rec) => {
      selectedFeatured.value = rec
    }

    onMounted(() => {
      loadRecs()
    })

    return {
      recommendations,
      loading,
      refreshRecs,
      selectFeatured,
      selectedFeatured
    }
  }
}
</script>

<style scoped>
/* CSS Variables */
:root {
  --color-primary: #2563eb;
  --color-primary-dark: #1e40af;
  --color-secondary: #8b5cf6;
  --color-accent: #ec4899;
  --color-dark: #0f172a;
  --color-light: #f8fafc;
  --color-border: #e2e8f0;
  --radius: 16px;
  --radius-lg: 24px;
}

* {
  box-sizing: border-box;
}

.tourist-home {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 50%, #e0f2fe 100%);
  color: var(--color-dark);
  overflow-x: hidden;
}

/* ==================== HERO SECTION ==================== */
.hero {
  position: relative;
  overflow: hidden;
  padding: 3rem 2rem;
  min-height: 500px;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
  align-items: center;
  background: linear-gradient(135deg, #0f172a 0%, #1e293b 40%, #334155 100%);
  color: #fff;
}

.hero-background {
  position: absolute;
  inset: 0;
  overflow: hidden;
  z-index: 0;
}

.gradient-blob {
  position: absolute;
  border-radius: 50%;
  filter: blur(80px);
  opacity: 0.3;
  animation: float 20s ease-in-out infinite;
}

.blob-1 {
  width: 400px;
  height: 400px;
  background: linear-gradient(135deg, #2563eb 0%, #8b5cf6 100%);
  top: -100px;
  right: -100px;
  animation-delay: 0s;
}

.blob-2 {
  width: 300px;
  height: 300px;
  background: linear-gradient(135deg, #ec4899 0%, #f97316 100%);
  bottom: -50px;
  left: 10%;
  animation-delay: 5s;
}

.blob-3 {
  width: 350px;
  height: 350px;
  background: linear-gradient(135deg, #06b6d4 0%, #0ea5e9 100%);
  top: 50%;
  right: 20%;
  animation-delay: 10s;
}

@keyframes float {
  0%, 100% { transform: translate(0, 0) rotate(0deg); }
  50% { transform: translate(30px, -30px) rotate(180deg); }
}

.hero-content {
  position: relative;
  z-index: 2;
  display: flex;
  flex-direction: column;
  gap: 2rem;
}

.hero-text h1 {
  font-size: 3.5rem;
  font-weight: 800;
  margin: 0;
  line-height: 1.1;
  letter-spacing: -0.02em;
  background: linear-gradient(135deg, #ffffff 0%, #e0f2fe 100%);
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.hero-text .sub {
  font-size: 1.2rem;
  color: rgba(255, 255, 255, 0.85);
  margin: 0;
  line-height: 1.6;
  max-width: 500px;
}

.eyebrow {
  text-transform: uppercase;
  letter-spacing: 0.15em;
  font-size: 0.85rem;
  color: rgba(255, 255, 255, 0.7);
  margin: 0 0 0.5rem 0;
  font-weight: 700;
}

.hero-cta {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.btn {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.5rem;
  padding: 0.9rem 1.8rem;
  border: none;
  border-radius: 12px;
  font-weight: 700;
  text-decoration: none;
  font-size: 1rem;
  cursor: pointer;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
  position: relative;
  overflow: hidden;
}

.btn-icon {
  font-size: 1.2rem;
}

.btn.btn-primary {
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  color: white;
  box-shadow: 0 10px 30px rgba(37, 99, 235, 0.3);
}

.btn.btn-primary:hover {
  transform: translateY(-2px);
  box-shadow: 0 15px 40px rgba(37, 99, 235, 0.4);
}

.btn.btn-secondary {
  background: rgba(255, 255, 255, 0.15);
  color: white;
  border: 1.5px solid rgba(255, 255, 255, 0.3);
  backdrop-filter: blur(10px);
}

.btn.btn-secondary:hover {
  background: rgba(255, 255, 255, 0.25);
  border-color: rgba(255, 255, 255, 0.5);
  transform: translateY(-2px);
}

.hero-illustration {
  position: relative;
  z-index: 2;
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 1rem;
  height: 300px;
}

.floating-card {
  position: absolute;
  padding: 1.5rem 1rem;
  background: rgba(255, 255, 255, 0.1);
  border: 1px solid rgba(255, 255, 255, 0.2);
  border-radius: 16px;
  backdrop-filter: blur(20px);
  text-align: center;
  animation: bounce 3s ease-in-out infinite;
  min-width: 120px;
}

.floating-card p {
  font-size: 2.5rem;
  margin: 0;
}

.floating-card span {
  display: block;
  font-size: 1.5rem;
  font-weight: 800;
  color: #e0f2fe;
  margin: 0.5rem 0;
}

.floating-card p:last-child {
  font-size: 0.9rem;
  color: rgba(255, 255, 255, 0.8);
}

.card-1 {
  top: 20px;
  left: 0;
  animation-delay: 0s;
}

.card-2 {
  top: 50%;
  left: 50%;
  transform: translateX(-50%) translateY(-50%);
  animation-delay: 1s;
}

.card-3 {
  bottom: 20px;
  right: 0;
  animation-delay: 2s;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

/* ==================== STATS BAR ==================== */
.stats-bar {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  padding: 2rem;
  background: white;
  border-bottom: 1px solid var(--color-border);
  max-width: 900px;
  margin: 2rem auto;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.stat-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
}

.stat-icon {
  font-size: 2rem;
  min-width: 50px;
  text-align: center;
}

.stat-info p {
  margin: 0;
}

.stat-value {
  font-size: 1.5rem;
  font-weight: 800;
  color: var(--color-primary);
}

.stat-label {
  font-size: 0.85rem;
  color: #64748b;
}

.stat-divider {
  width: 1px;
  background: var(--color-border);
}

/* ==================== SECTIONS ==================== */
.section-container {
  width: 100%;
}

.section-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 1.5rem;
}

.header-text {
  flex: 1;
}

.section-header h2 {
  margin: 0;
  font-size: 2rem;
  font-weight: 800;
  color: var(--color-dark);
}

.header-actions {
  display: flex;
  gap: 1rem;
  align-items: center;
}

.btn-icon-only {
  background: linear-gradient(135deg, #f3f4f6 0%, #e5e7eb 100%);
  border: 1px solid var(--color-border);
  border-radius: 50%;
  width: 44px;
  height: 44px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.2rem;
  transition: all 0.3s ease;
}

.btn-icon-only:hover:not(:disabled) {
  background: linear-gradient(135deg, #e5e7eb 0%, #d1d5db 100%);
  transform: scale(1.1);
}

.btn-icon-only:disabled {
  opacity: 0.6;
  cursor: not-allowed;
}

.spinning {
  display: inline-block;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.btn.btn-text {
  background: transparent;
  color: var(--color-primary);
  padding: 0.5rem 1rem;
  font-size: 0.95rem;
  border: 1px solid var(--color-border);
  border-radius: 8px;
}

.btn.btn-text:hover {
  background: #f1f5f9;
  border-color: var(--color-primary);
}

/* ==================== FOR YOU SECTION ==================== */
.for-you-section {
  padding: 2rem;
  background: white;
  margin: 2rem;
  border-radius: var(--radius-lg);
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
}

.scroll-row-limited {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 240px;
  gap: 1.5rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding-bottom: 0.5rem;
}

.scroll-row-limited > * {
  scroll-snap-align: start;
}

.scroll-row-limited::-webkit-scrollbar {
  height: 6px;
}

.scroll-row-limited::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 10px;
}

.scroll-row-limited::-webkit-scrollbar-thumb {
  background: linear-gradient(135deg, #2563eb 0%, #8b5cf6 100%);
  border-radius: 10px;
}

/* ==================== CONTENT GRID ==================== */
.content-grid {
  display: grid;
  grid-template-columns: 2.5fr 1.5fr;
  gap: 2rem;
  padding: 2rem;
  flex: 1;
  overflow: hidden;
}

/* ==================== TRENDING COLUMN ==================== */
.trending-column {
  display: flex;
  flex-direction: column;
  background: white;
  border-radius: var(--radius-lg);
  padding: 2rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  overflow: hidden;
}

.scroll-column {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1.5rem;
  overflow-y: auto;
  flex: 1;
  padding-right: 1rem;
}

.scroll-column::-webkit-scrollbar {
  width: 6px;
}

.scroll-column::-webkit-scrollbar-track {
  background: #f1f5f9;
  border-radius: 10px;
}

.scroll-column::-webkit-scrollbar-thumb {
  background: linear-gradient(180deg, #2563eb 0%, #8b5cf6 100%);
  border-radius: 10px;
}

/* ==================== FEATURED COLUMN ==================== */
.featured-column {
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.featured-panel {
  background: white;
  border-radius: var(--radius-lg);
  padding: 2rem;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  height: 100%;
  overflow: hidden;
}

.featured-header {
  margin-bottom: 1.5rem;
  padding-bottom: 1rem;
  border-bottom: 2px solid var(--color-border);
}

.featured-header h3 {
  margin: 0;
  font-size: 1.3rem;
  font-weight: 800;
  color: var(--color-dark);
}

.featured-items {
  display: flex;
  flex-direction: column;
  gap: 1rem;
  overflow-y: auto;
  flex: 1;
  padding-right: 0.5rem;
}

.featured-items::-webkit-scrollbar {
  width: 4px;
}

.featured-items::-webkit-scrollbar-track {
  background: transparent;
}

.featured-items::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 10px;
}

.featured-item {
  cursor: pointer;
  transition: all 0.3s ease;
  flex-shrink: 0;
}

.featured-item:hover .featured-item-inner {
  transform: translateY(-4px);
  box-shadow: 0 12px 32px rgba(37, 99, 235, 0.15);
}

.featured-item-inner {
  border-radius: 12px;
  overflow: hidden;
  background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
  border: 1px solid var(--color-border);
  transition: all 0.3s ease;
  height: 100%;
}

.item-image {
  position: relative;
  height: 140px;
  overflow: hidden;
}

.item-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.3s ease;
}

.featured-item:hover .item-image img {
  transform: scale(1.1);
}

.image-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.3) 100%);
}

.item-content {
  padding: 1rem;
}

.item-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.5rem;
  gap: 0.5rem;
}

.item-location {
  font-size: 0.8rem;
  color: #64748b;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin: 0;
  font-weight: 700;
}

.featured-badge {
  display: inline-block;
  background: linear-gradient(135deg, #fbbf24 0%, #f97316 100%);
  color: white;
  padding: 0.3rem 0.7rem;
  border-radius: 999px;
  font-size: 0.7rem;
  font-weight: 700;
}

.item-title {
  margin: 0.3rem 0;
  font-size: 1rem;
  font-weight: 800;
  color: var(--color-dark);
  line-height: 1.3;
}

.item-operator {
  margin: 0.3rem 0;
  color: #64748b;
  font-size: 0.85rem;
}

.item-rating {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin: 0.5rem 0;
  font-size: 0.9rem;
  font-weight: 700;
}

.stars {
  color: var(--color-dark);
}

.reviews {
  color: #94a3b8;
}

.btn.btn-small {
  background: linear-gradient(135deg, var(--color-primary) 0%, var(--color-primary-dark) 100%);
  color: white;
  padding: 0.5rem 1rem;
  font-size: 0.8rem;
  font-weight: 600;
  width: 100%;
  text-align: center;
  margin-top: 0.5rem;
  border-radius: 8px;
}

.btn.btn-small:hover {
  transform: translateY(-1px);
  box-shadow: 0 4px 12px rgba(37, 99, 235, 0.2);
}

/* ==================== RESPONSIVE DESIGN ==================== */
@media (max-width: 1024px) {
  .hero {
    grid-template-columns: 1fr;
    min-height: auto;
  }

  .hero-illustration {
    position: relative;
    height: auto;
  }

  .floating-card {
    position: relative;
  }

  .content-grid {
    grid-template-columns: 1fr;
    gap: 1.5rem;
    padding: 1.5rem;
  }

  .scroll-column {
    grid-template-columns: 1fr;
  }

  .stats-bar {
    grid-template-columns: 1fr;
  }

  .stat-divider {
    width: 100%;
    height: 1px;
  }
}

@media (max-width: 768px) {
  .hero {
    padding: 2rem 1rem;
  }

  .hero-text h1 {
    font-size: 2.5rem;
  }

  .hero-cta {
    flex-direction: column;
  }

  .btn {
    width: 100%;
  }

  .for-you-section {
    margin: 1rem;
    padding: 1rem;
  }

  .content-grid {
    padding: 1rem;
  }

  .trending-column,
  .featured-panel {
    padding: 1rem;
  }

  .section-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 1rem;
  }

  .section-header h2 {
    font-size: 1.5rem;
  }

  .header-actions {
    width: 100%;
  }

  .scroll-row-limited {
    grid-auto-columns: 200px;
  }

  .hero-text h1 {
    font-size: 2rem;
  }

  .hero-text .sub {
    font-size: 1rem;
  }
}

@media (max-width: 480px) {
  .hero {
    padding: 1.5rem 1rem;
  }

  .hero-text h1 {
    font-size: 1.8rem;
  }

  .featured-item-inner {
    border-radius: 8px;
  }

  .item-image {
    height: 120px;
  }

  .scroll-row-limited {
    grid-auto-columns: 160px;
  }

  .stats-bar {
    padding: 1rem;
  }

  .stat-item {
    flex-direction: column;
    text-align: center;
    gap: 0.5rem;
  }

  .featured-items {
    gap: 0.75rem;
  }
}
</style>
