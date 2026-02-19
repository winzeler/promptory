import { useState } from "react";

interface Props {
  value: Record<string, unknown>;
  onChange: (value: Record<string, unknown>) => void;
}

export default function FrontMatterForm({ value, onChange }: Props) {
  const update = (key: string, val: unknown) => {
    onChange({ ...value, [key] : val });
  };

  const model = (value.model ?? {}) as Record<string, unknown>;
  const updateModel = (key: string, val: unknown) => {
    onChange({ ...value, model: { ...model, [key]: val } });
  };

  const modality = (value.modality ?? {}) as Record<string, string>;
  const updateModality = (key: string, val: string) => {
    onChange({ ...value, modality: { ...modality, [key]: val } });
  };

  const tts = (value.tts ?? {}) as Record<string, unknown>;
  const updateTts = (key: string, val: unknown) => {
    onChange({ ...value, tts: { ...tts, [key]: val } });
  };

  const audio = (value.audio ?? {}) as Record<string, unknown>;
  const updateAudio = (key: string, val: unknown) => {
    onChange({ ...value, audio: { ...audio, [key]: val } });
  };

  const currentType = String(value.type ?? "chat");
  const modalityOutput = String(modality.output ?? "text");
  const showTts = currentType === "tts" || modalityOutput === "tts";
  const showAudio = currentType === "tts";

  const [ttsOpen, setTtsOpen] = useState(showTts);
  const [audioOpen, setAudioOpen] = useState(showAudio);

  return (
    <div className="space-y-4 text-sm">
      <h3 className="font-semibold text-gray-900">Front Matter</h3>

      {/* Name */}
      <div>
        <label className="block text-xs font-medium text-gray-500">Name</label>
        <input
          type="text"
          value={String(value.name ?? "")}
          onChange={(e) => update("name", e.target.value)}
          className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 font-mono text-sm"
        />
      </div>

      {/* Domain */}
      <div>
        <label className="block text-xs font-medium text-gray-500">Domain</label>
        <input
          type="text"
          value={String(value.domain ?? "")}
          onChange={(e) => update("domain", e.target.value)}
          className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
        />
      </div>

      {/* Description */}
      <div>
        <label className="block text-xs font-medium text-gray-500">Description</label>
        <textarea
          value={String(value.description ?? "")}
          onChange={(e) => update("description", e.target.value)}
          rows={2}
          className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
        />
      </div>

      {/* Type */}
      <div>
        <label className="block text-xs font-medium text-gray-500">Type</label>
        <select
          value={currentType}
          onChange={(e) => update("type", e.target.value)}
          className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
        >
          <option value="chat">Chat</option>
          <option value="completion">Completion</option>
          <option value="tts">TTS</option>
          <option value="transcription">Transcription</option>
          <option value="image">Image</option>
        </select>
      </div>

      {/* Role */}
      <div>
        <label className="block text-xs font-medium text-gray-500">Role</label>
        <select
          value={String(value.role ?? "system")}
          onChange={(e) => update("role", e.target.value)}
          className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
        >
          <option value="system">System</option>
          <option value="user">User</option>
          <option value="assistant">Assistant</option>
        </select>
      </div>

      {/* Modality */}
      <div className="space-y-2 rounded border border-gray-200 p-3">
        <h4 className="text-xs font-semibold text-gray-700">Modality</h4>
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="block text-xs text-gray-500">Input</label>
            <select
              value={String(modality.input ?? "text")}
              onChange={(e) => updateModality("input", e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            >
              <option value="text">Text</option>
              <option value="audio">Audio</option>
              <option value="image">Image</option>
              <option value="video">Video</option>
              <option value="multimodal">Multimodal</option>
            </select>
          </div>
          <div className="flex-1">
            <label className="block text-xs text-gray-500">Output</label>
            <select
              value={modalityOutput}
              onChange={(e) => updateModality("output", e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            >
              <option value="text">Text</option>
              <option value="audio">Audio</option>
              <option value="image">Image</option>
              <option value="tts">TTS</option>
            </select>
          </div>
        </div>
      </div>

      {/* Model */}
      <div className="space-y-2 rounded border border-gray-200 p-3">
        <h4 className="text-xs font-semibold text-gray-700">Model</h4>
        <div>
          <label className="block text-xs text-gray-500">Default Model</label>
          <input
            type="text"
            value={String(model.default ?? "")}
            onChange={(e) => updateModel("default", e.target.value)}
            className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
          />
        </div>
        <div className="flex gap-2">
          <div className="flex-1">
            <label className="block text-xs text-gray-500">Temperature</label>
            <input
              type="number"
              step="0.1"
              min="0"
              max="2"
              value={Number(model.temperature ?? 0.7)}
              onChange={(e) => updateModel("temperature", parseFloat(e.target.value))}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </div>
          <div className="flex-1">
            <label className="block text-xs text-gray-500">Max Tokens</label>
            <input
              type="number"
              min="1"
              value={Number(model.max_tokens ?? 4000)}
              onChange={(e) => updateModel("max_tokens", parseInt(e.target.value))}
              className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
            />
          </div>
        </div>
      </div>

      {/* TTS Config (collapsible) */}
      {showTts && (
        <div className="rounded border border-purple-200 p-3">
          <button
            type="button"
            onClick={() => setTtsOpen(!ttsOpen)}
            className="flex w-full items-center justify-between text-xs font-semibold text-purple-700"
          >
            <span>TTS Config</span>
            <span>{ttsOpen ? "\u25B2" : "\u25BC"}</span>
          </button>
          {ttsOpen && (
            <div className="mt-3 space-y-2">
              <div>
                <label className="block text-xs text-gray-500">Provider</label>
                <select
                  value={String(tts.provider ?? "elevenlabs")}
                  onChange={(e) => updateTts("provider", e.target.value)}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                >
                  <option value="elevenlabs">ElevenLabs</option>
                  <option value="openai">OpenAI</option>
                  <option value="google">Google</option>
                </select>
              </div>
              <div>
                <label className="block text-xs text-gray-500">Voice ID</label>
                <input
                  type="text"
                  value={String(tts.voice_id ?? "")}
                  onChange={(e) => updateTts("voice_id", e.target.value)}
                  placeholder='e.g. abc123 or {{ user.voice_id }}'
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 font-mono text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">Model ID</label>
                <input
                  type="text"
                  value={String(tts.model_id ?? "eleven_multilingual_v2")}
                  onChange={(e) => updateTts("model_id", e.target.value)}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">
                  Stability: {Number(tts.stability ?? 0.5).toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={Number(tts.stability ?? 0.5)}
                  onChange={(e) => updateTts("stability", parseFloat(e.target.value))}
                  className="mt-1 w-full"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">
                  Similarity Boost: {Number(tts.similarity_boost ?? 0.75).toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={Number(tts.similarity_boost ?? 0.75)}
                  onChange={(e) => updateTts("similarity_boost", parseFloat(e.target.value))}
                  className="mt-1 w-full"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">
                  Style: {Number(tts.style ?? 0).toFixed(2)}
                </label>
                <input
                  type="range"
                  min="0"
                  max="1"
                  step="0.05"
                  value={Number(tts.style ?? 0)}
                  onChange={(e) => updateTts("style", parseFloat(e.target.value))}
                  className="mt-1 w-full"
                />
              </div>
              <div className="flex items-center gap-2">
                <input
                  type="checkbox"
                  checked={Boolean(tts.use_speaker_boost ?? true)}
                  onChange={(e) => updateTts("use_speaker_boost", e.target.checked)}
                  className="rounded"
                />
                <label className="text-xs text-gray-500">Speaker Boost</label>
              </div>
            </div>
          )}
        </div>
      )}

      {/* Audio Config (collapsible) */}
      {showAudio && (
        <div className="rounded border border-teal-200 p-3">
          <button
            type="button"
            onClick={() => setAudioOpen(!audioOpen)}
            className="flex w-full items-center justify-between text-xs font-semibold text-teal-700"
          >
            <span>Audio Config</span>
            <span>{audioOpen ? "\u25B2" : "\u25BC"}</span>
          </button>
          {audioOpen && (
            <div className="mt-3 space-y-2">
              <div>
                <label className="block text-xs text-gray-500">Target Duration (min)</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={Number(audio.target_duration_minutes ?? 10)}
                  onChange={(e) => updateAudio("target_duration_minutes", parseFloat(e.target.value))}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">Binaural Frequency (Hz, 0–40)</label>
                <input
                  type="number"
                  min="0"
                  max="40"
                  step="0.5"
                  value={Number(audio.binaural_frequency_hz ?? 5)}
                  onChange={(e) => updateAudio("binaural_frequency_hz", parseFloat(e.target.value))}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">BPM</label>
                <input
                  type="number"
                  min="1"
                  step="1"
                  value={Number(audio.bpm ?? 50)}
                  onChange={(e) => updateAudio("bpm", parseInt(e.target.value))}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">Key Signature</label>
                <input
                  type="text"
                  value={String(audio.key_signature ?? "")}
                  onChange={(e) => updateAudio("key_signature", e.target.value)}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">Background Track</label>
                <input
                  type="text"
                  value={String(audio.background_track ?? "")}
                  onChange={(e) => updateAudio("background_track", e.target.value)}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
                />
              </div>
              <div>
                <label className="block text-xs text-gray-500">Pause Marker Format</label>
                <input
                  type="text"
                  value={String(audio.pause_marker_format ?? "[PAUSE:3s]")}
                  onChange={(e) => updateAudio("pause_marker_format", e.target.value)}
                  className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 font-mono text-sm"
                />
              </div>
            </div>
          )}
        </div>
      )}

      {/* Tags */}
      <div>
        <label className="block text-xs font-medium text-gray-500">Tags (comma-separated)</label>
        <input
          type="text"
          value={Array.isArray(value.tags) ? (value.tags as string[]).join(", ") : ""}
          onChange={(e) =>
            update(
              "tags",
              e.target.value.split(",").map((t) => t.trim()).filter(Boolean)
            )
          }
          className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
        />
      </div>

      {/* Environment */}
      <div>
        <label className="block text-xs font-medium text-gray-500">Environment</label>
        <select
          value={String(value.environment ?? "development")}
          onChange={(e) => update("environment", e.target.value)}
          className="mt-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
        >
          <option value="development">Development</option>
          <option value="staging">Staging</option>
          <option value="production">Production</option>
        </select>
      </div>

      {/* Active */}
      <div className="flex items-center gap-2">
        <input
          type="checkbox"
          checked={Boolean(value.active ?? true)}
          onChange={(e) => update("active", e.target.checked)}
          className="rounded"
        />
        <label className="text-xs font-medium text-gray-500">Active</label>
      </div>
    </div>
  );
}
