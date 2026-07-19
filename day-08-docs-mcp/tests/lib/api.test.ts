import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";

const { mockSearchRepos, mockGetReadme, mockGetContent, mockGetRepo } =
  vi.hoisted(() => ({
    mockSearchRepos: vi.fn(),
    mockGetReadme: vi.fn(),
    mockGetContent: vi.fn(),
    mockGetRepo: vi.fn(),
  }));

vi.mock("octokit", () => ({
  Octokit: vi.fn().mockImplementation(() => ({
    rest: {
      search: { repos: mockSearchRepos },
      repos: {
        getReadme: mockGetReadme,
        getContent: mockGetContent,
        get: mockGetRepo,
      },
    },
  })),
}));

import { searchSources, fetchDocs } from "../../src/lib/api.js";

describe("API Client Layer", () => {
  beforeEach(() => {
    mockSearchRepos.mockReset();
    mockGetReadme.mockReset();
    mockGetContent.mockReset();
    mockGetRepo.mockReset();
  });

  describe("searchSources", () => {
    it("should return array of SourceResult", async () => {
      mockSearchRepos.mockResolvedValue({
        data: {
          items: [
            {
              full_name: "test/repo",
              html_url: "https://github.com/test/repo",
              description: "A test repo",
              stargazers_count: 100,
              score: 50,
            },
          ],
        },
      });

      const result = await searchSources({
        query: "test query",
        maxResults: 5,
      });

      expect(Array.isArray(result)).toBe(true);
      expect(result.length).toBeGreaterThan(0);
      expect(result[0]).toHaveProperty("id");
      expect(result[0]).toHaveProperty("type");
      expect(result[0]).toHaveProperty("url");
      expect(result[0]).toHaveProperty("description");
      expect(result[0]).toHaveProperty("relevanceScore");
    });

    it("should filter by source type when specified", async () => {
      mockSearchRepos.mockResolvedValue({
        data: {
          items: [
            {
              full_name: "test/repo",
              html_url: "https://github.com/test/repo",
              description: "A test repo",
              stargazers_count: 0,
              score: 1,
            },
          ],
        },
      });

      const result = await searchSources({
        query: "test",
        sourceType: "github",
        maxResults: 5,
      });

      result.forEach((item) => {
        expect(item.type).toBe("github");
      });
    });

    it("should respect maxResults limit", async () => {
      mockSearchRepos.mockResolvedValue({
        data: {
          items: [
            {
              full_name: "test/repo",
              html_url: "https://github.com/test/repo",
              description: "A test repo",
              stargazers_count: 0,
              score: 1,
            },
          ],
        },
      });

      const result = await searchSources({
        query: "test",
        maxResults: 3,
      });

      expect(result.length).toBeLessThanOrEqual(3);
    });
  });

  describe("fetchDocs", () => {
    it("should return DocsContent with sourceId", async () => {
      mockGetReadme.mockResolvedValue({
        data: {
          name: "README.md",
          content: Buffer.from("# Test Repo\n\nHello").toString("base64"),
        },
      });
      mockGetContent.mockResolvedValue({ data: [] });
      mockGetRepo.mockResolvedValue({
        data: {
          full_name: "test/repo",
          owner: { login: "test" },
          pushed_at: "2024-01-01T00:00:00Z",
        },
      });

      const result = await fetchDocs({
        sourceId: "github:test/repo",
      });

      expect(result).toHaveProperty("sourceId");
      expect(result).toHaveProperty("content");
      expect(result).toHaveProperty("metadata");
      expect(result.sourceId).toBe("github:test/repo");
    });

    it("should recursively walk docs/ subdirectories", async () => {
      mockGetReadme.mockRejectedValue(new Error("no readme"));
      mockGetRepo.mockResolvedValue({
        data: {
          full_name: "test/repo",
          owner: { login: "test" },
          pushed_at: "2024-01-01T00:00:00Z",
        },
      });

      mockGetContent.mockImplementation(async ({ path }: { path: string }) => {
        if (path === "docs") {
          return {
            data: [
              { type: "file", name: "index.md", path: "docs/index.md" },
              { type: "dir", name: "api", path: "docs/api" },
            ],
          };
        }
        if (path === "docs/api") {
          return {
            data: [
              { type: "file", name: "auth.md", path: "docs/api/auth.md" },
            ],
          };
        }
        if (path === "docs/index.md") {
          return {
            data: {
              name: "index.md",
              content: Buffer.from("# Index\n\nroot doc").toString("base64"),
            },
          };
        }
        if (path === "docs/api/auth.md") {
          return {
            data: {
              name: "auth.md",
              content: Buffer.from("# Auth\n\nnested doc").toString("base64"),
            },
          };
        }
        throw new Error(`unexpected path ${path}`);
      });

      const result = await fetchDocs({ sourceId: "github:test/repo" });
      expect(result.content).toContain("root doc");
      expect(result.content).toContain("nested doc");
    });

    it("should include metadata fields", async () => {
      mockGetReadme.mockResolvedValue({
        data: {
          name: "README.md",
          content: Buffer.from("# Test Repo").toString("base64"),
        },
      });
      mockGetContent.mockResolvedValue({ data: [] });
      mockGetRepo.mockResolvedValue({
        data: {
          full_name: "test/repo",
          owner: { login: "test" },
          pushed_at: "2024-01-01T00:00:00Z",
        },
      });

      const result = await fetchDocs({
        sourceId: "github:test/repo",
      });

      expect(result.metadata).toHaveProperty("title");
      expect(result.metadata).toHaveProperty("author");
      expect(result.metadata).toHaveProperty("lastUpdated");
    });
  });

  describe("local source", () => {
    let dir: string;
    const originalDocsDir = process.env.DOCS_DIR;

    beforeEach(() => {
      dir = mkdtempSync(join(tmpdir(), "docs-mcp-"));
      mkdirSync(join(dir, "sub"), { recursive: true });
      writeFileSync(join(dir, "armadillo.md"), "# Armadillo\n\nHello armadillo.");
      writeFileSync(join(dir, "sub", "nested.md"), "# Nested\n\ndeep");
      writeFileSync(join(dir, "ignore.txt"), "not markdown");
      process.env.DOCS_DIR = dir;
    });

    afterEach(() => {
      rmSync(dir, { recursive: true, force: true });
      if (originalDocsDir === undefined) delete process.env.DOCS_DIR;
      else process.env.DOCS_DIR = originalDocsDir;
    });

    it("searchSources returns local .md files matching query", async () => {
      const result = await searchSources({
        query: "armadillo",
        sourceType: "local",
        maxResults: 10,
      });

      expect(result.length).toBeGreaterThan(0);
      const ids = result.map((r) => r.id);
      expect(ids).toContain("local:armadillo.md");
      expect(ids).toContain("local:sub/nested.md");
      expect(result.every((r) => r.type === "local")).toBe(true);
      const armadillo = result.find((r) => r.id === "local:armadillo.md")!;
      const nested = result.find((r) => r.id === "local:sub/nested.md")!;
      expect(armadillo.relevanceScore).toBeGreaterThan(nested.relevanceScore);
    });

    it("fetchDocs reads a local file", async () => {
      const result = await fetchDocs({ sourceId: "local:armadillo.md" });
      expect(result.sourceId).toBe("local:armadillo.md");
      expect(result.content).toContain("Hello armadillo.");
      expect(result.metadata.title).toBe("armadillo.md");
    });
  });

  describe("network sources", () => {
    const originalFetch = globalThis.fetch;
    let fetchMock: ReturnType<typeof vi.fn>;

    beforeEach(() => {
      fetchMock = vi.fn();
      globalThis.fetch = fetchMock as any;
    });
    afterEach(() => {
      globalThis.fetch = originalFetch;
    });

    const jsonResponse = (body: any, status = 200) =>
      ({
        ok: status >= 200 && status < 300,
        status,
        json: async () => body,
        text: async () => JSON.stringify(body),
        headers: { get: () => null },
      }) as any;

    const textResponse = (body: string, contentType = "text/html") =>
      ({
        ok: true,
        status: 200,
        json: async () => ({}),
        text: async () => body,
        headers: {
          get: (k: string) =>
            k.toLowerCase() === "content-type" ? contentType : null,
        },
      }) as any;

    describe("npm", () => {
      it("searchSources returns npm packages", async () => {
        fetchMock.mockResolvedValue(
          jsonResponse({
            objects: [
              {
                searchScore: 1000,
                package: {
                  name: "zod",
                  description: "TypeScript schema validation",
                  links: { npm: "https://www.npmjs.com/package/zod" },
                },
              },
            ],
          }),
        );
        const result = await searchSources({
          query: "zod",
          sourceType: "npm",
          maxResults: 3,
        });
        expect(fetchMock).toHaveBeenCalledWith(
          expect.stringContaining("registry.npmjs.org/-/v1/search?text=zod"),
        );
        expect(result[0].id).toBe("npm:zod");
        expect(result[0].type).toBe("npm");
      });

      it("fetchDocs returns npm package README", async () => {
        fetchMock.mockResolvedValue(
          jsonResponse({
            "dist-tags": { latest: "4.0.0" },
            versions: {
              "4.0.0": { description: "Schema validation", readme: "" },
            },
            readme: "# zod\n\nInstall with npm install zod",
            time: { modified: "2024-01-01T00:00:00Z" },
            author: { name: "colinhacks" },
          }),
        );
        const result = await fetchDocs({ sourceId: "npm:zod" });
        expect(result.content).toContain("Install with npm install zod");
        expect(result.metadata.title).toBe("zod");
      });
    });

    describe("pypi", () => {
      it("searchSources returns single package by exact name", async () => {
        fetchMock.mockResolvedValue(
          jsonResponse({
            info: {
              name: "requests",
              summary: "HTTP for Humans",
              project_url: "https://pypi.org/project/requests/",
            },
          }),
        );
        const result = await searchSources({
          query: "requests",
          sourceType: "pypi",
          maxResults: 5,
        });
        expect(result).toHaveLength(1);
        expect(result[0].id).toBe("pypi:requests");
      });

      it("searchSources returns [] for 404", async () => {
        fetchMock.mockResolvedValue(jsonResponse({}, 404));
        const result = await searchSources({
          query: "nonexistent-pkg-xyzzy",
          sourceType: "pypi",
        });
        expect(result).toEqual([]);
      });

      it("fetchDocs returns pypi description", async () => {
        fetchMock.mockResolvedValue(
          jsonResponse({
            info: {
              name: "requests",
              version: "2.31.0",
              summary: "HTTP for Humans",
              description: "# Requests\n\nElegant HTTP.",
              author: "Kenneth Reitz",
            },
            urls: [{ upload_time_iso_8601: "2024-01-01T00:00:00Z" }],
          }),
        );
        const result = await fetchDocs({ sourceId: "pypi:requests" });
        expect(result.content).toContain("Elegant HTTP.");
        expect(result.metadata.title).toBe("requests 2.31.0");
      });
    });

    describe("web", () => {
      it("searchSources returns DDG results", async () => {
        fetchMock.mockResolvedValue(
          jsonResponse({
            AbstractURL: "https://en.wikipedia.org/wiki/MCP",
            AbstractText: "Model Context Protocol",
            Heading: "MCP",
            RelatedTopics: [
              {
                FirstURL: "https://example.com/mcp-spec",
                Text: "MCP specification",
              },
            ],
          }),
        );
        const result = await searchSources({
          query: "model context protocol",
          sourceType: "web",
          maxResults: 5,
        });
        expect(result.length).toBeGreaterThan(0);
        expect(result[0].type).toBe("web");
        expect(result[0].id).toContain("web:");
      });

      it("fetchDocs strips HTML tags", async () => {
        fetchMock.mockResolvedValue(
          textResponse(
            "<html><body><h1>Title</h1><p>Body text</p><script>bad()</script></body></html>",
          ),
        );
        const result = await fetchDocs({
          sourceId: "web:https://example.com/page",
        });
        expect(result.content).toContain("Title");
        expect(result.content).toContain("Body text");
        expect(result.content).not.toContain("<h1>");
        expect(result.content).not.toContain("bad()");
      });
    });
  });
});
