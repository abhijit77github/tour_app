# Itinerary Data Preparation

This guide defines a practical workflow for preparing operator itinerary templates that can be retrieved by the planner LLM.

## Goal

Populate `operator_itinerary_templates` with high-quality, published templates that match well on:

- `primary_location`
- `duration_days`
- `trip_styles`
- `traveler_types`
- `budget_band`

The planner currently retrieves published operator templates and uses them as grounded itinerary ideas.

The same collection can also hold internal library rows tagged to `internal_operator_source`. This is the recommended path for centrally curated destination itineraries that are not owned by an operator account.

## What To Collect From Operators

Collect raw trip information in a staging sheet or form first. Do not ask operators to enter Mongo-ready JSON directly.

Each itinerary should capture:

- Operator email
- Destination name
- State
- Country
- Package title
- Best-fit traveler type
- Best-fit trip styles
- Duration in days
- Budget band
- Best season
- One-paragraph summary
- Planner note: when should this itinerary be used
- Day-wise outline with highlights

## Normalization Rules

Use controlled values wherever possible.

### Budget band

- `budget`
- `mid`
- `premium`

### Traveler types

- `solo`
- `couple`
- `family`
- `friends`
- `senior`

### Recommended trip styles

- `family`
- `cultural`
- `adventure`
- `relaxed`
- `romantic`
- `food`
- `scenic`
- `road-trip`
- `beach`
- `nature`
- `nightlife`

Keep the vocabulary tight. Retrieval works better with a small consistent tag set than with free-form labels.

## Quality Rules

Before importing, check each record against these rules:

1. `primary_location` must match one of the operator's serving areas exactly.
2. `title` should include destination and duration where possible.
3. `summary` should explain fit, not marketing language.
4. `days` should be realistic and not exceed `duration_days`.
5. Variants should differ materially by pace, audience, or budget.
6. Only import `published` templates when they are ready for LLM retrieval.

## Dataset Format

Use a JSON array like the starter file at `backend/scripts/data/itinerary_templates.sample.json`.

For centrally curated destination content, set `operator_email` to `internal_operator_source`. The importer will tag those rows into the same template collection with internal-source metadata while leaving normal operator-owned templates unchanged.

Each row looks like this:

```json
{
  "seed_tag": "seed-itinerary-manali-family-4d",
  "operator_email": "operator2@tourapp.local",
  "import_source": "starter_dataset",
  "template": {
    "title": "4D3N Manali family snow and sightseeing circuit",
    "summary": "Comfortable Manali plan for families...",
    "primary_location": {
      "area_name": "Manali",
      "state": "Himachal Pradesh",
      "country": "India"
    },
    "route_locations": [],
    "duration_days": 4,
    "trip_styles": ["family", "scenic", "relaxed"],
    "traveler_types": ["family"],
    "season_tags": ["winter", "summer"],
    "budget_band": "mid",
    "notes_for_planner": "Use when the tourist wants...",
    "days": [
      {
        "day_number": 1,
        "title": "Arrival and acclimatization",
        "summary": "Check in, rest...",
        "highlights": ["Mall Road"],
        "overnight_location": "Manali"
      }
    ],
    "status": "published"
  }
}
```

## Import Workflow

1. Seed or confirm your operator profiles exist.
2. Copy the sample JSON file and replace starter rows with real operator data.
3. For internal library rows, use `internal_operator_source` as the operator email sentinel.
4. Run a dry validation first.
5. Import into Mongo.

Commands:

```bash
python -m backend.scripts.seed_itineraries --schema-only
python -m backend.scripts.seed_itineraries --dry-run
python -m backend.scripts.seed_itineraries --file backend/scripts/data/itinerary_templates.sample.json
```

The importer also accepts a directory of JSON chunk files. This is the preferred format for large internal libraries that are maintained state-by-state.

## Progress Tracking

Use `backend/scripts/data/internal_itinerary_progress.json` to track the internal library rollout.

Recommended workflow:

1. Maintain one or more JSON files per state or regional cluster.
2. Mark each state as `not_started`, `in_progress`, or `seeded_first_wave`.
3. Keep the tracking hierarchy aligned to state, then district or city cluster, then sub-area or route.

## Suggested Real Data Rollout

Start small:

1. Pick 5 to 8 destinations.
2. Create 3 to 5 templates per destination.
3. Ensure each destination has variation across duration, budget, and audience.

Recommended first wave:

1. Manali
2. Goa
3. Mysore
4. Bangalore weekend
5. Coorg
6. Jaipur or Udaipur

## Operational Recommendation

Keep one dataset file per market or collection cycle, then import it idempotently using `seed_tag`.

That gives you:

- repeatable updates
- safer edits
- easy rollback by dataset
- predictable test coverage for planner retrieval