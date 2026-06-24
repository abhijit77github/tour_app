# Admin Dashboard - Quick Start Guide

## Prerequisites
- MongoDB running locally (or connection configured)
- Backend server running (`python main.py` from `/backend`)
- Frontend development server running (`npm run dev` from `/frontend`)

## Step 1: Ensure Local Admin Accounts Exist

Local Docker development already seeds admin accounts into `tour_app_db` via `backend.scripts.seed_local_dev`.
If you need to recreate or backfill them from the host machine, run:

```bash
cd /path/to/tour_app
python -m backend.scripts.create_admin
```

**Output:**
```
==================================================
   TOUR APP - LOCAL ADMIN USER CREATION
==================================================

Connected to MongoDB at mongodb://localhost:27017
Target database: tour_app_db

Ensuring super_admin account...
✅ Admin user created successfully!
   Email: admin@tourapp.local
   Password: admin@123
   Role: super_admin
   ID: <admin_id>


Ensuring moderator account...
✅ Moderator user created successfully!
   Email: moderator@tourapp.local
   Password: moderator@123
   Role: moderator
   ID: <moderator_id>

==================================================
   Local admin setup complete.
==================================================
```

## Step 2: Access Admin Dashboard

1. Open browser: `http://localhost:5173/admin/login`
2. Enter credentials:
   - Email: `admin@tourapp.local`
   - Password: `admin@123`
3. Click "Sign In"

## Step 3: Explore Dashboard Features

### Dashboard Overview (`/admin/dashboard`)
- View key business metrics
- Check user growth and quote trends
- See top destinations and states
- Quick actions to management pages

### Tourists Management (`/admin/tourists`)
- Search tourists by name, email, or phone
- Filter by status (Active/Inactive)
- View detailed tourist profiles
- Suspend or activate tourists
- View recent quote activity
- Delete tourist accounts

**Actions:**
- 👁️ **View** - See full profile and quote history
- ⏸️ **Suspend** - Deactivate tourist account
- ▶️ **Activate** - Reactivate suspended tourist
- 🗑️ **Delete** - Remove tourist (requires confirmation)

### Operators Management (`/admin/operators`)
- Search operators by business or owner name
- Filter by rating (4.0+, 3.0+, Below 3.0)
- View detailed operator profiles
- Check performance analytics
- Suspend or activate operators

**Actions:**
- 👁️ **View** - See operator profile and details
- 📈 **Performance** - View detailed analytics
- ⏸️ **Suspend** - Deactivate operator
- ▶️ **Activate** - Reactivate operator

### Quotes Management (`/admin/quotes`)
- Search quotes by tourist name, location, destination
- Filter by status (Open/Closed)
- Filter by response count (0, 1+, 5+)
- View complete quote details
- See all operator responses
- Close or delete quotes

**Actions:**
- 👁️ **View** - See full quote details
- 💬 **Responses** - View all operator responses
- ✓ **Close** - Mark quote as closed (archive)
- 🗑️ **Delete** - Remove quote permanently

### Operator Performance (`/admin/performance`)

**Leaderboard View:**
- Rankings sorted by rating, responses, or response time
- Quick performance snapshot for each operator
- Detailed analytics modal

**Metrics View:**
- Table showing all operators with metrics
- Comprehensive performance comparison
- Search functionality

## Key Features to Test

### 1. Search & Filtering
- Try searching by various criteria
- Combine multiple filters
- Verify pagination works correctly

### 2. Modals & Details
- Click on actions to open modals
- Verify detailed information displays
- Test modal close buttons

### 3. Confirmation Dialogs
- Test suspend/activate actions
- Verify delete confirmations
- Confirm cancellation works

### 4. Responsive Design
- Resize browser window
- Test on mobile (DevTools mobile mode)
- Verify layout adapts properly

### 5. Data Operations
- Create test data if needed
- Update and delete records
- Verify changes reflect in real-time

## Admin Panel Navigation

```
Dashboard (📊)
├── Overview
├── Key Metrics
├── Trends & Charts
└── Quick Actions

User Management (👥)
├── Tourists (👥)
│   ├── Search & Filter
│   ├── View Profiles
│   └── Manage Status
└── Operators (🚀)
    ├── Search & Filter
    ├── View Profiles
    └── Manage Status

Business Management (📝)
├── Quotes (📝)
│   ├── Search & Filter
│   ├── View Details
│   └── Manage Responses
└── Performance (📈)
    ├── Leaderboard
    └── Metrics Table

System (⚙️)
├── Reports (📋) - Coming Soon
├── Settings (⚙️) - Coming Soon
└── My Profile (👤)
    ├── Account Info
    ├── Change Password
    └── Activity Log
```

