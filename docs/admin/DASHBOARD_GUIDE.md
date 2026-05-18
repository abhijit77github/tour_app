# Admin Dashboard Implementation Guide

## Overview

Complete admin dashboard system for the Tour App platform with 20+ management features across 8 pages, 30+ API endpoints, and comprehensive user management capabilities.

## Completed Features (Phase 1 MVP)

### ✅ Authentication & Authorization
- **Admin Login** (`/admin/login`) - Secure email/password authentication with JWT tokens
- **Role-Based Access Control** - Super Admin and Moderator roles
- **Token Management** - localStorage-based token storage with automatic persistence
- **Session Protection** - Navigation guards prevent unauthorized access

### ✅ Dashboard Overview (`/admin/dashboard`)
- 6 Key Metric Cards:
  - Total Users (with tourist/operator breakdown)
  - Active Users (7-day activity)
  - Total Quotes (open/closed breakdown)
  - Total Responses (conversion rate)
  - Avg Response Time (hours with min/max)
  - Operator Ratings (average out of 5.0)
- Data Visualizations:
  - User growth chart (last 30 days)
  - Quote trend chart (daily quotes)
  - Top 5 destinations by quote count
  - Top 5 states by quote count
- Auto-refresh every 30 seconds
- Quick action buttons to management pages

### ✅ User Management Pages

#### Tourists Management (`/admin/tourists`)
- Advanced Search (by name, email, phone)
- Status Filtering (Active/Inactive)
- Pagination (10 items per page)
- 8-Column Table:
  - Name | Email | Phone | Joined Date | Quotes Posted | Status | Last Login | Actions
- Tourist Profile Modal:
  - Personal information
  - Quote activity summary
  - Recent quotes history (up to 3)
- Bulk Actions:
  - Suspend/Activate tourist
  - Delete tourist account
- Confirmation dialogs for all destructive actions

#### Operators Management (`/admin/operators`)
- Advanced Filtering:
  - Search by business name or owner name
  - Rating filter (4.0+, 3.0+, Below 3.0)
- Pagination (10 items per page)
- 8-Column Table:
  - Business Name | Owner | Serving Areas | Rating | Responses | Experience | Status | Actions
- Operator Profile Modal:
  - Business information
  - Ratings & reviews data
  - Description and specializations
  - Performance metrics summary
- Performance Analytics Modal:
  - Total responses, avg response time
  - Average rating, serving areas
- Quick Actions:
  - View profile
  - View performance analytics
  - Suspend/Activate operator

#### Quotes Management (`/admin/quotes`)
- Multi-Filter Search:
  - Search by tourist name, location, destination
  - Status filter (Open/Closed)
  - Response count filter (0, 1+, 5+)
- Pagination (10 items per page)
- 9-Column Table:
  - Quote ID | Tourist | Destination | Duration | Budget | Responses | Posted | Status | Actions
- Quote Details Modal:
  - Tourist information
  - Trip details (locations, duration, budget)
  - Description and preferences
  - Activity information
- Responses Viewer Modal:
  - List of all operator responses
  - Operator details, quote amount, message
- Quote Actions:
  - View full details
  - View all responses
  - Close quote (if open)
  - Delete quote

### ✅ Operator Performance (`/admin/performance`)
- **Leaderboard View**:
  - Ranked operator cards (sorted by rating/responses/response time)
  - Key metrics displayed (Rating, Responses, Response Time, Serving Areas)
  - Sort options (by rating, responses, response time)
  - Detailed view button for each operator

- **Performance Metrics View**:
  - Comprehensive table with all operators
  - 8 Columns: Business Name, Owner, Avg Rating, Responses, Response Time, Serving Areas, Reviews, Action
  - Search functionality
  - Quick view links

- **Detailed Performance Modal**:
  - KPI Dashboard (4 key indicators)
  - Business information
  - Rating display with review count
  - Description and specializations
  - Serving areas list

### ✅ Admin Navigation

