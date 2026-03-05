import { useState } from "react";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { apiFetch } from "../api/client";
import ProviderConfigCard, {
  type ProviderStatus,
} from "../components/settings/ProviderConfigCard";
import ProviderSecretModal from "../components/settings/ProviderSecretModal";

interface RegistryProvider {
  category: string;
  models: string[];
  config_keys: string[];
}

export default function UserSettingsPage() {
  const queryClient = useQueryClient();
  const [configuring, setConfiguring] = useState<string | null>(null);

  const { data: registry } = useQuery({
    queryKey: ["provider-registry"],
    queryFn: () =>
      apiFetch<{ providers: Record<string, RegistryProvider> }>(
        "/api/v1/admin/providers/registry"
      ),
  });

  const { data: configs } = useQuery({
    queryKey: ["user-providers"],
    queryFn: () =>
      apiFetch<{ items: Array<{ provider: string; secrets: Record<string, unknown> }> }>(
        "/api/v1/admin/user/providers"
      ),
  });

  const saveMutation = useMutation({
    mutationFn: (data: {
      provider: string;
      secrets: Record<string, string>;
      environment?: string;
    }) =>
      apiFetch(`/api/v1/admin/user/providers/${data.provider}`, {
        method: "PUT",
        body: JSON.stringify({
          secrets: data.secrets,
          environment: data.environment,
        }),
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-providers"] });
      setConfiguring(null);
    },
  });

  const removeMutation = useMutation({
    mutationFn: (provider: string) =>
      apiFetch(`/api/v1/admin/user/providers/${provider}`, {
        method: "DELETE",
      }),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["user-providers"] });
    },
  });

  const providers = registry?.providers ?? {};
  const configuredSet = new Set(
    (configs?.items ?? []).map((c) => c.provider)
  );

  const getStatus = (provider: string): ProviderStatus => {
    if (configuredSet.has(provider)) {
      return { configured: true, source: "user" };
    }
    return { configured: false, source: null };
  };

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold text-gray-900">Provider Keys</h1>
        <p className="mt-1 text-sm text-gray-500">
          Personal API keys used as fallback when no app-level key is configured.
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
        {Object.entries(providers).map(([name, info]) => (
          <ProviderConfigCard
            key={name}
            provider={name}
            category={info.category}
            models={info.models}
            status={getStatus(name)}
            onConfigure={setConfiguring}
            onRemove={(p) => removeMutation.mutate(p)}
          />
        ))}
      </div>

      {configuring && (
        <ProviderSecretModal
          provider={configuring}
          scope="user"
          onClose={() => setConfiguring(null)}
          onSave={(data) =>
            saveMutation.mutate({ provider: configuring, ...data })
          }
          isSaving={saveMutation.isPending}
        />
      )}
    </div>
  );
}
