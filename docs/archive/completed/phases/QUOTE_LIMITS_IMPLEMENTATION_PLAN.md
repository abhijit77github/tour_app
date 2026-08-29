# Quote Request Limits & Pagination - Implementation Plan

**Feature**: Limit open quote requests per membership tier with admin configuration  
**Date Created**: August 7, 2026  
**Status**: Phase 4 Complete ✅ (Ready for Phase 5 Testing)  
**Priority**: High (Pre-requisite for monetization)

---

## 📋 Feature Overview

### Business Requirements

1. **Quote Request Limits**:
   - Free members: Limited open requests (default: 5)
   - Paid members: Higher limits based on tier
   - Admin-configurable limits per tier
   - Clear error messaging when limit reached

2. **Pagination**:
   - Tourist quote history paginated (10 per page)
   - Performance optimization for large lists
   - Smooth UX with loading states

3. **Admin Configuration**:
   - Configure limits per membership tier
   - Real-time updates (no deployment needed)
   - Audit trail of configuration changes

### User Stories

**As a Free Tourist**:
- I want to know my quote limit upfront
- I want clear messaging when I hit my limit
- I want to see my quote history paginated
- I want to upgrade to get more quotes

**As a Paid Tourist**:
- I want higher quote limits based on my tier
- I want to track my quota usage
- I want seamless pagination

**As an Admin**:
- I want to configure quote limits per tier
- I want to see current limits at a glance
- I want to audit limit changes

---

## 🏗️ Architecture Analysis

### Current State

**Database**:
```python
# users collection
{
  "_id": ObjectId,
  "email": str,
  "user_type": "tourist" | "operator",
  "full_name": str,
  # No membership tier field currently
}

# quote_requests collection
{
  "_id": ObjectId,
  "tourist_id": str,
  "status": "open" | "closed" | "cancelled",
  "locations": [],
  "created_at": datetime,
  # No pagination currently
}
```

**Backend Endpoints**:
- `POST /quotes` - Create quote (no limit check)
- `GET /quotes/my` - Get all quotes (no pagination)

**Frontend**:
- Displays all quotes at once (no pagination)
- No limit messaging

### Required Changes

**Database Schema**:
```python
# users collection - ADD
{
  "membership_tier": "free" | "premium" | "enterprise",
  "membership_started_at": datetime,
  "membership_expires_at": datetime | null,
}

# system_config collection - NEW
{
  "_id": "quote_limits",
  "limits": {
    "free": 5,
    "premium": 20,
    "enterprise": 100
  },
  "updated_at": datetime,
  "updated_by": str,  # admin user ID
}
```

**Backend**:
- Add membership tier to User model
- Create SystemConfig model
- Add limit validation in POST /quotes
- Add pagination to GET /quotes/my
- Create admin endpoints for config

**Frontend**:
- Pagination component for quotes
- Limit exceeded error handling
- Quota display (e.g., "3/5 quotes used")

**Admin**:
- Quote limits configuration page
- Real-time preview of changes
- Save/reset functionality

---

## 📐 Detailed Implementation Plan

### Phase 1: Database & Models (Backend Foundation) ✅ COMPLETE
**Goal**: Set up data structures for membership tiers and limits  
**Status**: Complete ✅  
**Completion Date**: January 2025

**Tasks**:
1. ✅ Add migration to add membership fields to users
2. ✅ Create SystemConfig model
3. ✅ Create default system config document
4. ✅ Add indexes for performance

**Deliverables**:
- ✅ User model with membership_tier field
- ✅ SystemConfig collection with quote_limits
- ✅ Database migration script executed successfully (21 users migrated)
- ✅ 4 new database indexes created

**Estimated Effort**: 2 hours  
**Actual Effort**: ~2 hours

See [PHASE1_COMPLETION.md](./PHASE1_COMPLETION.md) for detailed documentation.

---

### Phase 2: Backend Validation & API (Core Logic) ✅ COMPLETE
**Goal**: Implement quote limit enforcement and pagination  
**Status**: Complete ✅  
**Completion Date**: January 2025

**Tasks**:
1. ✅ **Limit Validation**:
   - ✅ Add helper function to get user's quote limit
   - ✅ Count open quotes for user
   - ✅ Validate before creating new quote
   - ✅ Return clear error message with HTTP 429

