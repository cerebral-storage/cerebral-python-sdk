"""Tests for tilde._isoparse (Python 3.10-compatible ISO 8601 parsing)."""

from __future__ import annotations

from datetime import timezone

import pytest

from tilde._isoparse import parse_iso_datetime


class TestParseIsoDatetime:
    def test_z_suffix(self):
        dt = parse_iso_datetime("2025-01-02T03:04:05Z")
        assert dt.tzinfo == timezone.utc
        assert (dt.year, dt.month, dt.day) == (2025, 1, 2)

    def test_offset_suffix(self):
        dt = parse_iso_datetime("2025-01-02T03:04:05+00:00")
        assert dt.utcoffset().total_seconds() == 0  # type: ignore[union-attr]

    def test_no_fractional_seconds(self):
        dt = parse_iso_datetime("2025-01-02T03:04:05Z")
        assert dt.microsecond == 0

    def test_three_digit_fractional(self):
        dt = parse_iso_datetime("2025-01-02T03:04:05.123Z")
        assert dt.microsecond == 123000

    def test_six_digit_fractional(self):
        dt = parse_iso_datetime("2025-01-02T03:04:05.123456Z")
        assert dt.microsecond == 123456

    @pytest.mark.parametrize(
        "value, expected_micro",
        [
            # Sub-microsecond precision (Go's RFC3339Nano emits up to 9 digits).
            ("2026-04-19T20:34:16.34547019+00:00", 345470),
            ("2026-04-19T20:34:16.345470192+00:00", 345470),
            # Unusual digit counts.
            ("2026-04-19T20:34:16.5Z", 500000),
            ("2026-04-19T20:34:16.12Z", 120000),
            ("2026-04-19T20:34:16.1234Z", 123400),
            ("2026-04-19T20:34:16.12345Z", 123450),
        ],
    )
    def test_odd_fractional_lengths(self, value, expected_micro):
        dt = parse_iso_datetime(value)
        assert dt.microsecond == expected_micro

    def test_naive_datetime_passes_through(self):
        dt = parse_iso_datetime("2025-01-02T03:04:05")
        assert dt.tzinfo is None
