import { z } from "zod";

export const modelConfigSchema = z.object({
  default: z.string().min(1, "Default model is required"),
  fallback: z.array(z.string()).optional(),
  temperature: z.number().min(0).max(2).optional(),
  max_tokens: z.number().int().positive().optional(),
  top_p: z.number().min(0).max(1).optional(),
  response_format: z.enum(["text", "json", "json_schema"]).optional(),
});

export const ttsConfigSchema = z.object({
  provider: z.enum(["elevenlabs", "openai", "google"]).default("elevenlabs"),
  voice_id: z.string().optional(),
  model_id: z.string().optional(),
  stability: z.number().min(0).max(1).optional(),
  similarity_boost: z.number().min(0).max(1).optional(),
  style: z.number().min(0).max(1).optional(),
  use_speaker_boost: z.boolean().optional(),
});

export const audioConfigSchema = z.object({
  target_duration_minutes: z.number().positive().optional(),
  binaural_frequency_hz: z.number().min(0).max(40).optional(),
  bpm: z.number().int().positive().optional(),
  key_signature: z.string().optional(),
  background_track: z.string().optional(),
  pause_marker_format: z.string().optional(),
});

export const modalityConfigSchema = z.object({
  input: z.enum(["text", "audio", "image", "video", "multimodal"]).default("text"),
  output: z.enum(["text", "audio", "image", "tts"]).default("text"),
});

export const frontMatterSchema = z.object({
  name: z
    .string()
    .regex(/^[a-z][a-z0-9_]*$/, "Must be lowercase snake_case"),
  domain: z.string().optional(),
  description: z.string().max(500).optional(),
  type: z.enum(["chat", "completion", "tts", "transcription", "image"]).default("chat"),
  role: z.enum(["system", "user", "assistant"]).default("system"),
  model: modelConfigSchema.optional(),
  tts: ttsConfigSchema.optional(),
  audio: audioConfigSchema.optional(),
  modality: modalityConfigSchema.optional(),
  environment: z.enum(["development", "staging", "production"]).default("development"),
  active: z.boolean().default(true),
  tags: z.array(z.string()).optional(),
});

export type FrontMatter = z.infer<typeof frontMatterSchema>;
export type TTSConfig = z.infer<typeof ttsConfigSchema>;
export type AudioConfig = z.infer<typeof audioConfigSchema>;
export type ModalityConfig = z.infer<typeof modalityConfigSchema>;
