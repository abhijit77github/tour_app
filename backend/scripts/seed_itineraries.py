"""Import operator itinerary templates from a JSON dataset.

Run:
  python -m backend.scripts.seed_itineraries
  python -m backend.scripts.seed_itineraries --file backend/scripts/data/itinerary_templates.sample.json
  python -m backend.scripts.seed_itineraries --dry-run

Dataset format:
  [
    {
      "seed_tag": "seed-itinerary-manali-family-4d",
      "operator_email": "operator2@tourapp.local",
      "template": {
        ...OperatorItineraryTemplateCreate fields...
      }
    }
  ]
"""

from __future__ import annotations

import argparse
import asyncio
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from backend.database import close_mongo_connection, connect_to_mongo, get_database
from backend.models.itinerary import OperatorItineraryTemplateCreate


DEFAULT_DATASET_PATH = Path(__file__).resolve().parent / "data" / "itinerary_templates.sample.json"
INTERNAL_OPERATOR_SOURCE = "internal_operator_source"
INTERNAL_OPERATOR_NAME = "Internal Destination Library"


def _normalize(value: str | None) -> str:
    return " ".join((value or "").strip().lower().split())


def _location_matches(scope: dict[str, Any], target: dict[str, Any]) -> bool:
    if scope.get("area_name") and _normalize(scope.get("area_name")) != _normalize(target.get("area_name")):
        return False
    if scope.get("state") and _normalize(scope.get("state")) != _normalize(target.get("state")):
        return False
    if scope.get("country") and _normalize(scope.get("country")) != _normalize(target.get("country")):
        return False
    return True


def _find_serving_area(profile: dict[str, Any], location: dict[str, Any]) -> dict[str, Any] | None:
    for area in profile.get("serving_areas", []):
        if _location_matches(area, location):
            return area
    return None


def _load_dataset(file_path: Path) -> list[dict[str, Any]]:
    if file_path.is_dir():
        rows: list[dict[str, Any]] = []
        for child in sorted(file_path.glob("*.json")):
            if child.name in {"progress.json", "manifest.json"} or child.name.startswith("_"):
                continue
            child_rows = json.loads(child.read_text())
            if not isinstance(child_rows, list):
                raise ValueError(f"Dataset file must be a JSON array: {child}")
            rows.extend(child_rows)
        return rows

    rows = json.loads(file_path.read_text())
    if not isinstance(rows, list):
        raise ValueError("Dataset root must be a JSON array")
    return rows


async def _resolve_operator(db, operator_email: str) -> tuple[dict[str, Any], dict[str, Any]]:
    if operator_email == INTERNAL_OPERATOR_SOURCE:
        return (
            {
                "_id": INTERNAL_OPERATOR_SOURCE,
                "email": INTERNAL_OPERATOR_SOURCE,
                "user_type": "system",
            },
            {
                "_id": INTERNAL_OPERATOR_SOURCE,
                "business_name": INTERNAL_OPERATOR_NAME,
                "serving_areas": [],
            },
        )

    user = await db.users.find_one({"email": operator_email, "user_type": "operator"})
    if not user:
        raise ValueError(f"Operator user not found for email: {operator_email}")

    profile = await db.operator_profiles.find_one({"user_id": str(user["_id"])})
    if not profile:
        raise ValueError(f"Operator profile not found for email: {operator_email}")

    return user, profile


def _validate_dataset_rows(rows: list[dict[str, Any]]) -> list[str]:
    seen_seed_tags: set[str] = set()
    messages: list[str] = []

    for index, entry in enumerate(rows, start=1):
        seed_tag = entry.get("seed_tag")
        operator_email = entry.get("operator_email")
        template_payload = entry.get("template")

        if not seed_tag:
            raise ValueError(f"Row {index}: seed_tag is required")
        if seed_tag in seen_seed_tags:
            raise ValueError(f"Duplicate seed_tag found: {seed_tag}")
        seen_seed_tags.add(seed_tag)

        if not operator_email:
            raise ValueError(f"{seed_tag}: operator_email is required")
        if not isinstance(template_payload, dict):
            raise ValueError(f"{seed_tag}: template must be an object")

        OperatorItineraryTemplateCreate(**template_payload)
        messages.append(f"VALID {seed_tag} -> {operator_email}")

    return messages


async def _upsert_template(db, entry: dict[str, Any], dry_run: bool) -> str:
    seed_tag = entry.get("seed_tag")
    operator_email = entry.get("operator_email")
    template_payload = entry.get("template")

    if not seed_tag:
        raise ValueError("Each row requires a seed_tag")
    if not operator_email:
        raise ValueError(f"{seed_tag}: operator_email is required")
    if not isinstance(template_payload, dict):
        raise ValueError(f"{seed_tag}: template must be an object")

    user, profile = await _resolve_operator(db, operator_email)
    validated = OperatorItineraryTemplateCreate(**template_payload)
    template_doc = validated.model_dump()
    is_internal_source = operator_email == INTERNAL_OPERATOR_SOURCE

    serving_area = _find_serving_area(profile, template_doc["primary_location"])
    if not is_internal_source and not serving_area:
        raise ValueError(
            f"{seed_tag}: primary_location must match one of the operator serving areas for {operator_email}"
        )

    if serving_area and not template_doc["primary_location"].get("coordinates") and serving_area.get("coordinates"):
        template_doc["primary_location"]["coordinates"] = serving_area["coordinates"]

    now = datetime.now(timezone.utc)
    document = {
        **template_doc,
        "seed_tag": seed_tag,
        "import_source": entry.get("import_source", "json_import"),
        "operator_profile_id": str(profile["_id"]),
        "operator_user_id": str(user["_id"]),
        "operator_name": profile.get("business_name"),
        "is_internal_source": is_internal_source,
        "source_scope": "internal" if is_internal_source else "operator",
        "created_at": now,
        "updated_at": now,
    }

    existing = await db.operator_itinerary_templates.find_one({"seed_tag": seed_tag})
    action = "create"
    if existing:
        action = "update"
        document["created_at"] = existing.get("created_at", now)

    if dry_run:
        return f"DRY RUN {action.upper()} {seed_tag} -> {document['operator_name']} / {document['title']}"

    if existing:
        await db.operator_itinerary_templates.update_one(
            {"_id": existing["_id"]},
            {"$set": document},
        )
    else:
        await db.operator_itinerary_templates.insert_one(document)

    return f"{action.upper()}D {seed_tag} -> {document['operator_name']} / {document['title']}"


async def seed(file_path: Path, dry_run: bool = False, schema_only: bool = False) -> None:
    rows = _load_dataset(file_path)
    print(f"Loaded {len(rows)} itinerary rows from {file_path}")

    if schema_only:
        for message in _validate_dataset_rows(rows):
            print(message)
        return

    await connect_to_mongo()
    try:
        db = await get_database()
        for entry in rows:
            message = await _upsert_template(db, entry, dry_run=dry_run)
            print(message)
    finally:
        await close_mongo_connection()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Seed operator itinerary templates from JSON")
    parser.add_argument(
        "--file",
        default=str(DEFAULT_DATASET_PATH),
        help="Path to itinerary dataset JSON file",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and print actions without writing to MongoDB",
    )
    parser.add_argument(
        "--schema-only",
        action="store_true",
        help="Validate dataset structure and template schema without connecting to MongoDB",
    )
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_args()
    asyncio.run(seed(Path(args.file), dry_run=args.dry_run, schema_only=args.schema_only))