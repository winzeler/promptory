import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";

interface ApiKey {
  id: string;
  key_prefix: string;
  name: string;
  scopes: Record<string, unknown> | null;
  expires_at: string | null;
  last_used_at: string | null;
  created_at: string;
}

export default function ApiKeysPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["api-keys"],
    queryFn: () => apiFetch<{ items: ApiKey[] }>("/api/v1/admin/api-keys"),
  });

  const [newKeyName, setNewKeyName] = useState("");
  const [createdKey, setCreatedKey] = useState<string | null>(null);

  const createMutation = useMutation({
    mutationFn: (name: string) =>
      apiFetch<{ key: string }>("/api/v1/admin/api-keys", {
        method: "POST",
        body: JSON.stringify({ name }),
      }),
    onSuccess: (data) => {
      setCreatedKey(data.key);
      setNewKeyName("");
      qc.invalidateQueries({ queryKey: ["api-keys"] });
    },
  });

  const revokeMutation = useMutation({
    mutationFn: (keyId: string) =>
      apiFetch(`/api/v1/admin/api-keys/${keyId}`, { method: "DELETE" }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["api-keys"] }),
  });

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold text-gray-900">API Keys</h1>

      {/* Create key */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-gray-700">Generate New Key</h2>
        <div className="mt-2 flex items-center gap-2">
          <input
            type="text"
            value={newKeyName}
            onChange={(e) => setNewKeyName(e.target.value)}
            placeholder="Key name (e.g., Production SDK)"
            className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <button
            onClick={() => newKeyName && createMutation.mutate(newKeyName)}
            disabled={!newKeyName || createMutation.isPending}
            className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            Generate
          </button>
        </div>

        {createdKey && (
          <div className="mt-3 rounded border border-yellow-200 bg-yellow-50 p-3">
            <p className="text-xs font-medium text-yellow-800">
              Copy this key now - it won't be shown again:
            </p>
            <code className="mt-1 block break-all text-sm font-mono text-yellow-900">
              {createdKey}
            </code>
            <button
              onClick={() => {
                navigator.clipboard.writeText(createdKey);
              }}
              className="mt-2 text-xs text-yellow-700 underline hover:no-underline"
            >
              Copy to clipboard
            </button>
          </div>
        )}
      </div>

      {/* Key list */}
      <div>
        <h2 className="text-sm font-semibold text-gray-700">Active Keys</h2>
        {isLoading ? (
          <p className="mt-2 text-sm text-gray-500">Loading...</p>
        ) : !data?.items.length ? (
          <p className="mt-2 text-sm text-gray-500">No API keys. Generate one above.</p>
        ) : (
          <table className="mt-2 w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
                <th className="py-2">Name</th>
                <th className="py-2">Prefix</th>
                <th className="py-2">Last Used</th>
                <th className="py-2">Created</th>
                <th className="py-2" />
              </tr>
            </thead>
            <tbody>
              {data.items.map((key) => (
                <tr key={key.id} className="border-b border-gray-100">
                  <td className="py-2 font-medium">{key.name}</td>
                  <td className="py-2 font-mono text-gray-500">{key.key_prefix}...</td>
                  <td className="py-2 text-gray-500">
                    {key.last_used_at ? new Date(key.last_used_at).toLocaleDateString() : "Never"}
                  </td>
                  <td className="py-2 text-gray-500">
                    {new Date(key.created_at).toLocaleDateString()}
                  </td>
                  <td className="py-2 text-right">
                    <button
                      onClick={() => revokeMutation.mutate(key.id)}
                      className="text-xs text-red-600 hover:text-red-800"
                    >
                      Revoke
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
