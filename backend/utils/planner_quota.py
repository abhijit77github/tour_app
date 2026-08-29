from __future__ import annotations

import hashlib
from datetime import datetime, timedelta, timezone
from typing import Optional

from pymongo import ReturnDocument


PLANNER_TOURIST_QUOTA_SETTINGS_KEY = "planner_tourist_quota"
PLANNER_REWARD_SOURCE_MAP = {
    "ad": ("ad_reward_daily_credits", "ad_reward_monthly_credits"),
    "promotion": ("promotion_reward_daily_credits", "promotion_reward_monthly_credits"),
}


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _normalize_limit(value: object, *, default: int, upper_bound: int) -> int:
    try:
        return max(0, min(int(value if value is not None else default), upper_bound))
    except (TypeError, ValueError):
        return default


def get_default_planner_tourist_quota_settings() -> dict:
    return {
        "daily_limit": 400,
        "monthly_limit": 1000,
        "ad_reward_daily_credits": 1,
        "ad_reward_monthly_credits": 1,
        "promotion_reward_daily_credits": 1,
        "promotion_reward_monthly_credits": 2,
    }


def _normalize_planner_tourist_quota_settings(values: Optional[dict]) -> dict:
    source = values if isinstance(values, dict) else {}
    defaults = get_default_planner_tourist_quota_settings()
    return {
        "daily_limit": _normalize_limit(source.get("daily_limit"), default=defaults["daily_limit"], upper_bound=100),
        "monthly_limit": _normalize_limit(source.get("monthly_limit"), default=defaults["monthly_limit"], upper_bound=1000),
        "ad_reward_daily_credits": _normalize_limit(source.get("ad_reward_daily_credits"), default=defaults["ad_reward_daily_credits"], upper_bound=20),
        "ad_reward_monthly_credits": _normalize_limit(source.get("ad_reward_monthly_credits"), default=defaults["ad_reward_monthly_credits"], upper_bound=100),
        "promotion_reward_daily_credits": _normalize_limit(source.get("promotion_reward_daily_credits"), default=defaults["promotion_reward_daily_credits"], upper_bound=20),
        "promotion_reward_monthly_credits": _normalize_limit(source.get("promotion_reward_monthly_credits"), default=defaults["promotion_reward_monthly_credits"], upper_bound=100),
    }


async def get_planner_tourist_quota_settings(db=None) -> dict:
    defaults = get_default_planner_tourist_quota_settings()
    if db is None or not hasattr(db, "admin_settings"):
        return defaults

    persisted = await db.admin_settings.find_one({"key": PLANNER_TOURIST_QUOTA_SETTINGS_KEY})
    return _normalize_planner_tourist_quota_settings((persisted or {}).get("value"))


async def get_planner_tourist_quota_settings_document(db=None) -> dict:
    values = await get_planner_tourist_quota_settings(db)
    if db is None or not hasattr(db, "admin_settings"):
        return {
            "values": values,
            "source": "environment",
            "updated_at": None,
            "updated_by": None,
        }

    persisted = await db.admin_settings.find_one({"key": PLANNER_TOURIST_QUOTA_SETTINGS_KEY})
    if not persisted:
        return {
            "values": values,
            "source": "environment",
            "updated_at": None,
            "updated_by": None,
        }

    return {
        "values": values,
        "source": "database",
        "updated_at": persisted.get("updated_at"),
        "updated_by": persisted.get("updated_by"),
    }


def _day_key(reference: datetime) -> str:
    return reference.astimezone(timezone.utc).strftime("%Y-%m-%d")


def _month_key(reference: datetime) -> str:
    return reference.astimezone(timezone.utc).strftime("%Y-%m")


def _next_day_reset(reference: datetime) -> datetime:
    current = reference.astimezone(timezone.utc)
    return datetime(current.year, current.month, current.day, tzinfo=timezone.utc) + timedelta(days=1)


def _next_month_reset(reference: datetime) -> datetime:
    current = reference.astimezone(timezone.utc)
    if current.month == 12:
        return datetime(current.year + 1, 1, 1, tzinfo=timezone.utc)
    return datetime(current.year, current.month + 1, 1, tzinfo=timezone.utc)


def _reward_idempotency_key(*, user_id: str, reward_type: str, reward_id: str) -> str:
    raw = "|".join([user_id, reward_type, reward_id])
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


