<template>
  <div class="th-page">

    <!-- ── Hero ──────────────────────────────────────────────────────────── -->
    <section class="th-hero">
      <div class="th-hero-bg"></div>
      <div class="th-hero-inner">
        <div class="th-hero-text">
          <span class="eyebrow">Your Travel Dashboard</span>
          <h1>Where will you go next?</h1>
          <p class="sub">Discover curated experiences from local experts — tours, car services, and more.</p>
          <div class="hero-actions">
            <router-link to="/search" class="btn-hero-primary">
              <svg width="16" height="16" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5"><circle cx="11" cy="11" r="8"/><path d="m21 21-4.35-4.35"/></svg>
              Search Operators
            </router-link>
            <router-link to="/quote-builder" class="btn-hero-quote">Get a Quote</router-link>
            <router-link to="/plan" class="btn-hero-ghost">Plan with AI →</router-link>
          </div>
        </div>
        <div class="hero-stats">
          <div class="hstat">
            <strong>50K+</strong>
            <span>Travelers</span>
          </div>
          <div class="hstat-div"></div>
          <div class="hstat">
            <strong>150+</strong>
            <span>Regions</span>
          </div>
          <div class="hstat-div"></div>
          <div class="hstat">
            <strong>4.8★</strong>
            <span>Avg Rating</span>
          </div>
          <div class="hstat-div"></div>
          <div class="hstat">
            <strong>24h</strong>
            <span>Response</span>
          </div>
        </div>
      </div>
    </section>

    <!-- ── Main content ──────────────────────────────────────────────────── -->
    <div class="th-container">

      <!-- Personalized recommendations -->
      <section class="th-card">
        <div class="th-card-head">
          <div>
            <p class="card-label">Tailored for you</p>
            <h2 class="card-title">Recommended Experiences</h2>
          </div>
          <div class="head-actions">
            <button class="btn-refresh" @click="refreshRecs" :disabled="loading" :title="loading ? 'Refreshing…' : 'Refresh'">
              <span :class="{ spinning: loading }">↻</span>
            </button>
            <router-link to="/recommendations" class="btn-link">See all →</router-link>
          </div>
        </div>
        <p v-if="loading" class="empty-state">Loading recommendations…</p>
        <p v-else-if="!recommendations.personalized.length" class="empty-state">
          No personalised recommendations yet — explore destinations to train your feed.
        </p>
        <div v-else class="rec-scroll">
          <RecommendationCard
            v-for="rec in recommendations.personalized.slice(0, 6)"
            :key="rec.operator_id + rec.area_name"
            :rec="rec"
          />
        </div>
      </section>

      <!-- Two-column: Popular + Featured -->
      <div class="th-two-col">

        <!-- Popular destinations -->
        <section class="th-card">
          <div class="th-card-head">
            <div>
              <p class="card-label">Trending worldwide</p>
              <h2 class="card-title">Popular Destinations</h2>
            </div>
          </div>
          <p v-if="loading" class="empty-state">Loading…</p>
          <p v-else-if="!recommendations.popular.length" class="empty-state">No trending destinations right now.</p>
          <div v-else class="pop-grid">
            <RecommendationCard
              v-for="rec in recommendations.popular"
              :key="rec.operator_id + rec.area_name + '-pop'"
              :rec="rec"
            />
          </div>
        </section>

        <!-- Featured experiences -->
        <section class="th-card">
          <div class="th-card-head">
            <div>
              <p class="card-label">Hand-picked</p>
              <h2 class="card-title">Featured Experiences</h2>
            </div>
          </div>
          <p v-if="loading" class="empty-state">Loading…</p>
          <p v-else-if="!recommendations.sponsored.length" class="empty-state">No featured experiences at the moment.</p>
          <div v-else class="feat-list">
            <div
              class="feat-item"
              v-for="rec in recommendations.sponsored.slice(0, 4)"
              :key="rec.operator_id + rec.area_name + '-spon'"
              @click="selectFeatured(rec)"
              @keyup.enter="selectFeatured(rec)"
              tabindex="0"
              :class="{ 'feat-item--active': selectedFeatured?.operator_id === rec.operator_id && selectedFeatured?.area_name === rec.area_name }"
            >
              <div class="feat-img-wrap">
                <img :src="rec.thumbnail" :alt="rec.area_name" v-if="rec.thumbnail" />
                <div v-else class="feat-img-placeholder">{{ rec.area_name?.charAt(0) }}</div>
              </div>
              <div class="feat-body">
                <div class="feat-top">
                  <span class="feat-state">{{ rec.state }}</span>
                  <span class="feat-badge">Featured</span>
                </div>
                <p class="feat-name">{{ rec.area_name }}</p>
                <p class="feat-op">By {{ rec.operator_name }}</p>
                <div class="feat-rating">
                  ⭐ {{ rec.average_rating?.toFixed(1) }}
                  <span class="feat-reviews">({{ rec.total_reviews }})</span>
                </div>
              </div>
              <router-link :to="`/operator/${rec.operator_id}`" class="feat-arrow" @click.stop>→</router-link>
            </div>
          </div>
        </section>
      </div>

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
/* ── Page ─────────────────────────────────────────────────────────────────── */
.th-page {
  min-height: 100vh;
  background: #f0f4f8;
  padding-bottom: 5rem;
}