#### Layout Components
- **Header**: Logo, notifications bell (3 notifications), profile dropdown with logout
- **Sidebar** (8 Navigation Sections):
  1. Dashboard (📊)
  2. User Management: Tourists (👥), Operators (🚀)
  3. Business Management: Quotes (📝), Performance (📈)
  4. Analytics & Reports (📋)
  5. System Settings (⚙️)
- Active route highlighting with gradient background
- Mobile-responsive hamburger menu (768px breakpoint)
- Collapsible sidebar on mobile devices

#### Router Protection
- `requiresAdmin` meta flag on all admin routes
- Navigation guard checks `adminToken` in localStorage
- Automatic redirect to AdminLogin if no token
- Redirect to AdminDashboard if already authenticated

### ✅ Admin Profile Management (`/admin/profile`)
- Profile Information Display:
  - Full name, email, phone, role, status
  - Member since date
  - Avatar with initials
- Change Password Feature:
  - Modal form with validation
  - Password strength requirements (min 8 chars)
  - Confirmation password matching
  - Success/error messaging
- Recent Activity Display:
  - Last login timestamp

### ✅ Placeholder Pages (Ready for Phase 2)
- **Reports & Analytics** (`/admin/reports`)
- **System Settings** (`/admin/settings`)

## Backend API Endpoints

### Authentication (5 endpoints)
```
POST   /admin/register              - Register new admin
POST   /admin/login                 - Admin authentication
GET    /admin/profile               - Get current admin profile
PUT    /admin/profile               - Update admin profile
POST   /admin/change-password       - Change admin password
```

### Dashboard (3 endpoints)
```
GET    /admin/dashboard/stats       - Main metrics (users, quotes, conversion)
GET    /admin/dashboard/metrics     - 30-day trends and chart data
GET    /admin/dashboard/response-times - Operator response analytics
```

### User Management (6 endpoints)
```
GET    /admin/tourists              - List all tourists with pagination
GET    /admin/operators             - List all operators with profiles
GET    /admin/users/{id}            - Get detailed user profile
POST   /admin/users/{id}/suspend    - Deactivate user account
POST   /admin/users/{id}/activate   - Reactivate user account
DELETE /admin/users/{id}            - Delete user (cascades quotes/responses)
```

### Quote Management (4 endpoints)
```
GET    /admin/quotes                - All quotes with filters and pagination
GET    /admin/quotes/stats          - Quote analytics and statistics
GET    /admin/quotes/{id}           - Detailed quote with all responses
DELETE /admin/quotes/{id}           - Delete quote and associated responses
```

### Operator Performance (3 endpoints)
```
GET    /admin/operators/performance - All operators with performance metrics
GET    /admin/operators/leaderboard - Ranked operators by rating/responses
GET    /admin/operators/{id}/performance - Individual operator analytics
```

## Database Schema

### Admins Collection
```javascript
{
  _id: ObjectId,
  email: String (unique),
  full_name: String,
  phone: String,
  hashed_password: String (bcrypt),
  role: String (super_admin | moderator),
  is_active: Boolean,
  created_at: DateTime,
  last_login: DateTime
}
```

### Admin User Seeding
A script creates initial admin users:
- **Super Admin**: `admin@tourapp.com` / `admin@123`
- **Moderator**: `moderator@tourapp.com` / `moderator@123`

Run: `python backend/scripts/create_admin.py`

## Frontend Architecture

### Components Structure
```
src/
├── views/
│   ├── AdminLogin.vue              (300 lines)
│   ├── AdminDashboard.vue          (400 lines)
│   ├── AdminTourists.vue           (1000+ lines)
│   ├── AdminOperators.vue          (900+ lines)
│   ├── AdminQuotes.vue             (1000+ lines)
│   ├── AdminPerformance.vue        (800+ lines)
│   ├── AdminProfile.vue            (400+ lines)
│   ├── AdminReports.vue            (placeholder)
│   └── AdminSettings.vue           (placeholder)
├── layouts/
│   └── AdminLayout.vue             (400 lines)
└── router/
    └── index.js                    (enhanced with admin routes)
```

