from __future__ import annotations

import asyncio
import hashlib
import logging
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

import boto3
from bson import ObjectId

from ..config import settings
from .audit_events import append_audit_event_safe

BACKUP_COLLECTION = "backup_jobs"
BACKUP_TASKS_STATE_KEY = "backup_tasks"

logger = logging.getLogger(__name__)


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _primary_database(ops_db):
    return ops_db.client[settings.database_name]


async def _record_backup_system_event(ops_db, *, job: dict, severity: str, error_code: str, message: str, details: str) -> None:
    primary_db = _primary_database(ops_db)
    title = f"{job.get('job_type', 'backup').title()} job {job.get('status', 'updated')}"
    await append_audit_event_safe(
        primary_db,
        category="system",
        title=title,
        severity=severity,
        service="backup",
        error_code=error_code,
        message=message,
        details=details,
        metadata={
            "job_id": str(job.get("_id")),
            "job_code": job.get("job_code"),
            "job_type": job.get("job_type"),
            "status": job.get("status"),
            "destination": job.get("destination"),
            "source": job.get("source"),
            "created_by": (job.get("created_by") or {}).get("email"),
        },
    )


def _base_directory() -> Path:
    configured = Path(settings.backup_local_dir)
    if configured.is_absolute():
        return configured
    return Path(__file__).resolve().parents[1] / configured


def _temporary_directory() -> Path:
    return _base_directory() / ".tmp"


def ensure_backup_directories() -> None:
    _base_directory().mkdir(parents=True, exist_ok=True)
    _temporary_directory().mkdir(parents=True, exist_ok=True)


def _job_code(prefix: str) -> str:
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
    return f"{prefix}-{stamp}-{uuid4().hex[:6].upper()}"


def serialize_backup_job(job: dict) -> dict:
    serialized = dict(job)
    serialized["_id"] = str(serialized["_id"])
    if serialized.get("source_backup_id"):
        serialized["source_backup_id"] = str(serialized["source_backup_id"])
    for key in ("created_at", "updated_at", "started_at", "completed_at"):
        if serialized.get(key):
            serialized[key] = serialized[key].isoformat()
    return serialized


def get_backup_capabilities() -> dict:
    ensure_backup_directories()
    local_dir = _base_directory()
    return {
        "local": {
            "enabled": True,
            "directory": str(local_dir),
            "writable": local_dir.exists() and local_dir.is_dir(),
        },
        "s3": {
            "enabled": bool(settings.backup_s3_bucket),
            "bucket": settings.backup_s3_bucket,
            "prefix": settings.backup_s3_prefix,
            "region": settings.backup_s3_region or settings.aws_region,
        },
        "tools": {
            "mongodump": shutil.which(settings.backup_tool_mongodump),
            "mongorestore": shutil.which(settings.backup_tool_mongorestore),
        },
    }


def _get_s3_client():
    client_kwargs = {
        "service_name": "s3",
        "region_name": settings.backup_s3_region or settings.aws_region,
    }
    if settings.aws_access_key_id and settings.aws_secret_access_key:
        client_kwargs["aws_access_key_id"] = settings.aws_access_key_id
        client_kwargs["aws_secret_access_key"] = settings.aws_secret_access_key
    if settings.aws_session_token:
        client_kwargs["aws_session_token"] = settings.aws_session_token
    return boto3.client(**client_kwargs)


def _build_archive_name(job_code: str) -> str:
    return f"{job_code}.archive.gz"


def _build_local_archive_path(job_code: str) -> Path:
    ensure_backup_directories()
    return _base_directory() / _build_archive_name(job_code)


def _build_temp_restore_path(job_code: str) -> Path:
    ensure_backup_directories()
    return _temporary_directory() / _build_archive_name(job_code)


def _build_s3_key(job_code: str) -> str:
    prefix = settings.backup_s3_prefix.strip("/")
    file_name = _build_archive_name(job_code)
    return f"{prefix}/{file_name}" if prefix else file_name


