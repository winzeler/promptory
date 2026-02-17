import { useState } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usePromptDetail } from "../hooks/usePrompts";
import { runEval, fetchEvalRuns, EvalRun } from "../api/eval";

export default function EvaluationPage() {
  const { id } = useParams<{ id: string }>();
  const { data: prompt } = usePromptDetail(id ?? null);
  const { data: runsData, isLoading } = useQuery({
    queryKey: ["eval-runs", id],
    queryFn: () => fetchEvalRuns(id!),
    enabled: !!id,
  });

  const [selectedModels, setSelectedModels] = useState(["gemini-2.0-flash", "gpt-4o"]);
  const qc = useQueryClient();

  const evalMutation = useMutation({
    mutationFn: () => runEval(id!, selectedModels),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["eval-runs", id] }),
  });

  return (
    <div className="space-y-6">
      <div className="flex items-center gap-3">
        <Link to={`/prompts/${id}/edit`} className="text-sm text-gray-500 hover:text-gray-700">&larr; Editor</Link>
        <h1 className="text-2xl font-bold text-gray-900">
          Evaluation: {prompt?.name ?? "..."}
        </h1>
      </div>

      {/* Run new eval */}
      <div className="rounded-lg border border-gray-200 bg-white p-4">
        <h2 className="text-sm font-semibold text-gray-700">Run Evaluation</h2>
        <div className="mt-2 flex items-center gap-3">
          <input
            type="text"
            value={selectedModels.join(", ")}
            onChange={(e) => setSelectedModels(e.target.value.split(",").map((m) => m.trim()).filter(Boolean))}
            placeholder="Models (comma-separated)"
            className="flex-1 rounded border border-gray-300 px-3 py-2 text-sm"
          />
          <button
            onClick={() => evalMutation.mutate()}
            disabled={evalMutation.isPending}
            className="rounded bg-gray-900 px-4 py-2 text-sm font-medium text-white hover:bg-gray-800 disabled:opacity-50"
          >
            {evalMutation.isPending ? "Running..." : "Run Eval"}
          </button>
        </div>
        {evalMutation.isSuccess && (
          <p className="mt-2 text-xs text-green-600">Evaluation runs created. Full execution coming in Phase 2.</p>
        )}
      </div>

      {/* Eval history */}
      <div>
        <h2 className="text-sm font-semibold text-gray-700">Evaluation History</h2>
        {isLoading ? (
          <p className="mt-2 text-sm text-gray-500">Loading...</p>
        ) : !runsData?.items.length ? (
          <p className="mt-2 text-sm text-gray-500">No evaluation runs yet.</p>
        ) : (
          <table className="mt-2 w-full text-sm">
            <thead>
              <tr className="border-b border-gray-200 text-left text-xs text-gray-500">
                <th className="py-2">Model</th>
                <th className="py-2">Version</th>
                <th className="py-2">Status</th>
                <th className="py-2">Triggered</th>
                <th className="py-2">Date</th>
              </tr>
            </thead>
            <tbody>
              {runsData.items.map((run: EvalRun) => (
                <tr key={run.id} className="border-b border-gray-100">
                  <td className="py-2 font-mono">{run.model}</td>
                  <td className="py-2">{run.prompt_version}</td>
                  <td className="py-2">
                    <span className={`rounded px-1.5 py-0.5 text-xs ${
                      run.status === "completed" ? "bg-green-100 text-green-700" :
                      run.status === "failed" ? "bg-red-100 text-red-700" :
                      "bg-gray-100 text-gray-700"
                    }`}>
                      {run.status}
                    </span>
                  </td>
                  <td className="py-2 text-gray-500">{run.triggered_by}</td>
                  <td className="py-2 text-gray-500">{new Date(run.created_at).toLocaleString()}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
