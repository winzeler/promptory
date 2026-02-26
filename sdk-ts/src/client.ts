import { LRUCache } from "./cache.js";
import {
  PromptdisError,
  NotFoundError,
  AuthenticationError,
  RateLimitError,
} from "./errors.js";
import type { Prompt } from "./models.js";
import { renderLocal } from "./models.js";

export interface PromptClientOptions {
  baseUrl: string;
  apiKey: string;
  /** Maximum cache entries (default 100) */
  cacheMaxSize?: number;
  /** Cache TTL in milliseconds (default 60000) */
  cacheTtlMs?: number;
  /** Max retry attempts on 429/5xx (default 3) */
  maxRetries?: number;
}

export class PromptClient {
  private baseUrl: string;
  private apiKey: string;
  private cache: LRUCache<Prompt>;
  private maxRetries: number;

  constructor(options: PromptClientOptions) {
    this.baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.apiKey = options.apiKey;
    this.cache = new LRUCache(
      options.cacheMaxSize ?? 100,
      options.cacheTtlMs ?? 60_000
    );
    this.maxRetries = options.maxRetries ?? 3;
  }

  /** Fetch a prompt by UUID. */
  async get(promptId: string): Promise<Prompt> {
    const cacheKey = `id:${promptId}`;
    return this._fetchWithCache(
      `/api/v1/prompts/${promptId}`,
      cacheKey
    );
  }

  /** Fetch a prompt by fully qualified name (org/app/name). */
  async getByName(
    org: string,
    app: string,
    name: string,
    environment?: string
  ): Promise<Prompt> {
    const envSuffix = environment ? `?environment=${environment}` : "";
    const cacheKey = `name:${org}/${app}/${name}:${environment ?? "any"}`;
    return this._fetchWithCache(
      `/api/v1/prompts/by-name/${org}/${app}/${name}${envSuffix}`,
      cacheKey
    );
  }

  /** Render a prompt server-side with Jinja2 variables. */
  async render(
    promptId: string,
    variables: Record<string, unknown>
  ): Promise<{ rendered_body: string; meta: Record<string, unknown> }> {
    const resp = await this._fetch(`/api/v1/prompts/${promptId}/render`, {
      method: "POST",
      body: JSON.stringify({ variables }),
    });
    return resp as { rendered_body: string; meta: Record<string, unknown> };
  }

  /** Render locally with basic {{var}} substitution (no Jinja2 features). */
  renderLocal(body: string, variables: Record<string, string>): string {
    return renderLocal(body, variables);
  }

  /** Return cache statistics. */
  cacheStats() {
    return this.cache.stats();
  }

  /** Invalidate a specific cache entry. */
  cacheInvalidate(key: string): boolean {
    return this.cache.invalidate(key);
  }

  /** Clear the entire cache. */
  cacheClear(): void {
    this.cache.clear();
  }

  // ── Internal ──

  private async _fetchWithCache(
    path: string,
    cacheKey: string
  ): Promise<Prompt> {
    const cached = this.cache.get(cacheKey);
    const headers: Record<string, string> = {};
    if (cached?.etag) {
      headers["If-None-Match"] = cached.etag;
    }

    try {
      const resp = await this._fetchRaw(path, { headers });

      if (resp.status === 304 && cached) {
        return cached.value;
      }

      if (!resp.ok) {
        await this._handleError(resp);
      }

      const data: Prompt = await resp.json();
      const etag = resp.headers.get("etag");
      this.cache.set(cacheKey, data, etag);
      return data;
    } catch (e) {
      // On network error, return cached if available
      if (cached && !(e instanceof PromptdisError)) {
        return cached.value;
      }
      throw e;
    }
  }

  private async _fetch(
    path: string,
    init: RequestInit = {}
  ): Promise<unknown> {
    const resp = await this._fetchRaw(path, init);
    if (!resp.ok) {
      await this._handleError(resp);
    }
    return resp.json();
  }

  private async _fetchRaw(
    path: string,
    init: RequestInit = {}
  ): Promise<Response> {
    const url = `${this.baseUrl}${path}`;
    const headers: Record<string, string> = {
      Authorization: `Bearer ${this.apiKey}`,
      "Content-Type": "application/json",
      ...(init.headers as Record<string, string> ?? {}),
    };

    let lastError: Error | null = null;
    for (let attempt = 0; attempt <= this.maxRetries; attempt++) {
      try {
        const resp = await fetch(url, { ...init, headers });

        // Retry on 429 or 5xx
        if (
          attempt < this.maxRetries &&
          (resp.status === 429 || resp.status >= 500)
        ) {
          const retryAfter = resp.headers.get("retry-after");
          const delayMs = retryAfter
            ? parseInt(retryAfter, 10) * 1000
            : Math.min(1000 * 2 ** attempt, 10_000);
          await new Promise((r) => setTimeout(r, delayMs));
          continue;
        }

        return resp;
      } catch (e) {
        lastError = e as Error;
        if (attempt < this.maxRetries) {
          await new Promise((r) =>
            setTimeout(r, Math.min(1000 * 2 ** attempt, 10_000))
          );
        }
      }
    }

    throw new PromptdisError(
      `Request failed after ${this.maxRetries + 1} attempts: ${lastError?.message}`
    );
  }

  private async _handleError(resp: Response): Promise<never> {
    const body = await resp.json().catch(() => ({}));
    const message =
      (body as Record<string, Record<string, string>>)?.error?.message ??
      resp.statusText;

    switch (resp.status) {
      case 401:
        throw new AuthenticationError(message);
      case 404:
        throw new NotFoundError(message);
      case 429:
        throw new RateLimitError(
          resp.headers.get("retry-after")
            ? parseInt(resp.headers.get("retry-after")!, 10)
            : null
        );
      default:
        throw new PromptdisError(`${resp.status}: ${message}`);
    }
  }
}
