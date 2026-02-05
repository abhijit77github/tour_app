<template>
  <div class="recommendations-page">
    <header class="page-header">
      <button @click="goBack" class="btn back-btn">← Back</button>
      <h1>Personalized for you</h1>
    </header>

    <div class="filters">
      <button 
        v-for="cat in categories"
        :key="cat"
        @click="selectedCategory = cat"
        :class="['filter-btn', { active: selectedCategory === cat }]"
      >
        {{ cat }}
      </button>
    </div>

    <div class="grid">
      <RecommendationCard
        v-for="rec in filteredRecommen"
        :key="rec.operator_id + rec.area_name"
        :rec="rec"
      />
    </div>

    <div v-if="filteredRecommen.length === 0" class="empty">
      <p>No recommendations found.</p>
    </div>
  </div>
</template>

<script>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import api from '../services/api'
import RecommendationCard from '../components/RecommendationCard.vue'

export default {
  name: 'RecommendationsPage',
  components: { RecommendationCard },
  setup() {
    const router = useRouter()
    const recommendations = ref([])
    const selectedCategory = ref('All')
    const loading = ref(false)

    const categories = ['All', 'Trekking', 'Beaches', 'City Walks', 'Family']

    const filteredRecommen = computed(() => {
      if (selectedCategory.value === 'All') {
        return recommendations.value
      }
      return recommendations.value.filter(r =>
        r.specializations?.includes(selectedCategory.value)
      )
    })

    const loadRecs = async () => {
      loading.value = true
      try {
        const res = await api.get('/recommendations/custom')
        recommendations.value = [
          ...res.data.personalized,
          ...res.data.popular,
        ]
      } catch (error) {
        console.error('Failed to load recommendations', error)
      } finally {
        loading.value = false
      }
    }

    const goBack = () => {
      router.back()
    }

    onMounted(loadRecs)

    return {
      recommendations,
      selectedCategory,
      categories,
      filteredRecommen,
      loading,
      goBack
    }
  }
}
</script>

<style scoped>
.recommendations-page {
  padding: 2rem;
  max-width: 1200px;
  margin: 0 auto;
}

.page-header {
  display: flex;
  align-items: center;
  gap: 1rem;
  margin-bottom: 2rem;
}

.back-btn {
  background: transparent;
  border: none;
  color: #2563eb;
  cursor: pointer;
  font-weight: 600;
  padding: 0;
  font-size: 1rem;
}

.page-header h1 {
  margin: 0;
  color: #111827;
}

.filters {
  display: flex;
  gap: 0.75rem;
  margin-bottom: 2rem;
  flex-wrap: wrap;
}

.filter-btn {
  padding: 0.5rem 1rem;
  border: 2px solid #e5e7eb;
  border-radius: 25px;
  background: white;
  color: #666;
  cursor: pointer;
  font-weight: 600;
  transition: all 0.3s ease;
}

.filter-btn:hover {
  border-color: #2563eb;
  color: #2563eb;
}

.filter-btn.active {
  background: #2563eb;
  color: white;
  border-color: #2563eb;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 1.5rem;
  margin-bottom: 2rem;
}

.empty {
  text-align: center;
  padding: 3rem 1rem;
  color: #999;
}
</style>