2. ✅ **Pagination**:
   - ✅ Add pagination params to GET /quotes/my
   - ✅ Implement skip/limit pagination
   - ✅ Return total count, page metadata, and has_more flag
   - ✅ Include quota info (open_count, limit, tier, remaining)

3. ✅ **Admin Config API**:
   - ✅ GET /admin/config/quote-limits
   - ✅ PUT /admin/config/quote-limits
   - ✅ Validation for limit values (range and ordering)
   - ✅ Audit trail with admin email and timestamp

**Estimated Effort**: 4 hours  
**Actual Effort**: ~3 hours

See [PHASE2_QUOTE_LIMITS_COMPLETION.md](./PHASE2_QUOTE_LIMITS_COMPLETION.md) for detailed documentation.

**Code Changes**:

```python
# backend/models/user.py
class UserInDB(UserBase):
    membership_tier: str = "free"  # free, premium, enterprise
    membership_started_at: Optional[datetime] = None
    membership_expires_at: Optional[datetime] = None

# backend/models/system_config.py (NEW)
class QuoteLimitsConfig(BaseModel):
    free: int = 5
    premium: int = 20
    enterprise: int = 100

class SystemConfig(BaseModel):
    id: str = Field(alias="_id")
    config_key: str  # "quote_limits"
    quote_limits: QuoteLimitsConfig
    updated_at: datetime
    updated_by: Optional[str] = None

# backend/routers/quotes.py
async def get_user_quote_limit(user_id: str, db) -> dict:
    """Get user's membership tier and corresponding limit."""
    user = await db.users.find_one({"_id": ObjectId(user_id)})
    tier = user.get("membership_tier", "free")
    
    config = await db.system_config.find_one({"config_key": "quote_limits"})
    limits = config.get("quote_limits", {"free": 5, "premium": 20, "enterprise": 100})
    
    return {
        "tier": tier,
        "limit": limits.get(tier, 5),
        "tier_name": tier.capitalize()
    }

@router.post("", status_code=status.HTTP_201_CREATED)
async def create_quote_request(
    quote: QuoteRequestCreate,
    current_user: dict = Depends(get_current_user)
):
    # ... existing validations ...
    
    db = await get_database()
    
    # NEW: Check quote limit
    user_limit_info = await get_user_quote_limit(str(current_user["_id"]), db)
    open_count = await db.quote_requests.count_documents({
        "tourist_id": str(current_user["_id"]),
        "status": "open"
    })
    
    if open_count >= user_limit_info["limit"]:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"You have reached your limit of {user_limit_info['limit']} open quote requests. "
                   f"Please close or cancel existing quotes, or upgrade to {next_tier} for more quotes."
        )
    
    # ... rest of creation logic ...

@router.get("/my")
async def get_my_quote_requests(
    current_user: dict = Depends(get_current_user),
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=50)
):
    # ... existing validation ...
    
    db = await get_database()
    skip = (page - 1) * page_size
    
    # Get total count
    total = await db.quote_requests.count_documents({
        "tourist_id": str(current_user["_id"])
    })
    
    # Get paginated results
    cursor = db.quote_requests.find({
        "tourist_id": str(current_user["_id"])
    }).sort("created_at", -1).skip(skip).limit(page_size)
    
    quotes = []
    async for q in cursor:
        quotes.append(_serialize_quote(q))
    
    return {
        "quotes": quotes,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "total_pages": (total + page_size - 1) // page_size,
            "has_more": skip + len(quotes) < total
        }
    }
```

**Deliverables**:
- Quote limit validation working
- Pagination API functional
- Clear error messages

**Estimated Effort**: 4 hours

---

### Phase 3: Admin Configuration UI
**Goal**: Allow admins to configure quote limits

**Tasks**:
1. Create admin config page route
2. Build configuration form
3. Add validation
4. Show current limits
5. Save/reset functionality
6. Success/error feedback

