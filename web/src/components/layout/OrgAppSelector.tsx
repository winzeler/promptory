import { useState, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import { useOrgs, useApps } from "../../hooks/usePrompts";

export default function OrgAppSelector() {
  const { data: orgs } = useOrgs();
  const [selectedOrgId, setSelectedOrgId] = useState<string | null>(null);
  const { data: apps } = useApps(selectedOrgId);
  const navigate = useNavigate();

  useEffect(() => {
    if (orgs && orgs.length > 0 && !selectedOrgId) {
      setSelectedOrgId(orgs[0].id);
    }
  }, [orgs, selectedOrgId]);

  return (
    <div className="space-y-2">
      <label className="block text-xs font-medium text-gray-500">Organization</label>
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

      {apps && apps.length > 0 && (
        <>
          <label className="block text-xs font-medium text-gray-500">Application</label>
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
        </>
      )}
    </div>
  );
}
