import { describe, it, expect } from "vitest";
import { frontMatterSchema, modelConfigSchema } from "./schema";

describe("modelConfigSchema", () => {
  it("accepts valid model config", () => {
    const result = modelConfigSchema.safeParse({
      default: "gemini-2.0-flash",
      temperature: 0.7,
      max_tokens: 1000,
    });
    expect(result.success).toBe(true);
  });

  it("rejects empty default model", () => {
    const result = modelConfigSchema.safeParse({ default: "" });
    expect(result.success).toBe(false);
  });

  it("rejects temperature out of range", () => {
    const result = modelConfigSchema.safeParse({
      default: "gpt-4o",
      temperature: 3,
    });
    expect(result.success).toBe(false);
  });

  it("rejects negative max_tokens", () => {
    const result = modelConfigSchema.safeParse({
      default: "gpt-4o",
      max_tokens: -1,
    });
    expect(result.success).toBe(false);
  });

  it("accepts top_p within bounds", () => {
    const result = modelConfigSchema.safeParse({
      default: "gpt-4o",
      top_p: 0.95,
    });
    expect(result.success).toBe(true);
  });

  it("accepts fallback model list", () => {
    const result = modelConfigSchema.safeParse({
      default: "gpt-4o",
      fallback: ["gpt-4o-mini", "gemini-2.0-flash"],
    });
    expect(result.success).toBe(true);
  });
});

describe("frontMatterSchema", () => {
  it("accepts valid front matter", () => {
    const result = frontMatterSchema.safeParse({
      name: "greeting_prompt",
      domain: "messaging",
      type: "chat",
      role: "system",
      environment: "production",
      active: true,
      tags: ["greeting", "onboarding"],
    });
    expect(result.success).toBe(true);
  });

  it("enforces snake_case for name", () => {
    const result = frontMatterSchema.safeParse({
      name: "GreetingPrompt",
    });
    expect(result.success).toBe(false);
  });

  it("rejects name starting with number", () => {
    const result = frontMatterSchema.safeParse({
      name: "1invalid",
    });
    expect(result.success).toBe(false);
  });

  it("allows underscores in name", () => {
    const result = frontMatterSchema.safeParse({
      name: "my_prompt_v2",
    });
    expect(result.success).toBe(true);
  });

  it("applies defaults for type, role, environment", () => {
    const result = frontMatterSchema.parse({
      name: "test_prompt",
    });
    expect(result.type).toBe("chat");
    expect(result.role).toBe("system");
    expect(result.environment).toBe("development");
    expect(result.active).toBe(true);
  });

  it("rejects invalid type", () => {
    const result = frontMatterSchema.safeParse({
      name: "test",
      type: "invalid_type",
    });
    expect(result.success).toBe(false);
  });

  it("rejects invalid role", () => {
    const result = frontMatterSchema.safeParse({
      name: "test",
      role: "invalid_role",
    });
    expect(result.success).toBe(false);
  });

  it("rejects description over 500 chars", () => {
    const result = frontMatterSchema.safeParse({
      name: "test",
      description: "x".repeat(501),
    });
    expect(result.success).toBe(false);
  });

  it("accepts valid prompt types", () => {
    const types = ["chat", "completion", "tts", "transcription", "image"];
    for (const t of types) {
      const result = frontMatterSchema.safeParse({ name: "test", type: t });
      expect(result.success).toBe(true);
    }
  });

  it("accepts optional model config", () => {
    const result = frontMatterSchema.safeParse({
      name: "test",
      model: {
        default: "gemini-2.0-flash",
        temperature: 0.5,
      },
    });
    expect(result.success).toBe(true);
  });
});
