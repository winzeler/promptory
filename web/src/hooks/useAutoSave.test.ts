import { describe, it, expect, vi, beforeEach, afterEach } from "vitest";
import { loadDraft, clearDraft } from "./useAutoSave";

describe("loadDraft", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("returns null when no draft exists", () => {
    expect(loadDraft("nonexistent")).toBeNull();
  });

  it("returns parsed draft data", () => {
    const data = { name: "test", body: "Hello {{ name }}" };
    localStorage.setItem("promptdis_draft_test-key", JSON.stringify(data));
    expect(loadDraft("test-key")).toEqual(data);
  });

  it("returns null for invalid JSON", () => {
    localStorage.setItem("promptdis_draft_bad", "not-json{{{");
    expect(loadDraft("bad")).toBeNull();
  });
});

describe("clearDraft", () => {
  beforeEach(() => {
    localStorage.clear();
  });

  it("removes the draft from localStorage", () => {
    localStorage.setItem("promptdis_draft_my-key", '{"data":"value"}');
    clearDraft("my-key");
    expect(localStorage.getItem("promptdis_draft_my-key")).toBeNull();
  });

  it("does not throw when key does not exist", () => {
    expect(() => clearDraft("nonexistent")).not.toThrow();
  });
});
