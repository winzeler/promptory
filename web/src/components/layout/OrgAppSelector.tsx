import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useOrgs, useApps, useCreateOrg, useCreateApp, useGitHubOrgs, useGitHubRepos } from "../../hooks/usePrompts";
import Modal from "./Modal";

export default function OrgAppSelector() {
  const { data: orgs } = useOrgs();
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const { data: apps } = useApps(selectedOrgId);
  const navigate = useNavigate();

  const [showAddOrg, setShowAddOrg] = useState(false);
  const [showAddApp, setShowAddApp] = useState(false);

  // Add Org state
  const [selectedGHOwner, setSelectedGHOwner] = useState("");
  const [orgDisplayName, setOrgDisplayName] = useState("");

  // Add App state
  const [repoFilter, setRepoFilter] = useState("");
  const [selectedRepo, setSelectedRepo] = useState<{ full_name: string; default_branch: string } | null>(null);
  const [appDisplayName, setAppDisplayName] = useState("");
  const [appBranch, setAppBranch] = useState("main");
  const [appSubdir, setAppSubdir] = useState("");

  const createOrg = useCreateOrg();
  const createApp = useCreateApp(selectedOrgId ?? "");

  // GitHub discovery hooks — always called, conditional fetching via enabled
  const { data: ghOrgs, isLoading: ghOrgsLoading, error: ghOrgsError } = useGitHubOrgs();

  const selectedPdOrg = orgs?.find((o) => o.id === selectedOrgId);
  const githubOwnerForApp = selectedPdOrg?.github_owner ?? null;
  const { data: ghRepos, isLoading: ghReposLoading } = useGitHubRepos(showAddApp ? githubOwnerForApp : null);

  useEffect(() => {
    if (orgs && orgs.length > 0 && !selectedOrgId) {
      setSelectedOrgId(orgs[0].id);
    }
  }, [orgs, selectedOrgId]);

  function handleAddOrgClose() {
    setShowAddOrg(false);
    setSelectedGHOwner("");
    setOrgDisplayName("");
    createOrg.reset();
  }

  function handleAddAppClose() {
    setShowAddApp(false);
    setRepoFilter("");
    setSelectedRepo(null);
    setAppDisplayName("");
    setAppBranch("main");
    setAppSubdir("");
    createApp.reset();
  }

  async function submitAddOrg(e: React.FormEvent) {
    e.preventDefault();
    const org = await createOrg.mutateAsync({
      github_owner: selectedGHOwner,
      display_name: orgDisplayName || undefined,
    });
    setSelectedOrgId(org.id);
    handleAddOrgClose();
  }

  async function submitAddApp(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedRepo) return;
    const app = await createApp.mutateAsync({
      github_repo: selectedRepo.full_name,
      display_name: appDisplayName || undefined,
      default_branch: appBranch || "main",
      subdirectory: appSubdir || undefined,
    });
    handleAddAppClose();
    navigate(`/apps/${app.id}/prompts`);
  }

  const filteredRepos = ghRepos?.filter((r) =>
    r.name.toLowerCase().includes(repoFilter.toLowerCase())
  ) ?? [];

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <label className="block text-xs font-medium text-gray-500">Organization</label>
        <button
          onClick={() => setShowAddOrg(true)}
          className="text-xs text-gray-400 hover:text-gray-600"
          title="Add organization"
        >
          +
        </button>
      </div>
      <select
        value={selectedOrgId ?? ""}
        onChange={(e) => setSelectedOrgId(e.target.value || null)}
        className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm"
      >
        <option value="">Select org...</option>
        {orgs?.map((org) => (
          <option key={org.id} value={org.id}>
            {org.display_name || org.github_owner}
          </option>
        ))}
      </select>

      {selectedOrgId && (
        <div className="flex items-center justify-between">
          <label className="block text-xs font-medium text-gray-500">Application</label>
          <button
            onClick={() => setShowAddApp(true)}
            className="text-xs text-gray-400 hover:text-gray-600"
            title="Add application"
          >
            +
          </button>
        </div>
      )}

      {apps && apps.length > 0 && (
        <div className="space-y-1">
          {apps.map((app) => (
            <button
              key={app.id}
              onClick={() => navigate(`/apps/${app.id}/prompts`)}
              className="flex w-full items-center justify-between rounded border border-gray-200 px-2 py-1.5 text-left text-sm hover:bg-gray-50"
            >
              <span>{app.display_name || app.github_repo}</span>
              <span className="text-xs text-gray-400">
                {app.last_synced_at ? "synced" : "not synced"}
              </span>
            </button>
          ))}
        </div>
      )}

      {showAddOrg && (
        <Modal title="Add Organization" onClose={handleAddOrgClose}>
          <form onSubmit={submitAddOrg} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">
                GitHub account <span className="text-red-500">*</span>
              </label>
              {ghOrgsLoading ? (
                <p className="text-xs text-gray-400">Loading GitHub accounts…</p>
              ) : ghOrgsError ? (
                <p className="text-xs text-red-600">Failed to load GitHub accounts.</p>
              ) : (
                <div className="max-h-48 overflow-y-auto rounded border border-gray-200">
                  {ghOrgs?.map((ghOrg) => (
                    <button
                      key={ghOrg.login}
                      type="button"
                      onClick={() => {
                        setSelectedGHOwner(ghOrg.login);
                        if (!orgDisplayName) setOrgDisplayName(ghOrg.login);
                      }}
                      className={`flex w-full items-center gap-2 px-2 py-1.5 text-left text-sm hover:bg-gray-50 ${
                        selectedGHOwner === ghOrg.login ? "bg-blue-50 font-medium" : ""
                      }`}
                    >
                      {ghOrg.avatar_url && (
                        <img
                          src={ghOrg.avatar_url}
                          alt={ghOrg.login}
                          className="h-5 w-5 rounded-full"
                        />
                      )}
                      <span className="flex-1 truncate">{ghOrg.login}</span>
                      {ghOrg.description && (
                        <span className="truncate text-xs text-gray-400">{ghOrg.description}</span>
                      )}
                    </button>
                  ))}
                </div>
              )}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Display name</label>
              <input
                type="text"
                value={orgDisplayName}
                onChange={(e) => setOrgDisplayName(e.target.value)}
                placeholder="Optional"
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            {createOrg.error && (
              <p className="text-xs text-red-600">
                {(createOrg.error as Error).message}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleAddOrgClose}
                className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!selectedGHOwner || createOrg.isPending}
                className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {createOrg.isPending ? "Adding…" : "Add"}
              </button>
            </div>
          </form>
        </Modal>
      )}

      {showAddApp && selectedOrgId && (
        <Modal title="Add Application" onClose={handleAddAppClose}>
          <form onSubmit={submitAddApp} className="space-y-3">
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">
                GitHub repo <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={repoFilter}
                onChange={(e) => setRepoFilter(e.target.value)}
                placeholder="Filter repos…"
                className="mb-1 w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
              {ghReposLoading ? (
                <p className="text-xs text-gray-400">Loading repos…</p>
              ) : (
                <div className="max-h-48 overflow-y-auto rounded border border-gray-200">
                  {filteredRepos.length === 0 ? (
                    <p className="px-2 py-2 text-xs text-gray-400">No repos found.</p>
                  ) : (
                    filteredRepos.map((repo) => (
                      <button
                        key={repo.full_name}
                        type="button"
                        onClick={() => {
                          setSelectedRepo({ full_name: repo.full_name, default_branch: repo.default_branch });
                          setAppBranch(repo.default_branch);
                          if (!appDisplayName) setAppDisplayName(repo.name);
                        }}
                        className={`flex w-full items-center justify-between px-2 py-1.5 text-left text-sm hover:bg-gray-50 ${
                          selectedRepo?.full_name === repo.full_name ? "bg-blue-50 font-medium" : ""
                        }`}
                      >
                        <span className="truncate">{repo.name}</span>
                        <span className="ml-2 shrink-0 rounded bg-gray-100 px-1 py-0.5 text-xs text-gray-500">
                          {repo.private ? "private" : "public"}
                        </span>
                      </button>
                    ))
                  )}
                </div>
              )}
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Display name</label>
              <input
                type="text"
                value={appDisplayName}
                onChange={(e) => setAppDisplayName(e.target.value)}
                placeholder="Optional"
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Default branch</label>
              <input
                type="text"
                value={appBranch}
                onChange={(e) => setAppBranch(e.target.value)}
                placeholder="main"
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            <div>
              <label className="mb-1 block text-xs font-medium text-gray-700">Subdirectory</label>
              <input
                type="text"
                value={appSubdir}
                onChange={(e) => setAppSubdir(e.target.value)}
                placeholder="Optional, e.g. prompts/"
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
            </div>
            {createApp.error && (
              <p className="text-xs text-red-600">
                {(createApp.error as Error).message}
              </p>
            )}
            <div className="flex justify-end gap-2">
              <button
                type="button"
                onClick={handleAddAppClose}
                className="rounded px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-100"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={!selectedRepo || createApp.isPending}
                className="rounded bg-blue-600 px-3 py-1.5 text-sm text-white hover:bg-blue-700 disabled:opacity-50"
              >
                {createApp.isPending ? "Adding…" : "Add"}
              </button>
            </div>
          </form>
        </Modal>
      )}
    </div>
  );
}
