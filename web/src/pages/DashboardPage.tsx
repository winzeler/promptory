import { useOrgs, useApps, useRequestsPerDay, useCacheHitRate, useTopPrompts, useUsageByKey } from "../hooks/usePrompts";
import { Link } from "react-router-dom";

export default function DashboardPage() {
  const { data: orgs, isLoading: orgsLoading } = useOrgs();
  const firstOrgId = orgs?.[0]?.id ?? null;
  const { data: apps } = useApps(firstOrgId);

  const { data: requestsData } = useRequestsPerDay();
  const { data: cacheData } = useCacheHitRate();
  const { data: topData } = useTopPrompts(undefined, 30, 5);
  const { data: keyData } = useUsageByKey();

  // Compute aggregate cache hit rate
  const totalRequests = cacheData?.items.reduce((s, d) => s + (d.total ?? 0), 0) ?? 0;
  const totalHits = cacheData?.items.reduce((s, d) => s + (d.hits ?? 0), 0) ?? 0;
  const overallHitRate = totalRequests > 0 ? Math.round((100 * totalHits) / totalRequests) : 0;

  // Bar chart: find max for scaling
  const rpd = requestsData?.items ?? [];
  const maxCount = Math.max(...rpd.map((d) => d.count ?? 0), 1);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your LLM prompts across organizations and applications.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-4">
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <div className="text-sm font-medium text-gray-500">Organizations</div>
          <div className="mt-1 text-2xl font-semibold">{orgs?.length ?? 0}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <div className="text-sm font-medium text-gray-500">Applications</div>
          <div className="mt-1 text-2xl font-semibold">{apps?.length ?? 0}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <div className="text-sm font-medium text-gray-500">Total Requests (30d)</div>
          <div className="mt-1 text-2xl font-semibold">{totalRequests}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <div className="text-sm font-medium text-gray-500">Cache Hit Rate</div>
          <div className="mt-1 text-2xl font-semibold">{overallHitRate}%</div>
        </div>
      </div>

      {/* Requests per day chart */}
      {rpd.length > 0 && (
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h2 className="text-sm font-semibold text-gray-900">Requests per Day</h2>
          <div className="mt-3 flex items-end gap-1" style={{ height: 120 }}>
            {rpd.slice(-30).map((d) => {
              const h = Math.max(((d.count ?? 0) / maxCount) * 100, 2);
              return (
                <div
                  key={d.day}
                  title={`${d.day}: ${d.count}`}
                  className="flex-1 rounded-t bg-blue-500 transition-all hover:bg-blue-600"
                  style={{ height: `${h}%`, minWidth: 4 }}
                />
              );
            })}
          </div>
          <div className="mt-1 flex justify-between text-xs text-gray-400">
            <span>{rpd[0]?.day}</span>
            <span>{rpd[rpd.length - 1]?.day}</span>
          </div>
        </div>
      )}

      {/* Top prompts + API key usage side by side */}
      <div className="grid grid-cols-1 gap-4 lg:grid-cols-2">
        {/* Top prompts */}
        {topData?.items && topData.items.length > 0 && (
          <div className="rounded-lg border border-gray-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-gray-900">Top Prompts (30d)</h2>
            <table className="mt-3 w-full text-xs">
              <thead>
                <tr className="border-b border-gray-100 text-left text-gray-500">
                  <th className="pb-2">Prompt</th>
                  <th className="pb-2 text-right">Requests</th>
                  <th className="pb-2 text-right">Avg Latency</th>
                  <th className="pb-2 text-right">Cache %</th>
                </tr>
              </thead>
              <tbody>
                {topData.items.map((p) => (
                  <tr key={p.prompt_id} className="border-b border-gray-50">
                    <td className="py-1.5 font-mono text-gray-900">{p.prompt_name ?? p.prompt_id?.slice(0, 8)}</td>
                    <td className="py-1.5 text-right text-gray-700">{p.request_count}</td>
                    <td className="py-1.5 text-right text-gray-700">{p.avg_latency_ms}ms</td>
                    <td className="py-1.5 text-right text-gray-700">{p.cache_rate}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        {/* API key usage */}
        {keyData?.items && keyData.items.length > 0 && (
          <div className="rounded-lg border border-gray-200 bg-white p-5">
            <h2 className="text-sm font-semibold text-gray-900">Usage by API Key (30d)</h2>
            <table className="mt-3 w-full text-xs">
              <thead>
                <tr className="border-b border-gray-100 text-left text-gray-500">
                  <th className="pb-2">Key</th>
                  <th className="pb-2 text-right">Requests</th>
                  <th className="pb-2 text-right">Avg Latency</th>
                </tr>
              </thead>
              <tbody>
                {keyData.items.map((k) => (
                  <tr key={k.api_key_id ?? "anon"} className="border-b border-gray-50">
                    <td className="py-1.5 text-gray-900">{k.key_name ?? k.api_key_id ?? "Anonymous"}</td>
                    <td className="py-1.5 text-right text-gray-700">{k.request_count}</td>
                    <td className="py-1.5 text-right text-gray-700">{k.avg_latency_ms}ms</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {/* Applications */}
      <div>
        <h2 className="text-lg font-semibold text-gray-900">Applications</h2>
        {orgsLoading ? (
          <p className="mt-2 text-sm text-gray-500">Loading...</p>
        ) : apps && apps.length > 0 ? (
          <div className="mt-4 grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {apps.map((app) => (
              <Link
                key={app.id}
                to={`/apps/${app.id}/prompts`}
                className="block rounded-lg border border-gray-200 bg-white p-5 hover:border-gray-300 hover:shadow-sm"
              >
                <h3 className="font-medium text-gray-900">
                  {app.display_name || app.github_repo}
                </h3>
                <p className="mt-1 text-sm text-gray-500">{app.github_repo}</p>
                <div className="mt-3 flex items-center gap-2 text-xs text-gray-400">
                  <span>Branch: {app.default_branch}</span>
                  {app.last_synced_at && (
                    <span>
                      Synced: {new Date(app.last_synced_at).toLocaleDateString()}
                    </span>
                  )}
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <p className="mt-4 text-sm text-gray-500">
            No applications connected. Add a GitHub repo to get started.
          </p>
        )}
      </div>
    </div>
  );
}
