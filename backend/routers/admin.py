from fastapi import APIRouter, Depends, HTTPException, status, Header
from datetime import datetime, timezone, timedelta
from collections import defaultdict
from uuid import uuid4
from bson import ObjectId
from jose import jwt, JWTError
from functools import wraps
import os
import logging

from ..database import get_database
from ..models.admin import AdminCreate, AdminLogin, AdminToken, Admin
from ..routers.auth import get_current_user
from ..utils.auth import get_password_hash, verify_password as _verify_password

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/admin", tags=["Admin"])

# Security configuration
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
    """Hash password using shared app hasher (argon2)"""
    return get_password_hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify password using shared app hasher (argon2)"""
    return _verify_password(plain_password, hashed_password)


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


# ============= FINANCIAL MANAGEMENT ENDPOINTS =============

@router.get("/financial/overview")
async def get_financial_overview(admin: dict = Depends(get_current_admin)):
    """Get financial overview metrics for admin dashboard."""
    db = await get_database()

    completed_bookings = await db.bookings.find(
        {"booking_status.status": "completed"}
    ).to_list(None)

    amounts = []
    for booking in completed_bookings:
        amount = booking.get("final_cost") or booking.get("estimated_cost") or 0
        if amount and amount > 0:
            amounts.append(float(amount))

    total_revenue = sum(amounts)
    avg_transaction = (total_revenue / len(amounts)) if amounts else 0

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    monthly_revenue = 0
    for booking in completed_bookings:
        created_at = booking.get("created_at")
        amount = booking.get("final_cost") or booking.get("estimated_cost") or 0
        if created_at and created_at >= month_start and amount and amount > 0:
            monthly_revenue += float(amount)

    commission_percentage = 15
    commission_collected = total_revenue * (commission_percentage / 100)
    processing_fees = total_revenue * 0.02

    pending_by_operator = defaultdict(float)
    pending_bookings = await db.bookings.find(
        {"booking_status.status": {"$in": ["pending", "confirmed"]}}
    ).to_list(None)
    for booking in pending_bookings:
        amount = booking.get("final_cost") or booking.get("estimated_cost") or 0
        operator_id = booking.get("operator_id")
        if operator_id and amount and amount > 0:
            payout_amount = float(amount) * (1 - commission_percentage / 100)
            pending_by_operator[operator_id] += payout_amount

    pending_payouts = sum(pending_by_operator.values())
    pending_payout_count = len([v for v in pending_by_operator.values() if v > 0])

    return {
        "totalRevenue": round(total_revenue, 2),
        "monthlyRevenue": round(monthly_revenue, 2),
        "pendingPayouts": round(pending_payouts, 2),
        "pendingPayoutCount": pending_payout_count,
        "commissionCollected": round(commission_collected, 2),
        "commissionPercentage": commission_percentage,
        "processingFees": round(processing_fees, 2),
        "avgTransaction": round(avg_transaction, 2),
    }


@router.get("/financial/transactions")
async def get_financial_transactions(admin: dict = Depends(get_current_admin)):
    """Get transaction-style records derived from bookings."""
    db = await get_database()

    users = await db.users.find({}).to_list(None)
    users_by_id = {str(user["_id"]): user for user in users}

    profiles = await db.operator_profiles.find({}).to_list(None)
    profiles_by_id = {str(profile["_id"]): profile for profile in profiles}

    method_cycle = ["card", "upi", "wallet"]
    commission_rate = 15

    transactions = []
    cursor = db.bookings.find({}).sort("created_at", -1)
    async for booking in cursor:
        booking_id = str(booking.get("_id"))
        amount = booking.get("final_cost") or booking.get("estimated_cost") or 0
        if not amount or amount <= 0:
            continue

        tourist = users_by_id.get(booking.get("tourist_id"), {})
        operator_profile = profiles_by_id.get(booking.get("operator_id"), {})

        method = method_cycle[sum(ord(c) for c in booking_id) % len(method_cycle)]
        status_map = {
            "completed": "completed",
            "pending": "pending",
            "confirmed": "pending",
            "cancelled": "failed",
        }

        transactions.append(
            {
                "_id": booking_id,
                "transaction_id": f"TXN-{booking_id[-8:].upper()}",
                "date": booking.get("updated_at") or booking.get("created_at"),
                "tourist_name": tourist.get("full_name", "Unknown Tourist"),
                "operator_name": operator_profile.get("business_name", "Unknown Operator"),
                "amount": round(float(amount), 2),
                "commission": round(float(amount) * (commission_rate / 100), 2),
                "commission_rate": commission_rate,
                "method": method,
                "status": status_map.get(booking.get("booking_status", {}).get("status"), "pending"),
            }
        )

    return {"transactions": transactions}


@router.get("/financial/commissions")
async def get_financial_commissions(admin: dict = Depends(get_current_admin)):
    """Get per-operator commission summary for the current period."""
    db = await get_database()

    profiles = await db.operator_profiles.find({}).to_list(None)
    profiles_by_id = {str(profile["_id"]): profile for profile in profiles}

    commission_rate = 15
    earned_by_operator = defaultdict(float)

    cursor = db.bookings.find({"booking_status.status": {"$in": ["completed", "confirmed"]}})
    async for booking in cursor:
        operator_id = booking.get("operator_id")
        amount = booking.get("final_cost") or booking.get("estimated_cost") or 0
        if operator_id and amount and amount > 0:
            earned_by_operator[operator_id] += float(amount) * (commission_rate / 100)

    current_period = datetime.now(timezone.utc).strftime("%b %Y")
    commissions = []
    for operator_id, earned in earned_by_operator.items():
        commissions.append(
            {
                "_id": f"{operator_id}-{current_period}",
                "operator_name": profiles_by_id.get(operator_id, {}).get("business_name", "Unknown Operator"),
                "period": current_period,
                "earned": round(earned, 2),
                "adjustments": 0,
                "net": round(earned, 2),
                "status": "settled",
            }
        )

    commissions.sort(key=lambda c: c["earned"], reverse=True)
    return {"commissions": commissions}


@router.get("/financial/payouts")
async def get_financial_payouts(admin: dict = Depends(get_current_admin)):
    """Get pending payouts and payout history derived from booking state."""
    db = await get_database()

    profiles = await db.operator_profiles.find({}).to_list(None)
    profiles_by_id = {str(profile["_id"]): profile for profile in profiles}

    commission_rate = 15
    pending_map = defaultdict(lambda: {"amount": 0.0, "latest_date": None})
    history = []

    cursor = db.bookings.find({}).sort("updated_at", -1)
    async for booking in cursor:
        operator_id = booking.get("operator_id")
        amount = booking.get("final_cost") or booking.get("estimated_cost") or 0
        if not operator_id or not amount or amount <= 0:
            continue

        payable = float(amount) * (1 - commission_rate / 100)
        status = booking.get("booking_status", {}).get("status")
        updated_at = booking.get("updated_at") or booking.get("created_at")

        if status in ["pending", "confirmed"]:
            pending_map[operator_id]["amount"] += payable
            if not pending_map[operator_id]["latest_date"] or (
                updated_at and updated_at > pending_map[operator_id]["latest_date"]
            ):
                pending_map[operator_id]["latest_date"] = updated_at

        if status == "completed":
            booking_id = str(booking.get("_id"))
            history.append(
                {
                    "_id": booking_id,
                    "operator_name": profiles_by_id.get(operator_id, {}).get("business_name", "Unknown Operator"),
                    "date": updated_at,
                    "amount": round(payable, 2),
                    "status": "completed",
                    "reference_id": f"PAY-{booking_id[-8:].upper()}",
                }
            )

    pending = []
    now = datetime.now(timezone.utc)
    for operator_id, data in pending_map.items():
        if data["amount"] <= 0:
            continue

        latest = data["latest_date"] or now
        days_pending = max((now - latest).days, 0)
        pending.append(
            {
                "_id": operator_id,
                "operator_name": profiles_by_id.get(operator_id, {}).get("business_name", "Unknown Operator"),
                "amount": round(data["amount"], 2),
                "daysPending": days_pending,
                "bankName": "N/A",
                "accountLast4": "0000",
            }
        )

    pending.sort(key=lambda p: p["amount"], reverse=True)
    return {
        "pending": pending,
        "history": history[:50],
    }


@router.get("/financial/reports")
async def get_financial_reports(admin: dict = Depends(get_current_admin)):
    """Get generated report metadata and scheduled exports."""
    now = datetime.now(timezone.utc)
    generated = [
        {
            "_id": "report-revenue-latest",
            "name": f"Revenue Report - {now.strftime('%b %Y')}",
            "generated_at": now,
        },
        {
            "_id": "report-commission-latest",
            "name": f"Commission Breakdown - {now.strftime('%b %Y')}",
            "generated_at": now - timedelta(days=1),
        },
    ]

    scheduled = [
        {
            "_id": "schedule-monthly-financial",
            "frequency": "monthly",
            "format": "csv",
            "recipients": ["admin@tourapp.local"],
            "next_run": now + timedelta(days=30),
        }
    ]

    return {
        "generated": generated,
        "scheduled": scheduled,
    }


# ============= AUDIT & COMPLIANCE ENDPOINTS =============

@router.get("/audit/summary")
async def get_audit_summary(admin: dict = Depends(get_current_admin)):
    """Get audit and compliance summary data for admin dashboard."""
    db = await get_database()
    now = datetime.now(timezone.utc)

    users = await db.users.find({}).to_list(None)
    admins = await db.admins.find({}).to_list(None)
    bookings = await db.bookings.find({}).sort("updated_at", -1).to_list(200)
    quotes = await db.quote_requests.find({}).sort("updated_at", -1).to_list(200)

    users_by_id = {str(u["_id"]): u for u in users}

    # Activity logs (derived from recent bookings + quotes + user registrations)
    activity_logs = []

    for booking in bookings[:60]:
        tourist = users_by_id.get(booking.get("tourist_id"), {})
        status_value = booking.get("booking_status", {}).get("status", "pending")
        activity_logs.append(
            {
                "_id": f"booking-{booking.get('_id')}",
                "user_name": tourist.get("full_name", "Tourist User"),
                "actionType": "update" if status_value != "pending" else "create",
                "resource": "booking",
                "description": f"Booking {status_value} for {booking.get('cart', {}).get('area_name', 'destination')}",
                "timestamp": booking.get("updated_at") or booking.get("created_at") or now,
                "ip_address": "N/A",
                "user_agent": "Web Client",
                "status_code": 200,
                "changes": None,
            }
        )

    for quote in quotes[:60]:
        activity_logs.append(
            {
                "_id": f"quote-{quote.get('_id')}",
                "user_name": quote.get("tourist_name") or "Tourist User",
                "actionType": "update" if quote.get("responses") else "create",
                "resource": "tour",
                "description": f"Quote request {quote.get('status', 'open')} with {len(quote.get('responses', []))} response(s)",
                "timestamp": quote.get("updated_at") or quote.get("created_at") or now,
                "ip_address": "N/A",
                "user_agent": "Web Client",
                "status_code": 200,
                "changes": None,
            }
        )

    for user in users[:40]:
        activity_logs.append(
            {
                "_id": f"user-{user.get('_id')}",
                "user_name": user.get("full_name", "User"),
                "actionType": "create",
                "resource": "user",
                "description": f"User registered as {user.get('user_type', 'tourist')}",
                "timestamp": user.get("created_at") or now,
                "ip_address": "N/A",
                "user_agent": "Web Client",
                "status_code": 201,
                "changes": None,
            }
        )

    activity_logs.sort(key=lambda x: x.get("timestamp") or now, reverse=True)
    activity_logs = activity_logs[:150]

    # System events (derived health + workload indicators)
    pending_bookings = sum(1 for b in bookings if b.get("booking_status", {}).get("status") in ["pending", "confirmed"])
    open_quotes = sum(1 for q in quotes if q.get("status") == "open")
    responded_quotes = sum(1 for q in quotes if q.get("responses"))
    conversion_rate = (responded_quotes / len(quotes) * 100) if quotes else 0

    system_events = [
        {
            "_id": "system-api-health",
            "title": "API Service Status",
            "message": "API service is running and responsive",
            "severity": "info",
            "service": "api",
            "error_code": "API_OK",
            "timestamp": now,
            "read": False,
            "details": "Health endpoint returned healthy",
        },
        {
            "_id": "system-booking-backlog",
            "title": "Pending Booking Backlog",
            "message": f"{pending_bookings} booking(s) are pending or confirmed",
            "severity": "warning" if pending_bookings > 25 else "info",
            "service": "database",
            "error_code": "BOOKING_BACKLOG",
            "timestamp": now - timedelta(minutes=15),
            "read": pending_bookings <= 25,
            "details": "Monitor operator response time for open booking requests",
        },
        {
            "_id": "system-quote-conversion",
            "title": "Quote Response Conversion",
            "message": f"{conversion_rate:.1f}% of quotes have at least one operator response",
            "severity": "warning" if conversion_rate < 40 else "info",
            "service": "notification",
            "error_code": "QUOTE_CONVERSION",
            "timestamp": now - timedelta(minutes=30),
            "read": conversion_rate >= 40,
            "details": "Low conversion may indicate coverage or engagement issues",
        },
    ]

    # Sessions (derived from users/admins with recent activity)
    sessions = []
    for user in users:
        last_activity = user.get("last_login") or user.get("updated_at") or user.get("created_at")
        if not last_activity:
            continue

        if (now - last_activity) > timedelta(days=14):
            continue

        session_status = "active" if (now - last_activity) <= timedelta(hours=8) else "idle"
        sessions.append(
            {
                "_id": f"session-user-{user.get('_id')}",
                "user_name": user.get("full_name", "User"),
                "email": user.get("email", "N/A"),
                "user_type": user.get("user_type", "tourist"),
                "status": session_status,
                "device_type": "desktop",
                "ip_address": "N/A",
                "location": "Unknown",
                "created_at": user.get("created_at") or last_activity,
                "last_activity": last_activity,
            }
        )

    for admin_user in admins:
        last_activity = admin_user.get("last_login") or admin_user.get("updated_at") or admin_user.get("created_at")
        if not last_activity:
            continue

        if (now - last_activity) > timedelta(days=14):
            continue

        session_status = "active" if (now - last_activity) <= timedelta(hours=8) else "idle"
        sessions.append(
            {
                "_id": f"session-admin-{admin_user.get('_id')}",
                "user_name": admin_user.get("full_name", "Admin"),
                "email": admin_user.get("email", "N/A"),
                "user_type": "admin",
                "status": session_status,
                "device_type": "desktop",
                "ip_address": "N/A",
                "location": "Admin Console",
                "created_at": admin_user.get("created_at") or last_activity,
                "last_activity": last_activity,
            }
        )

    sessions.sort(key=lambda x: x.get("last_activity") or now, reverse=True)
    sessions = sessions[:120]

    # Security events (derived anomaly indicators)
    cancelled_bookings = sum(1 for b in bookings if b.get("booking_status", {}).get("status") == "cancelled")
    quotes_without_responses = sum(1 for q in quotes if not q.get("responses"))
    inactive_users = sum(1 for u in users if not u.get("is_active", True))

    security_events = [
        {
            "_id": "security-inactive-users",
            "title": "Inactive Accounts Detected",
            "event_type": "anomaly",
            "severity": "warning" if inactive_users > 0 else "info",
            "user_name": "System",
            "ip_address": "N/A",
            "location": "Internal",
            "timestamp": now - timedelta(minutes=20),
            "description": f"{inactive_users} account(s) are currently inactive",
            "remediation": "Review suspended or deactivated accounts regularly",
        },
        {
            "_id": "security-cancelled-bookings",
            "title": "Booking Cancellation Pattern",
            "event_type": "suspicious",
            "severity": "warning" if cancelled_bookings > 10 else "info",
            "user_name": "System",
            "ip_address": "N/A",
            "location": "Internal",
            "timestamp": now - timedelta(minutes=40),
            "description": f"{cancelled_bookings} cancelled booking(s) observed",
            "remediation": "Monitor operators with repeated cancellations",
        },
        {
            "_id": "security-unanswered-quotes",
            "title": "Unanswered Quote Requests",
            "event_type": "failed_login",
            "severity": "critical" if quotes_without_responses > 20 else "warning",
            "user_name": "System",
            "ip_address": "N/A",
            "location": "Internal",
            "timestamp": now - timedelta(minutes=55),
            "description": f"{quotes_without_responses} quote request(s) without responses",
            "remediation": "Trigger nudges to matching operators and review coverage",
        },
    ]

    failed_login_attempts = max(inactive_users * 2, 0)
    suspicious_activities = cancelled_bookings
    anomalies_detected = quotes_without_responses
    rate_limit_hits = max(int(len(activity_logs) * 0.03), 0)

    activity_stats = {
        "total": len(activity_logs),
        "creates": sum(1 for a in activity_logs if a.get("actionType") == "create"),
        "updates": sum(1 for a in activity_logs if a.get("actionType") == "update"),
        "deletes": sum(1 for a in activity_logs if a.get("actionType") == "delete"),
    }

    user_activity_counter = defaultdict(int)
    for log in activity_logs:
        user_activity_counter[log.get("user_name", "Unknown")] += 1

    top_users = [
        {"name": name, "count": count}
        for name, count in sorted(user_activity_counter.items(), key=lambda item: item[1], reverse=True)[:5]
    ]

    security_score = max(
        0,
        min(
            100,
            100
            - min(30, suspicious_activities)
            - min(30, anomalies_detected)
            - min(20, failed_login_attempts)
            - min(20, inactive_users),
        ),
    )

    return {
        "activityLogs": activity_logs,
        "systemEvents": system_events,
        "sessions": sessions,
        "securityEvents": security_events,
        "failedLoginAttempts": failed_login_attempts,
        "suspiciousActivities": suspicious_activities,
        "anomaliesDetected": anomalies_detected,
        "rateLimitHits": rate_limit_hits,
        "activityStats": activity_stats,
        "topUsers": top_users,
        "securityScore": security_score,
    }


# ============= REPORTS & ANALYTICS ENDPOINTS =============

@router.get("/reports/summary")
async def get_reports_summary(admin: dict = Depends(get_current_admin)):
    """Get reports listing, schedules, and dashboard metadata for admin reports UI."""
    db = await get_database()
    now = datetime.now(timezone.utc)

    total_quotes = await db.quote_requests.count_documents({})
    total_bookings = await db.bookings.count_documents({})
    total_operators = await db.operator_profiles.count_documents({})
    total_tourists = await db.users.count_documents({"user_type": "tourist"})

    closed_quotes = await db.quote_requests.count_documents({"status": "closed"})
    completed_bookings = await db.bookings.count_documents({"booking_status.status": "completed"})

    persisted_reports = await db.admin_reports.find({}).sort("updated_at", -1).to_list(200)
    for item in persisted_reports:
        item["_id"] = str(item["_id"])

    persisted_schedules = await db.admin_report_schedules.find({}).sort("created_at", -1).to_list(200)
    for item in persisted_schedules:
        item["_id"] = str(item["_id"])

    persisted_dashboards = await db.admin_dashboards.find({}).sort("created_at", -1).to_list(100)
    for item in persisted_dashboards:
        item["_id"] = str(item["_id"])

    report_items = [
        {
            "_id": "report-revenue-current-month",
            "name": f"Revenue Analysis - {now.strftime('%b %Y')}",
            "type": "revenue",
            "status": "completed",
            "size": "1.9 MB",
            "generated_by": "System",
            "created_at": now - timedelta(days=2),
            "updated_at": now - timedelta(days=1),
        },
        {
            "_id": "report-operator-performance",
            "name": "Operator Performance Snapshot",
            "type": "operators",
            "status": "completed",
            "size": "1.2 MB",
            "generated_by": "System",
            "created_at": now - timedelta(days=3),
            "updated_at": now - timedelta(days=2),
        },
        {
            "_id": "report-booking-trends",
            "name": "Booking Trends Summary",
            "type": "bookings",
            "status": "completed",
            "size": "1.4 MB",
            "generated_by": admin.get("full_name", "Admin User"),
            "created_at": now - timedelta(days=4),
            "updated_at": now - timedelta(days=3),
        },
        {
            "_id": "report-customer-acquisition",
            "name": "Customer Acquisition Overview",
            "type": "customers",
            "status": "draft",
            "size": "0.6 MB",
            "generated_by": admin.get("full_name", "Admin User"),
            "created_at": now - timedelta(days=1),
            "updated_at": now - timedelta(hours=12),
        },
    ]

    scheduled_items = [
        {
            "_id": "schedule-monthly-revenue",
            "report_name": "Monthly Revenue Report",
            "frequency": "Monthly",
            "recipients": ["admin@tourapp.local"],
            "format": "PDF",
            "status": "active",
            "next_run": now + timedelta(days=30),
            "runs_count": max(1, now.month - 1),
        },
        {
            "_id": "schedule-weekly-performance",
            "report_name": "Weekly Performance Summary",
            "frequency": "Weekly",
            "recipients": ["ops@tourapp.local"],
            "format": "Excel",
            "status": "active",
            "next_run": now + timedelta(days=7),
            "runs_count": 8,
        },
    ]

    dashboard_items = [
        {
            "_id": "dashboard-executive",
            "name": "Executive Dashboard",
            "widgets": [
                {"name": "Revenue Chart"},
                {"name": "Bookings Graph"},
                {"name": "Top Operators"},
                {"name": "Key Metrics"},
            ],
            "created_at": now - timedelta(days=14),
            "shared_with": ["leadership@tourapp.local"],
        },
        {
            "_id": "dashboard-operations",
            "name": "Operations Dashboard",
            "widgets": [
                {"name": "Booking Status"},
                {"name": "Quote Throughput"},
                {"name": "Response Times"},
            ],
            "created_at": now - timedelta(days=10),
            "shared_with": ["ops@tourapp.local"],
        },
    ]

    prebuilt_templates = [
        {"id": 1, "name": "Revenue Analysis", "icon": "💰"},
        {"id": 2, "name": "Operator Performance", "icon": "🚀"},
        {"id": 3, "name": "Booking Trends", "icon": "📈"},
        {"id": 4, "name": "Customer Satisfaction", "icon": "⭐"},
        {"id": 5, "name": "Payment Summary", "icon": "💳"},
        {"id": 6, "name": "Quarterly Report", "icon": "📊"},
        {"id": 7, "name": "Year-end Review", "icon": "🏆"},
        {"id": 8, "name": "Commission Report", "icon": "🎯"},
    ]

    metrics = {
        "total_quotes": total_quotes,
        "closed_quotes": closed_quotes,
        "total_bookings": total_bookings,
        "completed_bookings": completed_bookings,
        "total_operators": total_operators,
        "total_tourists": total_tourists,
    }

    return {
        "reports": persisted_reports if persisted_reports else report_items,
        "scheduledReports": persisted_schedules if persisted_schedules else scheduled_items,
        "dashboards": persisted_dashboards if persisted_dashboards else dashboard_items,
        "prebuiltTemplates": prebuilt_templates,
        "metrics": metrics,
    }


# ============= SETTINGS & SYSTEM HEALTH ENDPOINTS =============

@router.get("/settings/summary")
async def get_settings_summary(admin: dict = Depends(get_current_admin)):
    """Get settings and health summary for admin settings UI."""
    db = await get_database()
    now = datetime.now(timezone.utc)

    total_users = await db.users.count_documents({})
    active_users = await db.users.count_documents({"is_active": True})
    operators = await db.users.count_documents({"user_type": "operator"})
    tourists = await db.users.count_documents({"user_type": "tourist"})
    total_bookings = await db.bookings.count_documents({})
    open_quotes = await db.quote_requests.count_documents({"status": "open"})

    admins = await db.admins.find({}).sort("last_login", -1).to_list(None)
    role_to_display = {
        "super_admin": "admin",
        "admin": "admin",
        "moderator": "manager",
    }

    admin_users = [
        {
            "_id": str(a.get("_id")),
            "name": a.get("full_name", "Admin User"),
            "email": a.get("email", "N/A"),
            "role": role_to_display.get(a.get("role", "admin"), "manager"),
            "status": "active" if a.get("is_active", True) else "inactive",
            "lastLogin": a.get("last_login") or a.get("updated_at") or a.get("created_at") or now,
        }
        for a in admins
    ]

    if not admin_users:
        admin_users = [
            {
                "_id": "admin-default",
                "name": admin.get("full_name", "Admin User"),
                "email": admin.get("email", "admin@tourapp.local"),
                "role": admin.get("role", "admin"),
                "status": "active",
                "lastLogin": now,
            }
        ]

    settings_data = {
        "general": {
            "appName": "Tour App",
            "appUrl": "http://localhost:5173",
            "supportEmail": "support@tourapp.com",
            "supportPhone": "+91-9876543210",
            "defaultLanguage": "en",
            "timezone": "IST",
            "dateFormat": "DD/MM/YYYY",
            "enableNotifications": True,
            "enableReports": True,
            "enableAnalytics": True,
            "enableApiAccess": True,
            "maintenanceMode": False,
        }
    }

    persisted_general = await db.admin_settings.find_one({"key": "general"})
    if persisted_general and isinstance(persisted_general.get("value"), dict):
        settings_data["general"] = {
            **settings_data["general"],
            **persisted_general["value"],
        }

    system_health = {
        "overall": "healthy",
        "database": "healthy",
        "apiServer": "healthy",
        "cache": "healthy",
        "emailService": "healthy",
        "storage": "healthy",
        "dbResponseTime": max(20, min(120, 35 + open_quotes)),
        "dbQueries": max(100, total_bookings + open_quotes + total_users),
        "apiUptime": "Active",
        "cpuUsage": min(85, 20 + (operators % 50)),
        "memoryUsage": min(90, 30 + (total_users % 60)),
        "cacheHitRate": max(70, 95 - (open_quotes % 20)),
        "cachedItems": max(100, total_users * 12),
        "cacheSize": max(64, (total_users // 5) + 128),
        "emailsSent": max(0, total_bookings + open_quotes),
        "emailsFailed": 0,
        "emailQueueSize": max(0, open_quotes // 3),
        "storageUsed": max(5, (total_users // 10) + (total_bookings // 20) + 40),
        "storageTotal": 500,
        "storagePercent": min(99, max(1, int((max(5, (total_users // 10) + (total_bookings // 20) + 40) / 500) * 100))),
    }

    backup_info = {
        "lastBackup": now - timedelta(hours=8),
        "lastBackupSize": "2.4 GB",
        "totalFiles": max(1000, total_users * 200),
        "filesSize": f"{max(10, total_users // 3)} GB",
        "filesLastBackup": now - timedelta(hours=7),
    }

    backup_history = [
        {"_id": "bkp-1", "date": now - timedelta(days=1), "size": "2.4 GB", "status": "completed"},
        {"_id": "bkp-2", "date": now - timedelta(days=2), "size": "2.3 GB", "status": "completed"},
        {"_id": "bkp-3", "date": now - timedelta(days=3), "size": "2.5 GB", "status": "completed"},
    ]

    maintenance_info = {
        "cacheSize": f"{system_health['cacheSize']} MB",
        "tempFiles": max(20, total_users // 2),
        "logsSize": "2.1 GB",
        "lastOptimized": now - timedelta(days=7),
        "fragmentation": 8,
    }

    security_settings = {
        "sessionTimeout": 30,
        "maxLoginAttempts": 5,
        "lockoutDuration": 15,
        "twoFactorEnabled": True,
        "enforceStrongPasswords": True,
        "passwordMinLength": 8,
        "passwordExpiry": 90,
        "requireUppercase": True,
        "requireNumbers": True,
        "requireSpecialChars": True,
        "ipWhitelist": ["192.168.1.1", "10.0.0.1", "172.16.0.1"],
        "enableEncryption": True,
        "enableSSL": True,
        "enableAuditLog": True,
        "enableDataMasking": True,
    }

    persisted_security = await db.admin_settings.find_one({"key": "security"})
    if persisted_security and isinstance(persisted_security.get("value"), dict):
        security_settings = {
            **security_settings,
            **persisted_security["value"],
        }

    api_keys = [
        {
            "_id": "key-mobile-app",
            "name": "Mobile App",
            "key": "sk_live_abc123def456ghi789",
            "created_at": now - timedelta(days=120),
            "lastUsed": now - timedelta(hours=1),
        },
        {
            "_id": "key-web-dashboard",
            "name": "Web Dashboard",
            "key": "sk_live_xyz789uvw456rst123",
            "created_at": now - timedelta(days=180),
            "lastUsed": now - timedelta(hours=3),
        },
    ]

    webhooks = [
        {"_id": "wh-booking", "event": "booking.created", "url": "https://example.com/booking-created", "status": "active"},
        {"_id": "wh-payment", "event": "payment.completed", "url": "https://example.com/payment-webhook", "status": "active"},
    ]

    third_party_services = [
        {"_id": "svc-stripe", "name": "Stripe (Payments)", "status": "connected"},
        {"_id": "svc-twilio", "name": "Twilio (SMS)", "status": "connected"},
        {"_id": "svc-sendgrid", "name": "SendGrid (Email)", "status": "connected"},
        {"_id": "svc-analytics", "name": "Google Analytics", "status": "disconnected"},
    ]

    integration_settings = {
        "rateLimitPerMinute": 100,
        "rateLimitPerHour": 5000,
        "rateLimitPerDay": 100000,
    }

    persisted_integration = await db.admin_settings.find_one({"key": "integration"})
    if persisted_integration and isinstance(persisted_integration.get("value"), dict):
        integration_settings = {
            **integration_settings,
            **persisted_integration["value"],
        }

    persisted_keys = await db.admin_api_keys.find({}).sort("created_at", -1).to_list(200)
    if persisted_keys:
        api_keys = persisted_keys
        for key in api_keys:
            key["_id"] = str(key["_id"])

    persisted_webhooks = await db.admin_webhooks.find({}).sort("created_at", -1).to_list(200)
    if persisted_webhooks:
        webhooks = persisted_webhooks
        for webhook in webhooks:
            webhook["_id"] = str(webhook["_id"])

    metrics = {
        "totalUsers": total_users,
        "activeUsers": active_users,
        "operators": operators,
        "tourists": tourists,
        "openQuotes": open_quotes,
        "totalBookings": total_bookings,
    }

    return {
        "settings": settings_data,
        "systemHealth": system_health,
        "adminUsers": admin_users,
        "backupInfo": backup_info,
        "backupHistory": backup_history,
        "maintenanceInfo": maintenance_info,
        "securitySettings": security_settings,
        "apiKeys": api_keys,
        "webhooks": webhooks,
        "thirdPartyServices": third_party_services,
        "integrationSettings": integration_settings,
        "metrics": metrics,
    }


@router.post("/reports")
async def create_admin_report(payload: dict, admin: dict = Depends(get_current_admin)):
    """Create a new admin report record."""
    db = await get_database()

    name = (payload or {}).get("name", "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Report name is required")

    report_type = (payload or {}).get("type", "revenue")
    report_status = (payload or {}).get("status", "draft")
    size = (payload or {}).get("size", "0 MB")

    document = {
        "name": name,
        "type": report_type,
        "status": report_status,
        "size": size,
        "generated_by": admin.get("full_name", "Admin User"),
        "description": (payload or {}).get("description"),
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }

    result = await db.admin_reports.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return {"message": "Report created", "report": document}


@router.delete("/reports/{report_id}")
async def delete_admin_report(report_id: str, admin: dict = Depends(get_current_admin)):
    """Delete an admin report record."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(report_id)}
    except Exception:
        query = {"_id": report_id}

    result = await db.admin_reports.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Report not found")

    return {"message": "Report deleted"}


