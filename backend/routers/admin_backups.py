from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from fastapi.responses import FileResponse

from ..database import get_backup_database
from ..database import get_database
from ..models.backup import BackupJobCreate, BackupRestoreRequest
from ..routers.admin import get_current_admin, get_current_admin_access_context
from ..utils.authorization import has_permission
from ..utils.audit_events import append_audit_event_safe
from ..utils.backup_manager import (
    create_backup_job_record,
    create_restore_job_record,
    get_backup_capabilities,
    get_backup_job_or_none,
    list_backup_jobs,
    reconcile_job_on_status_check,
    schedule_backup_job,
    schedule_restore_job,
    serialize_backup_job,
)

router = APIRouter(prefix="/admin/backups", tags=["Admin Backups"])


def _require_backup_permission(context: dict) -> None:
    permissions = set(context.get("permissions", []))
    if not has_permission(permissions, "admin.backups.manage"):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only super admins can manage backups")


@router.get("/capabilities")
async def get_backup_capabilities_endpoint(
    context: dict = Depends(get_current_admin_access_context),
):
    _require_backup_permission(context)
    return get_backup_capabilities()


@router.get("/jobs")
async def list_backup_jobs_endpoint(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=50),
    job_type: str | None = Query(default=None),
    context: dict = Depends(get_current_admin_access_context),
):
    _require_backup_permission(context)
    db = await get_backup_database()
    return await list_backup_jobs(db, page=page, page_size=page_size, job_type=job_type)


@router.get("/jobs/{job_id}")
async def get_backup_job_endpoint(
    job_id: str,
    request: Request,
    context: dict = Depends(get_current_admin_access_context),
):
    _require_backup_permission(context)
    db = await get_backup_database()
    job = await reconcile_job_on_status_check(db, request.app.state, job_id=job_id)
    if not job:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup job not found")
    return serialize_backup_job(job)


@router.post("/jobs", status_code=status.HTTP_202_ACCEPTED)
async def queue_backup_job_endpoint(
    payload: BackupJobCreate,
    request: Request,
    admin: dict = Depends(get_current_admin),
    context: dict = Depends(get_current_admin_access_context),
):
    _require_backup_permission(context)
    db = await get_backup_database()
    job = await create_backup_job_record(
        db,
        admin=admin,
        destination=payload.destination,
        label=payload.label,
    )
    primary_db = await get_database()
    await append_audit_event_safe(
        primary_db,
        category="system",
        title="Backup job queued",
        severity="info",
        service="backup",
        error_code="BACKUP_QUEUED",
        message=f"Backup job {job['job_code']} queued for {payload.destination} storage",
        details=f"Queued by {admin.get('email')} with label {payload.label or 'none'}",
        metadata={
            "job_id": str(job["_id"]),
            "job_code": job["job_code"],
            "job_type": job["job_type"],
            "destination": payload.destination,
            "created_by": admin.get("email"),
        },
    )
    schedule_backup_job(db, request.app.state, job_id=job["_id"])
    return serialize_backup_job(job)


@router.post("/jobs/{job_id}/restore", status_code=status.HTTP_202_ACCEPTED)
async def queue_restore_job_endpoint(
    job_id: str,
    payload: BackupRestoreRequest,
    request: Request,
    admin: dict = Depends(get_current_admin),
    context: dict = Depends(get_current_admin_access_context),
):
    _require_backup_permission(context)
    db = await get_backup_database()
    source_job = await get_backup_job_or_none(db, job_id)
    if not source_job or source_job.get("job_type") != "backup":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup record not found")
    if source_job.get("status") != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Only completed backups can be restored")
    if payload.confirmation_code != source_job.get("job_code"):
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Confirmation code does not match the backup record")

    restore_job = await create_restore_job_record(
        db,
        admin=admin,
        source_job=source_job,
        source=payload.source,
        drop_existing_data=payload.drop_existing_data,
    )
    primary_db = await get_database()
    await append_audit_event_safe(
        primary_db,
        category="system",
        title="Restore job queued",
        severity="warning",
        service="backup",
        error_code="RESTORE_QUEUED",
        message=f"Restore job {restore_job['job_code']} queued from {payload.source} backup source",
        details=f"Queued by {admin.get('email')} for backup {source_job.get('job_code')}",
        metadata={
            "job_id": str(restore_job["_id"]),
            "job_code": restore_job["job_code"],
            "job_type": restore_job["job_type"],
            "source": payload.source,
            "source_backup_id": str(source_job["_id"]),
            "created_by": admin.get("email"),
        },
    )
    schedule_restore_job(db, request.app.state, job_id=restore_job["_id"])
    return serialize_backup_job(restore_job)


@router.get("/jobs/{job_id}/download")
async def download_backup_archive_endpoint(
    job_id: str,
    context: dict = Depends(get_current_admin_access_context),
):
    _require_backup_permission(context)
    db = await get_backup_database()
    job = await get_backup_job_or_none(db, job_id)
    if not job or job.get("job_type") != "backup":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Backup record not found")
    if job.get("status") != "completed":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Backup is not ready for download")
    local_path = (job.get("artifact") or {}).get("local_path")
    if not local_path:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="This backup is not stored locally")
    if not Path(local_path).exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Local backup archive is no longer available")
    return FileResponse(local_path, filename=(job.get("artifact") or {}).get("file_name") or f"{job.get('job_code')}.archive.gz")