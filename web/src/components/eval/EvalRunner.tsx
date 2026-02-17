import { useState } from "react";

interface Props {
  onRun: (models: string[]) => void;
  isPending: boolean;
}

export default function EvalRunner({ onRun, isPending }: Props) {
  const [models, setModels] = useState("gemini-2.0-flash, gpt-4o");

  return (
    <div className="rounded-lg border border-gray-200 bg-white p-4">
      <h3 className="text-sm font-semibold text-gray-700">Run Evaluation</h3>
      <div className="mt-2 flex items-center gap-2">
        <input
          type="text"
          value={models}
          onChange={(e) => setModels(e.target.value)}
          placeholder="Models (comma-separated)"
          className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
        />
        <button
          onClick={() => onRun(models.split(",").map((m) => m.trim()).filter(Boolean))}
          disabled={isPending}
          className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
        >
          {isPending ? "Running..." : "Run"}
        </button>
      </div>
    </div>
  );
}
