export type SourceType = "github" | "local" | "npm" | "pypi" | "web";

export interface SourceResult {
  id: string;
  type: SourceType;
  url: string;
  description: string;
  relevanceScore: number;
}

export interface DocsContent {
  sourceId: string;
  content: string;
  metadata: {
    title?: string;
    author?: string;
    lastUpdated?: string;
  };
}

export interface SearchOptions {
  query: string;
  sourceType?: SourceType;
  maxResults?: number;
}

export interface FetchOptions {
  sourceId: string;
  topic?: string;
  tokenLimit?: number;
}
