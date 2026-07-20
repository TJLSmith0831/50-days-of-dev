#!/usr/bin/env node

import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

interface DemoRow {
  location: string;
  call: number;
  timeMs: string;
  status: string;
}

async function callWeather(client: Client, location: string) {
  const start = performance.now();
  const result: any = await client.callTool({
    name: "get_weather",
    arguments: { location },
  });
  const elapsed = performance.now() - start;
  const text = result.content?.[0]?.text ?? "";
  const parsed = JSON.parse(text) as { cached: boolean };

  return {
    elapsed,
    cached: parsed.cached,
  };
}

async function main() {
  const here = dirname(fileURLToPath(import.meta.url));
  const serverPath = resolve(here, "../dist/src/index.js");
  const transport = new StdioClientTransport({
    command: "node",
    args: [serverPath],
    env: process.env as Record<string, string>,
  });
  const client = new Client({ name: "cached-weather-demo", version: "1.0.0" });
  await client.connect(transport);

  const firstLocation = process.env.DEMO_LOCATION_A ?? "Paris";
  const secondLocation = process.env.DEMO_LOCATION_B;
  const rows: DemoRow[] = [];

  const first = await callWeather(client, firstLocation);
  rows.push({
    location: firstLocation,
    call: 1,
    timeMs: `${first.elapsed.toFixed(2)}ms`,
    status: first.cached ? "HIT" : "MISS",
  });

  const second = await callWeather(client, firstLocation);
  rows.push({
    location: firstLocation,
    call: 2,
    timeMs: `${second.elapsed.toFixed(2)}ms`,
    status: second.cached ? "HIT" : "MISS",
  });

  if (secondLocation) {
    const third = await callWeather(client, secondLocation);
    rows.push({
      location: secondLocation,
      call: 1,
      timeMs: `${third.elapsed.toFixed(2)}ms`,
      status: third.cached ? "HIT" : "MISS",
    });
  }

  console.table(rows);
  await client.close();
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
