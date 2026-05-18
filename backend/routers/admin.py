from fastapi import APIRouter, Depends, HTTPException, status, Header
from datetime import datetime, timezone, timedelta
from bson import ObjectId
from jose import jwt, JWTError
from passlib.context import CryptContext
from functools import wraps
import os
import logging

from ..database import get_database
from ..models.admin import AdminCreate, AdminLogin, AdminToken, Admin
from ..routers.auth import get_current_user

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

# Security configuration
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
SECRET_KEY = os.getenv("SECRET_KEY", "your-secret-key-change-this")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 480  # 8 hours

# Valid admin roles
VALID_ADMIN_ROLES = {"super_admin", "admin", "moderator"}


async def get_token_from_header(authorization: str = Header(None)) -> str:
    """Extract and validate Bearer token from Authorization header"""
    if not authorization:
        logger.warning("Authorization header missing")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token required",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        logger.warning(f"Invalid Authorization format: {len(parts)} parts")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    return parts[1]


def hash_password(password: str) -> str:
    """Hash password using bcrypt"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password against hash"""
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: timedelta | None = None) -> str:
    """Create JWT access token with expiration"""
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.now(timezone.utc) + expires_delta
    else:
        expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    
    to_encode.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


async def get_current_admin(token: str = Depends(get_token_from_header)) -> dict:
    """
    Verify admin token and return admin data with full validation.
    
    Validation checks:
    - Token signature and expiration
    - Admin exists in database
    - Admin is active
    - Admin has valid role
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        admin_id: str = payload.get("sub")
        
        if admin_id is None:
            logger.warning("Token missing 'sub' claim")
            raise credentials_exception
            
        # Check token expiration (redundant as jwt.decode validates, but explicit for clarity)
        exp: int = payload.get("exp")
        if exp and datetime.fromtimestamp(exp, tz=timezone.utc) < datetime.now(timezone.utc):
            logger.warning(f"Token expired for admin: {admin_id}")
            raise credentials_exception
            
    except JWTError as e:
        logger.warning(f"JWT decode error: {str(e)}")
        raise credentials_exception
    
    db = await get_database()
    
    try:
        admin = await db.admins.find_one({"_id": ObjectId(admin_id)})
    except Exception as e:
        logger.error(f"Database error retrieving admin: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    if admin is None:
        logger.warning(f"Admin not found: {admin_id}")
        raise credentials_exception
    
    # Check if admin is active
    if not admin.get("is_active"):
        logger.warning(f"Inactive admin attempted access: {admin_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive",
        )
    
    # Validate admin role
    admin_role = admin.get("role", "")
    if admin_role not in VALID_ADMIN_ROLES:
        logger.warning(f"Invalid admin role: {admin_role} for admin: {admin_id}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Invalid admin role",
        )
    

    admin["_id"] = str(admin["_id"])
    return admin


@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_admin(admin_data: AdminCreate, admin: dict = Depends(get_current_admin)):
    """
    Register a new admin (protected - requires super_admin role).
    Only super admins can create new admin accounts.
    """
    # Check if requesting admin has super_admin role
    if admin.get("role") != "super_admin":
        logger.warning(f"Unauthorized registration attempt by {admin.get('_id')} with role {admin.get('role')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only super admins can register new admins"
        )
    
    db = await get_database()
    
    # Validate email format
    if not admin_data.email or "@" not in admin_data.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid email format"
        )
    
    # Validate role
    if admin_data.role not in VALID_ADMIN_ROLES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Invalid role. Must be one of: {', '.join(VALID_ADMIN_ROLES)}"
        )
    
    # Validate password strength (minimum 8 characters)
    if len(admin_data.password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Check if admin with this email already exists
    existing_admin = await db.admins.find_one({"email": admin_data.email})
    if existing_admin:
        logger.warning(f"Registration attempted with existing email: {admin_data.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Admin with this email already exists"
        )
    
    # Hash password
    hashed_password = hash_password(admin_data.password)
    
    # Create admin document
    admin_doc = {
        "email": admin_data.email,
        "full_name": admin_data.full_name,
        "phone": admin_data.phone,
        "role": admin_data.role,
        "hashed_password": hashed_password,
        "is_active": True,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
        "last_login": None,
        "created_by": admin.get("_id")  # Track who created this admin
    }
    
    try:
        result = await db.admins.insert_one(admin_doc)
        logger.info(f"New admin created: {result.inserted_id} by {admin.get('_id')}")
        
        return {
            "message": "Admin registered successfully",
            "admin_id": str(result.inserted_id),
            "role": admin_data.role
        }
    except Exception as e:
        logger.error(f"Error creating admin: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


@router.post("/login")
async def admin_login(credentials: AdminLogin):
    """
    Admin login endpoint with security logging.
    Returns access token with 8-hour expiration and admin info.
    Failed attempts are logged for security auditing.
    """
    db = await get_database()
    
    admin = await db.admins.find_one({"email": credentials.email})
    
    if not admin:
        logger.warning(f"Login attempt with non-existent email: {credentials.email}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not admin.get("is_active"):
        logger.warning(f"Login attempt by inactive admin: {admin.get('_id')}")
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin account is inactive"
        )
    
    if not verify_password(credentials.password, admin.get("hashed_password", "")):
        logger.warning(f"Failed login attempt for admin: {admin.get('_id')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    # Update last login timestamp
    try:
        await db.admins.update_one(
            {"_id": admin["_id"]},
            {"$set": {"last_login": datetime.now(timezone.utc)}}
        )
        logger.info(f"Successful login for admin: {admin.get('_id')}")
    except Exception as e:
        logger.error(f"Error updating last_login: {str(e)}")
    
    # Create access token
    access_token = create_access_token(data={"sub": str(admin["_id"])})
    
    admin["_id"] = str(admin["_id"])
    
    return AdminToken(
        access_token=access_token,
        token_type="bearer",
        admin=Admin(**admin)
    )


@router.get("/profile")
async def get_admin_profile(admin: dict = Depends(get_current_admin)):
    """Get current admin profile"""
    return Admin(**admin)


@router.put("/profile")
async def update_admin_profile(
    updates: dict,
    admin: dict = Depends(get_current_admin)
):
    """Update admin profile"""
    db = await get_database()
    
    # Only allow certain fields to be updated
    allowed_fields = {"full_name", "phone"}
    update_data = {k: v for k, v in updates.items() if k in allowed_fields}
    
    if not update_data:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid fields to update"
        )
    
    update_data["updated_at"] = datetime.now(timezone.utc)
    
    await db.admins.update_one(
        {"_id": ObjectId(admin["_id"])},
        {"$set": update_data}
    )
    
    return {"message": "Profile updated successfully"}


@router.post("/change-password")
async def change_admin_password(
    old_password: str,
    new_password: str,
    admin: dict = Depends(get_current_admin)
):
    """
    Change admin password with validation.
    Requires old password for verification and enforces minimum length.
    """
    db = await get_database()
    
    # Verify old password
    if not verify_password(old_password, admin.get("hashed_password", "")):
        logger.warning(f"Failed password change attempt for admin: {admin.get('_id')}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )
    
    # Validate new password
    if len(new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password must be at least 8 characters long"
        )
    
    # Prevent reusing same password
    if verify_password(new_password, admin.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as current password"
        )
    
    # Hash new password
    hashed_password = hash_password(new_password)
    
    try:
        await db.admins.update_one(
            {"_id": ObjectId(admin["_id"])},
            {
                "$set": {
                    "hashed_password": hashed_password,
                    "updated_at": datetime.now(timezone.utc)
                }
            }
        )
        logger.info(f"Password changed for admin: {admin.get('_id')}")
        return {"message": "Password changed successfully"}
    except Exception as e:
        logger.error(f"Error changing password: {str(e)}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)


# ============= DASHBOARD ENDPOINTS =============

@router.get("/dashboard/stats")
async def get_dashboard_stats(admin: dict = Depends(get_current_admin)):
    """Get main dashboard statistics"""
    db = await get_database()
    
    # Count total users
    total_tourists = await db.users.count_documents({"user_type": "tourist"})
    total_operators = await db.users.count_documents({"user_type": "operator"})
    total_users = total_tourists + total_operators
    
    # Active users (logged in last 7 days)
    seven_days_ago = datetime.now(timezone.utc) - timedelta(days=7)
    active_users = await db.users.count_documents({"last_login": {"$gte": seven_days_ago}})
    
    # Quote statistics
    total_quotes = await db.quote_requests.count_documents({})
    open_quotes = await db.quote_requests.count_documents({"status": "open"})
    closed_quotes = await db.quote_requests.count_documents({"status": "closed"})
    
    # Total responses
    total_responses = 0
    async for quote in db.quote_requests.find({}):
        total_responses += len(quote.get("responses", []))
    
    # Calculate conversion rate
    conversion_rate = ((total_responses / total_quotes) * 100) if total_quotes > 0 else 0
    
    # Average responses per quote
    avg_responses_per_quote = (total_responses / total_quotes) if total_quotes > 0 else 0
    
    # Operator statistics
    total_operator_profiles = await db.operator_profiles.count_documents({})
    
    # Get average operator rating
    pipeline = [
        {"$group": {"_id": None, "avg_rating": {"$avg": "$average_rating"}}}
    ]
    rating_result = await db.operator_profiles.aggregate(pipeline).to_list(1)
    avg_operator_rating = rating_result[0]["avg_rating"] if rating_result else 0
    
    return {
        "users": {
            "total": total_users,
            "tourists": total_tourists,
            "operators": total_operators,
            "active_last_7_days": active_users
        },
        "quotes": {
            "total": total_quotes,
            "open": open_quotes,
            "closed": closed_quotes,
            "total_responses": total_responses,
            "conversion_rate": round(conversion_rate, 2),
            "avg_responses_per_quote": round(avg_responses_per_quote, 2)
        },
        "operators": {
            "total_profiles": total_operator_profiles,
            "avg_rating": round(avg_operator_rating, 2)
        }
    }


@router.get("/dashboard/metrics")
async def get_dashboard_metrics(admin: dict = Depends(get_current_admin)):
    """Get detailed metrics for charts"""
    db = await get_database()
    
    # User registration trend (last 30 days)
    thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
    pipeline_users = [
        {"$match": {"created_at": {"$gte": thirty_days_ago}}},
        {"$group": {
            "_id": {
                "date": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
                "user_type": "$user_type"
            },
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id.date": 1}}
    ]
    user_growth = await db.users.aggregate(pipeline_users).to_list(None)
    
    # Quote trend (last 30 days)
    pipeline_quotes = [
        {"$match": {"created_at": {"$gte": thirty_days_ago}}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$created_at"}},
            "count": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}}
    ]
    quote_trend = await db.quote_requests.aggregate(pipeline_quotes).to_list(None)
    
    # Top destinations (most requested)
    pipeline_destinations = [
        {"$unwind": "$locations"},
        {"$group": {
            "_id": "$locations.name",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_destinations = await db.quote_requests.aggregate(pipeline_destinations).to_list(None)
    
    # Top states
    pipeline_states = [
        {"$unwind": "$locations"},
        {"$group": {
            "_id": "$locations.state",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 10}
    ]
    top_states = await db.quote_requests.aggregate(pipeline_states).to_list(None)
    
    return {
        "user_growth": [
            {
                "date": item["_id"]["date"],
                "tourists": next((x["count"] for x in user_growth if x["_id"]["date"] == item["_id"]["date"] and x["_id"]["user_type"] == "tourist"), 0),
                "operators": next((x["count"] for x in user_growth if x["_id"]["date"] == item["_id"]["date"] and x["_id"]["user_type"] == "operator"), 0)
            }
            for item in user_growth if "date" in item["_id"]
        ],
        "quote_trend": [
            {
                "date": item["_id"],
                "count": item["count"]
            }
            for item in quote_trend
        ],
        "top_destinations": [
            {
                "name": item["_id"],
                "count": item["count"]
            }
            for item in top_destinations
        ],
        "top_states": [
            {
                "name": item["_id"],
                "count": item["count"]
            }
            for item in top_states
        ]
    }


@router.get("/dashboard/response-times")
async def get_response_times(admin: dict = Depends(get_current_admin)):
    """Get operator response time analytics"""
    db = await get_database()
    
    response_times = []
    
    # Iterate through quotes with responses
    async for quote in db.quote_requests.find({"responses": {"$exists": True, "$not": {"$size": 0}}}):
        quote_created = quote.get("created_at")
        for response in quote.get("responses", []):
            response_time = response.get("created_at", quote_created)
            if quote_created and response_time:
                time_diff_hours = (response_time - quote_created).total_seconds() / 3600
                response_times.append(time_diff_hours)
    
    if response_times:
        avg_response_time = sum(response_times) / len(response_times)
        min_response_time = min(response_times)
        max_response_time = max(response_times)
        median_response_time = sorted(response_times)[len(response_times) // 2]
    else:
        avg_response_time = min_response_time = max_response_time = median_response_time = 0
    
    return {
        "average_hours": round(avg_response_time, 2),
        "minimum_hours": round(min_response_time, 2),
        "maximum_hours": round(max_response_time, 2),
        "median_hours": round(median_response_time, 2),
        "total_responses_analyzed": len(response_times)
    }


# ============= USER MANAGEMENT ENDPOINTS =============

@router.get("/tourists")
async def get_all_tourists(
    skip: int = 0,
    limit: int = 50,
    search: str = "",
    admin: dict = Depends(get_current_admin)
):
    """Get all tourists with pagination and search"""
    db = await get_database()
    
    # Build search query
    query = {"user_type": "tourist"}
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count
    total = await db.users.count_documents(query)
    
    # Get paginated results
    tourists = []
    cursor = db.users.find(query).skip(skip).limit(limit).sort("created_at", -1)
    async for tourist in cursor:
        # Count quotes posted
        quotes_count = await db.quote_requests.count_documents({"tourist_id": str(tourist["_id"])})
        
        tourist["_id"] = str(tourist["_id"])
        tourist["quotes_posted"] = quotes_count
        tourists.append(tourist)
    
    return {
        "tourists": tourists,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/operators")
async def get_all_operators(
    skip: int = 0,
    limit: int = 50,
    search: str = "",
    admin: dict = Depends(get_current_admin)
):
    """Get all operators with pagination and search"""
    db = await get_database()
    
    # Build search query for operators
    query = {"user_type": "operator"}
    if search:
        query["$or"] = [
            {"full_name": {"$regex": search, "$options": "i"}},
            {"email": {"$regex": search, "$options": "i"}},
            {"phone": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count
    total = await db.users.count_documents(query)
    
    # Get paginated results
    operators = []
    cursor = db.users.find(query).skip(skip).limit(limit).sort("created_at", -1)
    async for operator in cursor:
        operator_profile = await db.operator_profiles.find_one({"user_id": str(operator["_id"])})
        
        operator["_id"] = str(operator["_id"])
        operator["profile"] = None
        operator["serving_areas_count"] = 0
        operator["quotes_responded"] = 0
        operator["avg_rating"] = 0
        
        if operator_profile:
            operator["profile"] = {
                "_id": str(operator_profile["_id"]),
                "business_name": operator_profile.get("business_name"),
                "description": operator_profile.get("description"),
                "years_of_experience": operator_profile.get("years_of_experience"),
                "average_rating": operator_profile.get("average_rating", 0)
            }
            operator["serving_areas_count"] = len(operator_profile.get("serving_areas", []))
            operator["avg_rating"] = operator_profile.get("average_rating", 0)
            
            # Count responses
            responses_count = 0
            async for quote in db.quote_requests.find({}):
                responses_count += sum(1 for r in quote.get("responses", []) if r.get("operator_id") == str(operator_profile["_id"]))
            operator["quotes_responded"] = responses_count
        
        operators.append(operator)
    
    return {
        "operators": operators,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.post("/users/{user_id}/suspend")
async def suspend_user(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Suspend a user account"""
    db = await get_database()
    
    try:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": False, "updated_at": datetime.now(timezone.utc)}}
        )
        return {"message": "User suspended successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error suspending user: {str(e)}"
        )


