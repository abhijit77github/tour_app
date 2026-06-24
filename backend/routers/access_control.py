from __future__ import annotations

from datetime import datetime, timezone

from bson import ObjectId
from fastapi import APIRouter, Depends, HTTPException, Query, status

from ..database import get_database
from ..models.access_control import OrganizationMemberUpsert, OrganizationMembershipUpdate
from ..models.admin import validate_app_email as validate_admin_email
from ..models.user import validate_app_email as validate_user_email
from ..routers.admin import get_current_admin, get_current_admin_access_context
from ..routers.auth import get_current_operator_access_context
from ..utils.auth import get_password_hash
from ..utils.cursor_pagination import build_desc_created_cursor_match, decode_datetime_objectid_cursor, encode_datetime_objectid_cursor
from ..utils.authorization import (
    ADMIN_ORG_TYPE,
    OPERATOR_ORG_TYPE,
    SYSTEM_ROLE_TEMPLATES,
    _permission_set,
    ensure_membership,
)

router = APIRouter(tags=["Access Control"])


def _serialize_membership_with_principal(membership: dict, principal: dict | None) -> dict:
    permissions = sorted(_permission_set(membership.get("role_keys", []), membership.get("permission_overrides")))
    return {
        "_id": str(membership["_id"]),
        "organization_id": membership.get("organization_id"),
        "principal_type": membership.get("principal_type"),
        "principal_id": membership.get("principal_id"),
        "membership_status": membership.get("membership_status"),
        "role_keys": membership.get("role_keys", []),
        "permission_overrides": membership.get("permission_overrides", {"allow": [], "deny": []}),
        "scope_constraints": membership.get("scope_constraints", {}),
        "permissions": permissions,
        "principal": principal,
        "created_at": membership.get("created_at"),
        "updated_at": membership.get("updated_at"),
    }


async def _load_principal(db, *, principal_type: str, principal_id: str) -> dict | None:
    collection = db.users if principal_type == "user" else db.admins
    if not ObjectId.is_valid(principal_id):
        return None
    doc = await collection.find_one({"_id": ObjectId(principal_id)})
    if not doc:
        return None
    if principal_type == "user":
        return {
            "_id": str(doc["_id"]),
            "email": doc.get("email"),
            "full_name": doc.get("full_name"),
            "phone": doc.get("phone"),
            "user_type": doc.get("user_type"),
            "is_active": doc.get("is_active"),
        }
    return {
        "_id": str(doc["_id"]),
        "email": doc.get("email"),
        "full_name": doc.get("full_name"),
        "phone": doc.get("phone"),
        "role": doc.get("role"),
        "is_active": doc.get("is_active"),
    }


async def _list_memberships(
    db,
    *,
    organization_id: str,
    principal_type: str,
    cursor: str | None = None,
    page_size: int = 12,
) -> tuple[list[dict], int, str | None, bool]:
    base_query = {"organization_id": organization_id, "principal_type": principal_type}
    total_items = await db.organization_memberships.count_documents(base_query)
    effective_query = dict(base_query)
    if cursor:
        cursor_created_at, cursor_object_id = decode_datetime_objectid_cursor(cursor)
        effective_query["$and"] = [
            build_desc_created_cursor_match(created_at=cursor_created_at, object_id=cursor_object_id)
        ]
    rows = []
    memberships = await db.organization_memberships.find(effective_query).sort([("created_at", -1), ("_id", -1)]).limit(page_size + 1).to_list(length=page_size + 1)
    has_more = len(memberships) > page_size
    memberships = memberships[:page_size]
    next_cursor = None
    if has_more and memberships:
        last_membership = memberships[-1]
        next_cursor = encode_datetime_objectid_cursor(created_at=last_membership["created_at"], object_id=last_membership["_id"])
    for membership in memberships:
        principal = await _load_principal(db, principal_type=principal_type, principal_id=membership["principal_id"])
        rows.append(_serialize_membership_with_principal(membership, principal))
    return rows, total_items, next_cursor, has_more


