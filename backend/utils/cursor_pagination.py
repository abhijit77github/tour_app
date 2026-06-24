from __future__ import annotations

import base64
import json
from datetime import datetime, timezone

from bson import ObjectId


def encode_datetime_objectid_cursor(*, created_at: datetime, object_id: ObjectId) -> str:
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    payload = {
        "created_at": created_at.isoformat(),
        "object_id": str(object_id),
    }
    return base64.urlsafe_b64encode(json.dumps(payload, separators=(",", ":")).encode("utf-8")).decode("ascii")


def decode_datetime_objectid_cursor(cursor: str) -> tuple[datetime, ObjectId]:
    decoded = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
    payload = json.loads(decoded)
    created_at = datetime.fromisoformat(payload["created_at"])
    object_id = ObjectId(payload["object_id"])
    if created_at.tzinfo is None:
        created_at = created_at.replace(tzinfo=timezone.utc)
    return created_at, object_id


def build_desc_created_cursor_match(*, created_at: datetime, object_id: ObjectId, field_name: str = "created_at") -> dict:
    return {
        "$or": [
            {field_name: {"$lt": created_at}},
            {field_name: created_at, "_id": {"$lt": object_id}},
        ]
    }