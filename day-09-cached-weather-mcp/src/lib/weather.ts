export interface Coordinates {
  name: string;
  latitude: number;
  longitude: number;
}

export interface ForecastPayload {
  current: Record<string, unknown>;
  daily: Record<string, unknown>;
}

export interface WeatherResult {
  location: string;
  normalizedLocation: string;
  cached: boolean;
  responseTimeMs: number;
  forecast: ForecastPayload;
}

interface CacheEntry {
  timestamp: number;
  value: ForecastPayload;
  location: string;
}

interface WeatherServiceDeps {
  geocodeLocation?: (location: string) => Promise<Coordinates>;
  fetchForecast?: (coordinates: Coordinates) => Promise<ForecastPayload>;
  now?: () => number;
  ttlMs?: number;
}

export function normalizeLocation(location: string): string {
  return location.trim().toLowerCase();
}

async function geocodeLocation(location: string): Promise<Coordinates> {
  const url = new URL("https://geocoding-api.open-meteo.com/v1/search");
  url.searchParams.set("name", location);
  url.searchParams.set("count", "1");

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Geocoding failed with status ${response.status}`);
  }

  const data = (await response.json()) as {
    results?: Array<{ name: string; latitude: number; longitude: number }>;
  };

  const match = data.results?.[0];
  if (!match) {
    throw new Error(`No coordinates found for location: ${location}`);
  }

  return {
    name: match.name,
    latitude: match.latitude,
    longitude: match.longitude,
  };
}

async function fetchForecast(
  coordinates: Coordinates,
): Promise<ForecastPayload> {
  const url = new URL("https://api.open-meteo.com/v1/forecast");
  url.searchParams.set("latitude", String(coordinates.latitude));
  url.searchParams.set("longitude", String(coordinates.longitude));
  url.searchParams.set("current", "temperature_2m,weather_code");
  url.searchParams.set(
    "daily",
    "weather_code,temperature_2m_max,temperature_2m_min",
  );
  url.searchParams.set("timezone", "auto");
  url.searchParams.set("forecast_days", "7");

  const response = await fetch(url);
  if (!response.ok) {
    throw new Error(`Weather lookup failed with status ${response.status}`);
  }

  const data = (await response.json()) as ForecastPayload;
  return {
    current: data.current,
    daily: data.daily,
  };
}

export function createWeatherService(deps: WeatherServiceDeps = {}) {
  const cache = new Map<string, CacheEntry>();
  const getCoordinates = deps.geocodeLocation ?? geocodeLocation;
  const getForecast = deps.fetchForecast ?? fetchForecast;
  const now = deps.now ?? Date.now;
  const ttlMs = deps.ttlMs ?? 600000;

  return {
    async getWeather(location: string): Promise<WeatherResult> {
      const normalizedLocation = normalizeLocation(location);
      if (!normalizedLocation) {
        throw new Error("Location is required");
      }

      const start = performance.now();
      const existing = cache.get(normalizedLocation);
      const currentTime = now();

      if (existing && currentTime - existing.timestamp < ttlMs) {
        return {
          location: existing.location,
          normalizedLocation,
          cached: true,
          responseTimeMs: performance.now() - start,
          forecast: existing.value,
        };
      }

      const coordinates = await getCoordinates(location);
      const forecast = await getForecast(coordinates);
      cache.set(normalizedLocation, {
        timestamp: currentTime,
        value: forecast,
        location: coordinates.name,
      });

      return {
        location: coordinates.name,
        normalizedLocation,
        cached: false,
        responseTimeMs: performance.now() - start,
        forecast,
      };
    },
  };
}
