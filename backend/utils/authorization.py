from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from bson import ObjectId
from fastapi import HTTPException, status

from .policy_registry import has_registry_rule_match, resolve_permission_from_registry


OPERATOR_ORG_TYPE = "operator"
ADMIN_ORG_TYPE = "internal_admin"
MEMBERSHIP_ACTIVE = "active"
RBAC_DENY_UNMAPPED_PERMISSION = "rbac.deny.unmapped"
SENSITIVE_PERMISSIONS = {
    "platform.super_admin",
    "admin.backups.manage",
    "admin.billing.manage",
    "admin.settings.manage",
    "admin.operators.manage",
}


SYSTEM_ROLE_TEMPLATES: dict[str, dict[str, Any]] = {
    "operator_owner": {
        "organization_type": OPERATOR_ORG_TYPE,
        "name": "Operator Owner",
        "description": "Full access for an operator organization owner.",
        "permissions": [
            "operator.profile.read",
            "operator.profile.update",
            "operator.serving_areas.manage",
            "operator.quotes.read",
            "operator.quotes.respond",
            "operator.itineraries.manage",
            "operator.promotions.read",
            "operator.promotions.manage",
            "operator.billing.read",
            "operator.billing.manage",
            "operator.team.manage",
            "operator.analytics.read",
            "operator.tickets.read",
            "operator.tickets.create",
        ],
    },
    "operator_manager": {
        "organization_type": OPERATOR_ORG_TYPE,
        "name": "Operator Manager",
        "description": "Operational manager access across operator sections.",
        "permissions": [
            "operator.profile.read",
            "operator.profile.update",
            "operator.serving_areas.manage",
            "operator.quotes.read",
            "operator.quotes.respond",
            "operator.itineraries.manage",
            "operator.promotions.read",
            "operator.promotions.manage",
            "operator.billing.read",
            "operator.analytics.read",
            "operator.tickets.read",
            "operator.tickets.create",
        ],
    },
    "operator_sales": {
        "organization_type": OPERATOR_ORG_TYPE,
        "name": "Operator Sales",
        "description": "Quote and promotion access for sales staff.",
        "permissions": [
            "operator.profile.read",
            "operator.quotes.read",
            "operator.quotes.respond",
            "operator.promotions.read",
            "operator.promotions.manage",
            "operator.analytics.read",
            "operator.tickets.read",
            "operator.tickets.create",
        ],
    },
    "operator_content_editor": {
        "organization_type": OPERATOR_ORG_TYPE,
        "name": "Operator Content Editor",
        "description": "Profile, serving area, and itinerary access.",
        "permissions": [
            "operator.profile.read",
            "operator.profile.update",
            "operator.serving_areas.manage",
            "operator.itineraries.manage",
            "operator.analytics.read",
            "operator.tickets.read",
            "operator.tickets.create",
        ],
    },
    "operator_finance": {
        "organization_type": OPERATOR_ORG_TYPE,
        "name": "Operator Finance",
        "description": "Billing and analytics access.",
        "permissions": [
            "operator.profile.read",
            "operator.billing.read",
            "operator.analytics.read",
            "operator.tickets.read",
            "operator.tickets.create",
        ],
    },
    "platform_super_admin": {
        "organization_type": ADMIN_ORG_TYPE,
        "name": "Platform Super Admin",
        "description": "Full platform access.",
        "permissions": ["platform.super_admin"],
    },
    "admin_operations": {
        "organization_type": ADMIN_ORG_TYPE,
        "name": "Admin Operations",
        "description": "Broad operational admin access.",
        "permissions": [
            "admin.dashboard.read",
            "admin.tourists.read",
            "admin.operators.read",
            "admin.operators.manage",
            "admin.quotes.read",
            "admin.notifications.manage",
            "admin.tickets.manage",
            "admin.billing.read",
            "admin.billing.manage",
            "admin.audit.read",
            "admin.reports.read",
            "admin.settings.manage",
            "admin.team.manage",
        ],
    },
    "admin_support": {
        "organization_type": ADMIN_ORG_TYPE,
        "name": "Admin Support",
        "description": "Support ticket queue access and ticket status handling.",
        "permissions": [
            "admin.dashboard.read",
            "admin.tickets.manage",
        ],
    },
    "admin_finance": {
        "organization_type": ADMIN_ORG_TYPE,
        "name": "Admin Finance",
        "description": "Finance and billing access.",
        "permissions": [
            "admin.dashboard.read",
            "admin.billing.read",
            "admin.billing.manage",
            "admin.reports.read",
        ],
    },
    "admin_marketing": {
        "organization_type": ADMIN_ORG_TYPE,
        "name": "Admin Marketing",
        "description": "Notifications and operator promotion access.",
        "permissions": [
            "admin.dashboard.read",
            "admin.notifications.manage",
            "admin.operators.read",
            "admin.operators.manage",
            "admin.reports.read",
        ],
    },
    "admin_compliance": {
        "organization_type": ADMIN_ORG_TYPE,
        "name": "Admin Compliance",
        "description": "Audit and review access.",
        "permissions": [
            "admin.dashboard.read",
            "admin.audit.read",
            "admin.reports.read",
            "admin.tourists.read",
            "admin.operators.read",
            "admin.quotes.read",
        ],
    },
    "admin_readonly": {
        "organization_type": ADMIN_ORG_TYPE,
        "name": "Admin Read Only",
        "description": "Read-only dashboard and reporting access.",
        "permissions": [
            "admin.dashboard.read",
            "admin.tourists.read",
            "admin.operators.read",
            "admin.quotes.read",
            "admin.billing.read",
            "admin.audit.read",
            "admin.reports.read",
        ],
    },
}


