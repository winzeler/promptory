import { useOrgs, useApps } from "../hooks/usePrompts";
import { Link } from "react-router-dom";

export default function DashboardPage() {
  const { data: orgs, isLoading: orgsLoading } = useOrgs();
  const firstOrgId = orgs?.[0]?.id ?? null;
  const { data: apps } = useApps(firstOrgId);

  return (
    <div className="space-y-8">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Dashboard</h1>
        <p className="mt-1 text-sm text-gray-500">
          Manage your LLM prompts across organizations and applications.
        </p>
      </div>

      {/* Stats */}
      <div className="grid grid-cols-1 gap-4 sm:grid-cols-3">
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <div className="text-sm font-medium text-gray-500">Organizations</div>
          <div className="mt-1 text-2xl font-semibold">{orgs?.length ?? 0}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <div className="text-sm font-medium text-gray-500">Applications</div>
          <div className="mt-1 text-2xl font-semibold">{apps?.length ?? 0}</div>
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <div className="text-sm font-medium text-gray-500">Cache Size</div>
          <div className="mt-1 text-2xl font-semibold">--</div>
        </div>
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
