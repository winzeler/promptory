import { useState } from "react";
import { EvalRun } from "../../api/eval";

interface Props {
  runs: EvalRun[];
  onDelete?: (runId: string) => void;
}

export default function EvalResults({ runs, onDelete }: Props) {
  const [expandedRun, setExpandedRun] = useState<string | null>(null);

  if (!runs.length) {
    return <p className="text-sm text-gray-500">No evaluation runs yet.</p>;
  }

  const exportResults = () => {
    const blob = new Blob([JSON.stringify(runs, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `eval-results-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <h3 className="text-sm font-semibold text-gray-700">
          Evaluation History ({runs.length} runs)
        </h3>
        <button
          onClick={exportResults}
          className="rounded border border-gray-300 px-2 py-1 text-xs text-gray-600 hover:bg-gray-50"
        >
          Export JSON
        </button>
      </div>
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
            <th className="py-2">Model</th>
            <th className="py-2">Status</th>
            <th className="py-2">Cost</th>
            <th className="py-2">Duration</th>
            <th className="py-2">Date</th>
            <th className="py-2 w-16"></th>
          </tr>
        </thead>
        <tbody>
          {runs.map((run) => (
            <>
              <tr
                key={run.id}
                className="border-b border-gray-100 cursor-pointer hover:bg-gray-50"
                onClick={() => setExpandedRun(expandedRun === run.id ? null : run.id)}
              >
                <td className="py-2 font-mono text-xs">{run.model}</td>
                <td className="py-2">
                  <span
                    className={`rounded px-1.5 py-0.5 text-xs ${
                      run.status === "completed"
                        ? "bg-green-100 text-green-700"
                        : run.status === "failed"
                          ? "bg-red-100 text-red-700"
                          : run.status === "running"
                            ? "bg-blue-100 text-blue-700"
                            : "bg-gray-100 text-gray-700"
                    }`}
                  >
                    {run.status}
                  </span>
                </td>
                <td className="py-2 text-gray-500 text-xs">
                  {run.cost_usd != null ? `$${run.cost_usd.toFixed(4)}` : "--"}
                </td>
                <td className="py-2 text-gray-500 text-xs">
                  {run.duration_ms != null
                    ? run.duration_ms > 1000
                      ? `${(run.duration_ms / 1000).toFixed(1)}s`
                      : `${run.duration_ms}ms`
                    : "--"}
                </td>
                <td className="py-2 text-gray-500 text-xs">
                  {new Date(run.created_at).toLocaleString()}
                </td>
                <td className="py-2 text-right">
                  {onDelete && (
                    <button
                      onClick={(e) => {
                        e.stopPropagation();
                        onDelete(run.id);
                      }}
                      className="text-xs text-red-500 hover:text-red-700"
                    >
                      Delete
                    </button>
                  )}
                </td>
              </tr>
              {expandedRun === run.id && (
                <tr key={`${run.id}-details`}>
                  <td colSpan={6} className="border-b border-gray-100 bg-gray-50 p-3">
                    <RunDetails run={run} />
                  </td>
                </tr>
              )}
            </>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function RunDetails({ run }: { run: EvalRun }) {
  if (run.error_message) {
    return (
      <div className="rounded border border-red-200 bg-red-50 p-2 text-xs text-red-700">
        <strong>Error:</strong> {run.error_message}
      </div>
    );
  }

  if (!run.results) {
    return <p className="text-xs text-gray-500">No detailed results available.</p>;
  }

  const results = run.results as Record<string, unknown>;
  const evalResults = (results.results ?? []) as Array<Record<string, unknown>>;

  if (!evalResults.length) {
    return (
      <pre className="max-h-40 overflow-auto rounded bg-white p-2 text-xs">
        {JSON.stringify(results, null, 2)}
      </pre>
    );
  }

  return (
    <div className="space-y-2">
      <p className="text-xs font-medium text-gray-600">
        {evalResults.length} result{evalResults.length !== 1 ? "s" : ""}
      </p>
      {evalResults.map((r, i) => {
        const output = String(r.response ?? r.output ?? "");
        const assertions = (r.gradingResult?.componentResults ?? []) as Array<Record<string, unknown>>;
        return (
          <div key={i} className="rounded border border-gray-200 bg-white p-2 text-xs">
            <pre className="max-h-32 overflow-auto whitespace-pre-wrap text-gray-700">
              {output.slice(0, 2000)}
            </pre>
            {assertions.length > 0 && (
              <div className="mt-2 space-y-0.5">
                {assertions.map((a, j) => (
                  <div key={j} className="flex items-center gap-2">
                    <span className={a.pass ? "text-green-600" : "text-red-600"}>
                      {a.pass ? "PASS" : "FAIL"}
                    </span>
                    <span className="text-gray-500">
                      {String(a.assertion ?? a.type ?? `Assertion ${j + 1}`)}
                    </span>
                    {a.score != null && (
                      <span className="text-gray-400">({String(a.score)})</span>
                    )}
                  </div>
                ))}
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
