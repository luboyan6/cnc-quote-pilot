"""Lead-time contract tests; recorded labels do not establish live quote gates."""

import json
import unittest
from dataclasses import replace

import _support  # noqa: F401 -- adds the isolated backend import root

from app.modules.cnc.browser.contracts import DayBasis, LeadTime, LeadTimeDate, LeadTimeKind
from app.modules.cnc.browser.errors import BrowserStop, Reason


class LeadTimeTests(unittest.TestCase):
    def assert_invalid(self, lead):
        for action in (lead.validate, lead.as_dict):
            with self.assertRaises(BrowserStop) as failure:
                action()
            self.assertEqual(failure.exception.reason, Reason.QUOTE_INVALID)
            self.assertEqual(str(failure.exception), "quote_invalid")

    def assert_invalid_snapshot(self, value):
        with self.assertRaises(BrowserStop) as failure:
            LeadTime.from_dict(value)
        self.assertEqual(failure.exception.reason, Reason.QUOTE_INVALID)
        self.assertEqual(str(failure.exception), "quote_invalid")

    def test_old_constructor_and_exact_legacy_snapshot_migrate_to_v2(self):
        legacy = {"text": "5-7 business days", "minimum_days": 5, "maximum_days": 7, "basis": "business_days"}
        original = dict(legacy)
        lead = LeadTime("5-7 business days", 5, 7, DayBasis.BUSINESS)
        self.assertEqual(LeadTime.from_dict(legacy), lead)
        expected = {
            "schema_version": 2,
            "kind": "duration",
            "text": "5-7 business days",
            "source": None,
            "minimum_days": 5,
            "maximum_days": 7,
            "basis": "business_days",
            "start_point": None,
            "date": None,
        }
        self.assertEqual(lead.as_dict(), expected)
        self.assertEqual(lead.kind, LeadTimeKind.DURATION)
        self.assertNotEqual(LeadTime.from_dict(legacy).kind, LeadTimeKind.PRODUCTION_DURATION)
        self.assertEqual(LeadTime.from_dict(json.loads(json.dumps(expected))), lead)
        self.assertEqual(legacy, original)

    def test_explicit_production_duration_preserves_source_and_start_point_without_default(self):
        # Synthetic verified duration, not the unverified generic PDF/JLC labels.
        for basis in DayBasis:
            with self.subTest(basis=basis):
                lead = LeadTime("  5-7 days as stated  ", 5, 7, basis, kind=LeadTimeKind.PRODUCTION_DURATION, source="synthetic-duration-evidence", start_point="after acceptance")
                snapshot = lead.as_dict()
                self.assertEqual(snapshot["kind"], "production_duration")
                self.assertEqual(snapshot["text"], "  5-7 days as stated  ")
                self.assertEqual(snapshot["source"], "synthetic-duration-evidence")
                self.assertEqual(snapshot["start_point"], "after acceptance")
                self.assertIsNone(snapshot["date"])
                self.assertEqual(LeadTime.from_dict(json.loads(json.dumps(snapshot))), lead)

    def test_explicit_production_duration_requires_nonempty_source(self):
        lead = LeadTime("Synthetic production duration", 5, 7, DayBasis.BUSINESS, kind=LeadTimeKind.PRODUCTION_DURATION, source="synthetic-production-evidence")
        snapshot = lead.as_dict()
        for source in (None, "", " \t", False, 5):
            with self.subTest(source=source):
                self.assert_invalid(replace(lead, source=source))
                self.assert_invalid_snapshot({**snapshot, "source": source})

    def test_recorded_generic_durations_do_not_claim_production_semantics(self):
        # The supplied numbers/basis are source-backed; the labels do not prove
        # production semantics, a start event, or a definitive quote status.
        cases = (
            ("8 business days", 8, "Xometry B quantity 5 Economy PDF"),
            ("6 个工作日", 6, "JLC existing item quantity 1 standard reference estimate"),
        )
        for text, days, source in cases:
            with self.subTest(source=source):
                lead = LeadTime(text, days, days, DayBasis.BUSINESS, source=source)
                snapshot = lead.as_dict()
                self.assertEqual(snapshot["kind"], "duration")
                self.assertEqual(snapshot["text"], text)
                self.assertEqual(snapshot["source"], source)
                self.assertEqual((snapshot["minimum_days"], snapshot["maximum_days"], snapshot["basis"]), (days, days, "business_days"))
                self.assertIsNone(snapshot["start_point"])
                self.assertIsNone(snapshot["date"])
                self.assertEqual(LeadTime.from_dict(json.loads(json.dumps(snapshot))), lead)

    def test_explicit_full_ship_and_arrival_dates_round_trip(self):
        for kind in (LeadTimeKind.SHIP_DATE, LeadTimeKind.ARRIVAL_DATE):
            with self.subTest(kind=kind):
                lead = LeadTime("Synthetic date: 2028-02-29", kind=kind, source="synthetic-date-evidence", date=LeadTimeDate(2, 29, 2028))
                snapshot = lead.as_dict()
                self.assertEqual(snapshot["kind"], kind.value)
                self.assertEqual(snapshot["date"], {"month": 2, "day": 29, "year": 2028})
                for field in ("minimum_days", "maximum_days", "basis", "start_point"):
                    self.assertIsNone(snapshot[field])
                self.assertEqual(LeadTime.from_dict(json.loads(json.dumps(snapshot))), lead)

    def test_recorded_labels_retain_distinct_semantics_sources_and_missing_years(self):
        # The B PDF ship date is conditional. Its generic "8 business days"
        # label and JLC's recorded 6 business days do not prove production semantics.
        cases = (
            ("Nov5", LeadTimeKind.ARRIVAL_DATE, LeadTimeDate(11, 5), "Xometry A quantity 2 Economy UI"),
            ("Nov 9", LeadTimeKind.ARRIVAL_DATE, LeadTimeDate(11, 9), "Xometry B quantity 5 Economy UI"),
            ("Tuesday, Nov. 03", LeadTimeKind.SHIP_DATE, LeadTimeDate(11, 3), "Xometry B quantity 5 Economy PDF conditional ship date"),
        )
        for text, kind, date, source in cases:
            with self.subTest(source=source):
                lead = LeadTime(text, kind=kind, source=source, date=date)
                snapshot = lead.as_dict()
                self.assertEqual(snapshot["text"], text)
                self.assertEqual(snapshot["source"], source)
                self.assertEqual(snapshot["kind"], kind.value)
                self.assertEqual(snapshot["date"], {"month": date.month, "day": date.day, "year": None})
                self.assertIsNone(snapshot["minimum_days"])
                self.assertIsNone(snapshot["maximum_days"])
                self.assertIsNone(snapshot["basis"])
                self.assertIsNone(snapshot["start_point"])
                self.assertEqual(LeadTime.from_dict(json.loads(json.dumps(snapshot))), lead)

    def test_unexplained_raw_labels_never_become_known_lead_times(self):
        for text in ("unknown", "TBD", "8 business days", "6 个工作日"):
            with self.subTest(text=text):
                self.assert_invalid(LeadTime(text))
                for kind in (LeadTimeKind.ARRIVAL_DATE, LeadTimeKind.SHIP_DATE):
                    self.assert_invalid(LeadTime(text, kind=kind, source="label-only-observation"))

    def test_unknown_year_february_29_is_preserved_without_a_fabricated_year(self):
        lead = LeadTime("Feb 29", kind=LeadTimeKind.ARRIVAL_DATE, source="synthetic-leap-date-evidence", date=LeadTimeDate(2, 29))
        snapshot = lead.as_dict()
        self.assertEqual(snapshot["date"], {"month": 2, "day": 29, "year": None})
        self.assertEqual(LeadTime.from_dict(snapshot), lead)

    def test_invalid_calendar_dates_and_date_types_fail(self):
        for date in (
            LeadTimeDate(0, 1),
            LeadTimeDate(13, 1),
            LeadTimeDate(2, 30),
            LeadTimeDate(4, 31),
            LeadTimeDate(1, 0),
            LeadTimeDate(2, 29, 2026),
            LeadTimeDate(2, 29, 1900),
            LeadTimeDate(1, 1, 0),
            LeadTimeDate(1, 1, 10000),
            LeadTimeDate(True, 1),
            LeadTimeDate(1, False),
            LeadTimeDate(1, 1, True),
            LeadTimeDate(1.0, 1),
            LeadTimeDate(1, 1.0),
            LeadTimeDate(1, 1, 2026.0),
            LeadTimeDate("11", 1),
            LeadTimeDate(1, "1"),
            LeadTimeDate(1, 1, "2026"),
        ):
            with self.subTest(date=date):
                self.assert_invalid(LeadTime("Invalid date", kind=LeadTimeKind.ARRIVAL_DATE, source="synthetic-evidence", date=date))

    def test_duration_requires_positive_integer_ordered_days_and_known_basis(self):
        lead = LeadTime("Synthetic duration", 5, 7, DayBasis.BUSINESS)
        for changes in (
            {"minimum_days": True},
            {"maximum_days": True},
            {"minimum_days": 5.0},
            {"maximum_days": 7.0},
            {"minimum_days": "5"},
            {"maximum_days": "7"},
            {"minimum_days": None},
            {"maximum_days": None},
            {"minimum_days": 0},
            {"minimum_days": -1},
            {"maximum_days": 4},
            {"basis": None},
            {"basis": "business_days"},
            {"basis": "unknown"},
        ):
            with self.subTest(changes=changes):
                self.assert_invalid(replace(lead, **changes))

    def test_duration_rejects_date_fields_invalid_labels_and_unknown_kind(self):
        lead = LeadTime("Synthetic duration", 5, 7, DayBasis.BUSINESS)
        for changes in (
            {"date": LeadTimeDate(11, 9)},
            {"text": None},
            {"text": " \t"},
            {"text": 5},
            {"source": ""},
            {"source": " "},
            {"source": False},
            {"source": 5},
            {"start_point": ""},
            {"start_point": True},
            {"kind": "production_duration"},
            {"kind": "unknown"},
            {"kind": None},
        ):
            with self.subTest(changes=changes):
                self.assert_invalid(replace(lead, **changes))

    def test_date_requires_source_and_typed_date_without_duration_fields(self):
        for kind in (LeadTimeKind.ARRIVAL_DATE, LeadTimeKind.SHIP_DATE):
            lead = LeadTime("Nov 9", kind=kind, source="synthetic-evidence", date=LeadTimeDate(11, 9))
            for changes in (
                {"minimum_days": 5},
                {"maximum_days": 7},
                {"basis": DayBasis.BUSINESS},
                {"start_point": "after acceptance"},
                {"source": None},
                {"source": ""},
                {"source": True},
                {"date": None},
                {"date": "Nov 9"},
                {"date": {"month": 11, "day": 9, "year": None}},
            ):
                with self.subTest(kind=kind, changes=changes):
                    self.assert_invalid(replace(lead, **changes))

    def test_decode_requires_exact_fields_and_object_shape(self):
        legacy = {"text": "5-7 business days", "minimum_days": 5, "maximum_days": 7, "basis": "business_days"}
        snapshot = LeadTime("Nov 9", kind=LeadTimeKind.ARRIVAL_DATE, source="synthetic-evidence", date=LeadTimeDate(11, 9)).as_dict()
        for value in (None, [], "Nov 9", 5, True, {}, {**legacy, "source": None}, {**snapshot, "unexpected": "token=secret"}):
            with self.subTest(value=value):
                self.assert_invalid_snapshot(value)
        for value in (legacy, snapshot):
            for field in value:
                with self.subTest(missing=field, value=value):
                    self.assert_invalid_snapshot({key: entry for key, entry in value.items() if key != field})
        date = snapshot["date"]
        assert isinstance(date, dict)
        for field in ("month", "day", "year"):
            self.assert_invalid_snapshot({**snapshot, "date": {key: entry for key, entry in date.items() if key != field}})
        self.assert_invalid_snapshot({**snapshot, "date": {**date, "unexpected": "secret"}})

    def test_decode_rejects_unknown_versions_kinds_and_untyped_values(self):
        snapshot = LeadTime("Nov 9", kind=LeadTimeKind.ARRIVAL_DATE, source="synthetic-evidence", date=LeadTimeDate(11, 9)).as_dict()
        for version in (None, True, 2.0, "2", 1, 3):
            with self.subTest(version=version):
                self.assert_invalid_snapshot({**snapshot, "schema_version": version})
        for kind in (None, True, "unknown", "TBD"):
            with self.subTest(kind=kind):
                self.assert_invalid_snapshot({**snapshot, "kind": kind})
        for changes in (
            {"text": None},
            {"source": None},
            {"source": 5},
            {"minimum_days": 5},
            {"basis": "business_days"},
            {"start_point": "after acceptance"},
            {"date": None},
            {"date": "Nov 9"},
            {"date": {"month": "11", "day": 9, "year": None}},
            {"date": {"month": 11, "day": True, "year": None}},
            {"date": {"month": 11, "day": 9, "year": 2026.0}},
            {"date": {"month": 2, "day": 30, "year": None}},
        ):
            with self.subTest(changes=changes):
                self.assert_invalid_snapshot({**snapshot, **changes})

    def test_legacy_and_v2_duration_decode_have_the_same_strict_semantics(self):
        legacy = {"text": "5-7 business days", "minimum_days": 5, "maximum_days": 7, "basis": "business_days"}
        current = LeadTime.from_dict(legacy).as_dict()
        for changes in (
            {"text": ""},
            {"minimum_days": True},
            {"maximum_days": 7.0},
            {"minimum_days": "5"},
            {"maximum_days": None},
            {"minimum_days": 0},
            {"maximum_days": 4},
            {"basis": None},
            {"basis": "unknown"},
            {"basis": []},
        ):
            for snapshot in (legacy, current):
                with self.subTest(changes=changes, version=snapshot.get("schema_version")):
                    self.assert_invalid_snapshot({**snapshot, **changes})

    def test_raw_text_and_source_are_not_in_domain_repr_or_error_messages(self):
        lead = LeadTime("private raw label", kind=LeadTimeKind.ARRIVAL_DATE, source="private evidence ref", date=LeadTimeDate(11, 9))
        self.assertNotIn("private raw label", repr(lead))
        self.assertNotIn("private evidence ref", repr(lead))
        self.assert_invalid_snapshot({**lead.as_dict(), "kind": "token=private"})
