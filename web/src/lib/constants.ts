export const PROMPT_TYPES = ["chat", "completion", "tts", "transcription", "image"] as const;
export const ENVIRONMENTS = ["development", "staging", "production"] as const;
export const ROLES = ["system", "user", "assistant"] as const;
export const MODALITY_INPUTS = ["text", "audio", "image", "video", "multimodal"] as const;
export const MODALITY_OUTPUTS = ["text", "audio", "image", "tts"] as const;