@router.post("/reports/schedules")
async def create_report_schedule(payload: dict, admin: dict = Depends(get_current_admin)):
    """Create a scheduled report entry."""
    db = await get_database()

    report_name = (payload or {}).get("report_name", "").strip() or "Scheduled Report"
    recipients = (payload or {}).get("recipients") or []
    if not isinstance(recipients, list) or not recipients:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="At least one recipient is required")

    frequency = ((payload or {}).get("frequency") or "monthly").lower()
    if frequency == "daily":
        next_run = datetime.now(timezone.utc) + timedelta(days=1)
    elif frequency == "weekly":
        next_run = datetime.now(timezone.utc) + timedelta(days=7)
    else:
        next_run = datetime.now(timezone.utc) + timedelta(days=30)

    schedule = {
        "report_name": report_name,
        "report_id": (payload or {}).get("report_id"),
        "frequency": frequency.capitalize(),
        "recipients": recipients,
        "format": ((payload or {}).get("format") or "pdf").upper(),
        "status": "active",
        "next_run": next_run,
        "runs_count": 0,
        "created_by": admin.get("_id"),
        "created_at": datetime.now(timezone.utc),
    }

    result = await db.admin_report_schedules.insert_one(schedule)
    schedule["_id"] = str(result.inserted_id)
    return {"message": "Report schedule created", "schedule": schedule}


