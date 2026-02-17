import { z } from "zod";

export const modelConfigSchema = z.object({
  default: z.string().min(1, "Default model is required"),
  fallback: z.array(z.string()).optional(),
  temperature: z.number().min(0).max(2).optional(),
  max_tokens: z.number().int().positive().optional(),
  top_p: z.number().min(0).max(1).optional(),
  response_format: z.enum(["text", "json", "json_schema"]).optional(),
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
  environment: z.enum(["development", "staging", "production"]).default("development"),
  active: z.boolean().default(true),
  tags: z.array(z.string()).optional(),
});

export type FrontMatter = z.infer<typeof frontMatterSchema>;