**UI Mockup**:
```
┌─────────────────────────────────────────────────────┐
│  Quote Request Limits Configuration                 │
│                                                      │
│  Configure the maximum number of open quote         │
│  requests allowed per membership tier.              │
│                                                      │
│  ┌────────────────────────────────────────────────┐ │
│  │ Free Members          [  5  ] open requests    │ │
│  │ Premium Members       [ 20  ] open requests    │ │
│  │ Enterprise Members    [ 100 ] open requests    │ │
│  └────────────────────────────────────────────────┘ │
│                                                      │
│  Last updated: Aug 7, 2026 by admin@example.com    │
│                                                      │
│  [ Reset to Defaults ]       [ Save Changes ]       │
└─────────────────────────────────────────────────────┘
```

**Code Structure**:
```vue
<!-- frontend/src/views/AdminQuoteLimits.vue (NEW) -->
<template>
  <div class="admin-config-page">
    <div class="page-header">
      <h1>Quote Request Limits</h1>
      <p>Configure maximum open quote requests per membership tier</p>
    </div>

    <div class="config-card">
      <div class="config-section">
        <label>
          <span class="tier-icon">🆓</span>
          Free Members
        </label>
        <input 
          v-model.number="limits.free" 
          type="number" 
          min="1" 
          max="50"
          class="limit-input"
        />
        <span class="hint">open requests</span>
      </div>

      <div class="config-section">
        <label>
          <span class="tier-icon">⭐</span>
          Premium Members
        </label>
        <input 
          v-model.number="limits.premium" 
          type="number" 
          min="1" 
          max="100"
          class="limit-input"
        />
        <span class="hint">open requests</span>
      </div>

      <div class="config-section">
        <label>
          <span class="tier-icon">💎</span>
          Enterprise Members
        </label>
        <input 
          v-model.number="limits.enterprise" 
          type="number" 
          min="1" 
          max="500"
          class="limit-input"
        />
        <span class="hint">open requests</span>
      </div>

      <div v-if="lastUpdated" class="update-info">
        Last updated: {{ formatDate(lastUpdated.date) }} 
        by {{ lastUpdated.admin }}
      </div>

      <div class="actions">
        <button @click="reset" class="btn-secondary">
          Reset to Defaults
        </button>
        <button 
          @click="save" 
          :disabled="!hasChanges || saving"
          class="btn-primary"
        >
          {{ saving ? 'Saving...' : 'Save Changes' }}
        </button>
      </div>

      <div v-if="successMessage" class="msg-success">
        {{ successMessage }}
      </div>
      <div v-if="errorMessage" class="msg-error">
        {{ errorMessage }}
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import api from '../services/api'

const limits = ref({ free: 5, premium: 20, enterprise: 100 })
const originalLimits = ref({ free: 5, premium: 20, enterprise: 100 })
const lastUpdated = ref(null)
const saving = ref(false)
const successMessage = ref('')
const errorMessage = ref('')

const hasChanges = computed(() => {
  return limits.value.free !== originalLimits.value.free ||
         limits.value.premium !== originalLimits.value.premium ||
         limits.value.enterprise !== originalLimits.value.enterprise
})

const fetchLimits = async () => {
  try {
    const res = await api.get('/admin/config/quote-limits')
    limits.value = { ...res.data.quote_limits }
    originalLimits.value = { ...res.data.quote_limits }
    lastUpdated.value = res.data.updated
  } catch (err) {
    errorMessage.value = 'Failed to load configuration'
  }
}

const save = async () => {
  saving.value = true
  errorMessage.value = ''
  successMessage.value = ''
  
  try {
    await api.put('/admin/config/quote-limits', {
      quote_limits: limits.value
    })
    originalLimits.value = { ...limits.value }
    successMessage.value = 'Quote limits updated successfully!'
    setTimeout(() => successMessage.value = '', 3000)
    await fetchLimits()
  } catch (err) {
    errorMessage.value = err.response?.data?.detail || 'Failed to save changes'
  } finally {
    saving.value = false
  }
}

const reset = () => {
  limits.value = { free: 5, premium: 20, enterprise: 100 }
}

const formatDate = (date) => {
  return new Date(date).toLocaleString()
}

onMounted(() => {
  fetchLimits()
})
</script>
```

**Deliverables**:
- Admin configuration page functional
- Real-time limit updates
- Clear success/error feedback

**Estimated Effort**: 3 hours

---

### Phase 4: Frontend Pagination & Quota Display
**Goal**: Show paginated quotes with quota information

