# Testing Guide - New Features

## Prerequisites
- Backend running on http://localhost:8808
- Frontend running on http://localhost:5173
- MongoDB running
- At least one operator and one tourist account created

---

## 1. Testing Photo Upload System

### As Operator:

1. **Login as Operator**
   - Navigate to http://localhost:5173/login
   - Login with operator credentials

2. **Upload Profile Image**
   - Go to Operator Dashboard → Profile tab
   - Click "Edit Profile"
   - You'll see "Profile Image" section with upload area
   - **Test drag-and-drop:**
     - Drag an image file onto the upload area
     - Should see preview and upload status
   - **Test click-to-upload:**
     - Click the upload area
     - Select an image from file dialog
     - Should auto-upload and show success

3. **Add Serving Area with Images**
   - Go to "Serving Areas" tab
   - Click "+ Add Serving Area"
   - Fill in area name, state, country
   - Scroll to "Area Images" section
   - Upload multiple images (up to 10)
   - **Verify:** Each image shows with preview

4. **Add Sub-location with Images and Map**
   - In the same serving area form
   - Click "+ Add Sub-location"
   - Enter sub-location details
   - Upload images for this specific location
   - Click on the map to set coordinates
   - **Verify:** Map shows red marker, coordinates display below
   - Submit the form

5. **Verify Images Persist**
   - Refresh the page
   - Images should still be visible in your profile
   - Check serving areas list shows locations

### Expected Results:
- ✅ Images upload without errors
- ✅ Previews show before and after upload
- ✅ Coordinates are saved when map is clicked
- ✅ Images persist after page refresh

### Troubleshooting:
- **"Upload failed"** - Check backend is running and uploads directory exists
- **Images don't show** - Check browser console for CORS or URL issues
- **Map doesn't appear** - Check Leaflet library loaded correctly

---

## 2. Testing Map Integration

### In Operator Dashboard:

1. **Test Coordinate Selection**
   - Add a new serving area
   - Scroll to map section
   - Click anywhere on the map
   - **Verify:** 
     - Red marker appears
     - Coordinates display below map
     - "Confirm Location" button appears
   - Click "Confirm Location"
   - **Verify:** Coordinates are saved

2. **Test Map Visualization**
   - Add multiple sub-locations with different coordinates
   - Submit the form
   - View your serving areas
   - **Expected:** Map should show all locations

### As Tourist (Public Profile):

1. **View Operator Profile**
   - Logout or open incognito window
   - Go to Search page
   - Search for operators
   - Click "View Details" on any operator

2. **Check Map Display**
   - Scroll to "All Locations on Map" section
   - **Verify:**
     - Map loads correctly
     - All sub-locations appear as markers
     - Click markers to see location names

### Expected Results:
- ✅ Maps load without errors
- ✅ Markers appear for each location
- ✅ Clicking map sets coordinates
- ✅ All locations visible on public profile map

---

## 3. Testing Cart System

### As Tourist:

1. **Login as Tourist**
   - Navigate to login page
   - Use tourist account credentials

2. **Browse Operators**
   - Go to Search page
   - Search for operators (by area/state)
   - Click "View Details" on an operator with sub-locations

3. **Add Items to Cart**
   - Scroll through sub-locations
   - Click "+ Add to Cart" on several locations
   - **Verify:** Button changes to "In Cart"
   - Check header - cart badge should show count

4. **View Cart**
   - Click "🛒 Cart" link in header
   - **Verify:**
     - All added items appear
     - Items grouped by operator and area
     - Each item shows image, name, description
     - Map shows all cart locations

5. **Manage Cart Items**
   - Click "Exclude" on an item
   - **Verify:** Item appears grayed out
   - Click "Include" to re-add
   - Click "Remove" on an item
   - **Verify:** Item disappears from cart
   - Cart count in header updates

6. **View Cart on Map**
   - Scroll to map in cart view
   - **Verify:** All included items show as markers
   - Excluded items should not appear on map

7. **Send Booking Request**
   - Click "Send Booking Request" button
   - **Expected:** Success message
   - Cart items for that operator are removed
   - Go to operator dashboard → Bookings tab
   - **Verify:** New booking request appears

8. **Test Persistence**
   - Add items to cart
   - Refresh page or close/reopen browser
   - **Verify:** Cart items still present

### Expected Results:
- ✅ Add to cart works from operator profiles
- ✅ Cart badge shows correct count
- ✅ Items display with images and details
- ✅ Map visualizes all cart locations
- ✅ Include/exclude toggles work
- ✅ Remove from cart works
- ✅ Booking request sent successfully
- ✅ Cart persists after page refresh

---

## 4. Testing Public Operator Profiles

