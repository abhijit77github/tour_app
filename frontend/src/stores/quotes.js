import { defineStore } from 'pinia'
import api from '../services/api'

export const useQuoteStore = defineStore('quote', {
  state: () => ({
    bucket: [],
    recentQuotes: [],
    loading: false,
    searching: false,
    error: null,
    
    // Quota information
    quota: {
      open_count: 0,
      limit: 5,
      tier: 'free',
      tier_name: 'Free',
      remaining: 5
    },
    
    // Pagination
    pagination: {
      page: 1,
      page_size: 10,
      total: 0,
      total_pages: 0,
      has_more: false
    },
    
    // Limit error tracking
    limitReached: false,
    limitErrorMessage: null,
    
    // Step management
    currentStep: 1,
    stepValidation: {
      step1: false,
      step2: false
    },
    
    // Undo functionality
    undoStack: [],
    undoTimer: null,
    
    // Animation tracking
    lastAddedId: null,
    
    // Form draft for Step 2
    formDraft: {
      travel_window: '',
      travelers: 2,
      budget: null,
      notes: '',
      attached_itinerary_id: null
    }
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
      })),
    
    step1Completed: (state) => state.bucket.length > 0,
    
    step2Completed: (state) => {
      return !!(
        state.formDraft.travel_window &&
        state.formDraft.travelers >= 1
      )
    }
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
      
      // Restore form draft
      const savedDraft = localStorage.getItem('quote_form_draft')
      if (savedDraft) {
        try {
          this.formDraft = { ...this.formDraft, ...JSON.parse(savedDraft) }
        } catch (err) {
          console.error('Failed to restore form draft', err)
        }
      }
      
      // Restore current step
      const savedStep = localStorage.getItem('quote_current_step')
      if (savedStep) {
        this.currentStep = parseInt(savedStep, 10) || 1
      }
    },

    persist() {
      localStorage.setItem('quote_bucket', JSON.stringify(this.bucket))
      localStorage.setItem('quote_form_draft', JSON.stringify(this.formDraft))
      localStorage.setItem('quote_current_step', this.currentStep.toString())
    },
    
    /**
     * Change current step
     * @param {number} step - Step number (1 or 2)
     */
    setStep(step) {
      if (step === 2 && !this.step1Completed) {
        console.warn('Cannot go to step 2 without completing step 1')
        return
      }
      this.currentStep = step
      this.persist()
    },
    
    /**
     * Update form draft
     * @param {Object} updates - Partial form data to update
     */
    updateFormDraft(updates) {
      this.formDraft = { ...this.formDraft, ...updates }
      this.persist()
    },
    
    /**
     * Clear form draft
     */
    clearFormDraft() {
      this.formDraft = {
        travel_window: '',
        travelers: 2,
        budget: null,
        notes: '',
        attached_itinerary_id: null
      }
      this.persist()
    },

    addLocation(location, options = {}) {
      if (!location.name || !location.coordinates) return
      const exists = this.bucket.some(
        (loc) => loc.name.toLowerCase() === location.name.toLowerCase() &&
          loc.coordinates.latitude === location.coordinates.latitude &&
          loc.coordinates.longitude === location.coordinates.longitude
      )
      if (!exists) {
        const newLocation = {
          id: Date.now() + Math.random(), // Unique ID for tracking
          name: location.name,
          state: location.state || '',
          country: location.country || '',
          coordinates: {
            latitude: Number(location.coordinates.latitude),
            longitude: Number(location.coordinates.longitude)
          },
          notes: location.notes || '',
          type: location.type || 'custom'
        }
        
        this.bucket.push(newLocation)
        
        // Track for animation
        if (options.animate) {
          this.lastAddedId = newLocation.id
          setTimeout(() => {
            this.lastAddedId = null
          }, 1000)
        }
        
        this.persist()
        return newLocation
      }
      return null
    },

    removeLocation(index, options = {}) {
      if (index < 0 || index >= this.bucket.length) return
      
      const removed = this.bucket[index]
      
      // Add to undo stack if undo is enabled
      if (!options.skipUndo) {
        this.undoStack.push({
          action: 'remove',
          location: removed,
          index: index,
          timestamp: Date.now()
        })
        
        // Clear undo after 5 seconds
        if (this.undoTimer) {
          clearTimeout(this.undoTimer)
        }
        this.undoTimer = setTimeout(() => {
          this.undoStack = []
        }, 5000)
      }
      
      this.bucket.splice(index, 1)
      this.persist()
    },
    
    /**
     * Undo last removal
     */
    undoRemove() {
      if (this.undoStack.length === 0) return
      
      const lastAction = this.undoStack.pop()
      if (lastAction.action === 'remove') {
        // Re-insert at original position
        this.bucket.splice(lastAction.index, 0, lastAction.location)
        this.persist()
      }
      
      // Clear timer
      if (this.undoTimer) {
        clearTimeout(this.undoTimer)
        this.undoTimer = null
      }
    },
    
    /**
     * Reorder bucket items
     * @param {number} oldIndex - Original index
     * @param {number} newIndex - New index
     */
    reorderBucket(oldIndex, newIndex) {
      if (oldIndex < 0 || oldIndex >= this.bucket.length) return
      if (newIndex < 0 || newIndex >= this.bucket.length) return
      
      const item = this.bucket.splice(oldIndex, 1)[0]
      this.bucket.splice(newIndex, 0, item)
      this.persist()
    },

    clearBucket() {
      this.bucket = []
      this.undoStack = []
      if (this.undoTimer) {
        clearTimeout(this.undoTimer)
        this.undoTimer = null
      }
      this.persist()
    },

    async searchPlaces(query) {
      if (!query || !query.trim()) return { global: [], from_operators: [] }
      this.searching = true
      this.error = null
      try {
        // Fetch operator locations from backend
        let operatorResults = []
        try {
          const operatorRes = await api.get(`/quotes/search/locations?query=${encodeURIComponent(query)}`)
          operatorResults = operatorRes.data.from_operators || []
        } catch (err) {
          console.warn('Failed to fetch operator locations:', err)
        }

        // Fetch global locations from Nominatim
        let globalResults = []
        try {
          const url = `https://nominatim.openstreetmap.org/search?format=json&limit=5&q=${encodeURIComponent(query)}`
          const res = await fetch(url, {
            headers: {
              Accept: 'application/json'
            }
          })
          if (res.ok) {
            const data = await res.json()
            globalResults = data.map((item) => ({
              id: item.place_id,
              name: item.display_name,
              lat: parseFloat(item.lat),
              lng: parseFloat(item.lon),
              state: item.address?.state || '',
              country: item.address?.country || '',
              type: 'global_location'
            }))
          }
        } catch (err) {
          console.warn('Global location search failed:', err)
        }

        return {
          global: globalResults,
          from_operators: operatorResults
        }
      } catch (err) {
        this.error = 'Location search failed. Try again.'
        return { global: [], from_operators: [] }
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
      this.limitReached = false
      this.limitErrorMessage = null
      
      try {
        const body = {
          ...payload,
          locations: this.bucket
        }
        const res = await api.post('/quotes', body)
        await this.loadMyQuotes()
        
        // Reset everything after successful publish
        this.clearBucket()
        this.clearFormDraft()
        this.currentStep = 1
        this.persist()
        
        return res.data.quote
      } catch (err) {
        // Handle HTTP 429 (quota exceeded) specially
        if (err.response?.status === 429) {
          this.limitReached = true
          this.limitErrorMessage = err.response?.data?.detail || 'You have reached your quote limit'
          this.error = this.limitErrorMessage
        } else {
          this.error = err.response?.data?.detail || 'Failed to publish quote request'
        }
        throw err
      } finally {
        this.loading = false
      }
    },

    async loadMyQuotes(page = 1, pageSize = 10) {
      this.loading = true
      try {
        const res = await api.get('/quotes/my', {
          params: {
            page,
            page_size: pageSize
          }
        })
        
        this.recentQuotes = res.data.quotes || []
        
        // Update pagination data
        if (res.data.pagination) {
          this.pagination = {
            page: res.data.pagination.page,
            page_size: res.data.pagination.page_size,
            total: res.data.pagination.total,
            total_pages: res.data.pagination.total_pages,
            has_more: res.data.pagination.has_more
          }
        }
        
        // Update quota data
        if (res.data.quota) {
          this.quota = {
            open_count: res.data.quota.open_count,
            limit: res.data.quota.limit,
            tier: res.data.quota.tier,
            tier_name: res.data.quota.tier_name,
            remaining: res.data.quota.remaining
          }
        }
      } catch (err) {
        console.error('Failed to load quotes', err)
      } finally {
        this.loading = false
      }
    },
    
    async loadNextPage() {
      if (this.pagination.has_more && !this.loading) {
        await this.loadMyQuotes(this.pagination.page + 1, this.pagination.page_size)
      }
    },
    
    async loadPreviousPage() {
      if (this.pagination.page > 1 && !this.loading) {
        await this.loadMyQuotes(this.pagination.page - 1, this.pagination.page_size)
      }
    },
    
    clearLimitError() {
      this.limitReached = false
      this.limitErrorMessage = null
    }
  }
})