def _validate_role_keys(*, organization_type: str, role_keys: list[str]) -> list[str]:
    if not role_keys:
        return ["operator_manager"] if organization_type == OPERATOR_ORG_TYPE else ["admin_readonly"]
    invalid = [key for key in role_keys if SYSTEM_ROLE_TEMPLATES.get(key, {}).get("organization_type") != organization_type]
    if invalid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid role keys for organization: {', '.join(invalid)}")
    return role_keys


@router.get("/operators/access/context")
async def get_operator_access_context(context: dict = Depends(get_current_operator_access_context)):
    return context


@router.get("/operators/team")
async def list_operator_team(
    cursor: str | None = None,
    page_size: int = Query(default=12, ge=1, le=100),
    context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    try:
        members, total_items, next_cursor, has_more = await _list_memberships(
            db,
            organization_id=context["organization"]["_id"],
            principal_type="user",
            cursor=cursor,
            page_size=page_size,
        )
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid cursor") from exc
    return {
        "organization": context["organization"],
        "members": members,
        "role_templates": context["role_templates"],
        "pagination": {
            "page_size": page_size,
            "total_items": total_items,
            "next_cursor": next_cursor,
            "has_more": has_more,
        },
    }


@router.post("/operators/team", status_code=status.HTTP_201_CREATED)
async def upsert_operator_team_member(
    payload: OrganizationMemberUpsert,
    context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    email = validate_user_email(payload.email)
    role_keys = _validate_role_keys(organization_type=OPERATOR_ORG_TYPE, role_keys=payload.role_keys)
    principal = await db.users.find_one({"email": email})
    if principal and principal.get("user_type") != "operator":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Existing account is not an operator user")

    now = datetime.now(timezone.utc)
    created_account = False
    if not principal:
        if not payload.password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required when creating a new operator team member")
        document = {
            "email": email,
            "full_name": payload.full_name,
            "phone": payload.phone,
            "user_type": "operator",
            "hashed_password": get_password_hash(payload.password),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
        }
        result = await db.users.insert_one(document)
        principal = {**document, "_id": result.inserted_id}
        created_account = True

    membership = await ensure_membership(
        db,
        organization_id=context["organization"]["_id"],
        principal_type="user",
        principal_id=str(principal["_id"]),
        role_keys=role_keys,
        invited_by=context["principal"]["_id"],
        permission_overrides=payload.permission_overrides,
        scope_constraints=payload.scope_constraints,
    )
    await db.organization_memberships.update_one(
        {"_id": membership["_id"]},
        {"$set": {"role_keys": role_keys, "permission_overrides": payload.permission_overrides, "scope_constraints": payload.scope_constraints, "updated_at": now}},
    )
    membership = await db.organization_memberships.find_one({"_id": membership["_id"]})
    principal = await _load_principal(db, principal_type="user", principal_id=membership["principal_id"])
    return {
        "message": "Operator team member provisioned",
        "created_account": created_account,
        "member": _serialize_membership_with_principal(membership, principal),
    }


@router.patch("/operators/team/{membership_id}")
async def update_operator_team_member(
    membership_id: str,
    payload: OrganizationMembershipUpdate,
    context: dict = Depends(get_current_operator_access_context),
):
    db = await get_database()
    try:
        membership = await db.organization_memberships.find_one({"_id": ObjectId(membership_id), "organization_id": context["organization"]["_id"], "principal_type": "user"})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid membership ID") from exc
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Team member not found")

    update_data = {key: value for key, value in payload.model_dump().items() if value is not None}
    if "role_keys" in update_data:
        update_data["role_keys"] = _validate_role_keys(organization_type=OPERATOR_ORG_TYPE, role_keys=update_data["role_keys"])
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data to update")
    update_data["updated_at"] = datetime.now(timezone.utc)
    await db.organization_memberships.update_one({"_id": membership["_id"]}, {"$set": update_data})
    updated = await db.organization_memberships.find_one({"_id": membership["_id"]})
    principal = await _load_principal(db, principal_type="user", principal_id=updated["principal_id"])
    return {"message": "Operator team member updated", "member": _serialize_membership_with_principal(updated, principal)}


@router.get("/admin/access/context")
async def get_admin_access_control_context(context: dict = Depends(get_current_admin_access_context)):
    return context


@router.get("/admin/team")
async def list_admin_team(context: dict = Depends(get_current_admin_access_context)):
    db = await get_database()
    members = await _list_memberships(db, organization_id=context["organization"]["_id"], principal_type="admin")
    return {"organization": context["organization"], "members": members, "role_templates": context["role_templates"]}


@router.post("/admin/team", status_code=status.HTTP_201_CREATED)
async def upsert_admin_team_member(
    payload: OrganizationMemberUpsert,
    context: dict = Depends(get_current_admin_access_context),
    current_admin: dict = Depends(get_current_admin),
):
    db = await get_database()
    email = validate_admin_email(payload.email)
    role_keys = _validate_role_keys(organization_type=ADMIN_ORG_TYPE, role_keys=payload.role_keys)
    if "platform_super_admin" in role_keys and "platform.super_admin" not in set(context["permissions"]):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Only a platform super admin can assign super admin access")

    principal = await db.admins.find_one({"email": email})
    now = datetime.now(timezone.utc)
    created_account = False
    if not principal:
        if not payload.password:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Password is required when creating a new admin member")
        document = {
            "email": email,
            "full_name": payload.full_name,
            "phone": payload.phone,
            "role": "super_admin" if "platform_super_admin" in role_keys else "moderator",
            "hashed_password": get_password_hash(payload.password),
            "is_active": True,
            "created_at": now,
            "updated_at": now,
            "last_login": None,
            "created_by": current_admin.get("_id"),
        }
        result = await db.admins.insert_one(document)
        principal = {**document, "_id": result.inserted_id}
        created_account = True

    membership = await ensure_membership(
        db,
        organization_id=context["organization"]["_id"],
        principal_type="admin",
        principal_id=str(principal["_id"]),
        role_keys=role_keys,
        invited_by=context["principal"]["_id"],
        permission_overrides=payload.permission_overrides,
        scope_constraints=payload.scope_constraints,
    )
    await db.organization_memberships.update_one(
        {"_id": membership["_id"]},
        {"$set": {"role_keys": role_keys, "permission_overrides": payload.permission_overrides, "scope_constraints": payload.scope_constraints, "updated_at": now}},
    )
    await db.admins.update_one(
        {"_id": principal["_id"]},
        {"$set": {"role": "super_admin" if "platform_super_admin" in role_keys else "moderator", "updated_at": now}},
    )
    membership = await db.organization_memberships.find_one({"_id": membership["_id"]})
    principal = await _load_principal(db, principal_type="admin", principal_id=membership["principal_id"])
    return {
        "message": "Admin member provisioned",
        "created_account": created_account,
        "member": _serialize_membership_with_principal(membership, principal),
    }


@router.patch("/admin/team/{membership_id}")
async def update_admin_team_member(
    membership_id: str,
    payload: OrganizationMembershipUpdate,
    context: dict = Depends(get_current_admin_access_context),
):
    db = await get_database()
    try:
        membership = await db.organization_memberships.find_one({"_id": ObjectId(membership_id), "organization_id": context["organization"]["_id"], "principal_type": "admin"})
    except Exception as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid membership ID") from exc
    if not membership:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Admin member not found")

    update_data = {key: value for key, value in payload.model_dump().items() if value is not None}
    if "role_keys" in update_data:
        update_data["role_keys"] = _validate_role_keys(organization_type=ADMIN_ORG_TYPE, role_keys=update_data["role_keys"])
    if not update_data:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="No data to update")
    update_data["updated_at"] = datetime.now(timezone.utc)
    await db.organization_memberships.update_one({"_id": membership["_id"]}, {"$set": update_data})
    updated = await db.organization_memberships.find_one({"_id": membership["_id"]})
    if "role_keys" in update_data:
        role_keys = update_data["role_keys"]
        await db.admins.update_one(
            {"_id": ObjectId(updated["principal_id"])},
            {"$set": {"role": "super_admin" if "platform_super_admin" in role_keys else "moderator", "updated_at": datetime.now(timezone.utc)}},
        )
    principal = await _load_principal(db, principal_type="admin", principal_id=updated["principal_id"])
    return {"message": "Admin member updated", "member": _serialize_membership_with_principal(updated, principal)}