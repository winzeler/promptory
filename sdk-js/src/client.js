import { LRUCache } from "./cache.js";
import {
  PromptdisError,
  NotFoundError,
  AuthenticationError,
  ForbiddenError,
  RateLimitError,
} from "./errors.js";
import { renderLocal } from "./models.js";

/**
 * @typedef {Object} PromptClientOptions
 * @property {string} baseUrl - Promptdis server URL
 * @property {string} apiKey - API key (pm_live_... or pm_test_...)
 * @property {number} [cacheMaxSize=100] - Maximum cache entries
 * @property {number} [cacheTtlMs=60000] - Cache TTL in milliseconds
 * @property {number} [maxRetries=3] - Max retry attempts on 429/5xx
 */

export class PromptClient {
  #baseUrl;
  #apiKey;
  #cache;
  #maxRetries;

  /** @param {PromptClientOptions} options */
  constructor(options) {
    this.#baseUrl = options.baseUrl.replace(/\/+$/, "");
    this.#apiKey = options.apiKey;
    this.#cache = new LRUCache(
      options.cacheMaxSize ?? 100,
      options.cacheTtlMs ?? 60_000
    );
    this.#maxRetries = options.maxRetries ?? 3;
  }

  /**
   * Fetch a prompt by UUID.
   * @param {string} promptId
   * @returns {Promise<import("./models.js").Prompt>}
   */
  async get(promptId) {
    const cacheKey = `id:${promptId}`;
    return this.#fetchWithCache(
      `/api/v1/prompts/${promptId}`,
      cacheKey
    );
  }

  /**
   * Fetch a prompt by fully qualified name (org/app/name).
   * @param {string} org
   * @param {string} app
   * @param {string} name
   * @param {string} [environment]
   * @returns {Promise<import("./models.js").Prompt>}
   */
  async getByName(org, app, name, environment) {
    const envSuffix = environment ? `?environment=${environment}` : "";
    const cacheKey = `name:${org}/${app}/${name}:${environment ?? "any"}`;
    return this.#fetchWithCache(
      `/api/v1/prompts/by-name/${org}/${app}/${name}${envSuffix}`,
      cacheKey
    );
  }

  /**
   * Render a prompt server-side with Jinja2 variables.
   * @param {string} promptId
   * @param {Object} variables
   * @returns {Promise<{ rendered_body: string, meta: Object }>}
   */
  async render(promptId, variables) {
    const resp = await this.#fetch(`/api/v1/prompts/${promptId}/render`, {
      method: "POST",
      body: JSON.stringify({ variables }),
    });
    return resp;
  }

  /**
   * Render locally with basic {{var}} substitution (no Jinja2 features).
   * @param {string} body
   * @param {Record<string, string>} variables
   * @returns {string}
   */
  renderLocal(body, variables) {
    return renderLocal(body, variables);
  }

  /** Return cache statistics. */
  cacheStats() {
    return this.#cache.stats();
  }

  /**
   * Invalidate a specific cache entry.
   * @param {string} key
   * @returns {boolean}
   */
  cacheInvalidate(key) {
    return this.#cache.invalidate(key);
  }

  /** Clear the entire cache. */
  cacheClear() {
    this.#cache.clear();
  }

  // ── Internal ──

  /**
   * @param {string} path
   * @param {string} cacheKey
   * @returns {Promise<import("./models.js").Prompt>}
   */
  async #fetchWithCache(path, cacheKey) {
    const cached = this.#cache.get(cacheKey);
    const headers = {};
    if (cached?.etag) {
      headers["If-None-Match"] = cached.etag;
    }

    try {
      const resp = await this.#fetchRaw(path, { headers });

      if (resp.status === 304 && cached) {
        return cached.value;
      }

      if (!resp.ok) {
        await this.#handleError(resp);
      }

      const data = await resp.json();
      const etag = resp.headers.get("etag");
      this.#cache.set(cacheKey, data, etag);
      return data;
    } catch (e) {
      // On network error, return cached if available
      if (cached && !(e instanceof PromptdisError)) {
        return cached.value;
      }
      throw e;
    }
  }

  /**
   * @param {string} path
   * @param {RequestInit} [init={}]
   * @returns {Promise<*>}
   */
  async #fetch(path, init = {}) {
    const resp = await this.#fetchRaw(path, init);
    if (!resp.ok) {
      await this.#handleError(resp);
    }
    return resp.json();
  }

  /**
   * @param {string} path
   * @param {RequestInit} [init={}]
   * @returns {Promise<Response>}
   */
  async #fetchRaw(path, init = {}) {
    const url = `${this.#baseUrl}${path}`;
    const headers = {
      Authorization: `Bearer ${this.#apiKey}`,
      "Content-Type": "application/json",
      ...(init.headers ?? {}),
    };

    let lastError = null;
    for (let attempt = 0; attempt <= this.#maxRetries; attempt++) {
      try {
        const resp = await fetch(url, { ...init, headers });

        // Retry on 429 or 5xx
        if (
          attempt < this.#maxRetries &&
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
        lastError = e;
        if (attempt < this.#maxRetries) {
          await new Promise((r) =>
            setTimeout(r, Math.min(1000 * 2 ** attempt, 10_000))
          );
        }
      }
    }

    throw new PromptdisError(
      `Request failed after ${this.#maxRetries + 1} attempts: ${lastError?.message}`
    );
  }

  /**
   * @param {Response} resp
   * @returns {Promise<never>}
   */
  async #handleError(resp) {
    const body = await resp.json().catch(() => ({}));
    const message = body?.error?.message ?? resp.statusText;

    switch (resp.status) {
      case 401:
        throw new AuthenticationError(message);
      case 403:
        throw new ForbiddenError(message);
      case 404:
        throw new NotFoundError(message);
      case 429:
        throw new RateLimitError(
          resp.headers.get("retry-after")
            ? parseInt(resp.headers.get("retry-after"), 10)
            : null
        );
      default:
        throw new PromptdisError(`${resp.status}: ${message}`);
    }
  }
}
