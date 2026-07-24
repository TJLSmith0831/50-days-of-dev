"""Run all 8 queries through every lane and print the comparison report.

Usage: `uv run main.py` (all lanes) or `uv run main.py naive router` (a subset).
"""

from __future__ import annotations

import asyncio
import sys

from bench import CALL_CAP, CATALOG_SIZE, QUERIES, STRATEGIES, Result, render_table, summarize
from strategies import (
    MODEL,
    TOOL_SEARCH_MODEL,
    run_naive,
    run_naive_control,
    run_native,
    run_router,
)

LANES = {
    "naive": run_naive,
    "router": run_router,
    "native": run_native,
    "naive-ts": run_naive_control,
}


async def main(lanes: list[str]) -> None:
    print(f"Model: {MODEL}  |  native + naive-ts lanes: {TOOL_SEARCH_MODEL}  |  call cap: {CALL_CAP}\n")
    results: list[Result] = []
    for query in QUERIES:
        for lane in lanes:
            print(f"  {lane:<9} {query.text[:60]}", flush=True)
            result = await LANES[lane](query)
            results.append(result)
            if result.routed:
                print(
                    f"    pre-filter kept {len(result.routed)}/{CATALOG_SIZE}: "
                    f"{', '.join(result.routed)}",
                    flush=True,
                )
            if result.error:
                print(f"    ! {result.error}", flush=True)

    print("\n" + "=" * 90)
    print("PER-QUERY DETAIL\n")
    print(render_table(results))
    print("=" * 90)
    print("PER-STRATEGY SUMMARY\n")
    print(summarize(results))
    if "naive-ts" in lanes:
        print(
            f"\nnaive-ts is a control, not a strategy: the naive baseline on "
            f"{TOOL_SEARCH_MODEL}, because the Responses API refuses `tool_search` on "
            f"{MODEL}. Read `native` against `naive-ts`, not against `naive`."
        )


if __name__ == "__main__":
    selected = [a for a in sys.argv[1:] if a in STRATEGIES] or list(STRATEGIES)
    asyncio.run(main(selected))
