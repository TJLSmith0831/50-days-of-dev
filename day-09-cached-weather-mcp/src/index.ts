#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/server";
import { StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import * as z from "zod/v4";
import { createWeatherService } from "./lib/weather.js";

export function createServerInstance() {
  const server = new McpServer({
    name: "cached-weather-mcp",
    version: "1.0.0",
  });
  const weatherService = createWeatherService();

  server.registerTool(
    "get_weather",
    {
      description:
        "Get current weather and a 7-day forecast for a location. Responses are cached in memory for 10 minutes using the normalized location string as the cache key.",
      inputSchema: z.object({
        location: z.string().min(1).describe("City or location name"),
      }),
    },
    async (args) => {
      try {
        const result = await weatherService.getWeather(args.location);
        return {
          content: [
            {
              type: "text",
              text: JSON.stringify(result, null, 2),
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: error instanceof Error ? error.message : "Unknown error",
            },
          ],
          isError: true,
        };
      }
    },
  );

  return server;
}

async function main() {
  const server = createServerInstance();
  const transport = new StdioServerTransport();
  await server.connect(transport);
}

main().catch((error) => {
  console.error("Server error:", error);
  process.exit(1);
});
