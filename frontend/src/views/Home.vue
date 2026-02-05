<template>
  <div class="home">
    <section class="hero">
      <div class="container">
        <h1>Find Your Perfect Tour</h1>
        <p>Connect with local tour operators and explore amazing destinations</p>
        <div class="hero-actions">
          <router-link to="/search" class="btn btn-primary btn-large">Search Tours</router-link>
          <router-link to="/register" class="btn btn-secondary btn-large">Become an Operator</router-link>
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
export default {
  name: 'Home'
}
</script>

<style scoped>
.hero {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 5rem 0;
  text-align: center;
}

.hero h1 {
  font-size: 3rem;
  margin-bottom: 1rem;
}

.hero p {
  font-size: 1.3rem;
  margin-bottom: 2rem;
}

.hero-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}

.btn-large {
  padding: 1rem 2rem;
  font-size: 1.1rem;
}

.features {
  padding: 4rem 0;
}

.features h2 {
  text-align: center;
  font-size: 2.5rem;
  margin-bottom: 3rem;
}

.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
  gap: 2rem;
}

.feature-card {
  background: white;
  padding: 2rem;
  border-radius: 10px;
  text-align: center;
  box-shadow: 0 4px 6px rgba(0,0,0,0.1);
  transition: transform 0.3s;
}

.feature-card:hover {
  transform: translateY(-5px);
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
  color: #666;
}
</style>
