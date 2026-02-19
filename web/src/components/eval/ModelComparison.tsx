import { useState } from "react";

export interface ModelOutput {
  model: string;
  output: string;
  latencyMs: number;
  cost: number;
  tokenCount?: number;
}

interface Props {
  outputs: ModelOutput[];
}

export default function ModelComparison({ outputs }: Props) {
  const [viewMode, setViewMode] = useState<"grid" | "diff">("grid");

  if (!outputs.length) {
    return <p className="text-sm text-gray-500">No model outputs to compare.</p>;
  }

  // Find best model by latency
  const fastest = outputs.reduce((a, b) => (a.latencyMs < b.latencyMs ? a : b));
  const cheapest = outputs.reduce((a, b) => (a.cost < b.cost ? a : b));

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">Model Comparison</h3>
        {outputs.length >= 2 && (
          <div className="flex gap-1 rounded border border-gray-200 p-0.5">
            <button
              onClick={() => setViewMode("grid")}
              className={`rounded px-2 py-0.5 text-xs ${
                viewMode === "grid" ? "bg-gray-900 text-white" : "text-gray-600"
              }`}
            >
              Grid
            </button>
            <button
              onClick={() => setViewMode("diff")}
              className={`rounded px-2 py-0.5 text-xs ${
                viewMode === "diff" ? "bg-gray-900 text-white" : "text-gray-600"
              }`}
            >
              Diff
            </button>
          </div>
        )}
      </div>

      {viewMode === "grid" ? (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {outputs.map((o) => (
            <div key={o.model} className="rounded-lg border border-gray-200 p-4">
              <div className="flex items-center justify-between">
                <h4 className="font-mono text-sm font-medium">{o.model}</h4>
                <div className="flex items-center gap-2">
                  {o.model === fastest.model && outputs.length > 1 && (
                    <span className="rounded bg-green-100 px-1.5 py-0.5 text-[10px] font-medium text-green-700">
                      Fastest
                    </span>
                  )}
                  {o.model === cheapest.model && outputs.length > 1 && (
                    <span className="rounded bg-blue-100 px-1.5 py-0.5 text-[10px] font-medium text-blue-700">
                      Cheapest
                    </span>
                  )}
                </div>
              </div>
              <div className="mt-1 flex gap-3 text-xs text-gray-500">
                <span>{o.latencyMs > 1000 ? `${(o.latencyMs / 1000).toFixed(1)}s` : `${o.latencyMs}ms`}</span>
                <span>${o.cost.toFixed(4)}</span>
                {o.tokenCount && <span>{o.tokenCount} tokens</span>}
              </div>
              <pre className="mt-2 max-h-60 overflow-auto rounded bg-gray-50 p-2 text-xs whitespace-pre-wrap">
                {o.output}
              </pre>
            </div>
          ))}
        </div>
      ) : (
        <DiffView outputs={outputs} />
      )}
    </div>
  );
}

function DiffView({ outputs }: { outputs: ModelOutput[] }) {
  if (outputs.length < 2) return null;

  const [a, b] = outputs;
  const linesA = a.output.split("\n");
  const linesB = b.output.split("\n");
  const maxLines = Math.max(linesA.length, linesB.length);

  return (
    <div className="overflow-auto rounded border border-gray-200">
      <div className="grid grid-cols-2 gap-0 text-xs font-mono">
        <div className="border-b border-r border-gray-200 bg-gray-50 px-3 py-1.5 font-sans font-semibold">
          {a.model}
        </div>
        <div className="border-b border-gray-200 bg-gray-50 px-3 py-1.5 font-sans font-semibold">
          {b.model}
        </div>
        {Array.from({ length: maxLines }, (_, i) => {
          const lineA = linesA[i] ?? "";
          const lineB = linesB[i] ?? "";
          const isDiff = lineA !== lineB;
          return (
            <>
              <div
                key={`a-${i}`}
                className={`border-r border-gray-100 px-3 py-0.5 whitespace-pre-wrap ${
                  isDiff ? "bg-red-50" : ""
                }`}
              >
                {lineA}
              </div>
              <div
                key={`b-${i}`}
                className={`px-3 py-0.5 whitespace-pre-wrap ${isDiff ? "bg-green-50" : ""}`}
              >
                {lineB}
              </div>
            </>
          );
        })}
      </div>
    </div>
  );
}