async def _append_quota_ledger_entry(
    db,
    *,
    user_id: str,
    event_type: str,
    source: str,
    credits_delta_daily: int,
    credits_delta_monthly: int,
    balance_daily_after: int,
    balance_monthly_after: int,
    reference_id: Optional[str],
    metadata: Optional[dict],
    created_at: datetime,
) -> None:
    await db.tourist_planner_quota_ledger.insert_one(
        {
            "user_id": user_id,
            "event_type": event_type,
            "source": source,
            "credits_delta_daily": credits_delta_daily,
            "credits_delta_monthly": credits_delta_monthly,
            "balance_daily_after": balance_daily_after,
            "balance_monthly_after": balance_monthly_after,
            "reference_id": reference_id,
            "metadata": metadata or {},
            "created_at": created_at,
        }
    )


async def _ensure_quota_document(db, *, user_id: str, now: datetime) -> None:
    await db.tourist_planner_quotas.update_one(
        {"user_id": user_id},
        {
            "$setOnInsert": {
                "user_id": user_id,
                "day_key": _day_key(now),
                "month_key": _month_key(now),
                "used_today": 0,
                "used_this_month": 0,
                "bonus_daily_credits": 0,
                "bonus_monthly_credits": 0,
                "created_at": now,
                "updated_at": now,
                "last_request_at": None,
            }
        },
        upsert=True,
    )


async def _rollover_quota_document(db, *, user_id: str, now: datetime) -> dict:
    await _ensure_quota_document(db, user_id=user_id, now=now)
    document = await db.tourist_planner_quotas.find_one({"user_id": user_id})
    if not document:
        raise RuntimeError("Planner quota document missing after upsert")

    current_day_key = _day_key(now)
    current_month_key = _month_key(now)
    set_data = {"updated_at": now}
    changed = False

    if document.get("month_key") != current_month_key:
        set_data.update(
            {
                "month_key": current_month_key,
                "day_key": current_day_key,
                "used_this_month": 0,
                "used_today": 0,
                "bonus_monthly_credits": 0,
                "bonus_daily_credits": 0,
            }
        )
        changed = True
    elif document.get("day_key") != current_day_key:
        set_data.update(
            {
                "day_key": current_day_key,
                "used_today": 0,
                "bonus_daily_credits": 0,
            }
        )
        changed = True

    if changed:
        await db.tourist_planner_quotas.update_one({"user_id": user_id}, {"$set": set_data})
        document.update(set_data)

    return document


def _build_status_payload(*, user_id: str, document: dict, settings: dict, now: datetime) -> dict:
    used_today = int(document.get("used_today") or 0)
    used_this_month = int(document.get("used_this_month") or 0)
    bonus_daily = int(document.get("bonus_daily_credits") or 0)
    bonus_monthly = int(document.get("bonus_monthly_credits") or 0)
    daily_limit = int(settings.get("daily_limit") or 0)
    monthly_limit = int(settings.get("monthly_limit") or 0)
    effective_daily_limit = daily_limit + bonus_daily
    effective_monthly_limit = monthly_limit + bonus_monthly

    return {
        "user_id": user_id,
        "day_key": document.get("day_key") or _day_key(now),
        "month_key": document.get("month_key") or _month_key(now),
        "used_today": used_today,
        "used_this_month": used_this_month,
        "bonus_daily_credits": bonus_daily,
        "bonus_monthly_credits": bonus_monthly,
        "daily_limit": daily_limit,
        "monthly_limit": monthly_limit,
        "effective_daily_limit": effective_daily_limit,
        "effective_monthly_limit": effective_monthly_limit,
        "daily_remaining": max(effective_daily_limit - used_today, 0),
        "monthly_remaining": max(effective_monthly_limit - used_this_month, 0),
        "daily_resets_at": _next_day_reset(now).isoformat(),
        "monthly_resets_at": _next_month_reset(now).isoformat(),
        "last_request_at": document.get("last_request_at").isoformat() if document.get("last_request_at") else None,
    }


async def get_tourist_planner_quota_status(db, *, user_id: str, current_time: Optional[datetime] = None) -> dict:
    now = current_time or utc_now()
    settings = await get_planner_tourist_quota_settings(db)
    document = await _rollover_quota_document(db, user_id=user_id, now=now)
    status = _build_status_payload(user_id=user_id, document=document, settings=settings, now=now)
    return {"settings": settings, "quota": status}


