#!/usr/bin/env node
import { Client } from "@modelcontextprotocol/client";
import { StdioClientTransport } from "@modelcontextprotocol/client/stdio";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

async function main() {
  const here = dirname(fileURLToPath(import.meta.url));
  const serverPath = resolve(here, "../dist/index.js");

  const transport = new StdioClientTransport({
    command: "node",
    args: [serverPath],
    env: process.env as Record<string, string>,
  });
  const client = new Client({ name: "docs-mcp-demo", version: "1.0.0" });
  await client.connect(transport);

  const query = process.env.DEMO_QUERY ?? "armadillo";
  const sourceType = (process.env.DEMO_SOURCE_TYPE ?? "local") as "github" | "local";
  const topic = process.env.DEMO_TOPIC ?? "armadillo";

  console.error(`> resolve-docs-source query="${query}" sourceType=${sourceType}`);
  const resolved: any = await client.callTool({
    name: "resolve-docs-source",
    arguments: { query, sourceType, maxResults: 5 },
  });
  const resolvedText = resolved.content?.[0]?.text ?? "";
  console.log(resolvedText);

  // Parse first "N. <id> (<type>)" line
  const match = resolvedText.match(/^1\. (\S+)/m);
  if (!match) {
    console.error("no source id in response, exiting");
    await client.close();
    process.exit(1);
  }
  const sourceId = match[1];

  console.error(`\n> get-docs-content sourceId=${sourceId} topic="${topic}"`);
  const fetched: any = await client.callTool({
    name: "get-docs-content",
    arguments: { sourceId, topic, tokenLimit: 2000 },
  });
  const fetchedText = fetched.content?.[0]?.text ?? "";
  console.log(fetchedText);

  await client.close();
  if (!fetchedText || fetched.isError) process.exit(1);
}

main().catch((err) => {
  console.error("Client error:", err);
  process.exit(1);
});
