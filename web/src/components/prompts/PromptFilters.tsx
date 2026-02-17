interface Props {
  search: string;
  onSearchChange: (value: string) => void;
  domain: string;
  onDomainChange: (value: string) => void;
  environment: string;
  onEnvironmentChange: (value: string) => void;
  domains: string[];
}

export default function PromptFilters({
  search, onSearchChange,
  domain, onDomainChange,
  environment, onEnvironmentChange,
  domains,
}: Props) {
  return (
    <div className="flex gap-3">
      <input
        type="text"
        placeholder="Search prompts..."
        value={search}
        onChange={(e) => onSearchChange(e.target.value)}
        className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
      />
      <select
        value={domain}
        onChange={(e) => onDomainChange(e.target.value)}
        className="rounded border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">All domains</option>
        {domains.map((d) => (
          <option key={d} value={d}>{d}</option>
        ))}
      </select>
      <select
        value={environment}
        onChange={(e) => onEnvironmentChange(e.target.value)}
        className="rounded border border-gray-300 px-3 py-2 text-sm"
      >
        <option value="">All environments</option>
        <option value="development">Development</option>
        <option value="staging">Staging</option>
        <option value="production">Production</option>
      </select>
    </div>
  );
}
