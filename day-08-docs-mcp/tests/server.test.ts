import { describe, it, expect, beforeEach, afterEach, vi } from "vitest";
import { Client, InMemoryTransport } from "@modelcontextprotocol/client";
import { createServerInstance } from "../src/index.js";

const { searchSourcesMock, fetchDocsMock } = vi.hoisted(() => ({
  searchSourcesMock: vi.fn(),
  fetchDocsMock: vi.fn(),
}));

vi.mock("../src/lib/api.js", () => ({
  searchSources: searchSourcesMock,
  fetchDocs: fetchDocsMock,
}));

describe("MCP Server Tools", () => {
  let server: ReturnType<typeof createServerInstance>;
  let client: Client;

  beforeEach(async () => {
    searchSourcesMock.mockReset();
    fetchDocsMock.mockReset();
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

  describe("resolve-docs-source tool", () => {
    it("should handle valid search query", async () => {
      searchSourcesMock.mockResolvedValue([
        {
          id: "github:test/repo",
          type: "github",
          url: "https://github.com/test/repo",
          description: "A test repo",
          relevanceScore: 0.5,
        },
      ]);

      const result = await client.callTool({
        name: "resolve-docs-source",
        arguments: {
          query: "next.js authentication",
          maxResults: 3,
        },
      });

      expect(result).toHaveProperty("content");
      expect(Array.isArray(result.content)).toBe(true);
      expect(result.content[0]).toHaveProperty("type");
      expect(result.content[0].type).toBe("text");
    });

    it("should handle empty results gracefully", async () => {
      searchSourcesMock.mockResolvedValue([]);

      const result = await client.callTool({
        name: "resolve-docs-source",
        arguments: {
          query: "xyz-nonexistent-query-12345",
          maxResults: 5,
        },
      });

      const text = (result.content[0] as { text: string }).text;
      expect(text).toContain("No documentation sources found");
    });

    it("should validate sourceType enum", async () => {
      const result = await client.callTool({
        name: "resolve-docs-source",
        arguments: {
          query: "test",
          sourceType: "invalid-type" as any,
        },
      });

      expect(result.isError).toBe(true);
    });

    it("should reject unimplemented sourceType 'npm'", async () => {
      const result = await client.callTool({
        name: "resolve-docs-source",
        arguments: {
          query: "test",
          sourceType: "npm" as any,
        },
      });

      expect(result.isError).toBe(true);
    });

    it("should accept sourceType 'local'", async () => {
      searchSourcesMock.mockResolvedValue([]);

      const result = await client.callTool({
        name: "resolve-docs-source",
        arguments: {
          query: "test",
          sourceType: "local",
        },
      });

      expect(result.isError).not.toBe(true);
    });
  });

  describe("get-docs-content tool", () => {
    it("should fetch docs for valid sourceId", async () => {
      fetchDocsMock.mockResolvedValue({
        sourceId: "github:test/repo",
        content: "# Test Repo\n\nSome docs content",
        metadata: {
          title: "test/repo",
          author: "test",
          lastUpdated: "2024-01-01T00:00:00Z",
        },
      });

      const result = await client.callTool({
        name: "get-docs-content",
        arguments: {
          sourceId: "github:test/repo",
          tokenLimit: 2000,
        },
      });

      const text = (result.content[0] as { text: string }).text;
      expect(text).toContain("Documentation from");
    });

    it("should return whole matching section, not just matching lines", async () => {
      fetchDocsMock.mockResolvedValue({
        sourceId: "github:test/repo",
        content:
          "# Intro\n\nSome intro text.\n\n## Installation\n\nRun the following:\n\n```bash\nnpm install foo\n```\n\nThat's it.\n\n## Other\n\nUnrelated content here.",
        metadata: {
          title: "test/repo",
          author: "test",
          lastUpdated: "2024-01-01T00:00:00Z",
        },
      });

      const result = await client.callTool({
        name: "get-docs-content",
        arguments: {
          sourceId: "github:test/repo",
          topic: "installation",
          tokenLimit: 2000,
        },
      });

      const text = (result.content[0] as { text: string }).text;
      expect(text).toContain("## Installation");
      expect(text).toContain("npm install foo");
      expect(text).toContain("That's it.");
      expect(text).not.toContain("Unrelated content here.");
    });

    it("should fall back to full content when no section matches topic", async () => {
      fetchDocsMock.mockResolvedValue({
        sourceId: "github:test/repo",
        content: "# Intro\n\nSome intro text.\n\n## Other\n\nMore text.",
        metadata: {
          title: "test/repo",
          author: "test",
          lastUpdated: "2024-01-01T00:00:00Z",
        },
      });

      const result = await client.callTool({
        name: "get-docs-content",
        arguments: {
          sourceId: "github:test/repo",
          topic: "nomatch-xyzzy",
          tokenLimit: 2000,
        },
      });

      const text = (result.content[0] as { text: string }).text;
      expect(text).toContain("Some intro text.");
      expect(text).toContain("More text.");
    });

    it("should enforce minimum token limit", async () => {
      const result = await client.callTool({
        name: "get-docs-content",
        arguments: {
          sourceId: "github:test/repo",
          tokenLimit: 500, // Below minimum of 1000
        },
      });

      expect(result.isError).toBe(true);
    });
  });
});
