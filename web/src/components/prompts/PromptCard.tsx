import { Link } from "react-router-dom";
import PromptBadges from "./PromptBadges";

interface Props {
  id: string;
  name: string;
  domain: string | null;
  description: string | null;
  type: string;
  environment: string;
  tags: string[];
  version: string | null;
}

export default function PromptCard({ id, name, domain, description, type, environment, tags, version }: Props) {
  return (
    <Link
      to={`/prompts/${id}/edit`}
      className="block rounded-lg border border-gray-200 bg-white p-4 hover:border-gray-300 hover:shadow-sm"
    >
      <div className="flex items-start justify-between">
        <h3 className="font-mono text-sm font-medium text-gray-900">{name}</h3>
        <PromptBadges type={type} environment={environment} />
      </div>
      {description && (
        <p className="mt-1 text-xs text-gray-500 line-clamp-2">{description}</p>
      )}
      <div className="mt-3 flex flex-wrap gap-1">
        {tags.slice(0, 4).map((tag) => (
          <span key={tag} className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
            {tag}
          </span>
        ))}
      </div>
      <div className="mt-2 flex items-center gap-3 text-xs text-gray-400">
        {domain && <span>{domain}</span>}
        {version && <span>v{version}</span>}
      </div>
    </Link>
  );
}
