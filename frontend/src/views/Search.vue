<template>
  <div class="search-page">
    <div class="container">
      <h1>Search Tour Operators</h1>
      
      <div class="search-form card">
        <div class="form-row">
          <div class="form-group">
            <label>Location</label>
            <input
              type="text"
              v-model="searchParams.area_name"
              placeholder="Enter location name"
            />
          </div>
          
          <div class="form-group">
            <label>State</label>
            <input
              type="text"
              v-model="searchParams.state"
              placeholder="Enter state"
            />
          </div>
          
          <div class="form-group">
            <label>Country</label>
            <input
              type="text"
              v-model="searchParams.country"
              placeholder="Enter country"
            />
          </div>
          
          <button @click="handleSearch" class="btn btn-primary">
            Search
          </button>
        </div>
      </div>

      <div v-if="loading" class="loading-container">
        <div class="loading"></div>
      </div>

      <div v-else-if="operators.length > 0" class="results">
        <h2>Found {{ operators.length }} operators</h2>
        <div class="operator-grid">
          <div v-for="operator in operators" :key="operator._id" class="operator-card card">
            <h3>{{ operator.business_name }}</h3>
            <p class="rating">⭐ {{ operator.average_rating.toFixed(1) }} ({{ operator.total_reviews }} reviews)</p>
            <p class="description">{{ operator.description || 'No description available' }}</p>
            <div class="serving-areas">
              <strong>Serving Areas:</strong>
              <ul>
                <li v-for="(area, idx) in operator.serving_areas" :key="idx">
                  {{ area.area_name }}, {{ area.state }}
                </li>
              </ul>
            </div>
            <router-link :to="`/operator/${operator._id}`" class="btn btn-primary">
              View Details
            </router-link>
          </div>
        </div>
      </div>

      <div v-else-if="searched" class="no-results">
        <p>No operators found. Try different search criteria.</p>
      </div>
    </div>
  </div>
</template>

<script>
import { ref } from 'vue'
import api from '../services/api'

export default {
  name: 'Search',
  setup() {
    const searchParams = ref({
      area_name: '',
      state: '',
      country: ''
    })

    const operators = ref([])
    const loading = ref(false)
    const searched = ref(false)

    const handleSearch = async () => {
      const params = {}
      if (searchParams.value.area_name) params.area_name = searchParams.value.area_name
      if (searchParams.value.state) params.state = searchParams.value.state
      if (searchParams.value.country) params.country = searchParams.value.country

      if (Object.keys(params).length === 0) {
        alert('Please enter at least one search criteria')
        return
      }

      loading.value = true
      searched.value = true

      try {
        const response = await api.get('/operators/search/location', { params })
        operators.value = response.data.operators
      } catch (error) {
        console.error('Search failed:', error)
        alert('Search failed. Please try again.')
      } finally {
        loading.value = false
      }
    }

    return {
      searchParams,
      operators,
      loading,
      searched,
      handleSearch
    }
  }
}
</script>

<style scoped>
.search-page h1 {
  margin-bottom: 2rem;
  color: #2c3e50;
}

.search-form {
  margin-bottom: 2rem;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr 1fr auto;
  gap: 1rem;
  align-items: end;
}

.loading-container {
  text-align: center;
  padding: 3rem;
}

.results h2 {
  margin-bottom: 1.5rem;
  color: #2c3e50;
}

.operator-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
  gap: 1.5rem;
}

.operator-card h3 {
  color: #2c3e50;
  margin-bottom: 0.5rem;
}

.rating {
  color: #f39c12;
  margin-bottom: 1rem;
}

.description {
  color: #666;
  margin-bottom: 1rem;
}

.serving-areas {
  margin: 1rem 0;
}

.serving-areas ul {
  margin-top: 0.5rem;
  padding-left: 1.5rem;
}

.serving-areas li {
  color: #555;
  margin: 0.25rem 0;
}

.no-results {
  text-align: center;
  padding: 3rem;
  color: #666;
}

@media (max-width: 768px) {
  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
