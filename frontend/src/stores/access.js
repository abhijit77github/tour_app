import { defineStore } from 'pinia'
import api from '../services/api'

export const useAccessStore = defineStore('access', {
  state: () => ({
    operatorContext: null,
    adminContext: null,
    loadingOperatorContext: false,
    loadingAdminContext: false,
  }),

  getters: {
    hasOperatorPermission: (state) => (permission) => {
      if (!permission) return true
      const permissions = state.operatorContext?.permissions || []
      return permissions.includes(permission) || permissions.includes('platform.super_admin')
    },
    hasAdminPermission: (state) => (permission) => {
      if (!permission) return true
      const permissions = state.adminContext?.permissions || []
      return permissions.includes(permission) || permissions.includes('platform.super_admin')
    },
  },

  actions: {
    async loadOperatorContext(force = false) {
      if (!localStorage.getItem('token')) {
        this.operatorContext = null
        return null
      }
      if (!force && this.operatorContext) {
        return this.operatorContext
      }
      this.loadingOperatorContext = true
      try {
        const response = await api.get('/operators/access/context')
        this.operatorContext = response.data
        return response.data
      } finally {
        this.loadingOperatorContext = false
      }
    },

    async loadAdminContext(force = false) {
      if (!localStorage.getItem('adminToken')) {
        this.adminContext = null
        return null
      }
      if (!force && this.adminContext) {
        return this.adminContext
      }
      this.loadingAdminContext = true
      try {
        const response = await api.get('/admin/access/context')
        this.adminContext = response.data
        return response.data
      } finally {
        this.loadingAdminContext = false
      }
    },

    reset() {
      this.operatorContext = null
      this.adminContext = null
      this.loadingOperatorContext = false
      this.loadingAdminContext = false
    },
  },
})