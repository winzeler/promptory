import { useState } from "react";

const POPULAR_MODELS = [
  "gemini-2.0-flash",
  "gpt-4o",
  "claude-sonnet-4-5-20250929",
  "gpt-4o-mini",
];

interface Props {
  onRun: (models: string[], variables?: Record<string, string>) => void;
  onGenerateTests?: () => void;
  isPending: boolean;
  isGenerating?: boolean;
}

export default function EvalRunner({ onRun, onGenerateTests, isPending, isGenerating }: Props) {
  const [selectedModels, setSelectedModels] = useState<string[]>(["gemini-2.0-flash", "gpt-4o"]);
  const [customModel, setCustomModel] = useState("");
  const [showVars, setShowVars] = useState(false);
  const [varsText, setVarsText] = useState("{}");

  const toggleModel = (model: string) => {
    setSelectedModels((prev) =>
      prev.includes(model) ? prev.filter((m) => m !== model) : [...prev, model],
    );
  };

  const addCustomModel = () => {
    const trimmed = customModel.trim();
    if (trimmed && !selectedModels.includes(trimmed)) {
      setSelectedModels((prev) => [...prev, trimmed]);
      setCustomModel("");
    }
  };

  const handleRun = () => {
    let variables: Record<string, string> | undefined;
    if (showVars && varsText.trim() !== "{}") {
      try {
        variables = JSON.parse(varsText);
      } catch {
        // ignore invalid JSON
      }
    }
    onRun(selectedModels, variables);
  };

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4 space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">Run Evaluation</h3>
        {onGenerateTests && (
          <button
            onClick={onGenerateTests}
            disabled={isGenerating}
            className="rounded border border-purple-300 px-3 py-1 text-xs font-medium text-purple-700 hover:bg-purple-50 disabled:opacity-50"
          >
            {isGenerating ? "Generating..." : "Auto-Generate Tests"}
          </button>
        )}
      </div>

      {/* Model selection chips */}
      <div>
        <label className="block text-xs font-medium text-gray-500 mb-1">Models</label>
        <div className="flex flex-wrap gap-1.5">
          {POPULAR_MODELS.map((model) => (
            <button
              key={model}
              onClick={() => toggleModel(model)}
              className={`rounded-full px-2.5 py-1 text-xs font-medium transition-colors ${
                selectedModels.includes(model)
                  ? "bg-gray-900 text-white"
                  : "bg-gray-100 text-gray-600 hover:bg-gray-200"
              }`}
            >
              {model}
            </button>
          ))}
          {selectedModels
            .filter((m) => !POPULAR_MODELS.includes(m))
            .map((model) => (
              <button
                key={model}
                onClick={() => toggleModel(model)}
                className="rounded-full bg-blue-100 px-2.5 py-1 text-xs font-medium text-blue-700"
              >
                {model} &times;
              </button>
            ))}
        </div>
        <div className="mt-1.5 flex gap-1.5">
          <input
            type="text"
            value={customModel}
            onChange={(e) => setCustomModel(e.target.value)}
            onKeyDown={(e) => e.key === "Enter" && addCustomModel()}
            placeholder="Add custom model..."
            className="flex-1 rounded border border-gray-300 px-2 py-1 text-xs"
          />
          <button
            onClick={addCustomModel}
            className="rounded border border-gray-300 px-2 py-1 text-xs hover:bg-gray-50"
          >
            Add
          </button>
        </div>
      </div>

      {/* Variables toggle */}
      <div>
        <button
          onClick={() => setShowVars(!showVars)}
          className="text-xs text-gray-500 hover:text-gray-700"
        >
          {showVars ? "Hide variables" : "Add variables (JSON)"}
        </button>
        {showVars && (
          <textarea
            value={varsText}
            onChange={(e) => setVarsText(e.target.value)}
            placeholder='{"name": "Alice", "topic": "meditation"}'
            className="mt-1 w-full rounded border border-gray-300 p-2 font-mono text-xs"
            rows={3}
          />
        )}
      </div>

      {/* Run button */}
      <button
        onClick={handleRun}
        disabled={isPending || selectedModels.length === 0}
        className="w-full rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
      >
        {isPending ? (
          <span className="flex items-center justify-center gap-2">
            <span className="inline-block h-3 w-3 animate-spin rounded-full border-2 border-white border-t-transparent" />
            Running evaluation...
          </span>
        ) : (
          `Run on ${selectedModels.length} model${selectedModels.length !== 1 ? "s" : ""}`
        )}
      </button>
    </div>
  );
}
