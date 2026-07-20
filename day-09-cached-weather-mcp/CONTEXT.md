# Day 9 — Cached Weather MCP — Context

## Glossary

**Cache entry** — A single stored weather API response, keyed by normalized location string. Contains the raw JSON from the weather API and a timestamp for TTL validation.

**Cache hit** — A request where the normalized location key exists in the cache and the entry is within the TTL window. Returns the stored API response without calling the external API.

**Cache miss** — A request where the normalized location key does not exist in the cache, or the entry has expired beyond the TTL window. Triggers a fresh API call to the weather service.

**Cache key** — The normalized location string (trimmed + lowercase) used to look up cache entries. Example: " San Francisco " → "san francisco". No alias resolution.

**Normalized location** — Location string after trimming whitespace and converting to lowercase. Used as the cache key. No semantic alias mapping (e.g., "SF" ≠ "san francisco").

**TTL (Time-To-Live)** — Fixed 10-minute (600,000 ms) window during which a cache entry is considered valid. After expiration, the entry is treated as a miss on next request.

**Weather API response** — Raw JSON returned by the weather service (Open-Meteo), containing current conditions and 7-day forecast. This is what gets cached, not the MCP-formatted output.

## Key Decisions

- **Single TTL**: 10 minutes for all weather data types. No per-datatype differentiation for this demo.
- **Cache scope**: Raw API responses only. MCP tool formatting/processing happens after cache retrieval.
- **Cache storage**: In-memory Map with manual TTL checking. No persistence across server restarts.
- **Normalization**: Trim + lowercase only. No alias resolution or geographic normalization.
- **Tool design**: Single `get_weather(location: string)` tool returning current conditions + 7-day forecast.
