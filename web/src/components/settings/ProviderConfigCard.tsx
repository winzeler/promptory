
export interface ProviderStatus {
  configured: boolean;
  source: string | null;
}

interface Props {
  provider: string;
  category: string;
  models: string[];
  status: ProviderStatus | null;
  onConfigure: (provider: string) => void;
  onRemove: (provider: string) => void;
}

const SOURCE_LABELS: Record<string, string> = {
  app: "App-level key",
  user: "Your personal key",
  global: "Server default",
};

export default function ProviderConfigCard({
  provider,
  category,
  models,
  status,
  onConfigure,
  onRemove,
}: Props) {
  const configured = status?.configured ?? false;
  const sourceLabel = status?.source ? SOURCE_LABELS[status.source] || status.source : "Not configured";

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <div className="flex items-center justify-between">
        <div>
          <h4 className="text-sm font-semibold text-gray-900 capitalize">{provider}</h4>
          <p className="text-xs text-gray-500">{category}</p>
        </div>
        <span
          className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${
            configured
              ? "bg-green-100 text-green-700"
              : "bg-gray-100 text-gray-500"
          }`}
        >
          {configured ? sourceLabel : "Not configured"}
        </span>
      </div>

      <div className="mt-2">
        <p className="text-xs text-gray-400">
          Models: {models.slice(0, 3).join(", ")}
          {models.length > 3 && ` +${models.length - 3} more`}
        </p>
      </div>

      <div className="mt-3 flex gap-2">
        <button
          onClick={() => onConfigure(provider)}
          className="rounded border border-gray-300 px-3 py-1 text-xs font-medium text-gray-700 hover:bg-gray-50"
        >
          {configured ? "Update" : "Configure"}
        </button>
        {configured && status?.source !== "global" && (
          <button
            onClick={() => onRemove(provider)}
            className="rounded border border-red-200 px-3 py-1 text-xs font-medium text-red-600 hover:bg-red-50"
          >
            Remove
          </button>
        )}
      </div>
    </div>
  );
}
