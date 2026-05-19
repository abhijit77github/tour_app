from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pathlib import Path
from .config import settings
from .database import connect_to_mongo, close_mongo_connection, get_database
from .routers import auth, operators, bookings, upload, chat, recommendations, quotes, admin, tour_planner

# Create FastAPI app
app = FastAPI(
    title="Tour App API",
    description="API for Tour Operator and Tourist Management System",
    version="1.0.0",
    debug=settings.debug
)

# Mount static files for uploads
UPLOAD_DIR = Path(__file__).parent / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)
app.mount("/uploads", StaticFiles(directory=str(UPLOAD_DIR)), name="uploads")

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=[settings.frontend_url, "http://localhost:3000", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Event handlers
@app.on_event("startup")
async def startup_event():
    """Connect to MongoDB on startup and setup indexes"""
    await connect_to_mongo()
    
    # Create TTL index for chat messages (7 days retention)
    db = await get_database()
    try:
        # Create TTL index to auto-delete messages after 7 days (604800 seconds)
        await db.chat_messages.create_index(
            "created_at",
            expireAfterSeconds=604800  # 7 days = 7 * 24 * 60 * 60
        )
        print("✅ Chat message TTL index created (7-day retention)")
    except Exception as e:
        print(f"⚠️ TTL index may already exist or error occurred: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Close MongoDB connection on shutdown"""
    await close_mongo_connection()


# Include routers
app.include_router(auth.router)
app.include_router(operators.router)
app.include_router(bookings.router)
app.include_router(upload.router)
app.include_router(tour_planner.router)
app.include_router(chat.router)
app.include_router(recommendations.router)
app.include_router(quotes.router)
app.include_router(admin.router)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Welcome to Tour App API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc"
    }


# Health check
@app.get("/health")
async def health_check():
    return {"status": "healthy"}