def _sha256_for_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


async def _run_process(*args: str) -> tuple[int, str]:
    process = await asyncio.create_subprocess_exec(
        *args,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await process.communicate()
    combined = "\n".join(
        part.decode("utf-8", errors="ignore").strip()
        for part in (stdout, stderr)
        if part
    ).strip()
    return process.returncode, combined


async def _mark_job_running(db, job_id: ObjectId) -> None:
    now = _utcnow()
    await db[BACKUP_COLLECTION].update_one(
        {"_id": job_id},
        {"$set": {"status": "running", "started_at": now, "updated_at": now}},
    )


async def _mark_job_failed(db, job_id: ObjectId, message: str) -> None:
    now = _utcnow()
    job = await db[BACKUP_COLLECTION].find_one({"_id": job_id})
    await db[BACKUP_COLLECTION].update_one(
        {"_id": job_id, "status": {"$in": ["queued", "running"]}},
        {
            "$set": {
                "status": "failed",
                "error_message": message,
                "completed_at": now,
                "updated_at": now,
            }
        },
    )
    if job:
        job.update({"status": "failed", "error_message": message, "completed_at": now})
        await _record_backup_system_event(
            db,
            job=job,
            severity="error",
            error_code=f"{str(job.get('job_type') or 'backup').upper()}_FAILED",
            message=f"{job.get('job_type', 'Backup').title()} job {job.get('job_code')} failed",
            details=message,
        )


async def _mark_job_completed(db, job_id: ObjectId, artifact: dict | None = None) -> None:
    now = _utcnow()
    job = await db[BACKUP_COLLECTION].find_one({"_id": job_id})
    payload = {
        "status": "completed",
        "completed_at": now,
        "updated_at": now,
        "error_message": None,
    }
    if artifact is not None:
        payload["artifact"] = artifact
    await db[BACKUP_COLLECTION].update_one({"_id": job_id}, {"$set": payload})
    if job:
        job.update({"status": "completed", "artifact": artifact or {}, "completed_at": now})
        artifact_label = (artifact or {}).get("file_name") or (artifact or {}).get("restored_from_job_code") or "artifact"
        await _record_backup_system_event(
            db,
            job=job,
            severity="info",
            error_code=f"{str(job.get('job_type') or 'backup').upper()}_COMPLETED",
            message=f"{job.get('job_type', 'Backup').title()} job {job.get('job_code')} completed",
            details=f"Completed successfully with {artifact_label}",
        )


async def reconcile_orphaned_jobs(db) -> int:
    now = _utcnow()
    stale_message = "Job was interrupted before completion. Status was reconciled on server startup."
    result = await db[BACKUP_COLLECTION].update_many(
        {"status": {"$in": ["queued", "running"]}},
        {
            "$set": {
                "status": "failed",
                "error_message": stale_message,
                "completed_at": now,
                "updated_at": now,
            }
        },
    )
    return result.modified_count


async def reconcile_job_on_status_check(db, app_state, *, job_id: str) -> dict | None:
    task_store = getattr(app_state, BACKUP_TASKS_STATE_KEY, {}) or {}
    task = task_store.get(job_id)
    if task and not task.done():
        return await get_backup_job_or_none(db, job_id)

    job = await get_backup_job_or_none(db, job_id)
    if not job or job.get("status") not in {"queued", "running"}:
        return job

    await _mark_job_failed(
        db,
        job["_id"],
        "Job was interrupted before completion. Status was reconciled during a manual refresh because no active worker task was found.",
    )
    return await db[BACKUP_COLLECTION].find_one({"_id": job["_id"]})


async def create_backup_job_record(db, *, admin: dict, destination: str, label: str | None) -> dict:
    now = _utcnow()
    document = {
        "job_code": _job_code("BKP"),
        "job_type": "backup",
        "status": "queued",
        "destination": destination,
        "label": label,
        "created_by": {
            "admin_id": admin.get("_id"),
            "email": admin.get("email"),
            "full_name": admin.get("full_name"),
        },
        "created_at": now,
        "updated_at": now,
    }
    result = await db[BACKUP_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def create_restore_job_record(
    db,
    *,
    admin: dict,
    source_job: dict,
    source: str,
    drop_existing_data: bool,
) -> dict:
    now = _utcnow()
    document = {
        "job_code": _job_code("RST"),
        "job_type": "restore",
        "status": "queued",
        "source": source,
        "source_backup_id": source_job["_id"],
        "drop_existing_data": drop_existing_data,
        "created_by": {
            "admin_id": admin.get("_id"),
            "email": admin.get("email"),
            "full_name": admin.get("full_name"),
        },
        "created_at": now,
        "updated_at": now,
    }
    result = await db[BACKUP_COLLECTION].insert_one(document)
    document["_id"] = result.inserted_id
    return document


def _register_task(app_state, task: asyncio.Task, *, job_id: str) -> None:
    task_store = getattr(app_state, BACKUP_TASKS_STATE_KEY, None)
    if task_store is None:
        task_store = {}
        setattr(app_state, BACKUP_TASKS_STATE_KEY, task_store)

    task_store[job_id] = task

    def _cleanup(_: asyncio.Task) -> None:
        current_store = getattr(app_state, BACKUP_TASKS_STATE_KEY, {})
        current_store.pop(job_id, None)

    task.add_done_callback(_cleanup)


async def _execute_backup_job(db, *, job_id: ObjectId) -> None:
    await _mark_job_running(db, job_id)
    job = await db[BACKUP_COLLECTION].find_one({"_id": job_id})
    if not job:
        return

    capabilities = get_backup_capabilities()
    if not capabilities["tools"]["mongodump"]:
        await _mark_job_failed(db, job_id, "mongodump is not installed on the server")
        return

    destination = job.get("destination")
    archive_path = _build_local_archive_path(job["job_code"])

    exit_code, output = await _run_process(
        settings.backup_tool_mongodump,
        f"--uri={settings.mongodb_url}",
        f"--db={settings.database_name}",
        f"--archive={archive_path}",
        "--gzip",
    )
    if exit_code != 0:
        await _mark_job_failed(db, job_id, output or "Backup process failed")
        return

    if not archive_path.exists():
        await _mark_job_failed(db, job_id, "Backup archive was not created")
        return

    artifact = {
        "file_name": archive_path.name,
        "size_bytes": archive_path.stat().st_size,
        "sha256": _sha256_for_file(archive_path),
    }

    if destination == "local":
        artifact["local_path"] = str(archive_path)
        await _mark_job_completed(db, job_id, artifact)
        return

    if destination == "s3":
        if not settings.backup_s3_bucket:
            archive_path.unlink(missing_ok=True)
            await _mark_job_failed(db, job_id, "backup_s3_bucket is not configured")
            return

        s3_key = _build_s3_key(job["job_code"])
        try:
            client = _get_s3_client()
            client.upload_file(str(archive_path), settings.backup_s3_bucket, s3_key)
        except Exception as exc:
            archive_path.unlink(missing_ok=True)
            await _mark_job_failed(db, job_id, f"S3 upload failed: {exc}")
            return

        artifact["s3_bucket"] = settings.backup_s3_bucket
        artifact["s3_key"] = s3_key
        archive_path.unlink(missing_ok=True)
        await _mark_job_completed(db, job_id, artifact)
        return

    archive_path.unlink(missing_ok=True)
    await _mark_job_failed(db, job_id, f"Unsupported backup destination: {destination}")


async def _resolve_restore_archive(source_job: dict, source: str, restore_job_code: str) -> tuple[Path, bool]:
    artifact = source_job.get("artifact") or {}

    if source == "local":
        local_path = artifact.get("local_path")
        if not local_path:
            raise FileNotFoundError("Local backup artifact is not available for this backup")
        archive_path = Path(local_path)
        if not archive_path.exists():
            raise FileNotFoundError("Local backup archive does not exist on disk")
        return archive_path, False

    if source == "s3":
        bucket = artifact.get("s3_bucket")
        key = artifact.get("s3_key")
        if not bucket or not key:
            raise FileNotFoundError("S3 backup artifact is not available for this backup")
        target_path = _build_temp_restore_path(restore_job_code)
        client = _get_s3_client()
        client.download_file(bucket, key, str(target_path))
        return target_path, True

    raise FileNotFoundError(f"Unsupported restore source: {source}")


async def _execute_restore_job(db, *, job_id: ObjectId) -> None:
    await _mark_job_running(db, job_id)
    job = await db[BACKUP_COLLECTION].find_one({"_id": job_id})
    if not job:
        return

    capabilities = get_backup_capabilities()
    if not capabilities["tools"]["mongorestore"]:
        await _mark_job_failed(db, job_id, "mongorestore is not installed on the server")
        return

    source_job = await db[BACKUP_COLLECTION].find_one({"_id": job.get("source_backup_id")})
    if not source_job:
        await _mark_job_failed(db, job_id, "Source backup record was not found")
        return

    downloaded_archive = None
    try:
        archive_path, should_cleanup = await _resolve_restore_archive(source_job, job.get("source"), job["job_code"])
        downloaded_archive = archive_path if should_cleanup else None
    except Exception as exc:
        await _mark_job_failed(db, job_id, f"Restore source preparation failed: {exc}")
        return

    command = [
        settings.backup_tool_mongorestore,
        f"--uri={settings.mongodb_url}",
        f"--nsInclude={settings.database_name}.*",
        f"--archive={archive_path}",
        "--gzip",
    ]
    if job.get("drop_existing_data"):
        command.append("--drop")

    exit_code, output = await _run_process(*command)
    if downloaded_archive:
        downloaded_archive.unlink(missing_ok=True)

    if exit_code != 0:
        await _mark_job_failed(db, job_id, output or "Restore process failed")
        return

    await _mark_job_completed(
        db,
        job_id,
        {
            "file_name": source_job.get("artifact", {}).get("file_name", "unknown"),
            "restored_from_job_code": source_job.get("job_code"),
            "source": job.get("source"),
        },
    )


async def _run_job_with_reconciliation(db, *, job_id: ObjectId, executor) -> None:
    try:
        await executor(db, job_id=job_id)
    except asyncio.CancelledError:
        await _mark_job_failed(db, job_id, "Job was cancelled before completion")
        raise
    except Exception as exc:
        await _mark_job_failed(db, job_id, f"Job crashed before completion: {exc}")


def schedule_backup_job(db, app_state, *, job_id: ObjectId) -> None:
    task = asyncio.create_task(_run_job_with_reconciliation(db, job_id=job_id, executor=_execute_backup_job))
    _register_task(app_state, task, job_id=str(job_id))


def schedule_restore_job(db, app_state, *, job_id: ObjectId) -> None:
    task = asyncio.create_task(_run_job_with_reconciliation(db, job_id=job_id, executor=_execute_restore_job))
    _register_task(app_state, task, job_id=str(job_id))


async def list_backup_jobs(db, *, page: int, page_size: int, job_type: str | None = None) -> dict:
    filters: dict[str, Any] = {}
    if job_type in {"backup", "restore"}:
        filters["job_type"] = job_type

    total = await db[BACKUP_COLLECTION].count_documents(filters)
    cursor = (
        db[BACKUP_COLLECTION]
        .find(filters)
        .sort("created_at", -1)
        .skip((page - 1) * page_size)
        .limit(page_size)
    )
    items = [serialize_backup_job(item) async for item in cursor]
    return {
        "items": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total": total,
            "pages": max(1, (total + page_size - 1) // page_size),
        },
    }


async def get_backup_job_or_none(db, job_id: str) -> dict | None:
    try:
        object_id = ObjectId(job_id)
    except Exception:
        return None
    return await db[BACKUP_COLLECTION].find_one({"_id": object_id})