/* ── Hero ─────────────────────────────────────────────────────────────────── */
.th-hero {
  background: linear-gradient(135deg, #0f172a 0%, #1a2d4a 55%, #0c4a6e 100%);
  padding: 3.7rem 2rem 2.4rem;
  position: relative;
  overflow: hidden;
}

.th-hero-bg {
  position: absolute;
  inset: 0;
  background:
    radial-gradient(ellipse at 10% 70%, rgba(56,189,248,0.1), transparent 50%),
    radial-gradient(ellipse at 90% 20%, rgba(99,102,241,0.1), transparent 50%),
    radial-gradient(ellipse at 50% 100%, rgba(16,185,129,0.07), transparent 50%);
  pointer-events: none;
}

.th-hero-inner {
  position: relative;
  z-index: 1;
  max-width: 1100px;
  margin: 0 auto;
}

.th-hero-text {
  text-align: center;
  max-width: 840px;
  margin: 0 auto 2rem;
}

.eyebrow {
  display: inline-block;
  background: rgba(56,189,248,0.15);
  color: #7dd3fc;
  border: 1px solid rgba(56,189,248,0.25);
  border-radius: 999px;
  font-size: 0.74rem;
  font-weight: 700;
  letter-spacing: 0.1em;
  text-transform: uppercase;
  padding: 0.3rem 1rem;
  margin-bottom: 1rem;
}

.th-hero-text h1 {
  font-size: clamp(2rem, 5vw, 3.2rem);
  font-weight: 800;
  color: #fff;
  line-height: 1.1;
  margin: 0 0 0.7rem;
  letter-spacing: -0.02em;
}

.th-hero-text .sub {
  color: rgba(255,255,255,0.62);
  font-size: 1.05rem;
  margin: 0 auto 1.6rem;
  max-width: 700px;
  line-height: 1.6;
}

.hero-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
  flex-wrap: wrap;
}

.btn-hero-primary {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.45rem;
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: #fff;
  border: none;
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 700;
  min-width: 205px;
  padding: 0.8rem 1.6rem;
  text-decoration: none;
  transition: opacity 0.2s, transform 0.15s;
}

.btn-hero-primary:hover { opacity: 0.88; transform: translateY(-1px); }

.btn-hero-quote {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(20, 184, 166, 0.18);
  color: #ecfeff;
  border: 1.5px solid rgba(45, 212, 191, 0.34);
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 700;
  min-width: 142px;
  padding: 0.8rem 1.6rem;
  text-decoration: none;
  transition: background 0.2s, transform 0.15s, border-color 0.2s;
}

.btn-hero-quote:hover {
  background: rgba(20, 184, 166, 0.26);
  border-color: rgba(94, 234, 212, 0.58);
  transform: translateY(-1px);
}

.btn-hero-ghost {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(255,255,255,0.1);
  color: #e2e8f0;
  border: 1.5px solid rgba(255,255,255,0.22);
  border-radius: 12px;
  font-size: 0.95rem;
  font-weight: 700;
  min-width: 155px;
  padding: 0.8rem 1.6rem;
  text-decoration: none;
  transition: background 0.2s;
}