### As Any User (No Login Required):

1. **Navigate to Operator Profile**
   - Go to Search page (no login needed)
   - Search for operators
   - Click "View Details"

2. **Verify Profile Sections**
   - **Hero Section:**
     - Background image (if operator uploaded cover)
     - Business name
     - Rating display
   
   - **About Section:**
     - Business description
     - Contact number
     - Years of experience
     - Specializations as tags
   
   - **Map Section:**
     - "All Locations on Map" heading
     - Interactive map with all sub-location markers
     - Click markers to see popup info
   
   - **Serving Areas:**
     - Area cards with descriptions
     - Photo galleries (up to 3 images)
     - Sub-locations list
     - Each sub-location shows:
       - Name with "⭐ Popular" badge (if marked)
       - Description
       - Image thumbnail
       - Coordinates
       - "+ Add to Cart" button (if logged in as tourist)
   
   - **Reviews Section:**
     - Existing reviews display
     - Rating stars
     - Review text
     - Date

3. **Test Add to Cart** (as tourist):
   - Login as tourist
   - Go back to operator profile
   - Click "+ Add to Cart" on sub-locations
   - **Verify:** Button changes to "In Cart"
   - Check cart badge increments

4. **Test Responsiveness**
   - Resize browser window
   - **Verify:** Layout adapts to smaller screens
   - Mobile view should stack cards vertically

### Expected Results:
- ✅ Profile loads without authentication
- ✅ All sections display correctly
- ✅ Images show in galleries
- ✅ Map displays all locations
- ✅ Add to cart works (when logged in)
- ✅ Responsive design works

---

## 5. End-to-End Flow Test

### Complete User Journey:

1. **Operator Sets Up Profile** (5-10 min)
   - Login as operator
   - Upload profile image
   - Add 2-3 serving areas with images
   - Add 3-4 sub-locations per area with coordinates
   - Save and verify

2. **Tourist Browses** (3-5 min)
   - Login as tourist
   - Search for operator
   - View operator profile
   - Browse photos and map
   - Add 5-6 locations to cart

3. **Tourist Manages Cart** (2-3 min)
   - Open cart
   - View all items on map
   - Exclude 1-2 items
   - Remove 1 item
   - Send booking request

4. **Operator Receives Request** (1-2 min)
   - Switch to operator account
   - Go to Bookings tab
   - See new booking request
   - View selected/excluded items
   - Confirm or update status

### Expected Results:
- ✅ Complete flow works without errors
- ✅ Data persists correctly
- ✅ Cart items match booking request
- ✅ Excluded items marked in booking

---

## 🐛 Common Issues & Fixes

### Issue: "Upload failed"
**Cause:** Backend not running or uploads directory missing  
**Fix:** 
```bash
# Ensure backend is running
cd backend
python run.py
```

### Issue: Images don't display
**Cause:** CORS or static file serving issue  
**Fix:** Check backend logs, verify static files mounted in main.py

### Issue: Map doesn't load
**Cause:** Leaflet library not loaded  
**Fix:** 
```bash
cd frontend
npm install leaflet
npm run dev
```

### Issue: Cart doesn't persist
**Cause:** localStorage disabled or browser privacy mode  
**Fix:** Check browser settings, use regular (non-incognito) window

### Issue: Coordinates not saving
**Cause:** Model expects specific format  
**Fix:** Click "Confirm Location" button after selecting on map

### Issue: "Operator not found"
**Cause:** Invalid operator ID in URL  
**Fix:** Use search page to find valid operator profiles

---

## 📸 Visual Checkpoints

After testing, you should see:

1. **Operator Dashboard:**
   - ✅ Profile image in edit form
   - ✅ Area images in serving areas section
   - ✅ Maps with markers in forms

2. **Public Profile:**
   - ✅ Hero image background
   - ✅ Photo galleries for areas
   - ✅ Map with all location pins
   - ✅ Sub-location thumbnails

3. **Cart View:**
   - ✅ Cart items with images
   - ✅ Map showing cart locations
   - ✅ Cart badge in header

4. **Header:**
   - ✅ Cart icon with count badge (tourists)
   - ✅ Badge turns red when items added

---

## 🎯 Success Criteria

✅ **Pass:** All features work as described  
⚠️ **Warning:** Minor issues but core functionality works  
❌ **Fail:** Critical errors preventing use  

Rate each feature:
- [ ] Photo Upload System: ___
- [ ] Map Integration: ___
- [ ] Cart System: ___
- [ ] Public Profiles: ___

---

**Report any issues with:**
- Browser console errors (F12)
- Network tab showing failed requests
- Backend terminal logs
- Specific steps to reproduce
