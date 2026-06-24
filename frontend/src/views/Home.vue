<template>
  <div class="home">
    <section class="hero">
      <div class="container">
        <div class="hero-layout">
          <div class="hero-copy">
            <p class="hero-kicker">Plan better trips with local experts</p>
            <h1>Find the Right Tour, Not Just Any Tour</h1>
            <p class="hero-subtitle">Discover operator-led experiences with real location depth, pricing clarity, and trusted reviews.</p>
            <div class="hero-actions">
              <router-link to="/search" class="btn btn-primary btn-large">Search Tours</router-link>
              <router-link to="/register" class="btn btn-large hero-register-btn">Become an Operator</router-link>
            </div>
          </div>

          <div class="hero-art" aria-hidden="true">
            <img :src="heroIllustration" alt="" class="hero-illustration" />
          </div>
        </div>

        <div class="hero-metrics">
          <div class="metric-item">
            <strong>150+</strong>
            <span>Regions Covered</span>
          </div>
          <div class="metric-item">
            <strong>3-step</strong>
            <span>Quote Workflow</span>
          </div>
          <div class="metric-item">
            <strong>24h</strong>
            <span>Typical Response</span>
          </div>
        </div>
      </div>
    </section>

    <section class="features">
      <div class="container">
        <h2>How It Works</h2>
        <div class="feature-grid">
          <div class="feature-card">
            <div class="feature-icon">🔍</div>
            <h3>Search Locations</h3>
            <p>Find tour operators in your desired destination</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">📍</div>
            <h3>Explore Offerings</h3>
            <p>Browse through curated locations and experiences</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">🗺️</div>
            <h3>Plan Your Trip</h3>
            <p>Create custom tour packages with interactive maps</p>
          </div>
          <div class="feature-card">
            <div class="feature-icon">⭐</div>
            <h3>Rate & Review</h3>
            <p>Share your experience and help others</p>
          </div>
        </div>
      </div>
    </section>
  </div>
</template>

<script>
import heroIllustration from '../../resources/logo/svg/undraw_adventure-map_tour-local.svg'

export default {
  name: 'Home',
  data() {
    return {
      heroIllustration
    }
  }
}
</script>

<style scoped>
.hero {
  background:
    radial-gradient(circle at 0% 0%, rgba(45, 212, 191, 0.28), transparent 38%),
    radial-gradient(circle at 100% 25%, rgba(20, 184, 166, 0.22), transparent 35%),
    linear-gradient(125deg, #0f172a 0%, #1e293b 45%, #0f766e 100%);
  color: white;
  padding: 5.8rem 0 4.7rem;
  text-align: center;
  position: relative;
  overflow: hidden;
}

.hero-layout {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(280px, 460px);
  gap: 2rem;
  align-items: center;
}

.hero-copy {
  text-align: left;
}

.hero-art {
  position: relative;
  padding: 0.4rem;
  border-radius: 30px;
  border: 1px solid rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.05);
}

.hero-art::before {
  content: none;
}

.hero-illustration {
  width: 100%;
  height: auto;
  display: block;
  position: relative;
  z-index: 1;
  border-radius: 26px;
  border: 0;
  background: linear-gradient(180deg, #eff6ff 0%, #ecfeff 100%);
  box-shadow: 0 18px 36px rgba(15, 23, 42, 0.12);
}

.hero-kicker {
  text-transform: uppercase;
  letter-spacing: 0.14em;
  font-size: 0.78rem;
  font-weight: 700;
  color: rgba(255, 255, 255, 0.72);
  margin-bottom: 0.8rem;
}

.hero h1 {
  font-family: 'Fraunces', Georgia, serif;
  font-size: clamp(2rem, 4.8vw, 3.55rem);
  margin-bottom: 1.1rem;
  line-height: 1.1;
  letter-spacing: -0.02em;
}

.hero-subtitle {
  font-size: clamp(1rem, 2.2vw, 1.2rem);
  max-width: 640px;
  margin: 0 0 2rem;
  color: rgba(240, 249, 255, 0.92);
}

.hero-actions {
  display: flex;
  gap: 1rem;
  flex-wrap: wrap;
}

.btn-large {
  padding: 0.95rem 1.85rem;
  font-size: 1rem;
}

.hero-register-btn {
  background: rgba(255, 255, 255, 0.14);
  color: #f8fafc;
  border: 1px solid rgba(255, 255, 255, 0.45);
  backdrop-filter: blur(6px);
}

.hero-register-btn:hover {
  background: rgba(255, 255, 255, 0.24);
  border-color: rgba(255, 255, 255, 0.75);
  transform: translateY(-1px);
}

.hero-metrics {
  margin-top: 2.2rem;
  display: grid;
  grid-template-columns: repeat(3, minmax(130px, 180px));
  gap: 0.75rem;
  justify-content: start;
}

.metric-item {
  background: rgba(255, 255, 255, 0.09);
  border: 1px solid rgba(255, 255, 255, 0.22);
  border-radius: 12px;
  padding: 0.8rem 0.65rem;
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  backdrop-filter: blur(5px);
}

.metric-item strong {
  font-size: 1.05rem;
}

.metric-item span {
  font-size: 0.78rem;
  color: rgba(255, 255, 255, 0.84);
}

.features {
  padding: 4.2rem 0;
}

.features h2 {
  text-align: center;
  font-size: clamp(1.8rem, 3vw, 2.5rem);
  margin-bottom: 2.5rem;
  font-family: 'Fraunces', Georgia, serif;
  color: #0f172a;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
}

.feature-card {
  background: white;
  padding: 2rem;
  border-radius: 14px;
  text-align: center;
  border: 1px solid rgba(148, 163, 184, 0.2);
  box-shadow: 0 12px 28px rgba(15, 23, 42, 0.07);
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}

.feature-card:hover {
  transform: translateY(-5px);
  box-shadow: 0 18px 34px rgba(15, 23, 42, 0.11);
}

.feature-icon {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.feature-card h3 {
  margin-bottom: 0.5rem;
  color: #2c3e50;
}

.feature-card p {
  color: #475569;
}

@media (max-width: 760px) {
  .hero {
    padding: 4.4rem 0 3.6rem;
  }

  .hero-layout {
    grid-template-columns: 1fr;
    gap: 1.4rem;
  }

  .hero-copy {
    text-align: center;
  }

  .hero-subtitle {
    margin-left: auto;
    margin-right: auto;
  }

  .hero-actions,
  .hero-metrics {
    justify-content: center;
  }

  .hero-metrics {
    grid-template-columns: 1fr;
    max-width: 280px;
    margin: 1.7rem auto 0;
  }
}
</style>
