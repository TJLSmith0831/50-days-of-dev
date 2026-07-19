#!/usr/bin/env node

import { McpServer } from "@modelcontextprotocol/server";
import { StdioServerTransport } from "@modelcontextprotocol/server/stdio";
import * as z from "zod/v4";
import { searchSources, fetchDocs } from "./lib/api.js";

function filterBySection(content: string, topic: string): string {
  const topicLower = topic.toLowerCase();
  // Split on lines starting with # / ## / ### but keep the heading with its body
  const parts = content.split(/(?=^#{1,3} )/m);
  const kept = parts.filter((section) => section.toLowerCase().includes(topicLower));
  if (kept.length === 0) return content;
  return kept.join("\n\n---\n\n").trim();
}

export function createServerInstance(apiKey?: string) {
  const server = new McpServer({
    name: "doc-research-mcp",
    version: "1.0.0",
  });

  server.registerTool(
    "resolve-docs-source",
    {
      description: `Search for documentation sources.

    Returns a ranked list of sources with IDs that can be used with get-docs-content.
    Supported source types:
      - "github" (default): GitHub repos via octokit
      - "local": walks DOCS_DIR for *.md
      - "npm":   npm registry search (registry.npmjs.org)
      - "pypi":  PyPI package lookup by exact name (pypi.org)
      - "web":   DuckDuckGo Instant Answer search`,
      inputSchema: z.object({
        query: z.string().describe("Search query for documentation"),
        sourceType: z
          .enum(["github", "local", "npm", "pypi", "web"])
          .optional()
          .describe("Filter by source type"),
        maxResults: z
          .number()
          .min(1)
          .max(10)
          .default(5)
          .describe("Maximum number of results"),
      }),
    },
    async (args) => {
      try {
        const results = await searchSources(
          {
            query: args.query,
            sourceType: args.sourceType,
            maxResults: args.maxResults,
          },
          apiKey,
        );

        if (results.length === 0) {
          return {
            content: [
              {
                type: "text",
                text: "No documentation sources found for your query. Try a different search term or source type.",
              },
            ],
          };
        }

        const formatted = results
          .map(
            (result, index) =>
              `${index + 1}. ${result.id} (${result.type})\n   URL: ${result.url}\n   Description: ${result.description}\n   Relevance: ${result.relevanceScore}`,
          )
          .join("\n\n");

        return {
          content: [
            {
              type: "text",
              text: `Found ${results.length} documentation source(s):\n\n${formatted}\n\nUse the source ID with get-docs-content to retrieve the documentation.`,
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Error searching for documentation sources: ${error instanceof Error ? error.message : "Unknown error"}`,
            },
          ],
          isError: true,
        };
      }
    },
  );

  server.registerTool(
    "get-docs-content",
    {
      description: `Retrieve documentation content from a resolved source ID.

    Usage guidance:
    - Specify a topic filter to get relevant sections instead of entire documentation
    - Use token limits to control the amount of content returned`,
      inputSchema: z.object({
        sourceId: z.string().describe("Source ID from resolve-docs-source"),
        topic: z
          .string()
          .optional()
          .describe("Filter content by topic or keyword"),
        tokenLimit: z
          .number()
          .min(1000)
          .default(5000)
          .describe("Maximum tokens to return"),
      }),
    },
    async (args) => {
      try {
        const docs = await fetchDocs(
          {
            sourceId: args.sourceId,
            topic: args.topic,
            tokenLimit: args.tokenLimit,
          },
          apiKey,
        );

        let content = docs.content;

        if (args.topic) {
          content = filterBySection(content, args.topic);
        }

        if (content.length > args.tokenLimit * 4) {
          content =
            content.substring(0, args.tokenLimit * 4) +
            "\n\n[Content truncated due to token limit]";
        }

        return {
          content: [
            {
              type: "text",
              text: `Documentation from ${docs.sourceId}:\n\n${content}`,
            },
          ],
        };
      } catch (error) {
        return {
          content: [
            {
              type: "text",
              text: `Error fetching documentation: ${error instanceof Error ? error.message : "Unknown error"}`,
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
