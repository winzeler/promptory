import { describe, it, expect, vi, beforeEach } from "vitest";
import { PromptClient } from "../src/client.js";
import { NotFoundError, AuthenticationError, RateLimitError } from "../src/errors.js";
import { LRUCache } from "../src/cache.js";
import { renderLocal } from "../src/models.js";

// Mock fetch globally
const mockFetch = vi.fn();
vi.stubGlobal("fetch", mockFetch);

function jsonResponse(data: unknown, status = 200, headers: Record<string, string> = {}) {
  return new Response(JSON.stringify(data), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

describe("PromptClient", () => {
  let client: PromptClient;

  beforeEach(() => {
    vi.clearAllMocks();
    client = new PromptClient({
      baseUrl: "https://api.example.com",
      apiKey: "pm_live_test123",
      maxRetries: 0,
    });
  });

  it("should construct with required options", () => {
    expect(client).toBeDefined();
  });

  it("should send authorization header", async () => {
    mockFetch.mockResolvedValueOnce(jsonResponse({ id: "1", name: "test", body: "Hello" }));
    await client.get("prompt-1");
    expect(mockFetch).toHaveBeenCalledTimes(1);
    const [, init] = mockFetch.mock.calls[0];
    expect(init.headers.Authorization).toBe("Bearer pm_live_test123");
  });

  describe("get()", () => {
    it("should fetch prompt by ID", async () => {
      const prompt = { id: "p1", name: "greeting", body: "Hello {{name}}" };
      mockFetch.mockResolvedValueOnce(jsonResponse(prompt));

      const result = await client.get("p1");
      expect(result.id).toBe("p1");
      expect(result.name).toBe("greeting");
    });

    it("should throw NotFoundError on 404", async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse({ error: { message: "Not found" } }, 404));
      await expect(client.get("missing")).rejects.toThrow(NotFoundError);
    });

    it("should throw AuthenticationError on 401", async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse({ error: { message: "Bad token" } }, 401));
      await expect(client.get("p1")).rejects.toThrow(AuthenticationError);
    });

    it("should throw RateLimitError on 429", async () => {
      mockFetch.mockResolvedValueOnce(
        jsonResponse({ error: { message: "Rate limited" } }, 429)
      );
      await expect(client.get("p1")).rejects.toThrow(RateLimitError);
    });
  });

  describe("getByName()", () => {
    it("should fetch by fully qualified name", async () => {
      const prompt = { id: "p2", name: "greet", body: "Hi" };
      mockFetch.mockResolvedValueOnce(jsonResponse(prompt));

      const result = await client.getByName("myorg", "myapp", "greet");
      expect(result.name).toBe("greet");
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain("/by-name/myorg/myapp/greet");
    });

    it("should include environment query param", async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse({ id: "p3", name: "greet" }));
      await client.getByName("org", "app", "greet", "production");
      const [url] = mockFetch.mock.calls[0];
      expect(url).toContain("?environment=production");
    });
  });

  describe("cache", () => {
    it("should cache responses and return from cache", async () => {
      const prompt = { id: "p1", name: "cached" };
      mockFetch.mockResolvedValueOnce(jsonResponse(prompt, 200, { ETag: '"v1"' }));

      // First call — cache miss
      await client.get("p1");
      expect(mockFetch).toHaveBeenCalledTimes(1);

      // Second call — sends If-None-Match, server returns 304
      mockFetch.mockResolvedValueOnce(new Response(null, { status: 304 }));
      const result = await client.get("p1");
      expect(result.name).toBe("cached");
    });

    it("should report cache stats", async () => {
      const stats = client.cacheStats();
      expect(stats.size).toBe(0);
      expect(stats.maxSize).toBe(100);
    });

    it("should invalidate cache entry", async () => {
      mockFetch.mockResolvedValueOnce(jsonResponse({ id: "p1", name: "test" }));
      await client.get("p1");
      const removed = client.cacheInvalidate("id:p1");
      expect(removed).toBe(true);
    });
  });
});

describe("LRUCache", () => {
  it("should get and set values", () => {
    const cache = new LRUCache<string>(10, 60_000);
    cache.set("a", "hello");
    const result = cache.get("a");
    expect(result?.value).toBe("hello");
  });

  it("should evict oldest entry when full", () => {
    const cache = new LRUCache<string>(2, 60_000);
    cache.set("a", "1");
    cache.set("b", "2");
    cache.set("c", "3"); // Should evict "a"
    expect(cache.get("a")).toBeNull();
    expect(cache.get("b")?.value).toBe("2");
    expect(cache.get("c")?.value).toBe("3");
  });

  it("should expire entries by TTL", async () => {
    const cache = new LRUCache<string>(10, 50); // 50ms TTL
    cache.set("a", "hello");
    await new Promise((r) => setTimeout(r, 60));
    expect(cache.get("a")).toBeNull();
  });

  it("should clear all entries", () => {
    const cache = new LRUCache<string>(10, 60_000);
    cache.set("a", "1");
    cache.set("b", "2");
    cache.clear();
    expect(cache.size).toBe(0);
  });
});

describe("renderLocal", () => {
  it("should substitute simple variables", () => {
    expect(renderLocal("Hello {{name}}!", { name: "Alice" })).toBe("Hello Alice!");
  });

  it("should handle spaces in braces", () => {
    expect(renderLocal("{{ greeting }}", { greeting: "Hi" })).toBe("Hi");
  });

  it("should replace missing vars with empty string", () => {
    expect(renderLocal("Hello {{name}}!", {})).toBe("Hello !");
  });
});
