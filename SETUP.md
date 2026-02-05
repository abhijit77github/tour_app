# Tour App - Setup Guide

## Quick Start Commands

### Backend Setup
```powershell
# Activate virtual environment
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example)
copy backend\.env.example backend\.env

# Run the backend server
cd backend
python run.py
```

### Frontend Setup
```powershell
# Install dependencies
cd frontend
npm install

# Run development server
npm run dev
```

### MongoDB Local Setup
```powershell
# Make sure MongoDB is installed and running
# Default: mongodb://localhost:27017
```

## Verify Installation

1. Backend API: http://localhost:8000
2. API Docs: http://localhost:8000/docs
3. Frontend: http://localhost:5173

## Next Steps

1. Update `backend/.env` with your MongoDB connection string
2. Start developing additional features as per requirements
3. Test the basic flow:
   - Register as operator/tourist
   - Create operator profile
   - Search for locations
   - Create bookings