def _slugify(value: str) -> str:
    cleaned = "".join(ch.lower() if ch.isalnum() else "-" for ch in (value or "").strip())
    collapsed = "-".join(part for part in cleaned.split("-") if part)
    return collapsed or "organization"


async def sync_system_roles(db) -> None:
    now = datetime.now(timezone.utc)
    for key, template in SYSTEM_ROLE_TEMPLATES.items():
        await db.access_roles.update_one(
            {"key": key, "organization_type": template["organization_type"]},
            {
                "$set": {
                    "name": template["name"],
                    "description": template["description"],
                    "permissions": template["permissions"],
                    "is_system": True,
                    "updated_at": now,
                },
                "$setOnInsert": {"created_at": now},
            },
            upsert=True,
        )


def _permission_set(role_keys: list[str], permission_overrides: dict[str, list[str]] | None = None) -> set[str]:
    permissions: set[str] = set()
    for role_key in role_keys:
        template = SYSTEM_ROLE_TEMPLATES.get(role_key)
        if template:
            permissions.update(template["permissions"])
    overrides = permission_overrides or {}
    permissions.update(overrides.get("allow", []))
    permissions.difference_update(overrides.get("deny", []))
    return permissions


def has_permission(permissions: set[str], permission: str | None) -> bool:
    if not permission:
        return True
    if permission == RBAC_DENY_UNMAPPED_PERMISSION:
        return False
    return "platform.super_admin" in permissions or permission in permissions


def permission_requires_step_up(permission: str | None) -> bool:
    return bool(permission and permission in SENSITIVE_PERMISSIONS)


def is_recent_auth_payload(payload: dict | None, *, max_age_minutes: int) -> bool:
    if not payload:
        return False
    issued_at = payload.get("iat")
    if not issued_at:
        return False
    try:
        issued_at_dt = datetime.fromtimestamp(int(issued_at), tz=timezone.utc)
    except Exception:
        return False
    now = datetime.now(timezone.utc)
    age_seconds = (now - issued_at_dt).total_seconds()
    return age_seconds <= max(int(max_age_minutes), 1) * 60


def list_role_templates(*, organization_type: str) -> list[dict[str, Any]]:
    rows = []
    for key, template in SYSTEM_ROLE_TEMPLATES.items():
        if template["organization_type"] != organization_type:
            continue
        rows.append(
            {
                "key": key,
                "name": template["name"],
                "description": template["description"],
                "permissions": template["permissions"],
            }
        )
    return rows


def default_admin_role_keys(admin_role: str) -> list[str]:
    if admin_role == "super_admin":
        return ["platform_super_admin"]
    return ["admin_operations"]


async def _ensure_unique_slug(db, *, base_slug: str) -> str:
    slug = base_slug
    suffix = 1
    while await db.organizations.find_one({"slug": slug}):
        suffix += 1
        slug = f"{base_slug}-{suffix}"
    return slug


async def ensure_operator_onboarding_access(db, *, user: dict) -> None:
    """Eagerly provision operator org + owner membership after verification."""
    if user.get("user_type") != "operator":
        return

    principal_id = str(user["_id"])
    existing_membership = await db.organization_memberships.find_one(
        {
            "principal_type": "user",
            "principal_id": principal_id,
            "membership_status": MEMBERSHIP_ACTIVE,
        }
    )
    if existing_membership:
        return

    organization = await db.organizations.find_one(
        {
            "organization_type": OPERATOR_ORG_TYPE,
            "owner_user_id": principal_id,
        }
    )
    if not organization:
        email_prefix = str(user.get("email") or "operator").split("@", 1)[0]
        org_name = str(user.get("full_name") or email_prefix or "Operator").strip()
        base_slug = _slugify(org_name)
        slug = await _ensure_unique_slug(db, base_slug=base_slug)
        now = datetime.now(timezone.utc)
        document = {
            "name": org_name,
            "slug": slug,
            "organization_type": OPERATOR_ORG_TYPE,
            "status": "active",
            "operator_profile_id": None,
            "owner_user_id": principal_id,
            "settings": {},
            "created_at": now,
            "updated_at": now,
        }
        result = await db.organizations.insert_one(document)
        organization = {**document, "_id": result.inserted_id}

    await ensure_membership(
        db,
        organization_id=str(organization["_id"]),
        principal_type="user",
        principal_id=principal_id,
        role_keys=["operator_owner"],
    )


