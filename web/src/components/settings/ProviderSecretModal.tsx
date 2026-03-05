import { useState } from "react";

interface Props {
  provider: string;
  scope: "app" | "user";
  onClose: () => void;
  onSave: (data: { secrets: Record<string, string>; config?: Record<string, string>; environment?: string }) => void;
  isSaving: boolean;
}

const ENVIRONMENTS = [
  { value: "", label: "All Environments" },
  { value: "development", label: "Development" },
  { value: "staging", label: "Staging" },
  { value: "production", label: "Production" },
];

export default function ProviderSecretModal({
  provider,
  scope,
  onClose,
  onSave,
  isSaving,
}: Props) {
  const [apiKey, setApiKey] = useState("");
  const [environment, setEnvironment] = useState("");

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!apiKey.trim()) return;
    onSave({
      secrets: { api_key: apiKey.trim() },
      environment: environment || undefined,
    });
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50">
      <div className="w-full max-w-md rounded-lg bg-white p-6 shadow-xl">
        <h3 className="text-lg font-semibold text-gray-900 capitalize">
          Configure {provider}
        </h3>
        <p className="mt-1 text-sm text-gray-500">
          {scope === "app" ? "App-level" : "Personal"} API key for {provider}.
          Encrypted at rest, never synced to GitHub.
        </p>

        <form onSubmit={handleSubmit} className="mt-4 space-y-4">
          <div>
            <label className="block text-sm font-medium text-gray-700">
              Environment
            </label>
            <select
              value={environment}
              onChange={(e) => setEnvironment(e.target.value)}
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
            >
              {ENVIRONMENTS.map((env) => (
                <option key={env.value} value={env.value}>
                  {env.label}
                </option>
              ))}
            </select>
          </div>

          <div>
            <label className="block text-sm font-medium text-gray-700">
              API Key
            </label>
            <input
              type="password"
              value={apiKey}
              onChange={(e) => setApiKey(e.target.value)}
              placeholder="sk-..."
              autoComplete="off"
              className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm font-mono"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="rounded border border-gray-300 px-4 py-2 text-sm font-medium text-gray-700 hover:bg-gray-50"
            >
              Cancel
            </button>
            <button
              type="submit"
              disabled={!apiKey.trim() || isSaving}
              className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
            >
              {isSaving ? "Saving..." : "Save"}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
