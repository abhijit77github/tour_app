<template>
  <div class="card" :class="{ sponsored: sponsored || rec.sponsored }">
    <div class="card-image" v-if="rec.thumbnail">
      <img :src="rec.thumbnail" :alt="rec.area_name" loading="lazy" />
      <div class="image-overlay"></div>
      <span v-if="sponsored || rec.sponsored" class="badge">Featured</span>
    </div>
    <div class="card-content">
      <p class="location">{{ rec.state }}</p>
      <h3 class="title">{{ rec.area_name }}</h3>
      <p class="operator">By {{ rec.operator_name }}</p>
      <div class="rating">
        <span class="stars">⭐ {{ rec.average_rating.toFixed(1) }}</span>
        <span class="reviews">({{ rec.total_reviews }})</span>
      </div>
      <router-link :to="`/operator/${rec.operator_id}`" class="btn">Explore →</router-link>
    </div>
  </div>
</template>

<script>
export default {
  name: 'RecommendationCard',
  props: {
    rec: {
      type: Object,
      required: true
    },
    sponsored: {
      type: Boolean,
      default: false
    }
  }
}
</script>

<style scoped>
.card {
  background: white;
  border: 1px solid #e2e8f0;
  border-radius: 16px;
  overflow: hidden;
  box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  height: 100%;
  transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover {
  transform: translateY(-8px);
  box-shadow: 0 16px 32px rgba(0, 0, 0, 0.12);
  border-color: #2563eb;
}

.card.sponsored {
  border: 2px solid #fbbf24;
  background: linear-gradient(135deg, rgba(254, 243, 199, 0.5) 0%, rgba(255, 255, 255, 0.8) 100%);
  box-shadow: 0 8px 24px rgba(251, 191, 36, 0.2);
}

.card-image {
  position: relative;
  height: 180px;
  background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
  overflow: hidden;
  flex-shrink: 0;
}

.card-image img {
  width: 100%;
  height: 100%;
  object-fit: cover;
  transition: transform 0.4s cubic-bezier(0.4, 0, 0.2, 1);
}

.card:hover .card-image img {
  transform: scale(1.08);
}

.image-overlay {
  position: absolute;
  inset: 0;
  background: linear-gradient(180deg, transparent 0%, rgba(0, 0, 0, 0.2) 100%);
  pointer-events: none;
}

.badge {
  position: absolute;
  top: 12px;
  right: 12px;
  background: linear-gradient(135deg, #fbbf24 0%, #f97316 100%);
  color: white;
  padding: 0.4rem 0.8rem;
  border-radius: 999px;
  font-size: 0.75rem;
  font-weight: 700;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  box-shadow: 0 4px 12px rgba(251, 191, 36, 0.3);
}

.card-content {
  padding: 1.2rem;
  display: flex;
  flex-direction: column;
  flex: 1;
  gap: 0.5rem;
}

.location {
  margin: 0;
  text-transform: uppercase;
  letter-spacing: 0.1em;
  font-size: 0.7rem;
  color: #64748b;
  font-weight: 700;
}

.title {
  margin: 0;
  font-size: 1.1rem;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.3;
}

.operator {
  margin: 0;
  color: #64748b;
  font-size: 0.9rem;
}

.rating {
  display: flex;
  gap: 0.5rem;
  align-items: center;
  margin-top: auto;
  padding-top: 0.5rem;
  border-top: 1px solid #e2e8f0;
  font-weight: 600;
}

.stars {
  color: #0f172a;
  font-size: 0.95rem;
}

.reviews {
  color: #94a3b8;
  font-size: 0.85rem;
}

.btn {
  display: inline-block;
  margin-top: 1rem;
  background: linear-gradient(135deg, #2563eb 0%, #1e40af 100%);
  color: white;
  padding: 0.65rem 1.2rem;
  border-radius: 8px;
  text-decoration: none;
  font-weight: 700;
  font-size: 0.9rem;
  text-align: center;
  transition: all 0.3s ease;
  border: none;
}

.btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 8px 16px rgba(37, 99, 235, 0.3);
}

@media (max-width: 768px) {
  .card {
    height: auto;
  }

  .card-image {
    height: 150px;
  }

  .title {
    font-size: 1rem;
  }
}
</style>
