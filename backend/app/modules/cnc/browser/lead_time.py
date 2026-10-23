"""Typed quote lead times and their single versioned snapshot boundary.

Trusted adapters supply the semantics and date parts; this module never parses
page labels or infers a year, production duration, or day-count starting event.
"""

from dataclasses import dataclass, field
from datetime import date as calendar_date
from enum import StrEnum

from .errors import BrowserStop, Reason

_LEGACY_FIELDS = frozenset({"text", "minimum_days", "maximum_days", "basis"})
_SNAPSHOT_FIELDS = _LEGACY_FIELDS | {"schema_version", "kind", "source", "start_point", "date"}
_DATE_FIELDS = frozenset({"month", "day", "year"})


class DayBasis(StrEnum):
    BUSINESS = "business_days"
    CALENDAR = "calendar_days"


class LeadTimeKind(StrEnum):
    DURATION = "duration"
    PRODUCTION_DURATION = "production_duration"
    SHIP_DATE = "ship_date"
    ARRIVAL_DATE = "arrival_date"


@dataclass(frozen=True)
class LeadTimeDate:
    """An explicit platform date; absent years stay absent in every snapshot."""

    month: int
    day: int
    year: int | None = None

    def validate(self) -> None:
        if type(self.month) is not int or type(self.day) is not int or (self.year is not None and type(self.year) is not int):
            raise BrowserStop(Reason.QUOTE_INVALID)
        try:
            # A leap year permits Feb 29 without assigning any year to the date.
            calendar_date(2000 if self.year is None else self.year, self.month, self.day)
        except (ValueError, OverflowError):
            raise BrowserStop(Reason.QUOTE_INVALID) from None

    def as_dict(self) -> dict[str, int | None]:
        self.validate()
        return {"month": self.month, "day": self.day, "year": self.year}


def _nonempty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


@dataclass(frozen=True)
class LeadTime:
    """Keep the four positional duration arguments compatible with older adapters.

    source is a trusted evidence reference or description, never a URL carrying
    session secrets. start_point preserves an explicitly verified duration start
    label; None does not imply ordering, payment, observation or another event.
    """

    text: str = field(repr=False)
    minimum_days: int | None = None
    maximum_days: int | None = None
    basis: DayBasis | None = None
    kind: LeadTimeKind = field(default=LeadTimeKind.DURATION, kw_only=True)
    source: str | None = field(default=None, kw_only=True, repr=False)
    start_point: str | None = field(default=None, kw_only=True, repr=False)
    date: LeadTimeDate | None = field(default=None, kw_only=True)

    def validate(self) -> None:
        if not _nonempty_text(self.text) or not isinstance(self.kind, LeadTimeKind):
            raise BrowserStop(Reason.QUOTE_INVALID)
        if self.source is not None and not _nonempty_text(self.source):
            raise BrowserStop(Reason.QUOTE_INVALID)
        if self.kind in (LeadTimeKind.DURATION, LeadTimeKind.PRODUCTION_DURATION):
            if (
                type(self.minimum_days) is not int
                or type(self.maximum_days) is not int
                or not 0 < self.minimum_days <= self.maximum_days
                or not isinstance(self.basis, DayBasis)
                or self.date is not None
                or (self.kind == LeadTimeKind.PRODUCTION_DURATION and self.source is None)
                or (self.start_point is not None and not _nonempty_text(self.start_point))
            ):
                raise BrowserStop(Reason.QUOTE_INVALID)
        else:
            if (
                self.minimum_days is not None
                or self.maximum_days is not None
                or self.basis is not None
                or self.start_point is not None
                or self.source is None
                or not isinstance(self.date, LeadTimeDate)
            ):
                raise BrowserStop(Reason.QUOTE_INVALID)
            self.date.validate()

    def as_dict(self) -> dict[str, object]:
        """Emit the complete v2 shape, including every unknown/irrelevant null."""
        self.validate()
        return {
            "schema_version": 2,
            "kind": self.kind.value,
            "text": self.text,
            "source": self.source,
            "minimum_days": self.minimum_days,
            "maximum_days": self.maximum_days,
            "basis": self.basis.value if self.basis is not None else None,
            "start_point": self.start_point,
            "date": self.date.as_dict() if self.date is not None else None,
        }

    @classmethod
    def from_dict(cls, value: object) -> "LeadTime":
        """Strictly decode v2 or the exact original four-field duration snapshot."""
        if not isinstance(value, dict):
            raise BrowserStop(Reason.QUOTE_INVALID)
        try:
            fields = set(value)
            if fields == _LEGACY_FIELDS:
                lead = cls(value["text"], value["minimum_days"], value["maximum_days"], DayBasis(value["basis"]))
            elif fields == _SNAPSHOT_FIELDS:
                if type(value["schema_version"]) is not int or value["schema_version"] != 2:
                    raise BrowserStop(Reason.QUOTE_INVALID)
                date = value["date"]
                if date is not None:
                    if not isinstance(date, dict) or set(date) != _DATE_FIELDS:
                        raise BrowserStop(Reason.QUOTE_INVALID)
                    date = LeadTimeDate(date["month"], date["day"], date["year"])
                lead = cls(
                    value["text"],
                    value["minimum_days"],
                    value["maximum_days"],
                    DayBasis(value["basis"]) if value["basis"] is not None else None,
                    kind=LeadTimeKind(value["kind"]),
                    source=value["source"],
                    start_point=value["start_point"],
                    date=date,
                )
            else:
                raise BrowserStop(Reason.QUOTE_INVALID)
        except (ValueError, TypeError):
            raise BrowserStop(Reason.QUOTE_INVALID) from None
        lead.validate()
        return lead