@router.post("/users/{user_id}/activate")
async def activate_user(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Activate a suspended user account"""
    db = await get_database()
    
    try:
        await db.users.update_one(
            {"_id": ObjectId(user_id)},
            {"$set": {"is_active": True, "updated_at": datetime.now(timezone.utc)}}
        )
        return {"message": "User activated successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error activating user: {str(e)}"
        )


@router.delete("/users/{user_id}")
async def delete_user(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Delete a user account"""
    db = await get_database()
    
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete user
        await db.users.delete_one({"_id": ObjectId(user_id)})
        
        # If operator, also delete operator profile
        if user.get("user_type") == "operator":
            await db.operator_profiles.delete_one({"user_id": user_id})
        
        return {"message": "User deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error deleting user: {str(e)}"
        )


@router.get("/users/{user_id}")
async def get_user_details(
    user_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Get detailed information about a user"""
    db = await get_database()
    
    try:
        user = await db.users.find_one({"_id": ObjectId(user_id)})
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        user["_id"] = str(user["_id"])
        user.pop("hashed_password", None)  # Don't expose password
        
        # Add additional info based on user type
        if user.get("user_type") == "tourist":
            quotes = []
            cursor = db.quote_requests.find({"tourist_id": user["_id"]}).sort("created_at", -1)
            async for quote in cursor:
                quote["_id"] = str(quote["_id"])
                quotes.append(quote)
            user["quotes"] = quotes
            
        elif user.get("user_type") == "operator":
            profile = await db.operator_profiles.find_one({"user_id": user["_id"]})
            if profile:
                profile["_id"] = str(profile["_id"])
                user["profile"] = profile
        
        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error fetching user: {str(e)}"
        )


# ============= QUOTE MANAGEMENT ENDPOINTS =============

@router.get("/quotes")
async def get_all_quotes(
    skip: int = 0,
    limit: int = 50,
    status_filter: str = None,
    search: str = "",
    admin: dict = Depends(get_current_admin)
):
    """Get all quotes with pagination, filtering and search"""
    db = await get_database()
    
    query = {}
    
    # Filter by status
    if status_filter and status_filter in ["open", "closed"]:
        query["status"] = status_filter
    
    # Search by tourist name or location
    if search:
        query["$or"] = [
            {"tourist_name": {"$regex": search, "$options": "i"}},
            {"locations.name": {"$regex": search, "$options": "i"}},
            {"locations.state": {"$regex": search, "$options": "i"}},
            {"locations.country": {"$regex": search, "$options": "i"}}
        ]
    
    # Get total count
    total = await db.quote_requests.count_documents(query)
    
    # Get paginated results
    quotes = []
    cursor = db.quote_requests.find(query).skip(skip).limit(limit).sort("created_at", -1)
    async for quote in cursor:
        quote["_id"] = str(quote["_id"])
        if "tourist_id" in quote:
            quote["tourist_id"] = str(quote["tourist_id"])
        
        # Add response count
        quote["responses_count"] = len(quote.get("responses", []))
        quotes.append(quote)
    
    return {
        "quotes": quotes,
        "total": total,
        "skip": skip,
        "limit": limit
    }


@router.get("/quotes/stats")
async def get_quotes_stats(admin: dict = Depends(get_current_admin)):
    """Get quote analytics and statistics"""
    db = await get_database()
    
    # Status breakdown
    total_quotes = await db.quote_requests.count_documents({})
    open_quotes = await db.quote_requests.count_documents({"status": "open"})
    closed_quotes = await db.quote_requests.count_documents({"status": "closed"})
    
    # Quotes by state
    pipeline_states = [
        {"$unwind": "$locations"},
        {"$group": {
            "_id": "$locations.state",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 15}
    ]
    quotes_by_state = await db.quote_requests.aggregate(pipeline_states).to_list(None)
    
    # Quotes by country
    pipeline_countries = [
        {"$unwind": "$locations"},
        {"$group": {
            "_id": "$locations.country",
            "count": {"$sum": 1}
        }},
        {"$sort": {"count": -1}},
        {"$limit": 15}
    ]
    quotes_by_country = await db.quote_requests.aggregate(pipeline_countries).to_list(None)
    
    # Average quote budget (if available)
    pipeline_budget = [
        {"$group": {
            "_id": None,
            "avg_budget": {"$avg": "$budget"},
            "min_budget": {"$min": "$budget"},
            "max_budget": {"$max": "$budget"}
        }}
    ]
    budget_stats = await db.quote_requests.aggregate(pipeline_budget).to_list(1)
    
    return {
        "status_breakdown": {
            "total": total_quotes,
            "open": open_quotes,
            "closed": closed_quotes
        },
        "by_state": [
            {"name": item["_id"], "count": item["count"]}
            for item in quotes_by_state
        ],
        "by_country": [
            {"name": item["_id"], "count": item["count"]}
            for item in quotes_by_country
        ],
        "budget_stats": budget_stats[0] if budget_stats else {}
    }


@router.get("/quotes/{quote_id}")
async def get_quote_details(
    quote_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Get detailed information about a quote"""
    db = await get_database()
    
    try:
        quote = await db.quote_requests.find_one({"_id": ObjectId(quote_id)})
        if not quote:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Quote not found"
            )
        
        quote["_id"] = str(quote["_id"])
        if "tourist_id" in quote:
            quote["tourist_id"] = str(quote["tourist_id"])
        
        # Get tourist details
        tourist = await db.users.find_one({"_id": ObjectId(quote["tourist_id"])})
        if tourist:
            tourist["_id"] = str(tourist["_id"])
            tourist.pop("hashed_password", None)
            quote["tourist_details"] = tourist
        
        # Get operator details for each response
        for response in quote.get("responses", []):
            operator_profile = await db.operator_profiles.find_one({"_id": ObjectId(response.get("operator_id", "0"))})
            if operator_profile:
                response["operator_profile"] = {
                    "_id": str(operator_profile["_id"]),
                    "business_name": operator_profile.get("business_name"),
                    "average_rating": operator_profile.get("average_rating")
                }
        
        return quote
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error fetching quote: {str(e)}"
        )


