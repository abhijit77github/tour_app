import { defineStore } from 'pinia'
import api from '../services/api'

export const useQuoteStore = defineStore('quote', {
  state: () => ({
    bucket: [],
    recentQuotes: [],
    loading: false,
    searching: false,
    error: null
  }),

  getters: {
    bucketCount: (state) => state.bucket.length,
    mapLocations: (state) => state.bucket
      .filter(loc => loc.coordinates)
      .map(loc => ({
        lat: loc.coordinates.latitude,
        lng: loc.coordinates.longitude,
        title: loc.name,
        description: loc.state || loc.country || loc.notes
      }))
  },

  actions: {
    hydrate() {
      const saved = localStorage.getItem('quote_bucket')
      if (saved) {
        try {
          this.bucket = JSON.parse(saved)
        } catch (err) {
          console.error('Failed to restore quote bucket', err)
          this.bucket = []
        }
      }
    },

    persist() {
      localStorage.setItem('quote_bucket', JSON.stringify(this.bucket))
    },

    addLocation(location) {
      if (!location.name || !location.coordinates) return
      const exists = this.bucket.some(
        (loc) => loc.name.toLowerCase() === location.name.toLowerCase() &&
          loc.coordinates.latitude === location.coordinates.latitude &&
          loc.coordinates.longitude === location.coordinates.longitude
      )
      if (!exists) {
        this.bucket.push({
          name: location.name,
          state: location.state || '',
          country: location.country || '',
          coordinates: {
            latitude: Number(location.coordinates.latitude),
            longitude: Number(location.coordinates.longitude)
          },
          notes: location.notes || ''
        })
        this.persist()
      }
    },

    removeLocation(index) {
      this.bucket.splice(index, 1)
      this.persist()
    },

    clearBucket() {
      this.bucket = []
      this.persist()
    },

    async searchPlaces(query) {
      if (!query || !query.trim()) return []
      this.searching = true
      this.error = null
      try {
        const url = `https://nominatim.openstreetmap.org/search?format=json&limit=6&q=${encodeURIComponent(query)}`
        const res = await fetch(url, {
          headers: {
            Accept: 'application/json'
          }
        })
        if (!res.ok) {
          throw new Error('Search failed')
        }
        const data = await res.json()
        return data.map((item) => ({
          id: item.place_id,
          name: item.display_name,
          lat: parseFloat(item.lat),
          lng: parseFloat(item.lon),
          state: item.address?.state || '',
          country: item.address?.country || ''
        }))
      } catch (err) {
        this.error = 'Location search failed. Try again.'
        return []
      } finally {
        this.searching = false
      }
    },

    async publishQuote(payload) {
      if (this.bucket.length === 0) {
        throw new Error('Add at least one location before publishing a quote request')
      }

      this.loading = true
      this.error = null
      try {
        const body = {
          ...payload,
          locations: this.bucket
        }
        const res = await api.post('/quotes', body)
        await this.loadMyQuotes()
        this.clearBucket()
        return res.data.quote
      } catch (err) {
        this.error = err.response?.data?.detail || 'Failed to publish quote request'
        throw err
      } finally {
        this.loading = false
      }
    },

    async loadMyQuotes() {
      this.loading = true
      try {
        const res = await api.get('/quotes/my')
        this.recentQuotes = res.data.quotes || []
      } catch (err) {
        console.error('Failed to load quotes', err)
      } finally {
        this.loading = false
      }
    }
  }
})