**Tasks**:
1. Add pagination component to QuoteBuilder
2. Fetch quotes with pagination
3. Show quota usage (e.g., "3/5 quotes used")
4. Handle limit exceeded error
5. Add loading states

**UI Components**:

```vue
<!-- Quota Display -->
<div class="quota-display">
  <div class="quota-info">
    <span class="quota-label">Open Quotes:</span>
    <span class="quota-value">{{ openCount }}/{{ userLimit }}</span>
    <span 
      v-if="openCount >= userLimit" 
      class="quota-warning"
    >
      Limit reached
    </span>
  </div>
  <div class="quota-bar">
    <div 
      class="quota-fill" 
      :style="{ width: quotaPercentage + '%' }"
      :class="{ 'quota-high': quotaPercentage >= 80 }"
    ></div>
  </div>
  <p v-if="membershipTier === 'free'" class="upgrade-hint">
    <router-link to="/pricing">Upgrade to Premium</router-link> 
    for {{ premiumLimit }} open quotes
  </p>
</div>

<!-- Pagination Controls -->
<div v-if="totalPages > 1" class="pagination">
  <button 
    @click="goToPage(currentPage - 1)" 
    :disabled="currentPage === 1"
    class="btn-page"
  >
    ← Previous
  </button>
  
  <div class="page-numbers">
    <button
      v-for="page in visiblePages"
      :key="page"
      @click="goToPage(page)"
      :class="{ 'active': page === currentPage }"
      class="btn-page-num"
    >
      {{ page }}
    </button>
  </div>
  
  <button 
    @click="goToPage(currentPage + 1)" 
    :disabled="currentPage === totalPages"
    class="btn-page"
  >
    Next →
  </button>
</div>
```

**Error Handling**:
```javascript
// In publishQuote()
try {
  await quoteStore.publishQuote()
  successMessage.value = '🎉 Quote published!'
} catch (err) {
  if (err.response?.status === 429) {
    // Quota exceeded
    const detail = err.response.data.detail
    quoteStore.error = detail
    
    // Show upgrade prompt for free users
    if (userMembershipTier.value === 'free') {
      showUpgradeModal.value = true
    }
  } else {
    quoteStore.error = 'Failed to publish quote. Please try again.'
  }
}
```

**Deliverables**:
- Pagination working smoothly
- Quota display visible
- Clear upgrade messaging
- Error handling for limits

**Estimated Effort**: 4 hours

---

### Phase 5: Testing & Refinement
**Goal**: Ensure all features work correctly

**Test Cases**:

1. **Free User Limit**:
   - ✅ Create 5 quotes successfully
   - ✅ 6th quote shows error
   - ✅ Close 1 quote, can create again
   - ✅ Error message mentions tier and limit

2. **Premium User Limit**:
   - ✅ Can create up to 20 quotes
   - ✅ Limit enforced at 21st
   - ✅ Quota bar shows correctly

3. **Pagination**:
   - ✅ Shows 10 quotes per page
   - ✅ Navigation works correctly
   - ✅ Total count accurate
   - ✅ Loading states display

4. **Admin Config**:
   - ✅ Load current limits
   - ✅ Update limits successfully
   - ✅ Validation prevents invalid values
   - ✅ Audit trail recorded

5. **Edge Cases**:
   - ✅ User with no membership tier defaults to free
   - ✅ Expired membership falls back to free
   - ✅ Concurrent quote creation handled
   - ✅ Config changes apply immediately

**Deliverables**:
- All test cases passing
- No regressions
- Performance validated

**Estimated Effort**: 3 hours

---

## 📊 Implementation Summary

### Total Effort Estimate
- **Phase 1** (DB/Models): 2 hours
- **Phase 2** (Backend API): 4 hours
- **Phase 3** (Admin UI): 3 hours
- **Phase 4** (Frontend): 4 hours
- **Phase 5** (Testing): 3 hours
- **Total**: ~16 hours (2 days)

### Files to Create
1. `backend/models/system_config.py` (NEW)
2. `backend/routers/admin_config.py` (NEW)
3. `backend/scripts/init_quote_limits.py` (NEW - migration)
4. `frontend/src/views/AdminQuoteLimits.vue` (NEW)
5. `frontend/src/components/PaginationControls.vue` (NEW)
6. `frontend/src/components/QuotaDisplay.vue` (NEW)