# ============= OPERATOR PERFORMANCE ENDPOINTS =============

@router.get("/operators/performance")
async def get_operators_performance(
    skip: int = 0,
    limit: int = 50,
    sort_by: str = "rating",
    admin: dict = Depends(get_current_admin)
):
    """Get operator performance metrics"""
    db = await get_database()
    
    # Sort options: rating, responses, experience
    sort_field = {"rating": "average_rating", "experience": "years_of_experience"}.get(sort_by, "average_rating")
    
    operators = []
    cursor = db.operator_profiles.find({}).skip(skip).limit(limit).sort(sort_field, -1)
    
    async for operator in cursor:
        operator["_id"] = str(operator["_id"])
        
        # Count total responses
        total_responses = 0
        async for quote in db.quote_requests.find({}):
            total_responses += sum(1 for r in quote.get("responses", []) if r.get("operator_id") == str(operator["_id"]))
        
        # Count quotes responded in last 30 days
        thirty_days_ago = datetime.now(timezone.utc) - timedelta(days=30)
        recent_responses = 0
        async for quote in db.quote_requests.find({"updated_at": {"$gte": thirty_days_ago}}):
            recent_responses += sum(1 for r in quote.get("responses", []) if r.get("operator_id") == str(operator["_id"]))
        
        operator["total_responses"] = total_responses
        operator["recent_responses_30d"] = recent_responses
        operator["response_rate"] = round((operator.get("average_rating", 0) / 5 * 100) if operator.get("average_rating") else 0, 2)
        
        operators.append(operator)
    
    return {
        "operators": operators,
        "skip": skip,
        "limit": limit
    }