async def consume_tourist_planner_request_quota(
    db,
    *,
    user_id: str,
    session_id: Optional[str] = None,
    current_time: Optional[datetime] = None,
) -> dict:
    now = current_time or utc_now()
    settings = await get_planner_tourist_quota_settings(db)
    document = await _rollover_quota_document(db, user_id=user_id, now=now)
    status = _build_status_payload(user_id=user_id, document=document, settings=settings, now=now)

    if status["daily_remaining"] <= 0 or status["monthly_remaining"] <= 0:
        return {"allowed": False, "quota": status, "reason": "quota_exhausted"}

    updated = None
    collection = db.tourist_planner_quotas
    if hasattr(collection, "find_one_and_update"):
        updated = await collection.find_one_and_update(
            {
                "user_id": user_id,
                "day_key": status["day_key"],
                "month_key": status["month_key"],
                "used_today": status["used_today"],
                "used_this_month": status["used_this_month"],
            },
            {
                "$inc": {"used_today": 1, "used_this_month": 1},
                "$set": {"updated_at": now, "last_request_at": now},
            },
            return_document=ReturnDocument.AFTER,
        )
    else:
        result = await collection.update_one(
            {
                "user_id": user_id,
                "day_key": status["day_key"],
                "month_key": status["month_key"],
                "used_today": status["used_today"],
                "used_this_month": status["used_this_month"],
            },
            {
                "$inc": {"used_today": 1, "used_this_month": 1},
                "$set": {"updated_at": now, "last_request_at": now},
            },
        )
        if result.modified_count:
            updated = await collection.find_one({"user_id": user_id})

    if not updated:
        refreshed = await get_tourist_planner_quota_status(db, user_id=user_id, current_time=now)
        return {"allowed": False, "quota": refreshed["quota"], "reason": "quota_retry_required"}

    updated_status = _build_status_payload(user_id=user_id, document=updated, settings=settings, now=now)
    await _append_quota_ledger_entry(
        db,
        user_id=user_id,
        event_type="consume",
        source="planner_chat",
        credits_delta_daily=-1,
        credits_delta_monthly=-1,
        balance_daily_after=updated_status["daily_remaining"],
        balance_monthly_after=updated_status["monthly_remaining"],
        reference_id=session_id,
        metadata={"day_key": updated_status["day_key"], "month_key": updated_status["month_key"]},
        created_at=now,
    )
    return {"allowed": True, "quota": updated_status, "reason": None}


async def grant_tourist_planner_reward(
    db,
    *,
    user_id: str,
    reward_id: str,
    reward_type: str,
    current_time: Optional[datetime] = None,
) -> dict:
    now = current_time or utc_now()
    if reward_type not in PLANNER_REWARD_SOURCE_MAP:
        raise ValueError("Unsupported reward type")

    verification = await db.tourist_planner_reward_verifications.find_one(
        {
            "user_id": user_id,
            "reward_id": reward_id,
            "reward_type": reward_type,
            "status": "verified",
        }
    )
    if not verification:
        return {"granted": False, "reason": "reward_not_verified"}

    settings = await get_planner_tourist_quota_settings(db)
    daily_key, monthly_key = PLANNER_REWARD_SOURCE_MAP[reward_type]
    daily_bonus = int(settings.get(daily_key) or 0)
    monthly_bonus = int(settings.get(monthly_key) or 0)

    idempotency_key = _reward_idempotency_key(user_id=user_id, reward_type=reward_type, reward_id=reward_id)
    reward_insert = await db.tourist_planner_reward_events.update_one(
        {"idempotency_key": idempotency_key},
        {
            "$setOnInsert": {
                "idempotency_key": idempotency_key,
                "user_id": user_id,
                "reward_id": reward_id,
                "reward_type": reward_type,
                "daily_bonus": daily_bonus,
                "monthly_bonus": monthly_bonus,
                "created_at": now,
            }
        },
        upsert=True,
    )
    if not reward_insert.upserted_id:
        current_status = await get_tourist_planner_quota_status(db, user_id=user_id, current_time=now)
        return {"granted": False, "reason": "duplicate_reward", "quota": current_status["quota"]}

    document = await _rollover_quota_document(db, user_id=user_id, now=now)
    await db.tourist_planner_quotas.update_one(
        {"user_id": user_id},
        {
            "$inc": {
                "bonus_daily_credits": daily_bonus,
                "bonus_monthly_credits": monthly_bonus,
            },
            "$set": {"updated_at": now},
        },
    )
    updated = await db.tourist_planner_quotas.find_one({"user_id": user_id})
    status = _build_status_payload(user_id=user_id, document=updated or document, settings=settings, now=now)
    await _append_quota_ledger_entry(
        db,
        user_id=user_id,
        event_type="bonus_grant",
        source=reward_type,
        credits_delta_daily=daily_bonus,
        credits_delta_monthly=monthly_bonus,
        balance_daily_after=status["daily_remaining"],
        balance_monthly_after=status["monthly_remaining"],
        reference_id=reward_id,
        metadata={"reward_type": reward_type, "verification_id": str(verification.get("_id")) if verification.get("_id") else None},
        created_at=now,
    )
    return {"granted": True, "reason": None, "quota": status}