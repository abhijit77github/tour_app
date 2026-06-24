from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import timedelta, datetime, timezone
from bson import ObjectId
import logging
from jose import JWTError, jwt

from ..models.user import (
    UserCreate, User, UserLogin, Token, UserInDB,
    ForgotPasswordRequest, VerifyOTPRequest, ResetPasswordRequest,
    RegistrationOTPVerifyRequest, ResendActivationOTPRequest
)
from ..database import get_database
from ..utils.auth import verify_password, get_password_hash, create_access_token, decode_access_token
from ..utils.audit_events import record_login_security_event
from ..utils.email import send_otp_email, send_password_reset_confirmation_email
from ..utils.otp import generate_otp, validate_otp, MAX_OTP_ATTEMPTS, OTP_VALIDITY_MINUTES
from ..config import settings
from ..utils.authorization import ensure_operator_access_context, has_permission, required_permission_for_request

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/auth", tags=["Authentication"])
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="auth/token")


def _request_ip(request: Request | None) -> str:
    if request and request.client and request.client.host:
        return request.client.host
    return "N/A"


async def _authenticate_login_user(db, *, email: str, password: str, request: Request | None) -> dict:
    normalized_email = email.strip().casefold()
    user = await db.users.find_one({"email": normalized_email})

    if not user or not verify_password(password, user["hashed_password"]):
        if user and user.get("user_type") == "operator":
            await record_login_security_event(
                db,
                principal_type="operator",
                email=normalized_email,
                outcome="invalid_credentials",
                ip_address=_request_ip(request),
                location="User Portal",
                user_name=user.get("full_name") or normalized_email,
                user_id=str(user.get("_id")),
                description=f"Invalid operator credentials for {normalized_email}",
            )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.get("is_active"):
        if user.get("user_type") == "operator":
            await record_login_security_event(
                db,
                principal_type="operator",
                email=normalized_email,
                outcome="inactive_account",
                ip_address=_request_ip(request),
                location="User Portal",
                user_name=user.get("full_name") or normalized_email,
                user_id=str(user.get("_id")),
                description=f"Login attempt against inactive operator account {normalized_email}",
                remediation="Verify the operator account status before retrying login.",
            )
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account not activated. Please verify the OTP sent to your email."
        )

    await db.users.update_one(
        {"_id": user["_id"]},
        {"$set": {"last_login": datetime.now(timezone.utc), "updated_at": datetime.utcnow()}},
    )

    if user.get("user_type") == "operator":
        await record_login_security_event(
            db,
            principal_type="operator",
            email=normalized_email,
            outcome="success",
            ip_address=_request_ip(request),
            location="User Portal",
            user_name=user.get("full_name") or normalized_email,
            user_id=str(user.get("_id")),
            description=f"Successful operator login for {normalized_email}",
            threshold_enabled=False,
        )

    return user


async def get_current_user(request: Request, token: str = Depends(oauth2_scheme)) -> dict:
    """Get current authenticated user"""
    email = decode_access_token(token)
    if email is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Could not validate credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    db = await get_database()
    user = await db.users.find_one({"email": email})
    if user is None:
        raise HTTPException(status_code=404, detail="User not found")

    request.state.user = user
    permission = required_permission_for_request(
        principal_type="user",
        path=request.url.path,
        method=request.method,
    )
    if user.get("user_type") == "operator":
        try:
            context = await ensure_operator_access_context(db, user=user)
            request.state.operator_access_context = context
            if permission and not has_permission(set(context["permissions"]), permission):
                raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Operator does not have access to this section")
        except HTTPException as exc:
            if request.url.path == "/operators/profile" and request.method == "POST" and exc.status_code == status.HTTP_404_NOT_FOUND:
                return user
            raise
    
    return user


