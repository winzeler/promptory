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
          value={String(value.type ?? "chat")}
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
