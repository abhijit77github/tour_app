from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from typing import List
import os
import uuid
from pathlib import Path
from ..routers.auth import get_current_user
from ..config import settings

router = APIRouter(prefix="/upload", tags=["Upload"])

# Create uploads directory if it doesn't exist
UPLOAD_DIR = Path(__file__).parent.parent / "uploads"
PROFILE_DIR = UPLOAD_DIR / "profiles"
LOCATION_DIR = UPLOAD_DIR / "locations"

PROFILE_DIR.mkdir(parents=True, exist_ok=True)
LOCATION_DIR.mkdir(parents=True, exist_ok=True)

# Allowed file extensions
ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB


def validate_image_file(file: UploadFile) -> None:
    """Validate uploaded image file"""
    # Check file extension
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File type not allowed. Allowed types: {', '.join(ALLOWED_EXTENSIONS)}"
        )
    
    # Check content type
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file content type. Must be an image."
        )


def save_upload_file(upload_file: UploadFile, destination: Path) -> str:
    """Save uploaded file and return filename"""
    # Generate unique filename
    file_ext = Path(upload_file.filename).suffix.lower()
    unique_filename = f"{uuid.uuid4()}{file_ext}"
    file_path = destination / unique_filename
    
    # Save file
    with open(file_path, "wb") as buffer:
        content = upload_file.file.read()
        
        # Check file size
        if len(content) > MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size: {MAX_FILE_SIZE / (1024*1024)}MB"
            )
        
        buffer.write(content)
    
    return unique_filename


@router.post("/profile-image")
async def upload_profile_image(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload profile image"""
    validate_image_file(file)
    
    try:
        filename = save_upload_file(file, PROFILE_DIR)
        image_url = f"/uploads/profiles/{filename}"
        
        return {
            "message": "Profile image uploaded successfully",
            "filename": filename,
            "url": image_url
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload file: {str(e)}"
        )


@router.post("/location-images")
async def upload_location_images(
    files: List[UploadFile] = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Upload multiple location images"""
    if len(files) > 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 10 images allowed per upload"
        )
    
    uploaded_files = []
    
    try:
        for file in files:
            validate_image_file(file)
            filename = save_upload_file(file, LOCATION_DIR)
            image_url = f"/uploads/locations/{filename}"
            
            uploaded_files.append({
                "filename": filename,
                "url": image_url,
                "original_name": file.filename
            })
        
        return {
            "message": f"{len(uploaded_files)} images uploaded successfully",
            "files": uploaded_files
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to upload files: {str(e)}"
        )


@router.delete("/image/{image_type}/{filename}")
async def delete_image(
    image_type: str,
    filename: str,
    current_user: dict = Depends(get_current_user)
):
    """Delete an uploaded image"""
    if image_type not in ["profiles", "locations"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid image type. Must be 'profiles' or 'locations'"
        )
    
    image_dir = PROFILE_DIR if image_type == "profiles" else LOCATION_DIR
    file_path = image_dir / filename
    
    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Image not found"
        )
    
    try:
        os.remove(file_path)
        return {"message": "Image deleted successfully"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete image: {str(e)}"
        )