.btn-hero-ghost:hover { background: rgba(255,255,255,0.18); }

/* Stats row */
.hero-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  align-items: stretch;
  gap: 0;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  border-radius: 20px;
  padding: 0.35rem 0.5rem;
  margin: 0 auto;
  width: min(100%, 820px);
  backdrop-filter: blur(8px);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.16);
}

.hstat {
  text-align: center;
  padding: 0.65rem 1rem;
  border-right: 1px solid rgba(255,255,255,0.14);
}

.hstat:last-of-type {
  border-right: 0;
}

.hstat strong {
  display: block;
  font-size: 1.5rem;
  font-weight: 800;
  color: #fff;
  line-height: 1;
}

.hstat span {
  font-size: 0.72rem;
  color: rgba(255,255,255,0.5);
  text-transform: uppercase;
  letter-spacing: 0.06em;
}

.hstat-div {
  display: none;
}

/* ── Container ────────────────────────────────────────────────────────────── */
.th-container {
  max-width: 1240px;
  margin: 1.85rem auto 0;
  padding: 0 1.5rem;
  display: flex;
  flex-direction: column;
  gap: 1.35rem;
}

/* ── Cards ────────────────────────────────────────────────────────────────── */
.th-card {
  background: #fff;
  border-radius: 20px;
  box-shadow: 0 8px 32px rgba(15,23,42,0.08);
  border: 1px solid #f1f5f9;
  padding: 1.65rem;
}

.th-card-head {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 1rem;
  gap: 1rem;
}

.card-label {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  color: #94a3b8;
  margin: 0 0 0.25rem;
}

.card-title {
  font-size: 1.3rem;
  font-weight: 800;
  color: #0f172a;
  margin: 0;
}

.head-actions {
  display: flex;
  align-items: center;
  gap: 0.8rem;
  flex-shrink: 0;
}

.btn-refresh {
  background: #f1f5f9;
  border: 1px solid #e2e8f0;
  border-radius: 50%;
  width: 36px;
  height: 36px;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  font-size: 1.1rem;
  font-weight: 700;
  color: #475569;
  transition: all 0.2s;
  line-height: 1;
}