async def get_current_operator_access_context(request: Request, current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("user_type") != "operator":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only operators can access this section")

    context = getattr(request.state, "operator_access_context", None)
    if context is None:
        db = await get_database()
        context = await ensure_operator_access_context(db, user=current_user)
        request.state.operator_access_context = context
    return context


@router.post("/register", response_model=dict, status_code=status.HTTP_201_CREATED)
async def register(user: UserCreate):
    """Register a new user"""
    db = await get_database()
    
    # Check if user already exists
    existing_user = await db.users.find_one({"email": user.email})
    if existing_user:
        if not existing_user.get("is_active"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email is already registered but not yet verified"
            )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Validate user type
    if user.user_type not in ["operator", "tourist"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User type must be 'operator' or 'tourist'"
        )
    
    # Create user
    user_dict = user.model_dump()
    password = user_dict.pop("password")
    otp = generate_otp()
    user_dict["hashed_password"] = get_password_hash(password)
    user_dict["is_active"] = False
    user_dict["registration_otp"] = otp
    user_dict["registration_otp_created_at"] = datetime.now(timezone.utc)
    user_dict["registration_otp_attempts"] = 0
    
    user_dict["created_at"] = datetime.utcnow()
    user_dict["updated_at"] = datetime.utcnow()
    
    result = await db.users.insert_one(user_dict)

    send_otp_email(
        recipient_email=user.email,
        otp=otp,
        full_name=user.full_name,
        purpose="account_activation",
        validity_minutes=OTP_VALIDITY_MINUTES,
    )
    
    return {
        "message": "Registration successful. Verify the OTP sent to your email to activate your account.",
        "user_id": str(result.inserted_id),
        "email": user.email,
        "requires_verification": True,
    }


@router.post("/verify-registration-otp", response_model=dict)
async def verify_registration_otp(request: RegistrationOTPVerifyRequest):
    """Verify registration OTP and activate account"""
    db = await get_database()

    user = await db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.get("is_active"):
        return {
            "message": "Account is already active",
            "email": request.email,
        }

    stored_otp = user.get("registration_otp")
    otp_created_at = user.get("registration_otp_created_at")
    attempts = user.get("registration_otp_attempts", 0)

    if not stored_otp or not otp_created_at:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active verification OTP. Please request a new one."
        )

    if attempts >= MAX_OTP_ATTEMPTS:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$unset": {"registration_otp": "", "registration_otp_created_at": "", "registration_otp_attempts": ""}}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed OTP attempts. Please request a new OTP."
        )

    is_valid, message = validate_otp(stored_otp, request.otp, otp_created_at)
    if not is_valid:
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$inc": {"registration_otp_attempts": 1}}
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "is_active": True,
                "email_verified_at": datetime.now(timezone.utc),
                "updated_at": datetime.utcnow(),
            },
            "$unset": {
                "registration_otp": "",
                "registration_otp_created_at": "",
                "registration_otp_attempts": "",
            }
        }
    )

    return {
        "message": "Account verified successfully. You can now log in.",
        "email": request.email,
    }


@router.post("/resend-registration-otp", response_model=dict)
async def resend_registration_otp(request: ResendActivationOTPRequest):
    """Resend registration OTP for inactive account"""
    db = await get_database()
    user = await db.users.find_one({"email": request.email})
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")

    if user.get("is_active"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is already active")

    otp = generate_otp()
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "registration_otp": otp,
                "registration_otp_created_at": datetime.now(timezone.utc),
                "registration_otp_attempts": 0,
                "updated_at": datetime.utcnow(),
            }
        }
    )

    send_otp_email(
        recipient_email=request.email,
        otp=otp,
        full_name=user.get("full_name"),
        purpose="account_activation",
        validity_minutes=OTP_VALIDITY_MINUTES,
    )

    return {
        "message": "A new verification OTP has been sent to your email.",
        "email": request.email,
    }


@router.post("/token", response_model=Token)
async def login(request: Request, form_data: OAuth2PasswordRequestForm = Depends()):
    """Login and get access token"""
    db = await get_database()
    user = await _authenticate_login_user(
        db,
        email=form_data.username,
        password=form_data.password,
        request=request,
    )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.post("/login", response_model=Token)
async def login_json(user_login: UserLogin, request: Request):
    """Login with JSON body and get access token"""
    db = await get_database()
    user = await _authenticate_login_user(
        db,
        email=user_login.email,
        password=user_login.password,
        request=request,
    )
    
    # Create access token
    access_token_expires = timedelta(minutes=settings.access_token_expire_minutes)
    access_token = create_access_token(
        data={"sub": user["email"]}, expires_delta=access_token_expires
    )
    
    return {"access_token": access_token, "token_type": "bearer"}


@router.get("/me")
async def get_me(current_user: dict = Depends(get_current_user)):
    """Get current user information"""
    user_data = {
        "_id": str(current_user["_id"]),
        "id": str(current_user["_id"]),  # Include both for compatibility
        "email": current_user["email"],
        "full_name": current_user["full_name"],
        "phone": current_user.get("phone"),
        "user_type": current_user["user_type"],
        "is_active": current_user["is_active"],
        "created_at": current_user["created_at"],
    }
    return user_data

# ============= PASSWORD RESET ENDPOINTS =============

@router.post("/forgot-password")
async def forgot_password(request: ForgotPasswordRequest):
    """
    Request password reset - sends OTP to email
    
    Args:
        request: Email address for password reset
    
    Returns:
        Message indicating OTP was sent
    """
    db = await get_database()
    
    # Find user by email
    user = await db.users.find_one({"email": request.email})
    if not user:
        # Don't reveal if email exists for security
        logger.warning(f"Password reset requested for non-existent email: {request.email}")
        return {
            "message": "If an account with that email exists, an OTP has been sent to it",
            "email": request.email
        }
    
    # Check if user account is active
    if not user.get("is_active"):
        logger.warning(f"Password reset attempted for inactive user: {request.email}")
        return {
            "message": "If an account with that email exists, an OTP has been sent to it",
            "email": request.email
        }
    
    # Generate OTP
    otp = generate_otp()
    
    # Store OTP in database with expiration
    await db.users.update_one(
        {"_id": user["_id"]},
        {
            "$set": {
                "password_reset_otp": otp,
                "password_reset_otp_created_at": datetime.now(timezone.utc),
                "password_reset_attempts": 0
            }
        }
    )
    
    logger.info(f"OTP generated for password reset: {request.email}")
    
    # Send OTP via email
    email_sent = send_otp_email(
        recipient_email=request.email,
        otp=otp,
        full_name=user.get("full_name"),
        purpose="password_reset",
        validity_minutes=OTP_VALIDITY_MINUTES,
    )
    
    if not email_sent:
        logger.error(f"Failed to send OTP email to {request.email}")
        # Still return success to not reveal email sending issues
    
    return {
        "message": "If an account with that email exists, an OTP has been sent to it",
        "email": request.email
    }


