# Spec: Day-09 Cached Weather MCP

## Problem Statement

The day's stated deliverable is "ttlMs caching, cache-hit vs cache-miss latency" for an MCP server. No implementation exists. The measurable outcome requires demonstrating that cached responses are significantly faster than fresh API calls, but there is no code to prove this.

## Solution

Build an MCP server that caches Open-Meteo weather API responses with a 10-minute TTL. The server will provide a single `get_weather` tool that returns current conditions and 7-day forecast. A demo client will call the same location twice to demonstrate the latency difference between cache misses and cache hits, printing a clear comparison table.

## User Stories

1. As an MCP client developer, I want a weather tool that returns current conditions and 7-day forecast, so that I can provide weather information to users.
2. As an MCP client developer, I want the weather tool to cache responses, so that repeated requests for the same location are faster.
3. As an MCP client developer, I want cache entries to expire after 10 minutes, so that stale weather data is not served indefinitely.
4. As a demo runner, I want to see a clear latency comparison between cache misses and cache hits, so that I can verify the caching is working.
5. As a demo runner, I want the demo to print a table showing location, call number, time, and cache status, so that the performance difference is obvious.
6. As a developer, I want location strings to be normalized (trim + lowercase) before caching, so that " San Francisco " and "san francisco" hit the same cache entry.
7. As a developer, I want the cache to be in-memory only, so that server restarts clear the cache (acceptable for a demo).
8. As a developer, I want to use Open-Meteo API, so that I don't need to manage API keys for the demo.

## Implementation Decisions

- **MCP server structure**: Single MCP server with one tool `get_weather(location: string)` that returns current conditions + 7-day forecast JSON from Open-Meteo.
- **Cache implementation**: In-memory Map with manual TTL checking. Each cache entry stores the raw API response JSON and a timestamp. On lookup, check if `(now - timestamp) < 600000ms` (10 minutes).
- **Cache key**: Normalized location string (trimmed + lowercase). No alias resolution or geographic normalization.
- **Weather API**: Open-Meteo (no API key required). Endpoint: `https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current=temperature_2m,weather_code&daily=weather_code,temperature_2m_max,temperature_2m_min`.
- **Location geocoding**: Open-Meteo requires lat/lon coordinates. Use Open-Meteo's geocoding API: `https://geocoding-api.open-meteo.com/v1/search?name={location}&count=1` to convert location string to coordinates before calling weather API.
- **Demo client**: TypeScript client using `@modelcontextprotocol/client` with stdio transport. Calls `get_weather` twice on the same location, measures latency with `performance.now()`, prints a comparison table.
- **Package.json scripts**: `"start": "tsx src/index.ts"` for the MCP server, `"demo": "tsx src/demo.ts"` for the performance demo.
- **Dependencies**: `@modelcontextprotocol/sdk`, `@modelcontextprotocol/client`, `tsx` for execution, `typescript` for type safety.

## Testing Decisions

- **What makes a good test**: The demo itself is the test — it must show a measurable latency difference between the first call (cache miss) and second call (cache hit) for the same location.
- **Testing approach**: No unit tests. The `pnpm demo` command is the verification. It must:
  1. Call `get_weather("Paris")` — measure time, expect cache miss
  2. Call `get_weather("Paris")` again — measure time, expect cache hit
  3. Print a table showing the latency difference
  4. The cache hit should be significantly faster (order of magnitude difference expected)
- **Prior art**: Day 8's demo client pattern — spawn server as child process, connect via stdio, call tools, print results, exit cleanly.

## Out of Scope

- Per-datatype TTL (single 10-minute TTL for all data)
- Cache persistence across server restarts
- Location alias resolution (e.g., "SF" → "San Francisco")
- Geographic normalization (e.g., "Bay Area" → specific coordinates)
- Multiple weather tools (e.g., separate current vs forecast tools)
- Cache size limits or eviction policies
- Error retry logic for failed API calls
- Interactive demo input (hardcoded locations only)

## Further Notes

- The geocoding API call is not cached — only the weather API response is cached. This is acceptable for the demo since geocoding is fast relative to weather data fetching.
- Open-Meteo has no rate limits for the free tier, so caching is purely for latency demonstration, not cost savings.
- The demo should use a real location (e.g., "Paris", "Tokyo", "New York") rather than a fake one to ensure the geocoding API returns valid coordinates.
