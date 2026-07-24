"""Offline self-check for the grading + tabulation seam. No OpenAI, no network.

Drives `bench.grade` over every outcome tier with fixture call sequences, then
renders a fixture report. Run: `uv run demo.py`.
"""

from __future__ import annotations

from bench import CALL_CAP, CATALOG_SIZE, QUERIES, Query, Result, grade, render_table, summarize

WEATHER = Query("What's the weather in Reykjavik?", "get_weather")
DENTIST = Query("Remind me to call the dentist", "set_reminder", {"create_calendar_event"})


def check_grading() -> None:
    # Precise: final tool is the primary.
    assert grade(["get_weather"], WEATHER, False) == "Precise"
    # Thrashing does not downgrade outcome — call count carries that story.
    assert grade(["search_web", "search_calendar", "get_weather"], WEATHER, False) == "Precise"

    # Acceptable: in the set, not primary. Only the ambiguous queries can hit this.
    assert grade(["create_calendar_event"], DENTIST, False) == "Acceptable"
    assert grade(["set_reminder"], DENTIST, False) == "Precise"
    assert grade(["create_calendar_event"], WEATHER, False) == "Incorrect"

    # Incorrect: stopped on its own, confidently, outside the set.
    assert grade(["search_web"], WEATHER, False) == "Incorrect"

    # Failed: never landed and ran out of road.
    assert grade([], WEATHER, False) == "Failed"
    assert grade(["search_web"] * CALL_CAP, WEATHER, True) == "Failed"
    # Capped, but it did land on the way — that is wasteful, not failed.
    assert grade(["get_weather"] + ["search_web"] * 4, WEATHER, True) == "Incorrect"
    # Capped and the final call landed — the landing wins.
    assert grade(["search_web"] * 4 + ["get_weather"], WEATHER, True) == "Precise"

    # Every query's acceptable set contains its own primary.
    assert all(q.primary in q.acceptable for q in QUERIES)
    # 6 unambiguous, 2 ambiguous, 8 distinct primaries — the spec's test set shape.
    assert sum(len(q.acceptable) == 1 for q in QUERIES) == 6
    assert len({q.primary for q in QUERIES}) == 8


def check_report() -> str:
    fixtures = [
        Result("naive", WEATHER, ["search_web", "search_calendar", "get_weather"], 4.1, 2400),
        Result("router", WEATHER, ["get_weather"], 1.2, 700, routed=["get_weather"]),
        Result("native", WEATHER, ["get_weather"], 2.0, 1100),
        Result("naive", DENTIST, ["send_email"] * CALL_CAP, 6.5, 3900, capped=True),
        Result("router", DENTIST, ["create_calendar_event"], 1.4, 800,
               routed=["set_reminder", "create_calendar_event"]),
        Result("native", DENTIST, ["set_reminder"], 2.2, 1200),
    ]
    table, summary = render_table(fixtures), summarize(fixtures)
    assert "Precise" in table and "Failed" in table and "Acceptable" in table
    # The pre-filter's decision is visible, and only on the lane that pre-filters.
    assert f"pre-filter: {CATALOG_SIZE} tools -> set_reminder, create_calendar_event" in table
    assert table.count("pre-filter") == 2
    # Summary tallies each strategy's 2 fixture rows.
    assert summary.count("\n") == 4  # header + rule + 3 strategies present
    assert "naive-ts" not in summary  # absent lanes are skipped, not zero-filled
    return f"{table}\n{summary}"


if __name__ == "__main__":
    check_grading()
    print(check_report())
    print("\nself-check OK")
