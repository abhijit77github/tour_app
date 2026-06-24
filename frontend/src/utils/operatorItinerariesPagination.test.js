import test from 'node:test'
import assert from 'node:assert/strict'

import { resolveRequestedPage } from './operatorItinerariesPagination.js'

test('resolveRequestedPage keeps a valid page number', () => {
  assert.equal(resolveRequestedPage(2, 1), 2)
})

test('resolveRequestedPage ignores refresh click event objects', () => {
  assert.equal(resolveRequestedPage({ type: 'click' }, 1), 1)
})

test('resolveRequestedPage falls back to 1 when both inputs are invalid', () => {
  assert.equal(resolveRequestedPage(undefined, 0), 1)
})