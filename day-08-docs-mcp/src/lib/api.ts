import { Octokit } from "octokit";
import { readFile, readdir, stat } from "node:fs/promises";
import { join, relative, resolve, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import {
  SourceResult,
  DocsContent,
  SearchOptions,
  FetchOptions,
} from "../types.js";

const MAX_REPO_DOCS_FILES = 20;
const MAX_REPO_DOCS_DEPTH = 3;
// ponytail: local walks are cheap; keep depth reasonable, no file cap
const MAX_LOCAL_DEPTH = 6;

function createOctokit(apiKey?: string): Octokit {
  const token = apiKey ?? process.env.GITHUB_TOKEN;
  return new Octokit(token ? { auth: token } : {});
}

function docsRoot(): string {
  if (process.env.DOCS_DIR) return resolve(process.env.DOCS_DIR);
  // ponytail: default to repo root two levels above this file
  return resolve(dirname(fileURLToPath(import.meta.url)), "../../..");
}

async function walkMarkdown(
  root: string,
  dir: string,
  depth: number,
  out: string[],
): Promise<void> {
  if (depth > MAX_LOCAL_DEPTH) return;
  let entries: string[];
  try {
    entries = await readdir(dir);
  } catch {
    return;
  }
  for (const name of entries) {
    if (name.startsWith(".") || name === "node_modules") continue;
    const full = join(dir, name);
    let s;
    try {
      s = await stat(full);
    } catch {
      continue;
    }
    if (s.isDirectory()) {
      await walkMarkdown(root, full, depth + 1, out);
    } else if (s.isFile() && name.toLowerCase().endsWith(".md")) {
      out.push(relative(root, full));
    }
  }
}

async function searchLocal(options: SearchOptions): Promise<SourceResult[]> {
  const root = docsRoot();
  const paths: string[] = [];
  await walkMarkdown(root, root, 0, paths);

  const q = options.query.toLowerCase();
  const scored = paths.map((rel) => {
    const nameHit = rel.toLowerCase().includes(q) ? 1 : 0;
    const relevanceScore = nameHit ? 0.9 : 0.1;
    return {
      id: `local:${rel}`,
      type: "local" as const,
      url: `file://${join(root, rel)}`,
      description: `Local Markdown file ${rel}`,
      relevanceScore,
    };
  });

  scored.sort((a, b) => b.relevanceScore - a.relevanceScore);
  return scored.slice(0, options.maxResults ?? 5);
}

async function fetchLocal(sourceId: string): Promise<DocsContent> {
  const rel = sourceId.replace(/^local:/, "");
  const root = docsRoot();
  const full = resolve(root, rel);
  if (!full.startsWith(root)) {
    throw new Error(`Path escapes DOCS_DIR: ${rel}`);
  }
  const content = await readFile(full, "utf8");
  const s = await stat(full);
  return {
    sourceId,
    content,
    metadata: {
      title: rel.split("/").pop(),
      author: "local",
      lastUpdated: s.mtime.toISOString(),
    },
  };
}

async function collectRepoMarkdown(
  octokit: Octokit,
  owner: string,
  repo: string,
  path: string,
  depth: number,
  out: string[],
): Promise<void> {
  if (depth > MAX_REPO_DOCS_DEPTH || out.length >= MAX_REPO_DOCS_FILES) return;
  let listing: any;
  try {
    const { data } = await octokit.rest.repos.getContent({ owner, repo, path });
    listing = data;
  } catch {
    return;
  }
  if (!Array.isArray(listing)) return;
  for (const entry of listing) {
    if (out.length >= MAX_REPO_DOCS_FILES) return;
    if (entry.type === "file" && entry.name.endsWith(".md")) {
      try {
        const { data: fileData } = await octokit.rest.repos.getContent({
          owner,
          repo,
          path: entry.path,
        });
        if (
          !Array.isArray(fileData) &&
          "content" in fileData &&
          typeof (fileData as any).content === "string"
        ) {
          const text = Buffer.from(
            (fileData as any).content,
            "base64",
          ).toString("utf8");
          out.push(`# ${(fileData as any).name ?? entry.name}\n\n${text}`);
        }
      } catch {
        // skip unreadable file
      }
    } else if (entry.type === "dir") {
      await collectRepoMarkdown(octokit, owner, repo, entry.path, depth + 1, out);
    }
  }
}

async function searchNpm(options: SearchOptions): Promise<SourceResult[]> {
  const size = Math.min(10, Math.max(1, options.maxResults ?? 5));
  const url = `https://registry.npmjs.org/-/v1/search?text=${encodeURIComponent(options.query)}&size=${size}`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`npm search failed: ${res.status}`);
  const data = (await res.json()) as { objects: Array<any> };
  return data.objects.map((obj) => {
    const pkg = obj.package;
    return {
      id: `npm:${pkg.name}`,
      type: "npm" as const,
      url: pkg.links?.npm ?? `https://www.npmjs.com/package/${pkg.name}`,
      description: pkg.description ?? `npm package ${pkg.name}`,
      relevanceScore: Math.min(1, (obj.searchScore ?? 0) / 100000),
    };
  });
}

