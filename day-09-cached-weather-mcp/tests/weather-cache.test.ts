import { describe, expect, it, vi } from "vitest";
import { createWeatherService } from "../src/lib/weather.js";

describe("createWeatherService", () => {
  it("caches raw weather responses by normalized location within TTL", async () => {
    const geocode = vi.fn().mockResolvedValue({
      name: "Paris",
      latitude: 48.8566,
      longitude: 2.3522,
    });
    const weather = vi.fn().mockResolvedValue({
      current: { temperature_2m: 24 },
      daily: { time: [] },
    });

    const service = createWeatherService({
      geocodeLocation: geocode,
      fetchForecast: weather,
    });

    const first = await service.getWeather(" Paris ");
    const second = await service.getWeather("paris");

    expect(first.normalizedLocation).toBe("paris");
    expect(first.cached).toBe(false);
    expect(first.responseTimeMs).toBeGreaterThanOrEqual(0);
    expect(second.cached).toBe(true);
    expect(second.responseTimeMs).toBeGreaterThanOrEqual(0);
    expect(second.forecast).toEqual(first.forecast);
    expect(geocode).toHaveBeenCalledTimes(1);
    expect(weather).toHaveBeenCalledTimes(1);
  });

  it("refreshes expired cache entries after the TTL window", async () => {
    const geocode = vi.fn().mockResolvedValue({
      name: "Paris",
      latitude: 48.8566,
      longitude: 2.3522,
    });
    const weather = vi
      .fn()
      .mockResolvedValueOnce({
        current: { temperature_2m: 24 },
        daily: { time: ["2026-07-20"] },
      })
      .mockResolvedValueOnce({
        current: { temperature_2m: 25 },
        daily: { time: ["2026-07-21"] },
      });

    const now = vi.fn().mockReturnValueOnce(0).mockReturnValueOnce(600001);
    const service = createWeatherService({
      geocodeLocation: geocode,
      fetchForecast: weather,
      now,
      ttlMs: 600000,
    });

    const first = await service.getWeather("Paris");
    const second = await service.getWeather("Paris");

    expect(first).not.toEqual(second);
    expect(first.responseTimeMs).toBeGreaterThanOrEqual(0);
    expect(second.responseTimeMs).toBeGreaterThanOrEqual(0);
    expect(weather).toHaveBeenCalledTimes(2);
  });
});
