export const hasOperatorResponded = (quote, operatorProfileId) => {
  if (!quote) return false
  if (typeof quote.responded_by_me === 'boolean') return quote.responded_by_me
  if (!operatorProfileId) return false
  return (quote.responses || []).some((response) => response.operator_id === operatorProfileId)
}

export const getOperatorQuoteState = (quote, operatorProfileId) => {
  const responded = hasOperatorResponded(quote, operatorProfileId)
  return {
    key: responded ? 'responded' : 'new',
    label: responded ? 'Responded' : 'New',
  }
}

const HOURS_MS = 1000 * 60 * 60
const DAYS_MS = HOURS_MS * 24
const URGENCY_NEW_HOURS = 24
const URGENCY_STALE_HOURS = 24
const URGENCY_RESPONDED_RECENTLY_HOURS = 24
const URGENCY_TRAVEL_SOON_DAYS = 30

const toValidDate = (value) => {
  if (!value) return null
  const parsed = new Date(value)
  return Number.isNaN(parsed.getTime()) ? null : parsed
}

export const getOperatorQuoteTravelStartDate = (quote) => {
  if (!quote) return null
  const directDate = toValidDate(quote.travel_start_date)
  if (directDate) return directDate

  const travelWindow = quote.travel_window
  if (!travelWindow) return null

  if (typeof travelWindow === 'object' && travelWindow !== null) {
    return toValidDate(travelWindow.start_date || travelWindow.from)
  }

  const rawText = String(travelWindow).split(' to ', 1)[0]?.trim()
  return toValidDate(rawText)
}

export const getOperatorQuoteUrgency = (quote, operatorProfileId) => {
  if (!quote) return null

  const now = new Date()
  const createdAt = toValidDate(quote.created_at)
  const travelStartDate = getOperatorQuoteTravelStartDate(quote)
  const responded = hasOperatorResponded(quote, operatorProfileId)

  if (responded) {
    const latestOwnResponse = (quote.responses || [])
      .filter((response) => response.operator_id === operatorProfileId)
      .map((response) => toValidDate(response.created_at))
      .filter(Boolean)
      .sort((left, right) => right - left)[0]

    if (latestOwnResponse && (now - latestOwnResponse) <= URGENCY_RESPONDED_RECENTLY_HOURS * HOURS_MS) {
      return {
        key: 'responded-recently',
        label: 'Responded recently',
      }
    }

    return null
  }

  if (travelStartDate) {
    const untilTravelMs = travelStartDate - now
    if (untilTravelMs >= 0 && untilTravelMs <= URGENCY_TRAVEL_SOON_DAYS * DAYS_MS) {
      return {
        key: 'travel-soon',
        label: 'Travel soon',
      }
    }
  }

  if (!createdAt) return null
  const ageMs = now - createdAt
  if (ageMs >= URGENCY_STALE_HOURS * HOURS_MS) {
    return {
      key: 'stale',
      label: 'Stale',
    }
  }

  if (ageMs <= URGENCY_NEW_HOURS * HOURS_MS) {
    return {
      key: 'new',
      label: 'New today',
    }
  }

  return null
}

export const formatOperatorQuoteAge = (dateString) => {
  if (!dateString) return 'Unknown'
  const date = new Date(dateString)
  if (Number.isNaN(date.getTime())) return 'Unknown'

  const now = new Date()
  const diffMs = now - date
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))

  if (diffDays === 0) {
    const diffHours = Math.floor(diffMs / (1000 * 60 * 60))
    if (diffHours === 0) {
      const diffMinutes = Math.floor(diffMs / (1000 * 60))
      return diffMinutes <= 1 ? 'Just now' : `${diffMinutes}m ago`
    }
    return `${diffHours}h ago`
  }

  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 7) return `${diffDays}d ago`
  return date.toLocaleDateString()
}

export const formatOperatorQuoteTravelWindow = (travelWindow) => {
  if (!travelWindow) return 'Not specified'
  if (typeof travelWindow === 'string') return travelWindow

  const startDate = travelWindow.start_date ? new Date(travelWindow.start_date) : null
  const endDate = travelWindow.end_date ? new Date(travelWindow.end_date) : null
  const startLabel = startDate && !Number.isNaN(startDate.getTime()) ? startDate.toLocaleDateString() : travelWindow.start_date
  const endLabel = endDate && !Number.isNaN(endDate.getTime()) ? endDate.toLocaleDateString() : travelWindow.end_date

  if (startLabel && endLabel) return `${startLabel} to ${endLabel}`
  return startLabel || endLabel || 'Not specified'
}

export const formatOperatorQuoteTravelers = (value) => {
  if (!value) return 'Travelers not set'
  return `${value} ${value === 1 ? 'person' : 'people'}`
}

export const formatOperatorQuoteBudget = (value, emptyLabel = 'Budget not set') => {
  if (value === null || value === undefined || value === '') return emptyLabel
  const numericValue = Number(value)
  if (!Number.isNaN(numericValue) && Number.isFinite(numericValue)) {
    return `₹${numericValue.toLocaleString()}`
  }
  return String(value)
}

export const buildOperatorQuoteRoute = (quoteId) => ({
  name: 'OperatorQuoteRequests',
  query: { quoteId },
})