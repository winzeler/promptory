import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useOrgs, useApps, useCreateOrg, useCreateApp } from "../../hooks/usePrompts";
import Modal from "./Modal";

export default function OrgAppSelector() {
  const { data: orgs } = useOrgs();
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const { data: apps } = useApps(selectedOrgId);
  const navigate = useNavigate();

  const [showAddOrg, setShowAddOrg] = useState(false);
  const [showAddApp, setShowAddApp] = useState(false);

  const [orgOwner, setOrgOwner] = useState("");
  const [orgDisplayName, setOrgDisplayName] = useState("");

  const [appRepo, setAppRepo] = useState("");
  const [appDisplayName, setAppDisplayName] = useState("");
  const [appBranch, setAppBranch] = useState("main");
  const [appSubdir, setAppSubdir] = useState("");

  const createOrg = useCreateOrg();
  const createApp = useCreateApp(selectedOrgId ?? "");

  useEffect(() => {
    if (orgs && orgs.length > 0 && !selectedOrgId) {
      setSelectedOrgId(orgs[0].id);
    }
  }, [orgs, selectedOrgId]);

  function handleAddOrgClose() {
    setShowAddOrg(false);
    setOrgOwner("");
    setOrgDisplayName("");
    createOrg.reset();
  }

  function handleAddAppClose() {
    setShowAddApp(false);
    setAppRepo("");
    setAppDisplayName("");
    setAppBranch("main");
    setAppSubdir("");
    createApp.reset();
  }

  async function submitAddOrg(e: React.FormEvent) {
    e.preventDefault();
    const org = await createOrg.mutateAsync({ github_owner: orgOwner, display_name: orgDisplayName || undefined });
    setSelectedOrgId(org.id);
    handleAddOrgClose();
  }

  async function submitAddApp(e: React.FormEvent) {
    e.preventDefault();
    const app = await createApp.mutateAsync({
      github_repo: appRepo,
      display_name: appDisplayName || undefined,
      default_branch: appBranch || "main",
      subdirectory: appSubdir || undefined,
    });
    handleAddAppClose();
    navigate(`/apps/${app.id}/prompts`);
  }

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
                GitHub owner <span className="text-red-500">*</span>
              </label>
              <input
                type="text"
                value={orgOwner}
                onChange={(e) => setOrgOwner(e.target.value)}
                placeholder="my-org or username"
                required
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
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
                disabled={createOrg.isPending}
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
                value={appRepo}
                onChange={(e) => setAppRepo(e.target.value)}
                placeholder="owner/repo"
                required
                className="w-full rounded border border-gray-300 px-2 py-1.5 text-sm focus:border-blue-500 focus:outline-none"
              />
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
                disabled={createApp.isPending}
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