### Files to Modify
1. `backend/models/user.py` - Add membership fields
2. `backend/routers/quotes.py` - Add validation and pagination
3. `backend/main.py` - Register admin routes
4. `frontend/src/views/QuoteBuilder.vue` - Add pagination
5. `frontend/src/stores/quotes.js` - Add pagination logic
6. `frontend/src/router/index.js` - Add admin route

### Database Changes
1. Add to `users` collection:
   - `membership_tier: str`
   - `membership_started_at: datetime`
   - `membership_expires_at: datetime`

2. Create `system_config` collection:
   - `_id: "quote_limits"`
   - `config_key: "quote_limits"`
   - `quote_limits: { free, premium, enterprise }`
   - `updated_at: datetime`
   - `updated_by: str`

### API Endpoints to Add
- `GET /admin/config/quote-limits` - Get current limits
- `PUT /admin/config/quote-limits` - Update limits
- `GET /quotes/my?page=1&page_size=10` - Paginated quotes
- `GET /quotes/quota` - Get user's quota info

---

## 🚀 Rollout Plan

### Phase 1: Backend Foundation (Silent Deploy)
- Deploy DB changes
- Add backend validation
- No user-facing changes yet
- Test in staging

### Phase 2: Admin Configuration (Internal)
- Deploy admin UI
- Configure initial limits
- Test with admin accounts
- Validate limits work

### Phase 3: Frontend Release (Public)
- Deploy pagination UI
- Deploy quota display
- Enable limit enforcement
- Monitor error rates

### Phase 4: Monitoring & Optimization
- Track quota exceeded events
- Monitor conversion to paid
- Optimize pagination performance
- Gather user feedback

---

## 🎯 Success Metrics

### Technical Metrics
- Quote creation error rate < 1%
- Pagination load time < 500ms
- Admin config save time < 1s
- Zero data inconsistencies

### Business Metrics
- % of free users hitting limit
- Upgrade conversion rate
- Average quotes per user by tier
- Support tickets about limits < 5/month

---

## 🔒 Security Considerations

1. **Authorization**:
   - Only admins can modify quote limits
   - Users can only see their own quota
   - Validate membership tier on server

2. **Validation**:
   - Enforce limits on server side (never trust client)
   - Validate limit values in admin UI (1-500)
   - Prevent negative or zero limits

3. **Rate Limiting**:
   - Prevent rapid-fire quote creation
   - Add cooldown between requests (1 minute)
   - Log suspicious activity

---

## 📝 Migration Strategy

### Step 1: Add Fields to Existing Users
```python
# backend/scripts/migrate_membership_tiers.py
async def migrate_users():
    db = await get_database()
    
    # Set all existing users to "free" tier
    result = await db.users.update_many(
        {"membership_tier": {"$exists": False}},
        {"$set": {
            "membership_tier": "free",
            "membership_started_at": datetime.now(timezone.utc)
        }}
    )
    print(f"Updated {result.modified_count} users")
```

### Step 2: Initialize System Config
```python
# backend/scripts/init_quote_limits.py
async def init_config():
    db = await get_database()
    
    existing = await db.system_config.find_one({"config_key": "quote_limits"})
    if not existing:
        await db.system_config.insert_one({
            "config_key": "quote_limits",
            "quote_limits": {
                "free": 5,
                "premium": 20,
                "enterprise": 100
            },
            "updated_at": datetime.now(timezone.utc),
            "updated_by": None
        })
        print("Quote limits config initialized")
    else:
        print("Quote limits config already exists")
```

---

## ✅ Acceptance Criteria

**Feature is complete when**:
- [ ] Free users limited to configured number (default 5)
- [ ] Paid users get higher limits based on tier
- [ ] Admins can configure limits via UI
- [ ] Pagination works on sent requests
- [ ] Quota display shows usage clearly
- [ ] Error messages are user-friendly
- [ ] Upgrade prompts shown to free users
- [ ] All tests passing
- [ ] Documentation updated
- [ ] Deployed to production

---

**Status**: Ready for Implementation  
**Next Step**: Proceed with Phase 1 (Database & Models)  
**Assigned To**: Development Team  
**Target Completion**: August 9, 2026
