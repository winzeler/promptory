import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { usePromptList, useSyncApp } from "../hooks/usePrompts";

export default function PromptBrowserPage() {
  const { appId } = useParams<{ appId: string }>();
  const [search, setSearch] = useState("");
  const [filterDomain, setFilterDomain] = useState("");
  const [filterEnv, setFilterEnv] = useState("");

  const params: Record<string, string> = {};
  if (search) params.search = search;
  if (filterDomain) params.domain = filterDomain;
  if (filterEnv) params.environment = filterEnv;

  const { data, isLoading } = usePromptList(appId ?? null, params);
  const syncMutation = useSyncApp();

  // Extract unique domains for filter
  const domains = [...new Set(data?.items.map((p) => p.domain).filter(Boolean))] as string[];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Prompts</h1>
          <p className="text-sm text-gray-500">
            {data ? `${data.total} prompts` : "Loading..."}
          </p>
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => appId && syncMutation.mutate(appId)}
            disabled={syncMutation.isPending}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            {syncMutation.isPending ? "Syncing..." : "Sync"}
          </button>
          <Link
            to={`/apps/${appId}/settings`}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
          >
            Settings
          </Link>
        </div>
      </div>

      {/* Filters */}
      <div className="flex gap-3">
        <input
          type="text"
          placeholder="Search prompts..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
        />
        <select
          value={filterDomain}
          onChange={(e) => setFilterDomain(e.target.value)}
          className="rounded border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All domains</option>
          {domains.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <select
          value={filterEnv}
          onChange={(e) => setFilterEnv(e.target.value)}
          className="rounded border border-gray-300 px-3 py-2 text-sm"
        >
          <option value="">All environments</option>
          <option value="development">Development</option>
          <option value="staging">Staging</option>
          <option value="production">Production</option>
        </select>
      </div>

      {/* Prompt Grid */}
      {isLoading ? (
        <div className="text-sm text-gray-500">Loading prompts...</div>
      ) : data?.items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 p-8 text-center text-sm text-gray-500">
          No prompts found. Sync from GitHub or create a new prompt.
        </div>
      ) : (
        <div className="grid grid-cols-1 gap-3 sm:grid-cols-2 lg:grid-cols-3">
          {data?.items.map((prompt) => (
            <Link
              key={prompt.id}
              to={`/prompts/${prompt.id}/edit`}
              className="rounded-lg border border-gray-200 bg-white p-4 hover:border-gray-300 hover:shadow-sm"
            >
              <div className="flex items-start justify-between">
                <h3 className="font-mono text-sm font-medium text-gray-900">
                  {prompt.name}
                </h3>
                <span
                  className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                    prompt.environment === "production"
                      ? "bg-green-100 text-green-700"
                      : prompt.environment === "staging"
                        ? "bg-yellow-100 text-yellow-700"
                        : "bg-gray-100 text-gray-700"
                  }`}
                >
                  {prompt.environment}
                </span>
              </div>
              {prompt.description && (
                <p className="mt-1 text-xs text-gray-500 line-clamp-2">
                  {prompt.description}
                </p>
              )}
              <div className="mt-3 flex flex-wrap gap-1">
                {prompt.tags.slice(0, 4).map((tag) => (
                  <span
                    key={tag}
                    className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600"
                  >
                    {tag}
                  </span>
                ))}
              </div>
              <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
                <span>{prompt.type}</span>
                {prompt.domain && <span>{prompt.domain}</span>}
                {prompt.version && <span>v{prompt.version}</span>}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
