import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import { syncAll } from "../api/prompts";

interface SyncItem {
  id: string;
  github_repo: string;
  display_name: string | null;
  last_synced_at: string | null;
}

export default function SyncStatusPage() {
  const qc = useQueryClient();
  const { data, isLoading } = useQuery({
    queryKey: ["sync-status"],
    queryFn: () => apiFetch<{ items: SyncItem[]; cache_size: number }>("/api/v1/admin/sync/status"),
  });

  const syncMutation = useMutation({
    mutationFn: syncAll,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["sync-status"] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold text-gray-900">Sync Status</h1>
        <button
          onClick={() => syncMutation.mutate()}
          disabled={syncMutation.isPending}
          className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
        >
          {syncMutation.isPending ? "Syncing..." : "Sync All"}
        </button>
      </div>

      {syncMutation.isSuccess && (
        <div className="rounded border border-green-200 bg-green-50 p-3 text-sm text-green-700">
          Synced {(syncMutation.data as { synced: number }).synced} prompts.
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-xs font-medium text-gray-500">Applications</div>
          <div className="mt-1 text-xl font-semibold">{data?.items.length ?? 0}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-4">
          <div className="text-xs font-medium text-gray-500">Cache Size</div>
          <div className="mt-1 text-xl font-semibold">{data?.cache_size ?? 0}</div>
        </div>
      </div>

      {/* App sync table */}
      {isLoading ? (
        <p className="text-sm text-gray-500">Loading...</p>
      ) : !data?.items.length ? (
        <p className="text-sm text-gray-500">No applications connected.</p>
      ) : (
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
              <th className="py-2">Application</th>
              <th className="py-2">Repository</th>
              <th className="py-2">Last Synced</th>
              <th className="py-2">Status</th>
            </tr>
          </thead>
          <tbody>
            {data.items.map((item) => (
              <tr key={item.id} className="border-b border-gray-100">
                <td className="py-2 font-medium">{item.display_name || item.github_repo}</td>
                <td className="py-2 font-mono text-gray-500">{item.github_repo}</td>
                <td className="py-2 text-gray-500">
                  {item.last_synced_at
                    ? new Date(item.last_synced_at).toLocaleString()
                    : "Never"}
                </td>
                <td className="py-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs ${
                      item.last_synced_at
                        ? "bg-green-100 text-green-700"
                        : "bg-yellow-100 text-yellow-700"
                    }`}
                  >
                    {item.last_synced_at ? "Synced" : "Pending"}
                  </span>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