async function fetchNpm(sourceId: string): Promise<DocsContent> {
  const pkg = sourceId.replace(/^npm:/, "");
  const res = await fetch(`https://registry.npmjs.org/${encodeURIComponent(pkg)}`);
  if (!res.ok) throw new Error(`npm fetch failed for ${pkg}: ${res.status}`);
  const data = (await res.json()) as any;
  const latest = data["dist-tags"]?.latest;
  const versionInfo = latest ? data.versions?.[latest] : undefined;
  let readme = (data.readme || versionInfo?.readme || "").trim();
  // Modern npm packages often omit README from the registry; fall back to unpkg.
  if (!readme) {
    try {
      const rr = await fetch(`https://unpkg.com/${encodeURIComponent(pkg)}/README.md`);
      if (rr.ok) readme = await rr.text();
    } catch {
      // best-effort fallback
    }
  }
  const description = versionInfo?.description ?? data.description ?? "";
  const content = `# ${pkg}\n\n${description}\n\n${readme}`.trim();
  return {
    sourceId,
    content,
    metadata: {
      title: pkg,
      author: data.author?.name ?? data.maintainers?.[0]?.name ?? "unknown",
      lastUpdated: data.time?.modified ?? new Date().toISOString(),
    },
  };
}

async function searchPypi(options: SearchOptions): Promise<SourceResult[]> {
  // ponytail: PyPI has no free JSON search endpoint; treat query as an exact package name.
  //   Add fuzzy search if libraries.io/BigQuery becomes worth the API key.
  const pkg = options.query.trim();
  const res = await fetch(`https://pypi.org/pypi/${encodeURIComponent(pkg)}/json`);
  if (res.status === 404) return [];
  if (!res.ok) throw new Error(`pypi lookup failed: ${res.status}`);
  const data = (await res.json()) as any;
  return [
    {
      id: `pypi:${data.info.name}`,
      type: "pypi" as const,
      url: data.info.project_url ?? `https://pypi.org/project/${data.info.name}/`,
      description: data.info.summary ?? `PyPI package ${data.info.name}`,
      relevanceScore: 1,
    },
  ];
}

async function fetchPypi(sourceId: string): Promise<DocsContent> {
  const pkg = sourceId.replace(/^pypi:/, "");
  const res = await fetch(`https://pypi.org/pypi/${encodeURIComponent(pkg)}/json`);
  if (!res.ok) throw new Error(`pypi fetch failed for ${pkg}: ${res.status}`);
  const data = (await res.json()) as any;
  const description = data.info.description ?? data.info.summary ?? "";
  const content = `# ${data.info.name} ${data.info.version}\n\n${data.info.summary ?? ""}\n\n${description}`.trim();
  return {
    sourceId,
    content,
    metadata: {
      title: `${data.info.name} ${data.info.version}`,
      author: data.info.author ?? data.info.author_email ?? "unknown",
      lastUpdated: data.urls?.[0]?.upload_time_iso_8601 ?? new Date().toISOString(),
    },
  };
}

async function searchWeb(options: SearchOptions): Promise<SourceResult[]> {
  const url = `https://api.duckduckgo.com/?q=${encodeURIComponent(options.query)}&format=json&no_html=1&no_redirect=1`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`web search failed: ${res.status}`);
  const data = (await res.json()) as any;
  const results: SourceResult[] = [];

  if (data.AbstractURL) {
    results.push({
      id: `web:${data.AbstractURL}`,
      type: "web",
      url: data.AbstractURL,
      description: data.AbstractText || data.Heading || data.AbstractURL,
      relevanceScore: 1,
    });
  }
  const topics = (data.RelatedTopics ?? []).filter((t: any) => t.FirstURL);
  for (const t of topics) {
    results.push({
      id: `web:${t.FirstURL}`,
      type: "web",
      url: t.FirstURL,
      description: t.Text ?? t.FirstURL,
      relevanceScore: 0.5,
    });
  }
  return results.slice(0, options.maxResults ?? 5);
}