## Common Tasks

### Change Admin Password
1. Click profile menu → "My Profile"
2. Scroll to Security section
3. Click "Change Password"
4. Enter current and new password
5. Click "Update Password"

### Find Inactive Users
1. Go to Tourists or Operators
2. Use Status filter
3. Select "Inactive"
4. View list of inactive accounts

### Search Specific Quote
1. Go to Quotes Management
2. Use search box (enter location, tourist name, etc.)
3. Filter by status if needed
4. Click on quote to view details

### View Operator Details
1. Go to Operators
2. Click 👁️ (View) button
3. See business info, ratings, specializations
4. Click "Close" to exit modal

### Check Performance Metrics
1. Go to Performance
2. Switch between Leaderboard and Metrics tabs
3. Use search or sort options
4. Click "View" for individual details

## Test Data Scenarios

### Scenario 1: Tourist Management
- Search for a tourist
- View their profile and recent quotes
- Suspend the tourist
- Reactivate the tourist

### Scenario 2: Operator Ranking
- View the leaderboard
- Sort by different metrics
- Check top-rated operator details
- Compare performance

### Scenario 3: Quote Management
- Find quotes with no responses
- View quote details and responses
- Check operator information
- Close or delete quotes as needed

## Keyboard Shortcuts

- `Esc` - Close modal dialogs
- `Tab` - Navigate form fields
- `Enter` - Submit forms
- `Ctrl/Cmd + F` - Page search (browser)

## Browser Console Tips

Check for errors:
1. Open DevTools: `F12` or `Ctrl+Shift+I`
2. Go to Console tab
3. Look for red error messages
4. Check Network tab for API calls

## API Response Examples

### Dashboard Stats
```json
{
  "total_users": 150,
  "total_tourists": 100,
  "total_operators": 50,
  "active_users_7_days": 75,
  "total_quotes": 200,
  "total_responses": 450,
  "avg_response_time_hours": 2.5
}
```

### Tourists List
```json
{
  "tourists": [
    {
      "_id": "...",
      "full_name": "John Doe",
      "email": "john@example.com",
      "phone": "+91-9876543210",
      "user_type": "tourist",
      "is_active": true,
      "created_at": "2024-01-15T10:30:00",
      "last_login": "2024-01-20T14:45:00",
      "quotes_posted": 5
    }
  ]
}
```

## Troubleshooting

### Issue: "Unauthorized" on login
- **Solution**: Verify email and password are correct
- Check MongoDB for admin user
- Restart backend server

### Issue: No data showing in tables
- **Solution**: Check if test data exists in database
- Verify backend API is running
- Check browser Network tab for API responses

### Issue: Modal not closing
- **Solution**: Click the ✕ button or Esc key
- Refresh page if stuck
- Check browser console for errors

### Issue: Styling looks broken
- **Solution**: Clear browser cache (Ctrl+Shift+Delete)
- Hard refresh (Ctrl+Shift+R)
- Check mobile/desktop responsive mode

## Next Steps

After exploring the dashboard:

1. **Create Test Data**:
   - Add tourists and operators
   - Create quote requests
   - Generate responses

2. **Test Workflows**:
   - Complete user management flow
   - Try all filter combinations
   - Test all action buttons

3. **Review Code**:
   - Check component implementations
   - Review API endpoints
   - Understand data flow

4. **Provide Feedback**:
   - Note any UI/UX improvements
   - Report bugs or issues
   - Suggest feature enhancements

## File Locations

- Admin Views: `/frontend/src/views/Admin*.vue`
- Admin Layout: `/frontend/src/layouts/AdminLayout.vue`
- Admin Backend: `/backend/routers/admin.py`
- Admin Models: `/backend/models/admin.py`

## Performance Tips

- Use pagination for large datasets (10 items/page)
- Apply filters to reduce results
- Search for specific records
- Use sorting to find what you need
- Clear filters when done

## Support

For questions or issues:
1. Check the detailed ADMIN_DASHBOARD_GUIDE.md
2. Review error messages in console
3. Check Network tab for API errors
4. Verify database connection
5. Restart servers if needed

---

**Happy Exploring! 🚀**