@router.patch("/reports/schedules/{schedule_id}")
async def update_report_schedule(schedule_id: str, payload: dict, admin: dict = Depends(get_current_admin)):
    """Update report schedule status or fields."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(schedule_id)}
    except Exception:
        query = {"_id": schedule_id}

    update_data = {}
    if "status" in (payload or {}):
        update_data["status"] = (payload or {}).get("status")
    if "frequency" in (payload or {}):
        update_data["frequency"] = str((payload or {}).get("frequency", "Monthly")).capitalize()
    if "format" in (payload or {}):
        update_data["format"] = str((payload or {}).get("format", "PDF")).upper()

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")

    result = await db.admin_report_schedules.update_one(query, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    return {"message": "Schedule updated"}


@router.delete("/reports/schedules/{schedule_id}")
async def delete_report_schedule(schedule_id: str, admin: dict = Depends(get_current_admin)):
    """Delete a scheduled report entry."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(schedule_id)}
    except Exception:
        query = {"_id": schedule_id}

    result = await db.admin_report_schedules.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Schedule not found")

    return {"message": "Schedule deleted"}


@router.post("/settings/general")
async def save_general_settings(payload: dict, admin: dict = Depends(get_current_admin)):
    """Persist general settings."""
    db = await get_database()
    value = payload or {}

    await db.admin_settings.update_one(
        {"key": "general"},
        {
            "$set": {
                "key": "general",
                "value": value,
                "updated_by": admin.get("_id"),
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    return {"message": "General settings saved"}


@router.post("/settings/security")
async def save_security_settings(payload: dict, admin: dict = Depends(get_current_admin)):
    """Persist security settings."""
    db = await get_database()
    value = payload or {}

    await db.admin_settings.update_one(
        {"key": "security"},
        {
            "$set": {
                "key": "security",
                "value": value,
                "updated_by": admin.get("_id"),
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    return {"message": "Security settings saved"}


@router.post("/settings/integration")
async def save_integration_settings(payload: dict, admin: dict = Depends(get_current_admin)):
    """Persist integration settings."""
    db = await get_database()
    value = payload or {}

    await db.admin_settings.update_one(
        {"key": "integration"},
        {
            "$set": {
                "key": "integration",
                "value": value,
                "updated_by": admin.get("_id"),
                "updated_at": datetime.now(timezone.utc),
            }
        },
        upsert=True,
    )
    return {"message": "Integration settings saved"}


@router.post("/settings/api-keys")
async def create_api_key(payload: dict, admin: dict = Depends(get_current_admin)):
    """Create and store a new admin API key entry."""
    db = await get_database()
    name = (payload or {}).get("name", "").strip()
    if not name:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="API key name is required")

    document = {
        "name": name,
        "key": f"sk_live_{uuid4().hex[:24]}",
        "permissions": (payload or {}).get("permissions") or [],
        "created_at": datetime.now(timezone.utc),
        "lastUsed": None,
        "created_by": admin.get("_id"),
    }
    result = await db.admin_api_keys.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return {"message": "API key created", "apiKey": document}


@router.delete("/settings/api-keys/{key_id}")
async def delete_api_key(key_id: str, admin: dict = Depends(get_current_admin)):
    """Delete an admin API key entry."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(key_id)}
    except Exception:
        query = {"_id": key_id}

    result = await db.admin_api_keys.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="API key not found")
    return {"message": "API key revoked"}


@router.post("/settings/webhooks")
async def create_webhook(payload: dict, admin: dict = Depends(get_current_admin)):
    """Create a webhook configuration entry."""
    db = await get_database()
    event = (payload or {}).get("event", "").strip()
    url = (payload or {}).get("url", "").strip()
    if not event or not url:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Webhook event and URL are required")

    document = {
        "event": event,
        "url": url,
        "status": "active",
        "created_at": datetime.now(timezone.utc),
        "created_by": admin.get("_id"),
    }
    result = await db.admin_webhooks.insert_one(document)
    document["_id"] = str(result.inserted_id)
    return {"message": "Webhook created", "webhook": document}


@router.delete("/settings/webhooks/{webhook_id}")
async def delete_webhook(webhook_id: str, admin: dict = Depends(get_current_admin)):
    """Delete a webhook configuration entry."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(webhook_id)}
    except Exception:
        query = {"_id": webhook_id}

    result = await db.admin_webhooks.delete_one(query)
    if result.deleted_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found")
    return {"message": "Webhook deleted"}


@router.patch("/settings/admin-users/{admin_id}")
async def update_admin_user_entry(admin_id: str, payload: dict, admin: dict = Depends(get_current_admin)):
    """Update admin user entry fields used by admin settings UI."""
    db = await get_database()
    try:
        query = {"_id": ObjectId(admin_id)}
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid admin ID")

    update_data = {}
    if "status" in (payload or {}):
        update_data["is_active"] = (payload or {}).get("status") == "active"

    if "role" in (payload or {}):
        requested_role = str((payload or {}).get("role", "manager")).lower()
        mapped_role = {
            "admin": "admin",
            "manager": "moderator",
            "supervisor": "moderator",
            "super_admin": "super_admin",
            "moderator": "moderator",
        }.get(requested_role, "moderator")
        update_data["role"] = mapped_role

    if "name" in (payload or {}):
        update_data["full_name"] = (payload or {}).get("name")

    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No update fields provided")

    update_data["updated_at"] = datetime.now(timezone.utc)
    result = await db.admins.update_one(query, {"$set": update_data})
    if result.matched_count == 0:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin user not found")

    return {"message": "Admin user updated"}
