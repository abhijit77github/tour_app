# Quote Builder Phase 1 - Testing Guide

## Quick Start

```bash
# 1. Start the development environment
cd /home/ubuntu/abhijit/tour_app
docker-compose up -d

# 2. Access the application
# Frontend: http://localhost:5173/quote-builder
# Backend API: http://localhost:8808/docs
```

## What to Test

### Priority 1: Core Flow (10 minutes)

1. **Step Navigation**
   - [ ] Progress bar starts at 25%
   - [ ] Add a location → progress goes to 50%
   - [ ] Click Step 2 → scrolls to publish form
   - [ ] Fill travel window → progress goes to 75%
   - [ ] All fields filled → progress reaches 100%

2. **Search & Add Locations**
   - [ ] Type "Paris" in search
   - [ ] Autocomplete appears after 2 characters
   - [ ] Click a suggestion → added to bucket with animation
   - [ ] Bucket shows location with map preview

3. **Manual Pin Drop**
   - [ ] Click anywhere on the map
   - [ ] Coordinates display below map
   - [ ] Enter name "My Custom Place"
   - [ ] Click "Add pin to bucket"
   - [ ] Location appears in bucket

4. **Drag & Reorder** (Desktop only)
   - [ ] Drag a location by the handle (⋮⋮)
   - [ ] Drop it in a different position
   - [ ] Number badges update (1, 2, 3...)

5. **Remove & Undo**
   - [ ] Click × button on a location
   - [ ] Snackbar appears at bottom
   - [ ] Click "Undo" within 5 seconds
   - [ ] Location is restored

6. **Publish Quote**
   - [ ] Fill in travel window (e.g., "March 2027")
   - [ ] Set travelers (e.g., 2)
   - [ ] Click "Get quotes" button
   - [ ] Success message appears
   - [ ] Returns to Step 1

### Priority 2: Persistence (5 minutes)

1. **Auto-Save Test**
   - [ ] Add 2-3 locations to bucket
   - [ ] Fill in travel details
   - [ ] Refresh the page (Ctrl+R / Cmd+R)
   - [ ] Everything is still there ✅

2. **LocalStorage Check**
   - [ ] Press F12 → Application tab → Local Storage
   - [ ] Look for:
     - `quote_bucket` (your locations)
     - `quote_form_draft` (travel details)
     - `quote_current_step` (1 or 2)

### Priority 3: Mobile Responsive (5 minutes)

1. **Open DevTools**
   - Press F12 → Toggle device toolbar (Ctrl+Shift+M)

2. **Test Mobile Sizes**
   - [ ] iPhone SE (375px) - everything stacks vertically
   - [ ] iPad (768px) - step indicators become vertical
   - [ ] Drag handles hidden on mobile
   - [ ] Undo snackbar full-width

### Priority 4: Edge Cases (5 minutes)

1. **Validation**
   - [ ] Try to go to Step 2 with empty bucket → disabled
   - [ ] Try to publish without travel window → no error, publishes anyway (optional field)

2. **Empty States**
   - [ ] Clear all locations → see "No destinations yet" message
   - [ ] Map shows default view

3. **Animations**
   - [ ] Add location → watch bounce animation
   - [ ] Remove location → smooth fade out
   - [ ] Reorder → smooth transition

## Browser Testing

Test in at least 2 browsers:
- [ ] Chrome/Chromium
- [ ] Firefox
- [ ] Safari (if on Mac)

## Known Issues (Expected)

- "Expand map" does nothing yet (placeholder for Phase 2)
- No keyboard shortcuts yet (Phase 4 feature)
- Recent quotes section uses old styling (not refactored yet)

## Success Criteria

✅ **Phase 1 is successful if**:
1. Step navigation works smoothly
2. Locations can be added/removed/reordered
3. Undo works within 5 seconds
4. Form persists across page refresh
5. Publishing works and clears form
6. Mobile layout is usable
7. No console errors

## Reporting Issues

If you find bugs, document:
1. What you did (steps to reproduce)
2. What you expected
3. What actually happened
4. Browser and device
5. Screenshot if visual issue

## Next Steps After Testing

Once testing is complete and any critical bugs are fixed:
- Mark Phase 1 as complete
- Begin Phase 2: Enhanced Search Features
  - Hover previews
  - Keyboard navigation
  - Recent searches
  - Location details panel

---

**Estimated Testing Time**: 25-30 minutes for thorough testing
**Priority**: High - blocks Phase 2 implementation
