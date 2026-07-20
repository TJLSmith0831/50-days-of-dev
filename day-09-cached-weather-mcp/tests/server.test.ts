import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import { Client, InMemoryTransport } from "@modelcontextprotocol/client";
import { createServerInstance } from "../src/index.js";

const { getWeatherMock } = vi.hoisted(() => ({
  getWeatherMock: vi.fn(),
}));

vi.mock("../src/lib/weather.js", () => ({
  createWeatherService: () => ({
    getWeather: getWeatherMock,
  }),
}));

describe("get_weather tool", () => {
  let server: ReturnType<typeof createServerInstance>;
  let client: Client;

  beforeEach(async () => {
    getWeatherMock.mockReset();
    server = createServerInstance();
    const [clientTransport, serverTransport] =
      InMemoryTransport.createLinkedPair();
    client = new Client({ name: "test-harness", version: "1.0.0" });
    await server.connect(serverTransport);
    await client.connect(clientTransport);
  });

  afterEach(async () => {
    await client.close();
    await server.close();
  });

  it("returns weather content for a valid location", async () => {
    getWeatherMock.mockResolvedValue({
      location: "Paris",
      normalizedLocation: "paris",
      cached: false,
      responseTimeMs: 1138.06,
      forecast: {
        current: { temperature_2m: 24, weather_code: 1 },
        daily: {
          time: ["2026-07-20"],
          weather_code: [1],
          temperature_2m_max: [27],
          temperature_2m_min: [18],
        },
      },
    });

    const result = await client.callTool({
      name: "get_weather",
      arguments: { location: "Paris" },
    });

    expect(result.isError).not.toBe(true);
    const text = (result.content[0] as { text: string }).text;
    expect(text).toContain('"normalizedLocation": "paris"');
    expect(text).toContain('"cached": false');
    expect(text).toContain('"responseTimeMs"');
  });
});
