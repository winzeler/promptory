import { describe, it, expect } from "vitest";
import {
  frontMatterSchema,
  modelConfigSchema,
  ttsConfigSchema,
  audioConfigSchema,
  modalityConfigSchema,
} from "./schema";

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

  it("accepts optional tts config", () => {
    const result = frontMatterSchema.safeParse({
      name: "test",
      type: "tts",
      tts: { provider: "elevenlabs", stability: 0.5 },
    });
    expect(result.success).toBe(true);
  });

  it("accepts optional audio config", () => {
    const result = frontMatterSchema.safeParse({
      name: "test",
      audio: { target_duration_minutes: 10, bpm: 60 },
    });
    expect(result.success).toBe(true);
  });

  it("accepts optional modality config", () => {
    const result = frontMatterSchema.safeParse({
      name: "test",
      modality: { input: "text", output: "tts" },
    });
    expect(result.success).toBe(true);
  });
});

describe("ttsConfigSchema", () => {
  it("accepts valid TTS config", () => {
    const result = ttsConfigSchema.safeParse({
      provider: "elevenlabs",
      voice_id: "abc123",
      stability: 0.5,
      similarity_boost: 0.75,
      style: 0.1,
      use_speaker_boost: true,
    });
    expect(result.success).toBe(true);
  });

  it("applies default provider", () => {
    const result = ttsConfigSchema.parse({});
    expect(result.provider).toBe("elevenlabs");
  });

  it("rejects invalid provider", () => {
    const result = ttsConfigSchema.safeParse({ provider: "azure" });
    expect(result.success).toBe(false);
  });

  it("rejects stability out of range", () => {
    const result = ttsConfigSchema.safeParse({ stability: 1.5 });
    expect(result.success).toBe(false);
  });

  it("rejects negative similarity_boost", () => {
    const result = ttsConfigSchema.safeParse({ similarity_boost: -0.1 });
    expect(result.success).toBe(false);
  });

  it("rejects style over 1", () => {
    const result = ttsConfigSchema.safeParse({ style: 2.0 });
    expect(result.success).toBe(false);
  });
});

describe("audioConfigSchema", () => {
  it("accepts valid audio config", () => {
    const result = audioConfigSchema.safeParse({
      target_duration_minutes: 10,
      binaural_frequency_hz: 5.0,
      bpm: 60,
      key_signature: "C Minor",
    });
    expect(result.success).toBe(true);
  });

  it("rejects negative duration", () => {
    const result = audioConfigSchema.safeParse({ target_duration_minutes: -5 });
    expect(result.success).toBe(false);
  });

  it("rejects binaural frequency over 40", () => {
    const result = audioConfigSchema.safeParse({ binaural_frequency_hz: 50 });
    expect(result.success).toBe(false);
  });

  it("rejects negative bpm", () => {
    const result = audioConfigSchema.safeParse({ bpm: -10 });
    expect(result.success).toBe(false);
  });

  it("rejects non-integer bpm", () => {
    const result = audioConfigSchema.safeParse({ bpm: 3.5 });
    expect(result.success).toBe(false);
  });
});

describe("modalityConfigSchema", () => {
  it("accepts valid modality config", () => {
    const result = modalityConfigSchema.safeParse({
      input: "text",
      output: "tts",
    });
    expect(result.success).toBe(true);
  });

  it("applies defaults", () => {
    const result = modalityConfigSchema.parse({});
    expect(result.input).toBe("text");
    expect(result.output).toBe("text");
  });

  it("rejects invalid input modality", () => {
    const result = modalityConfigSchema.safeParse({ input: "smell" });
    expect(result.success).toBe(false);
  });

  it("rejects invalid output modality", () => {
    const result = modalityConfigSchema.safeParse({ output: "hologram" });
    expect(result.success).toBe(false);
  });

  it("accepts all valid input types", () => {
    const inputs = ["text", "audio", "image", "video", "multimodal"];
    for (const inp of inputs) {
      const result = modalityConfigSchema.safeParse({ input: inp });
      expect(result.success).toBe(true);
    }
  });

  it("accepts all valid output types", () => {
    const outputs = ["text", "audio", "image", "tts"];
    for (const out of outputs) {
      const result = modalityConfigSchema.safeParse({ output: out });
      expect(result.success).toBe(true);
    }
  });
});
