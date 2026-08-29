import test from 'node:test'
import assert from 'node:assert/strict'

import { clearAdminSessionStorage, clearUserSessionStorage } from './authSession.js'

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

test('clearAdminSessionStorage removes admin token and admin user keys only', () => {
  const storage = createMemoryStorage({
    adminToken: 'admin-token',
    adminUser: '{"email":"admin@tourapp.local"}',
    token: 'user-token'
  })

  clearAdminSessionStorage(storage)

  assert.equal(storage.getItem('adminToken'), null)
  assert.equal(storage.getItem('adminUser'), null)
  assert.equal(storage.getItem('token'), 'user-token')
})

test('clearUserSessionStorage removes user token only', () => {
  const storage = createMemoryStorage({
    adminToken: 'admin-token',
    adminUser: '{"email":"admin@tourapp.local"}',
    token: 'user-token'
  })

  clearUserSessionStorage(storage)

  assert.equal(storage.getItem('token'), null)
  assert.equal(storage.getItem('adminToken'), 'admin-token')
  assert.equal(storage.getItem('adminUser'), '{"email":"admin@tourapp.local"}')
})