.btn-refresh:hover:not(:disabled) { background: #e2e8f0; transform: scale(1.1); }
.btn-refresh:disabled { opacity: 0.5; cursor: not-allowed; }

.spinning { display: inline-block; animation: spin 0.8s linear infinite; }

@keyframes spin {
  from { transform: rotate(0deg); }
  to   { transform: rotate(360deg); }
}

.btn-link {
  font-size: 0.88rem;
  font-weight: 700;
  color: #0ea5e9;
  text-decoration: none;
  border: 1px solid #e0f2fe;
  border-radius: 8px;
  padding: 0.4rem 0.9rem;
  background: #f0f9ff;
  transition: all 0.18s;
}

.btn-link:hover { background: #0ea5e9; color: #fff; border-color: #0ea5e9; }

/* ── Recommendation scroll row ────────────────────────────────────────────── */
.rec-scroll {
  display: grid;
  grid-auto-flow: column;
  grid-auto-columns: 198px;
  gap: 0.9rem;
  overflow-x: auto;
  scroll-snap-type: x mandatory;
  padding-bottom: 0.35rem;
}

.rec-scroll > * { scroll-snap-align: start; }

.rec-scroll::-webkit-scrollbar { height: 5px; }
.rec-scroll::-webkit-scrollbar-track { background: #f1f5f9; border-radius: 10px; }
.rec-scroll::-webkit-scrollbar-thumb { background: #cbd5e1; border-radius: 10px; }

/* ── Two-column layout ────────────────────────────────────────────────────── */
.th-two-col {
  display: grid;
  grid-template-columns: 1.4fr 1fr;
  gap: 1.5rem;
}

/* ── Popular grid ─────────────────────────────────────────────────────────── */
.pop-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 1rem;
}

/* ── Featured list ────────────────────────────────────────────────────────── */
.feat-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.feat-item {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  background: #fafbfe;
  border: 1px solid #f1f5f9;
  border-radius: 14px;
  padding: 0.8rem 0.9rem;
  cursor: pointer;
  transition: box-shadow 0.2s, transform 0.15s, border-color 0.2s;
  outline: none;
}

.feat-item:hover { box-shadow: 0 6px 20px rgba(15,23,42,0.1); transform: translateY(-1px); }
.feat-item:focus-visible { outline: 2px solid #0ea5e9; outline-offset: 2px; }
.feat-item--active { border-color: #0ea5e9; box-shadow: 0 0 0 3px rgba(14,165,233,0.15); }

.feat-img-wrap {
  width: 56px;
  height: 56px;
  border-radius: 12px;
  overflow: hidden;
  flex-shrink: 0;
  background: #e2e8f0;
}

.feat-img-wrap img {
  width: 100%;
  height: 100%;
  object-fit: cover;
}

.feat-img-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.4rem;
  font-weight: 800;
  background: linear-gradient(135deg, #0ea5e9, #2563eb);
  color: #fff;
}

.feat-body { flex: 1; min-width: 0; }

.feat-top {
  display: flex;
  align-items: center;
  gap: 0.5rem;
  margin-bottom: 0.2rem;
}

.feat-state {
  font-size: 0.7rem;
  font-weight: 700;
  text-transform: uppercase;
  color: #94a3b8;
  letter-spacing: 0.07em;
}

.feat-badge {
  background: linear-gradient(135deg, #fbbf24, #f97316);
  color: #fff;
  font-size: 0.65rem;
  font-weight: 700;
  padding: 0.15rem 0.5rem;
  border-radius: 999px;
}

.feat-name {
  font-size: 0.92rem;
  font-weight: 700;
  color: #0f172a;
  margin: 0;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.feat-op {
  font-size: 0.78rem;
  color: #64748b;
  margin: 0.1rem 0 0.25rem;
}

.feat-rating {
  font-size: 0.8rem;
  font-weight: 700;
  color: #0f172a;
}

.feat-reviews {
  font-weight: 400;
  color: #94a3b8;
}

.feat-arrow {
  color: #94a3b8;
  font-size: 1.1rem;
  text-decoration: none;
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  display: flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  border: 1px solid #e2e8f0;
  transition: all 0.18s;
}

.feat-arrow:hover { background: #0ea5e9; color: #fff; border-color: #0ea5e9; }

/* ── Empty / loading state ────────────────────────────────────────────────── */
.empty-state {
  font-size: 0.88rem;
  color: #94a3b8;
  background: #f8fafc;
  border: 1px dashed #cbd5e1;
  border-radius: 10px;
  padding: 1.2rem 1rem;
  text-align: center;
}

/* ── Responsive ───────────────────────────────────────────────────────────── */
@media (max-width: 1000px) {
  .th-two-col { grid-template-columns: 1fr; }
  .pop-grid   { grid-template-columns: repeat(2, 1fr); }
}

@media (max-width: 700px) {
  .th-hero { padding: 3.5rem 1.2rem 2.5rem; }
  .th-hero-text h1 { font-size: 2rem; }
  .th-container { padding: 0 1rem; margin-top: 1.8rem; }
  .th-card { padding: 1.2rem; }
  .hero-stats {
    display: flex;
    gap: 0.8rem;
    padding: 0.65rem 1.2rem;
    width: max-content;
    max-width: 100%;
    flex-wrap: wrap;
    justify-content: center;
  }
  .hstat {
    padding: 0;
    border-right: 0;
  }
  .hstat strong { font-size: 1.2rem; }
  .pop-grid { grid-template-columns: 1fr; }
  .hero-actions { flex-direction: column; align-items: center; }
  .btn-hero-primary, .btn-hero-quote, .btn-hero-ghost { width: 100%; max-width: 340px; justify-content: center; }
}

@media (max-width: 480px) {
  .th-two-col { gap: 1rem; }
  .th-card-head { flex-direction: column; }
  .head-actions { width: 100%; justify-content: flex-end; }
  .hstat-div { display: none; }
}

@media (prefers-reduced-motion: reduce) {
  .spinning { animation: none !important; }
  .btn-hero-primary, .btn-hero-quote, .btn-hero-ghost, .feat-item { transition: none !important; }
}
</style>
