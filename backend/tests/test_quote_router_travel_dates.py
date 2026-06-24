import unittest
from datetime import datetime, timezone

from bson import ObjectId

from backend.routers.quotes import (
    _build_operator_quote_inbox_query,
    _build_operator_quote_sort_spec,
    _build_quote_budget_match,
    _build_quote_inbox_cursor_match,
    _build_quote_travel_window_match,
    _decode_quote_inbox_cursor,
    _encode_quote_inbox_cursor,
    _normalize_quote_filter_now,
    _parse_quote_travel_start_date,
)


class QuoteRouterTravelDateTests(unittest.TestCase):
    def test_parse_quote_travel_start_date_from_string(self):
        parsed = _parse_quote_travel_start_date("2026-07-10 to 2026-07-12")

        self.assertEqual(parsed, datetime(2026, 7, 10, tzinfo=timezone.utc))

    def test_parse_quote_travel_start_date_from_dict(self):
        parsed = _parse_quote_travel_start_date({"start_date": "2026-08-05"})

        self.assertEqual(parsed, datetime(2026, 8, 5, tzinfo=timezone.utc))

    def test_parse_quote_travel_start_date_rejects_invalid_text(self):
        self.assertIsNone(_parse_quote_travel_start_date("sometime next summer"))

    def test_travel_soonest_sort_spec_orders_by_normalized_start_date(self):
        self.assertEqual(
            _build_operator_quote_sort_spec("travel_soonest"),
            [("sort_travel_start", 1), ("created_at", -1), ("_id", -1)],
        )

    def test_travel_soonest_cursor_round_trip_and_match(self):
        created_at = datetime(2026, 6, 1, 9, 0, tzinfo=timezone.utc)
        travel_start = datetime(2026, 7, 10, tzinfo=timezone.utc)
        row = {
            "_id": ObjectId(),
            "created_at": created_at,
            "sort_travel_start": travel_start,
        }

        cursor = _encode_quote_inbox_cursor(sort_mode="travel_soonest", row=row)
        decoded = _decode_quote_inbox_cursor(cursor)

        self.assertEqual(decoded["sort_mode"], "travel_soonest")
        self.assertEqual(decoded["travel_start"], travel_start)

        match = _build_quote_inbox_cursor_match(sort_mode="travel_soonest", cursor_payload=decoded)
        self.assertEqual(match["$or"][0], {"sort_travel_start": {"$gt": travel_start}})

    def test_budget_band_query_ranges(self):
        self.assertEqual(_build_quote_budget_match("budget"), {"budget": {"$lt": 20000}})
        self.assertEqual(_build_quote_budget_match("mid"), {"budget": {"$gte": 20000, "$lt": 50000}})
        self.assertEqual(_build_quote_budget_match("premium"), {"budget": {"$gte": 50000}})

    def test_location_filter_uses_exact_case_insensitive_match(self):
        query = _build_operator_quote_inbox_query(
            operator_profile_id="operator-1",
            status_filter="all",
            search=None,
            location_filter="Mysore",
            budget_band="all",
        )

        self.assertEqual(query["locations"]["$elemMatch"]["name"]["$regex"], "^Mysore$")
        self.assertEqual(query["locations"]["$elemMatch"]["name"]["$options"], "i")

    def test_travel_window_match_uses_normalized_ranges(self):
        start_of_today = _normalize_quote_filter_now(datetime(2026, 6, 18, 14, 45, tzinfo=timezone.utc))
        match = _build_quote_travel_window_match(travel_window="days_31_90", now=start_of_today)

        self.assertEqual(match["sort_travel_start"]["$gt"], datetime(2026, 7, 18, tzinfo=timezone.utc))
        self.assertEqual(match["sort_travel_start"]["$lte"], datetime(2026, 9, 16, tzinfo=timezone.utc))


if __name__ == "__main__":
    unittest.main()