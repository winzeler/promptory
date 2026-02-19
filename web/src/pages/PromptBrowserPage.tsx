import { useState, useCallback, useRef } from "react";
import { useParams, Link } from "react-router-dom";
import { usePromptList, useSyncApp, useBatchUpdate, useBatchDelete } from "../hooks/usePrompts";
import { importPrompty } from "../api/prompts";

export default function PromptBrowserPage() {
  const { appId } = useParams<{ appId: string }>();
  const [search, setSearch] = useState("");
  const [filterDomain, setFilterDomain] = useState("");
  const [filterEnv, setFilterEnv] = useState("");

  // Selection mode
  const [selectionMode, setSelectionMode] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());

  // Batch action state
  const [batchEnv, setBatchEnv] = useState("");

  // Import
  const fileInputRef = useRef<HTMLInputElement>(null);

  const params: Record<string, string> = {};
  if (search) params.search = search;
  if (filterDomain) params.domain = filterDomain;
  if (filterEnv) params.environment = filterEnv;

  const { data, isLoading } = usePromptList(appId ?? null, params);
  const syncMutation = useSyncApp();
  const batchUpdateMutation = useBatchUpdate();
  const batchDeleteMutation = useBatchDelete();

  // Extract unique domains for filter
  const domains = [...new Set(data?.items.map((p) => p.domain).filter(Boolean))] as string[];

  const toggleSelect = useCallback((id: string) => {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const handleBatchEnvUpdate = useCallback(() => {
    if (!batchEnv || selectedIds.size === 0) return;
    batchUpdateMutation.mutate({
      prompt_ids: [...selectedIds],
      field: "environment",
      value: batchEnv,
      commit_message: `Batch set environment to ${batchEnv}`,
    }, {
      onSuccess: () => {
        setSelectedIds(new Set());
        setBatchEnv("");
      },
    });
  }, [batchEnv, selectedIds, batchUpdateMutation]);

  const handleBatchToggleActive = useCallback(() => {
    if (selectedIds.size === 0) return;
    batchUpdateMutation.mutate({
      prompt_ids: [...selectedIds],
      field: "active",
      value: true,
      commit_message: "Batch toggle active",
    }, {
      onSuccess: () => setSelectedIds(new Set()),
    });
  }, [selectedIds, batchUpdateMutation]);

  const handleBatchDelete = useCallback(() => {
    if (selectedIds.size === 0) return;
    if (!window.confirm(`Delete ${selectedIds.size} prompts?`)) return;
    batchDeleteMutation.mutate({
      prompt_ids: [...selectedIds],
      commit_message: `Batch delete ${selectedIds.size} prompts`,
    }, {
      onSuccess: () => {
        setSelectedIds(new Set());
        setSelectionMode(false);
      },
    });
  }, [selectedIds, batchDeleteMutation]);

  const handleImportPrompty = useCallback(async (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0];
    if (!file || !appId) return;
    const content = await file.text();
    try {
      await importPrompty(appId, content);
      // Trigger re-fetch
      window.location.reload();
    } catch {
      // Import failed
    }
    if (fileInputRef.current) fileInputRef.current.value = "";
  }, [appId]);

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
            onClick={() => {
              setSelectionMode(!selectionMode);
              setSelectedIds(new Set());
            }}
            className={`rounded border px-3 py-1.5 text-sm ${
              selectionMode
                ? "border-blue-400 bg-blue-50 text-blue-700"
                : "border-gray-300 hover:bg-gray-50"
            }`}
          >
            {selectionMode ? "Cancel Select" : "Select"}
          </button>
          <button
            onClick={() => fileInputRef.current?.click()}
            className="rounded border border-gray-300 px-3 py-1.5 text-sm hover:bg-gray-50"
          >
            Import .prompty
          </button>
          <input
            ref={fileInputRef}
            type="file"
            accept=".prompty"
            className="hidden"
            onChange={handleImportPrompty}
          />
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

      {/* Batch action bar */}
      {selectionMode && selectedIds.size > 0 && (
        <div className="flex items-center gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3">
          <span className="text-sm font-medium text-blue-700">
            {selectedIds.size} selected
          </span>
          <select
            value={batchEnv}
            onChange={(e) => setBatchEnv(e.target.value)}
            className="rounded border border-gray-300 px-2 py-1 text-sm"
          >
            <option value="">Set Environment...</option>
            <option value="development">Development</option>
            <option value="staging">Staging</option>
            <option value="production">Production</option>
          </select>
          {batchEnv && (
            <button
              onClick={handleBatchEnvUpdate}
              disabled={batchUpdateMutation.isPending}
              className="rounded bg-blue-600 px-3 py-1 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
            >
              Apply
            </button>
          )}
          <button
            onClick={handleBatchToggleActive}
            disabled={batchUpdateMutation.isPending}
            className="rounded border border-gray-300 px-3 py-1 text-sm hover:bg-gray-50 disabled:opacity-50"
          >
            Toggle Active
          </button>
          <button
            onClick={handleBatchDelete}
            disabled={batchDeleteMutation.isPending}
            className="rounded border border-red-300 px-3 py-1 text-sm text-red-700 hover:bg-red-50 disabled:opacity-50"
          >
            Delete Selected
          </button>
        </div>
      )}

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
            <div
              key={prompt.id}
              className="relative rounded-lg border border-gray-200 bg-white p-4 hover:border-gray-300 hover:shadow-sm"
            >
              {selectionMode && (
                <input
                  type="checkbox"
                  checked={selectedIds.has(prompt.id)}
                  onChange={() => toggleSelect(prompt.id)}
                  className="absolute left-2 top-2 h-4 w-4"
                />
              )}
              <Link
                to={selectionMode ? "#" : `/prompts/${prompt.id}/edit`}
                onClick={(e) => {
                  if (selectionMode) {
                    e.preventDefault();
                    toggleSelect(prompt.id);
                  }
                }}
                className="block"
              >
                <div className={`flex items-start justify-between ${selectionMode ? "ml-6" : ""}`}>
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
                  {prompt.modality_output && prompt.modality_output !== "text" && (
                    <span className={`rounded px-1 py-0.5 text-xs font-medium ${
                      prompt.modality_output === "tts" ? "bg-purple-100 text-purple-700"
                      : prompt.modality_output === "audio" ? "bg-teal-100 text-teal-700"
                      : prompt.modality_output === "image" ? "bg-orange-100 text-orange-700"
                      : "bg-gray-100 text-gray-600"
                    }`}>
                      {prompt.modality_output}
                    </span>
                  )}
                  {prompt.domain && <span>{prompt.domain}</span>}
                  {prompt.version && <span>v{prompt.version}</span>}
                </div>
              </Link>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