@router.post("/verify-otp")
async def verify_otp(request: VerifyOTPRequest):
    """
    Verify OTP for password reset
    
    Args:
        request: Email and OTP to verify
    
    Returns:
        Message indicating OTP verification status
    """
    db = await get_database()
    
    # Find user
    user = await db.users.find_one({"email": request.email})
    if not user:
        logger.warning(f"OTP verification attempted for non-existent email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )
    
    # Check if OTP exists
    stored_otp = user.get("password_reset_otp")
    otp_created_at = user.get("password_reset_otp_created_at")
    
    if not stored_otp or not otp_created_at:
        logger.warning(f"OTP verification attempted without requesting reset: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active OTP request. Please request password reset first."
        )
    
    # Check attempt limit
    attempts = user.get("password_reset_attempts", 0)
    if attempts >= 3:
        logger.warning(f"OTP attempt limit exceeded for {request.email}")
        # Clear the OTP after too many attempts
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$unset": {"password_reset_otp": "", "password_reset_otp_created_at": ""}}
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed OTP attempts. Please request a new OTP."
        )
    
    # Validate OTP
    is_valid, message = validate_otp(stored_otp, request.otp, otp_created_at)
    
    if not is_valid:
        # Increment attempt counter
        await db.users.update_one(
            {"_id": user["_id"]},
            {"$inc": {"password_reset_attempts": 1}}
        )
        logger.warning(f"Invalid OTP verification attempt for {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Mark OTP as verified by setting a verification token
    verification_token = create_access_token(
        data={"sub": request.email, "type": "password_reset"},
        expires_delta=timedelta(minutes=15)
    )
    
    logger.info(f"OTP verified successfully for {request.email}")
    
    return {
        "message": "OTP verified successfully",
        "verification_token": verification_token,
        "email": request.email
    }


@router.post("/reset-password")
async def reset_password(request: ResetPasswordRequest):
    """
    Reset password with verified OTP
    
    Args:
        request: Email, OTP, and new password
    
    Returns:
        Message indicating successful password reset
    """
    db = await get_database()
    
    # Find user
    user = await db.users.find_one({"email": request.email})
    if not user:
        logger.warning(f"Password reset attempted for non-existent email: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found"
        )

    try:
        payload = jwt.decode(request.verification_token, settings.secret_key, algorithms=[settings.algorithm])
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )

    if payload.get("sub") != request.email or payload.get("type") != "password_reset":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Verification token does not match this password reset request"
        )
    
    # Check if OTP exists and is still valid
    stored_otp = user.get("password_reset_otp")
    otp_created_at = user.get("password_reset_otp_created_at")
    
    if not stored_otp or not otp_created_at:
        logger.warning(f"Password reset attempted without OTP: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active OTP request. Please request password reset first."
        )
    
    # Validate OTP
    is_valid, message = validate_otp(stored_otp, request.otp, otp_created_at)
    
    if not is_valid:
        logger.warning(f"Invalid OTP for password reset: {request.email}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=message
        )
    
    # Validate new password
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Password must be at least 8 characters long"
        )
    
    # Check if new password is same as old password
    if verify_password(request.new_password, user.get("hashed_password", "")):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="New password cannot be the same as current password"
        )
    
    # Hash new password
    hashed_password = get_password_hash(request.new_password)
    
    # Update password and clear OTP
    try:
        await db.users.update_one(
            {"_id": user["_id"]},
            {
                "$set": {
                    "hashed_password": hashed_password,
                    "updated_at": datetime.now(timezone.utc)
                },
                "$unset": {
                    "password_reset_otp": "",
                    "password_reset_otp_created_at": "",
                    "password_reset_attempts": ""
                }
            }
        )
        
        logger.info(f"Password successfully reset for {request.email}")
        
        # Send confirmation email
        send_password_reset_confirmation_email(
            recipient_email=request.email,
            full_name=user.get("full_name")
        )
        
        return {
            "message": "Password reset successfully. You can now login with your new password.",
            "email": request.email
        }
        
    except Exception as e:
        logger.error(f"Error resetting password for {request.email}: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error resetting password. Please try again."
        )