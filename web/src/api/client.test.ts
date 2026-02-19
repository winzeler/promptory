import { describe, it, expect, vi, beforeEach } from "vitest";
import { apiFetch, ApiError } from "./client";

describe("apiFetch", () => {
  beforeEach(() => {
    vi.restoreAllMocks();
  });

  it("makes a GET request and returns JSON", async () => {
    const mockData = { items: [{ id: "1", name: "test" }] };
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve(mockData),
      }),
    );

    const result = await apiFetch("/api/v1/admin/prompts");
    expect(result).toEqual(mockData);
    expect(fetch).toHaveBeenCalledOnce();
  });

  it("includes credentials and content-type header", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      }),
    );

    await apiFetch("/api/v1/admin/orgs");
    const [url, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(options.credentials).toBe("include");
    expect(options.headers["Content-Type"]).toBe("application/json");
  });

  it("throws ApiError on 404", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 404,
        statusText: "Not Found",
        json: () =>
          Promise.resolve({
            error: { code: "NOT_FOUND", message: "Prompt not found" },
          }),
      }),
    );

    await expect(apiFetch("/api/v1/prompts/bad-id")).rejects.toThrow(ApiError);
    try {
      await apiFetch("/api/v1/prompts/bad-id");
    } catch (e) {
      expect(e).toBeInstanceOf(ApiError);
      expect((e as ApiError).status).toBe(404);
      expect((e as ApiError).code).toBe("NOT_FOUND");
    }
  });

  it("throws ApiError on 401", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 401,
        statusText: "Unauthorized",
        json: () =>
          Promise.resolve({
            error: { code: "UNAUTHORIZED", message: "Authentication required" },
          }),
      }),
    );

    await expect(apiFetch("/api/v1/admin/orgs")).rejects.toThrow(ApiError);
  });

  it("handles 204 No Content", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 204,
        json: () => Promise.resolve(undefined),
      }),
    );

    const result = await apiFetch("/api/v1/admin/something");
    expect(result).toBeUndefined();
  });

  it("handles server error with non-JSON body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: false,
        status: 500,
        statusText: "Internal Server Error",
        json: () => Promise.reject(new Error("not json")),
      }),
    );

    await expect(apiFetch("/api/v1/health")).rejects.toThrow(ApiError);
  });

  it("passes custom headers", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({}),
      }),
    );

    await apiFetch("/api/v1/prompts/123", {
      headers: { Authorization: "Bearer test-key" },
    });

    const [, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(options.headers.Authorization).toBe("Bearer test-key");
  });

  it("sends POST with JSON body", async () => {
    vi.stubGlobal(
      "fetch",
      vi.fn().mockResolvedValue({
        ok: true,
        status: 200,
        json: () => Promise.resolve({ ok: true }),
      }),
    );

    await apiFetch("/api/v1/admin/prompts", {
      method: "POST",
      body: JSON.stringify({ name: "test" }),
    });

    const [, options] = (fetch as ReturnType<typeof vi.fn>).mock.calls[0];
    expect(options.method).toBe("POST");
    expect(options.body).toBe('{"name":"test"}');
  });
});
