import { useState } from "react";
import { useParams, Link, useNavigate } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { App } from "../api/prompts";

export default function AppSettingsPage() {
  const { appId } = useParams<{ appId: string }>();
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false);

  const { data: app, isLoading } = useQuery({
    queryKey: ["app", appId],
    queryFn: () => apiFetch<App>(`/api/v1/admin/apps/${appId}`),
    enabled: !!appId,
  });

  const deleteMutation = useMutation({
    mutationFn: () => apiFetch(`/api/v1/admin/apps/${appId}`, { method: "DELETE" }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["apps"] });
      navigate("/");
    },
  });

  if (isLoading) return <div className="text-sm text-gray-500">Loading...</div>;
  if (!app) return <div className="text-sm text-red-500">App not found</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to={`/apps/${appId}/prompts`} className="text-sm text-gray-500 hover:text-gray-700">&larr; Prompts</Link>
        <h1 className="text-2xl font-bold text-gray-900">App Settings</h1>
      </div>

      <div className="max-w-lg space-y-6 rounded-lg border border-gray-200 bg-white p-6">
        <div>
          <label className="block text-sm font-medium text-gray-700">GitHub Repository</label>
          <p className="mt-1 font-mono text-sm text-gray-900">{app.github_repo}</p>
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Display Name</label>
          <input
            type="text"
            defaultValue={app.display_name ?? ""}
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Default Branch</label>
          <input
            type="text"
            defaultValue={app.default_branch}
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Subdirectory</label>
          <input
            type="text"
            defaultValue={app.subdirectory}
            placeholder="(root)"
            className="mt-1 w-full rounded border border-gray-300 px-3 py-2 text-sm"
          />
        </div>

        <div>
          <label className="block text-sm font-medium text-gray-700">Last Synced</label>
          <p className="mt-1 text-sm text-gray-500">
            {app.last_synced_at ? new Date(app.last_synced_at).toLocaleString() : "Never"}
          </p>
        </div>

        <div className="border-t border-gray-200 pt-4">
          <h3 className="text-sm font-medium text-gray-700">Webhook URL</h3>
          <p className="mt-1 font-mono text-xs text-gray-500 break-all">
            {window.location.origin}/api/v1/webhooks/github
          </p>
          <p className="mt-1 text-xs text-gray-400">
            Add this as a webhook in your GitHub repo settings. Select "push" events.
          </p>
        </div>

        <button className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800">
          Save Settings
        </button>
      </div>

      <div className="max-w-lg rounded-lg border border-red-200 bg-white p-6">
        <h2 className="text-lg font-semibold text-red-700">Remove App</h2>
        <p className="mt-1 text-sm text-gray-600">
          Stop managing prompts from <span className="font-mono">{app.github_repo}</span>. This removes
          the app and all indexed prompts from Promptdis. The GitHub repository is not affected.
        </p>

        {!showDeleteConfirm ? (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="mt-4 rounded border border-red-300 px-4 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
          >
            Remove App...
          </button>
        ) : (
          <div className="mt-4 flex items-center gap-3">
            <button
              onClick={() => deleteMutation.mutate()}
              disabled={deleteMutation.isPending}
              className="rounded bg-red-600 px-4 py-2 text-sm font-medium text-white hover:bg-red-700 disabled:opacity-50"
            >
              {deleteMutation.isPending ? "Removing..." : "Yes, remove this app"}
            </button>
            <button
              onClick={() => setShowDeleteConfirm(false)}
              className="text-sm text-gray-500 hover:text-gray-700"
            >
              Cancel
            </button>
          </div>
        )}

        {deleteMutation.isError && (
          <p className="mt-2 text-sm text-red-600">Failed to remove app. Please try again.</p>
        )}
      </div>
    </div>
  );
}