function stripHtml(html: string): string {
  return html
    .replace(/<script[\s\S]*?<\/script>/gi, "")
    .replace(/<style[\s\S]*?<\/style>/gi, "")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/\s+/g, " ")
    .trim();
}

async function fetchWeb(sourceId: string): Promise<DocsContent> {
  const url = sourceId.replace(/^web:/, "");
  const res = await fetch(url, { redirect: "follow" });
  if (!res.ok) throw new Error(`web fetch failed for ${url}: ${res.status}`);
  const contentType = res.headers.get("content-type") ?? "";
  const raw = await res.text();
  const content = contentType.includes("html") ? stripHtml(raw) : raw;
  return {
    sourceId,
    content,
    metadata: {
      title: url,
      author: new URL(url).hostname,
      lastUpdated: res.headers.get("last-modified") ?? new Date().toISOString(),
    },
  };
}

export async function searchSources(
  options: SearchOptions,
  apiKey?: string,
): Promise<SourceResult[]> {
  if (options.sourceType === "local") return searchLocal(options);
  if (options.sourceType === "npm") return searchNpm(options);
  if (options.sourceType === "pypi") return searchPypi(options);
  if (options.sourceType === "web") return searchWeb(options);
  if (options.sourceType && options.sourceType !== "github") {
    throw new Error(`Unsupported sourceType: ${options.sourceType}`);
  }

  const octokit = createOctokit(apiKey);
  const perPage = Math.min(10, Math.max(1, options.maxResults ?? 5));

  const { data } = await octokit.rest.search.repos({
    q: options.query,
    per_page: perPage,
  });

  return data.items.map((item) => {
    const score = (item as any).score as number | undefined;
    const stars = item.stargazers_count ?? 0;
    const relevanceScore =
      score !== undefined
        ? Math.min(1, score / 100)
        : Math.min(1, stars / 10000);

    return {
      id: `github:${item.full_name}`,
      type: "github" as const,
      url: item.html_url,
      description: item.description ?? `GitHub repository ${item.full_name}`,
      relevanceScore,
    };
  });
}

export async function fetchDocs(
  options: FetchOptions,
  apiKey?: string,
): Promise<DocsContent> {
  if (options.sourceId.startsWith("local:")) return fetchLocal(options.sourceId);
  if (options.sourceId.startsWith("npm:")) return fetchNpm(options.sourceId);
  if (options.sourceId.startsWith("pypi:")) return fetchPypi(options.sourceId);
  if (options.sourceId.startsWith("web:")) return fetchWeb(options.sourceId);

  if (!options.sourceId.startsWith("github:")) {
    throw new Error(`Unsupported source ID: ${options.sourceId}`);
  }

  const octokit = createOctokit(apiKey);
  const [owner, repo] = options.sourceId.replace("github:", "").split("/", 2);
  if (!owner || !repo) {
    throw new Error(`Invalid GitHub source ID: ${options.sourceId}`);
  }

  const chunks: string[] = [];

  try {
    const { data: readme } = await octokit.rest.repos.getReadme({ owner, repo });
    const readmeText = Buffer.from(readme.content, "base64").toString("utf8");
    chunks.push(`# ${readme.name}\n\n${readmeText}`);
  } catch {
    // README may be missing
  }

  await collectRepoMarkdown(octokit, owner, repo, "docs", 0, chunks);

  let repoData: any;
  try {
    const { data } = await octokit.rest.repos.get({ owner, repo });
    repoData = data;
  } catch {
    repoData = null;
  }

  const lastUpdated = repoData?.pushed_at ?? new Date().toISOString();

  return {
    sourceId: options.sourceId,
    content: chunks.join("\n\n"),
    metadata: {
      title: repoData?.full_name ?? options.sourceId,
      author: repoData?.owner?.login ?? owner,
      lastUpdated,
    },
  };
}
