# Tour App - Tour Operator & Tourist Management System

## Project Overview
A comprehensive web application connecting tour operators with tourists. Built with FastAPI (backend) and Vue.js (frontend), using MongoDB as the database.

## Features

### For Tour Operators:
- Register and create business profiles
- Add and manage serving areas and locations
- Upload photos and location details
- Create tour packages with multiple destinations
- Manage bookings and communicate with tourists
- View ratings and reviews

### For Tourists:
- Search for tour operators by location
- View operator profiles and ratings
- Browse popular destinations
- Create custom tour packages
- Book tours and manage bookings
- Rate and review completed tours
- View locations on interactive maps

## Tech Stack

### Backend:
- **Framework:** FastAPI
- **Database:** MongoDB (Motor async driver)
- **Authentication:** JWT (python-jose)
- **Password Hashing:** bcrypt
- **API Documentation:** Swagger/OpenAPI (auto-generated)

### Frontend:
- **Framework:** Vue.js 3
- **State Management:** Pinia
- **Routing:** Vue Router
- **HTTP Client:** Axios
- **Maps:** Leaflet
- **Build Tool:** Vite

## Project Structure

```
tour_app/
├── backend/
│   ├── models/          # Pydantic models
│   ├── routers/         # API endpoints
│   ├── utils/           # Utility functions (auth, etc.)
│   ├── config.py        # Configuration
│   ├── database.py      # MongoDB connection
│   ├── main.py          # FastAPI application
│   └── run.py           # Application entry point
├── frontend/
│   ├── src/
│   │   ├── assets/      # CSS and static files
│   │   ├── components/  # Vue components
│   │   ├── views/       # Page components
│   │   ├── router/      # Vue Router configuration
│   │   ├── stores/      # Pinia stores
│   │   ├── services/    # API services
│   │   ├── App.vue      # Root component
│   │   └── main.js      # Application entry
│   ├── index.html
│   ├── package.json
│   └── vite.config.js
├── requirements.txt
├── .gitignore
└── README.md
```

## Getting Started

### Prerequisites
- Python 3.8+
- Node.js 16+
- MongoDB (local or cloud instance)

### Backend Setup

1. **Create and activate virtual environment:**
   ```bash
   python -m venv venv
   venv\Scripts\activate  # Windows
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment:**
   - Copy `backend/.env.example` to `backend/.env`
   - Update MongoDB connection string and other settings
   ```
   MONGODB_URL=mongodb://localhost:27017
   DATABASE_NAME=tour_app_db
   SECRET_KEY=your-secret-key-change-this
   ```

4. **Run the backend:**
   ```bash
   cd backend
   python run.py
   ```
   Or using uvicorn directly:
   ```bash
   uvicorn backend.main:app --reload
   ```

   Backend will be available at: http://localhost:8000
   API Documentation: http://localhost:8000/docs

### Frontend Setup

1. **Install dependencies:**
   ```bash
   cd frontend
   npm install
   ```

2. **Run development server:**
   ```bash
   npm run dev
   ```

   Frontend will be available at: http://localhost:5173

### MongoDB Setup

**Local MongoDB:**
```bash
# Install MongoDB Community Edition
# Start MongoDB service
mongod --dbpath C:\data\db  # Windows
```

**MongoDB Atlas (Cloud):**
1. Create account at mongodb.com/cloud/atlas
2. Create a cluster
3. Get connection string
4. Update `MONGODB_URL` in `.env`

## API Endpoints

### Authentication
- `POST /auth/register` - Register new user
- `POST /auth/login` - Login (JSON)
- `POST /auth/token` - Login (form data)
- `GET /auth/me` - Get current user

### Operators
- `POST /operators/profile` - Create operator profile
- `GET /operators/profile/me` - Get my profile
- `PUT /operators/profile/me` - Update my profile
- `POST /operators/profile/serving-areas` - Add serving area
- `GET /operators/{operator_id}` - Get operator by ID
- `GET /operators/search/location` - Search operators

### Bookings
- `POST /bookings` - Create booking
- `GET /bookings/my-bookings` - Get my bookings
- `GET /bookings/{booking_id}` - Get booking details
- `PUT /bookings/{booking_id}/status` - Update booking status
- `POST /bookings/ratings` - Create rating
- `GET /bookings/ratings/operator/{operator_id}` - Get operator ratings

## Development Notes

### Adding New Features
1. Define Pydantic models in `backend/models/`
2. Create API routes in `backend/routers/`
3. Create Vue components/views in `frontend/src/`
4. Add API calls in `frontend/src/services/`

### Database Indexing
For better performance, create indexes:
```javascript
// In MongoDB shell
db.operator_profiles.createIndex({ "serving_areas.area_name": "text", "serving_areas.state": "text" })
db.operator_profiles.createIndex({ "average_rating": -1 })
db.users.createIndex({ "email": 1 }, { unique: true })
```

## Environment Variables

### Backend (.env)
```
MONGODB_URL=mongodb://localhost:27017
DATABASE_NAME=tour_app_db
SECRET_KEY=your-secret-key
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
DEBUG=True
HOST=0.0.0.0
PORT=8000
FRONTEND_URL=http://localhost:5173
```

## Future Enhancements
- Real-time chat between operators and tourists
- Payment integration
- Mobile app (Android/iOS)
- Advanced map features with route planning
- Email notifications
- Multi-language support
- Photo upload functionality
- Social media integration

## Contributing
This is an initial version. Features will be added iteratively based on requirements.

## License
Private Project

## Contact
For questions or issues, please refer to `application_requirement.txt` for project scope.

