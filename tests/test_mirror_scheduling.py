#!/usr/bin/env python3
"""
Standalone checks for mirror scheduling calculations.
"""

import sys
from datetime import datetime
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))

from app.core.mirror_schedules import compute_next_run_at  # noqa: E402


def assert_equal(actual, expected, label):
    if actual != expected:
        raise AssertionError(f"{label}: expected {expected!r}, got {actual!r}")


def main():
    reference = datetime(2026, 4, 14, 10, 30, 0)  # Tuesday

    assert_equal(
        compute_next_run_at(True, "daily", "12:15", None, reference),
        datetime(2026, 4, 14, 12, 15, 0),
        "daily future same day",
    )
    assert_equal(
        compute_next_run_at(True, "daily", "09:15", None, reference),
        datetime(2026, 4, 15, 9, 15, 0),
        "daily next day",
    )
    assert_equal(
        compute_next_run_at(True, "weekly", "09:00", 0, reference),
        datetime(2026, 4, 19, 9, 0, 0),
        "weekly sunday",
    )
    assert_equal(
        compute_next_run_at(True, "monthly", "08:00", 31, reference),
        datetime(2026, 4, 30, 8, 0, 0),
        "monthly clamp to last day",
    )
    assert_equal(
        compute_next_run_at(False, "daily", "08:00", None, reference),
        None,
        "disabled schedule",
    )

    print("Mirror scheduling tests passed.")


if __name__ == "__main__":
    main()
