import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { usePromptDetail } from "../hooks/usePrompts";

export default function PromptPreviewPage() {
  const { id } = useParams<{ id: string }>();
  const { data: prompt, isLoading } = usePromptDetail(id ?? null);
  const [variablesJson, setVariablesJson] = useState('{\n  "user": {\n    "display_name": "Test User"\n  },\n  "vision": {\n    "identity_statement": "I am confident and focused"\n  }\n}');
  const [rendered, setRendered] = useState<string | null>(null);

  const handleRender = async () => {
    if (!id) return;
    try {
      const variables = JSON.parse(variablesJson);
      const resp = await fetch(`/api/v1/prompts/${id}/render`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        credentials: "include",
        body: JSON.stringify({ variables }),
      });
      const data = await resp.json();
      setRendered(data.rendered_body ?? JSON.stringify(data, null, 2));
    } catch (e) {
      setRendered(`Error: ${(e as Error).message}`);
    }
  };

  if (isLoading) return <div className="text-sm text-gray-500">Loading...</div>;
  if (!prompt) return <div className="text-sm text-red-500">Prompt not found</div>;

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to={`/prompts/${id}/edit`} className="text-sm text-gray-500 hover:text-gray-700">&larr; Editor</Link>
        <h1 className="text-2xl font-bold text-gray-900">Preview: {prompt.name}</h1>
      </div>

      <div className="grid grid-cols-2 gap-6">
        {/* Variables input */}
        <div>
          <h2 className="mb-2 text-sm font-semibold text-gray-700">Template Variables (JSON)</h2>
          <textarea
            value={variablesJson}
            onChange={(e) => setVariablesJson(e.target.value)}
            rows={12}
            className="w-full rounded border border-gray-300 p-3 font-mono text-sm"
          />
          <button
            onClick={handleRender}
            className="mt-2 rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800"
          >
            Render
          </button>
        </div>

        {/* Rendered output */}
        <div>
          <h2 className="mb-2 text-sm font-semibold text-gray-700">Rendered Output</h2>
          <div className="min-h-[300px] rounded border border-gray-200 bg-gray-50 p-4 text-sm whitespace-pre-wrap">
            {rendered ?? "Click 'Render' to see the output..."}
          </div>
        </div>
      </div>

      {/* Raw template */}
      <div>
        <h2 className="mb-2 text-sm font-semibold text-gray-700">Raw Template</h2>
        <pre className="rounded border border-gray-200 bg-gray-50 p-4 text-xs whitespace-pre-wrap">
          {prompt.body}
        </pre>
      </div>
    </div>
  );
}