async def ensure_operator_organization(db, *, profile: dict) -> dict:
    organization_id = profile.get("organization_id")
    if organization_id and ObjectId.is_valid(organization_id):
        existing = await db.organizations.find_one({"_id": ObjectId(organization_id)})
        if existing:
            return existing

    owner_user_id = str(profile.get("user_id") or "").strip() or None
    if owner_user_id:
        preprovisioned = await db.organizations.find_one(
            {
                "organization_type": OPERATOR_ORG_TYPE,
                "owner_user_id": owner_user_id,
            }
        )
        if preprovisioned:
            now = datetime.now(timezone.utc)
            org_updates = {
                "operator_profile_id": str(profile["_id"]),
                "updated_at": now,
            }
            if profile.get("business_name"):
                org_updates["name"] = profile["business_name"]
            await db.organizations.update_one(
                {"_id": preprovisioned["_id"]},
                {"$set": org_updates},
            )
            await db.operator_profiles.update_one(
                {"_id": profile["_id"]},
                {"$set": {"organization_id": str(preprovisioned["_id"]), "updated_at": now}},
            )
            preprovisioned.update(org_updates)
            return preprovisioned

    base_slug = _slugify(profile.get("business_name") or f"operator-{profile.get('_id')}")
    slug = await _ensure_unique_slug(db, base_slug=base_slug)
    now = datetime.now(timezone.utc)
    document = {
        "name": profile.get("business_name") or "Operator Organization",
        "slug": slug,
        "organization_type": OPERATOR_ORG_TYPE,
        "status": "active",
        "operator_profile_id": str(profile["_id"]),
        "owner_user_id": owner_user_id,
        "settings": {},
        "created_at": now,
        "updated_at": now,
    }
    result = await db.organizations.insert_one(document)
    document["_id"] = result.inserted_id
    await db.operator_profiles.update_one(
        {"_id": profile["_id"]},
        {"$set": {"organization_id": str(result.inserted_id), "updated_at": now}},
    )
    return document


async def ensure_internal_admin_organization(db) -> dict:
    existing = await db.organizations.find_one({"organization_type": ADMIN_ORG_TYPE, "slug": "internal-admin"})
    if existing:
        return existing
    now = datetime.now(timezone.utc)
    document = {
        "name": "Internal Admin Workspace",
        "slug": "internal-admin",
        "organization_type": ADMIN_ORG_TYPE,
        "status": "active",
        "operator_profile_id": None,
        "settings": {},
        "created_at": now,
        "updated_at": now,
    }
    result = await db.organizations.insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def ensure_membership(
    db,
    *,
    organization_id: str,
    principal_type: str,
    principal_id: str,
    role_keys: list[str],
    invited_by: str | None = None,
    permission_overrides: dict[str, list[str]] | None = None,
    scope_constraints: dict[str, Any] | None = None,
) -> dict:
    existing = await db.organization_memberships.find_one(
        {
            "organization_id": organization_id,
            "principal_type": principal_type,
            "principal_id": principal_id,
        }
    )
    now = datetime.now(timezone.utc)
    if existing:
        update_data = {}
        if existing.get("membership_status") != MEMBERSHIP_ACTIVE:
            update_data["membership_status"] = MEMBERSHIP_ACTIVE
        if update_data:
            update_data["updated_at"] = now
            await db.organization_memberships.update_one({"_id": existing["_id"]}, {"$set": update_data})
            existing.update(update_data)
        return existing

    document = {
        "organization_id": organization_id,
        "principal_type": principal_type,
        "principal_id": principal_id,
        "membership_status": MEMBERSHIP_ACTIVE,
        "role_keys": role_keys,
        "permission_overrides": permission_overrides or {"allow": [], "deny": []},
        "scope_constraints": scope_constraints or {},
        "invited_by": invited_by,
        "created_at": now,
        "updated_at": now,
        "last_accepted_at": now,
    }
    result = await db.organization_memberships.insert_one(document)
    document["_id"] = result.inserted_id
    return document


