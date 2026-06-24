import { defineStore } from 'pinia'
import api from '../services/api'

export const useNotificationsStore = defineStore('notifications', {
  state: () => ({
    unreadCount: 0,
    inboxItems: [],
    inboxPagination: {
      totalItems: 0,
      hasMore: false,
      nextCursor: null,
      pageSize: 10,
    },
    preferences: null,
    loading: false,
    initialized: false,
  }),

  actions: {
    reset() {
      this.unreadCount = 0
      this.inboxItems = []
      this.inboxPagination = { totalItems: 0, hasMore: false, nextCursor: null, pageSize: 10 }
      this.preferences = null
      this.loading = false
      this.initialized = false
    },

    async loadSummary() {
      try {
        const response = await api.get('/notifications/summary')
        this.unreadCount = response.data?.unread_count || 0
        this.preferences = response.data?.preferences || this.preferences
        this.initialized = true
      } catch (error) {
        console.error('Failed to load notification summary:', error)
      }
    },

    async loadInbox(options = {}) {
      this.loading = true
      try {
        const config = typeof options === 'boolean' ? { unreadOnly: options } : options
        const response = await api.get('/notifications/inbox', {
          params: {
            unread_only: Boolean(config.unreadOnly),
            cursor: config.cursor || undefined,
            page_size: config.pageSize || this.inboxPagination.pageSize || 10,
          }
        })
        this.inboxItems = response.data?.items || []
        this.inboxPagination = {
          totalItems: response.data?.pagination?.total_items || this.inboxItems.length,
          hasMore: Boolean(response.data?.pagination?.has_more),
          nextCursor: response.data?.pagination?.next_cursor || null,
          pageSize: response.data?.pagination?.page_size || config.pageSize || 10,
        }
        this.unreadCount = this.inboxItems.filter(item => item.status === 'delivered' && !item.read_at).length
        return response.data
      } finally {
        this.loading = false
      }
    },

    async loadPreferences() {
      const response = await api.get('/notifications/preferences')
      this.preferences = response.data?.preferences || null
      return this.preferences
    },

    async markRead(deliveryId) {
      await api.post(`/notifications/inbox/${deliveryId}/read`)
      await this.loadSummary()
    },

    async markAllRead() {
      await api.post('/notifications/inbox/read-all')
      await this.loadSummary()
    },

    async savePreferences(payload) {
      const response = await api.put('/notifications/preferences', payload)
      this.preferences = response.data?.preferences || payload
      await this.loadSummary()
      return this.preferences
    },
  },
})