import test from 'node:test'
import assert from 'node:assert/strict'

import api from './api.js'

function createMemoryStorage(seed = {}) {
  const state = { ...seed }
  return {
    getItem(key) {
      return Object.prototype.hasOwnProperty.call(state, key) ? state[key] : null
    },
    setItem(key, value) {
      state[key] = String(value)
    },
    removeItem(key) {
      delete state[key]
    }
  }
}

function getRequestInterceptor() {
  const handler = api.interceptors.request.handlers.find((entry) => typeof entry?.fulfilled === 'function')
  if (!handler) {
    throw new Error('Request interceptor not found')
  }
  return handler.fulfilled
}

test('request interceptor uses admin token for /admin routes', () => {
  globalThis.localStorage = createMemoryStorage({
    adminToken: 'admin-token',
    token: 'user-token'
  })

  const interceptor = getRequestInterceptor()
  const config = interceptor({ url: '/admin/audit', headers: {} })

  assert.equal(config.headers.Authorization, 'Bearer admin-token')
})

test('request interceptor uses user token for non-admin routes', () => {
  globalThis.localStorage = createMemoryStorage({
    adminToken: 'admin-token',
    token: 'user-token'
  })

  const interceptor = getRequestInterceptor()
  const config = interceptor({ url: '/auth/me', headers: {} })

  assert.equal(config.headers.Authorization, 'Bearer user-token')
})

test('request interceptor removes stale authorization when matching token is missing', () => {
  globalThis.localStorage = createMemoryStorage({
    token: 'user-token'
  })

  const interceptor = getRequestInterceptor()
  const config = interceptor({
    url: '/admin/dashboard',
    headers: { Authorization: 'Bearer stale-admin-token' }
  })

  assert.equal(config.headers.Authorization, undefined)
})