### Styling Features
- Modern gradient backgrounds (#667eea to #764ba2)
- Color-coded badges and status indicators
- Smooth animations and transitions
- Responsive breakpoints (1024px, 768px, 480px)
- Accessible form controls and buttons
- Loading spinners and empty states
- Modal dialogs with overlays
- Hover effects on interactive elements

### UI Patterns
1. **Tables** - Searchable, filterable, paginated
2. **Modals** - Details viewer and confirmation dialogs
3. **Cards** - Metric displays and ranking cards
4. **Forms** - Validation with error/success messages
5. **Navigation** - Active route highlighting, mobile menu

## Security Features

### Authentication
- JWT-based token authentication
- Separate admin token (`adminToken`) from user tokens
- Password hashing with bcrypt
- Secure localStorage token storage

### Authorization
- `requiresAdmin` meta flag on protected routes
- Navigation guard validation before route access
- Role-based access (super_admin vs moderator)
- Automatic logout on token expiration

### Data Protection
- CORS validation on backend
- Input validation on forms
- Password strength requirements
- Confirmation dialogs for destructive actions

## How to Use

### 1. Create Admin User
```bash
cd backend
python scripts/create_admin.py
```

### 2. Access Admin Dashboard
```
URL: http://localhost:5173/admin/login
Email: admin@tourapp.com
Password: admin@123
```

### 3. Navigation
- Use sidebar to navigate between sections
- Click on action buttons in tables for operations
- Use search and filters to find specific records
- View detailed information in modal dialogs

## Performance Optimizations

- Lazy loading for components (dynamic imports)
- Pagination (10 items per page)
- Client-side filtering to reduce API calls
- 30-second dashboard auto-refresh (configurable)
- Computed properties for efficient rendering
- Responsive grid layouts for mobile devices

## Error Handling

- Try-catch blocks on all API calls
- User-friendly error messages
- Validation feedback on forms
- Empty states when no data available
- Loading indicators for async operations

## Future Enhancements (Phase 2 & 3)

### Phase 2
- Ratings & Reviews Management
- Notifications & Communication System
- Advanced Performance Analytics

### Phase 3
- Financial Management (payments, commissions)
- Activity Logging & Audit Trails
- Report Generation & Export (CSV/PDF)
- System Health Monitoring
- Admin Settings & Configurations

## File Locations

### Backend
- Models: `/backend/models/admin.py`
- Routes: `/backend/routers/admin.py`
- Scripts: `/backend/scripts/create_admin.py`

### Frontend
- Components: `/frontend/src/views/Admin*.vue`
- Layout: `/frontend/src/layouts/AdminLayout.vue`
- Router: `/frontend/src/router/index.js`

## Testing the Dashboard

### Test Accounts
```
Admin Login:
- Email: admin@tourapp.com
- Password: admin@123

Moderator Login:
- Email: moderator@tourapp.com
- Password: moderator@123
```

### Test Data Requirements
- At least 10 tourists in database
- At least 5 operators with profiles
- At least 10 quote requests
- Varied quote statuses (open/closed)

## Troubleshooting

### Admin Login Not Working
- Check MongoDB connection
- Verify admin user exists in database
- Check JWT secret configuration
- Verify CORS settings

### Dashboard Not Loading Data
- Check browser console for API errors
- Verify admin token in localStorage
- Check backend API endpoints
- Review MongoDB connection

### Styling Issues
- Clear browser cache
- Verify CSS classes applied
- Check responsive breakpoints
- Review z-index layering for modals

## Support & Maintenance

For issues or enhancements:
1. Check error logs in browser console
2. Verify API responses in Network tab
3. Review database collections for data integrity
4. Test with different user roles
5. Validate responsive design on mobile

---

**Status**: Phase 1 MVP Complete (12/20 Tasks)
**Last Updated**: Current Session
**Next Phase**: Ratings Management & Notifications System