@router.get("/operators/leaderboard")
async def get_operators_leaderboard(
    metric: str = "rating",
    limit: int = 10,
    admin: dict = Depends(get_current_admin)
):
    """Get operator leaderboard by various metrics"""
    db = await get_database()
    
    if metric == "rating":
        sort_field = "average_rating"
    elif metric == "experience":
        sort_field = "years_of_experience"
    elif metric == "specializations":
        sort_field = "specializations"
    else:
        sort_field = "average_rating"
    
    leaderboard = []
    cursor = db.operator_profiles.find({}).sort(sort_field, -1).limit(limit)
    
    async for i, operator in enumerate(cursor):
        operator["_id"] = str(operator["_id"])
        
        # Count total responses
        total_responses = 0
        async for quote in db.quote_requests.find({}):
            total_responses += sum(1 for r in quote.get("responses", []) if r.get("operator_id") == str(operator["_id"]))
        
        operator["total_responses"] = total_responses
        operator["rank"] = i + 1
        leaderboard.append(operator)
    
    return {
        "metric": metric,
        "leaderboard": leaderboard
    }


@router.get("/operators/{operator_id}/performance")
async def get_operator_performance_details(
    operator_id: str,
    admin: dict = Depends(get_current_admin)
):
    """Get detailed performance analytics for a specific operator"""
    db = await get_database()
    
    try:
        operator = await db.operator_profiles.find_one({"_id": ObjectId(operator_id)})
        if not operator:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operator not found"
            )
        
        operator["_id"] = str(operator["_id"])
        
        # Count responses and quotes
        total_responses = 0
        response_times = []
        
        async for quote in db.quote_requests.find({}):
            for response in quote.get("responses", []):
                if response.get("operator_id") == str(operator["_id"]):
                    total_responses += 1
                    # Calculate response time
                    quote_created = quote.get("created_at")
                    response_created = response.get("created_at", quote_created)
                    if quote_created and response_created:
                        time_diff = (response_created - quote_created).total_seconds() / 3600
                        response_times.append(time_diff)
        
        # Calculate statistics
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Get specializations with count of responses for each
        specializations_count = {}
        for spec in operator.get("specializations", []):
            specializations_count[spec] = 0
        
        async for quote in db.quote_requests.find({}):
            for response in quote.get("responses", []):
                if response.get("operator_id") == str(operator["_id"]):
                    for spec in operator.get("specializations", []):
                        specializations_count[spec] += 1
        
        return {
            "operator": operator,
            "performance": {
                "total_responses": total_responses,
                "average_response_time_hours": round(avg_response_time, 2),
                "average_rating": operator.get("average_rating", 0),
                "total_reviews": operator.get("total_reviews", 0),
                "specializations": specializations_count,
                "serving_areas_count": len(operator.get("serving_areas", []))
            }
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Error fetching operator performance: {str(e)}"
        )