async def ensure_operator_access_context(db, *, user: dict) -> dict:
    membership = await db.organization_memberships.find_one(
        {
            "principal_type": "user",
            "principal_id": str(user["_id"]),
            "membership_status": MEMBERSHIP_ACTIVE,
        }
    )
    organization = None
    profile = None

    if membership:
        organization = await db.organizations.find_one({"_id": ObjectId(membership["organization_id"])})
        if organization and organization.get("operator_profile_id"):
            profile = await db.operator_profiles.find_one({"_id": ObjectId(organization["operator_profile_id"])})

    if not profile:
        profile = await db.operator_profiles.find_one({"user_id": str(user["_id"])})
        if not profile:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Operator profile not found")
        organization = await ensure_operator_organization(db, profile=profile)
        membership = await ensure_membership(
            db,
            organization_id=str(organization["_id"]),
            principal_type="user",
            principal_id=str(user["_id"]),
            role_keys=["operator_owner"],
        )

    permissions = sorted(_permission_set(membership.get("role_keys", []), membership.get("permission_overrides")))
    return {
        "principal_type": "user",
        "principal": {
            "_id": str(user["_id"]),
            "email": user.get("email"),
            "full_name": user.get("full_name"),
            "user_type": user.get("user_type"),
        },
        "organization": {
            "_id": str(organization["_id"]),
            "name": organization.get("name"),
            "slug": organization.get("slug"),
            "organization_type": organization.get("organization_type"),
            "status": organization.get("status"),
        },
        "membership": {
            "_id": str(membership["_id"]),
            "role_keys": membership.get("role_keys", []),
            "membership_status": membership.get("membership_status"),
            "scope_constraints": membership.get("scope_constraints", {}),
        },
        "operator_profile": {
            "_id": str(profile["_id"]),
            "business_name": profile.get("business_name"),
            "organization_id": str(organization["_id"]),
            "serving_areas": profile.get("serving_areas", []),
        },
        "permissions": permissions,
        "role_templates": list_role_templates(organization_type=OPERATOR_ORG_TYPE),
    }


async def ensure_admin_access_context(db, *, admin: dict) -> dict:
    organization = await ensure_internal_admin_organization(db)
    membership = await db.organization_memberships.find_one(
        {
            "organization_id": str(organization["_id"]),
            "principal_type": "admin",
            "principal_id": str(admin["_id"]),
        }
    )
    if not membership:
        membership = await ensure_membership(
            db,
            organization_id=str(organization["_id"]),
            principal_type="admin",
            principal_id=str(admin["_id"]),
            role_keys=default_admin_role_keys(admin.get("role", "moderator")),
        )

    permissions = sorted(_permission_set(membership.get("role_keys", []), membership.get("permission_overrides")))
    return {
        "principal_type": "admin",
        "principal": {
            "_id": str(admin["_id"]),
            "email": admin.get("email"),
            "full_name": admin.get("full_name"),
            "role": admin.get("role"),
        },
        "organization": {
            "_id": str(organization["_id"]),
            "name": organization.get("name"),
            "slug": organization.get("slug"),
            "organization_type": organization.get("organization_type"),
            "status": organization.get("status"),
        },
        "membership": {
            "_id": str(membership["_id"]),
            "role_keys": membership.get("role_keys", []),
            "membership_status": membership.get("membership_status"),
            "scope_constraints": membership.get("scope_constraints", {}),
        },
        "permissions": permissions,
        "role_templates": list_role_templates(organization_type=ADMIN_ORG_TYPE),
    }


def required_permission_for_request(*, principal_type: str, path: str, method: str) -> str | None:
    registry_permission = resolve_permission_from_registry(
        principal_type=principal_type,
        path=path,
        method=method,
    )
    if registry_permission is not None:
        return registry_permission

    if has_registry_rule_match(principal_type=principal_type, path=path, method=method):
        # Explicitly matched permissive routes return None (e.g. profile/access-context reads).
        return registry_permission

    if principal_type == "admin" and (path.startswith("/admin") or path.startswith("/tickets/admin")):
        return RBAC_DENY_UNMAPPED_PERMISSION

    if principal_type == "user":
        if path.startswith("/operators") or path.startswith("/operator/"):
            return RBAC_DENY_UNMAPPED_PERMISSION
        if path.startswith("/itineraries/operator"):
            return RBAC_DENY_UNMAPPED_PERMISSION
        if path == "/quotes/inbox" or path.startswith("/quotes/inbox/"):
            return RBAC_DENY_UNMAPPED_PERMISSION
        if path.startswith("/quotes/") and path.endswith("/respond"):
            return RBAC_DENY_UNMAPPED_PERMISSION
        if path.startswith("/tickets/operator"):
            return RBAC_DENY_UNMAPPED_PERMISSION

    return None
