import { useState, useCallback } from "react";
import { useParams, Link } from "react-router-dom";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { usePromptDetail } from "../hooks/usePrompts";
import { runEval, fetchEvalRuns, deleteEvalRun, generateTests, EvalRun } from "../api/eval";
import EvalRunner from "../components/eval/EvalRunner";
import EvalResults from "../components/eval/EvalResults";
import ModelComparison, { ModelOutput } from "../components/eval/ModelComparison";

export default function EvaluationPage() {
  const { id } = useParams<{ id: string }>();
  const { data: prompt } = usePromptDetail(id ?? null);
  const qc = useQueryClient();

  const {
    data: runsData,
    isLoading,
    refetch,
  } = useQuery({
    queryKey: ["eval-runs", id],
    queryFn: () => fetchEvalRuns(id!),
    enabled: !!id,
    refetchInterval: (query) => {
      const runs = query.state.data?.items;
      if (runs?.some((r: EvalRun) => r.status === "pending" || r.status === "running")) return 3000;
      return false;
    },
  });

  const [comparisonOutputs, setComparisonOutputs] = useState<ModelOutput[]>([]);
  const [generatedTests, setGeneratedTests] = useState<unknown[]>([]);

  // Run evaluation
  const evalMutation = useMutation({
    mutationFn: ({ models, variables }: { models: string[]; variables?: Record<string, string> }) =>
      runEval(id!, models, variables),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["eval-runs", id] });
    },
  });

  // Delete a run
  const deleteMutation = useMutation({
    mutationFn: (runId: string) => deleteEvalRun(runId),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["eval-runs", id] });
    },
  });

  // Generate tests
  const testGenMutation = useMutation({
    mutationFn: () => generateTests(id!),
    onSuccess: (data) => {
      setGeneratedTests(data.tests);
    },
  });

  const handleRun = useCallback(
    (models: string[], variables?: Record<string, string>) => {
      evalMutation.mutate({ models, variables });
    },
    [evalMutation],
  );

  const handleDelete = useCallback(
    (runId: string) => {
      deleteMutation.mutate(runId);
    },
    [deleteMutation],
  );

  const handleGenerateTests = useCallback(() => {
    testGenMutation.mutate();
  }, [testGenMutation]);

  // Build comparison outputs from completed runs
  const runs = runsData?.items ?? [];
  const completedRuns = runs.filter((r: EvalRun) => r.status === "completed" && r.results);

  const buildComparison = useCallback(() => {
    const outputs: ModelOutput[] = completedRuns
      .filter((r: EvalRun) => r.model)
      .map((r: EvalRun) => {
        const results = r.results as Record<string, unknown> | null;
        const resultItems = (results?.results ?? []) as Array<Record<string, unknown>>;
        const outputText = resultItems.map((item) => String(item.response ?? item.output ?? "")).join("\n---\n");

        return {
          model: r.model!,
          output: outputText || "(no output)",
          latencyMs: r.duration_ms ?? 0,
          cost: r.cost_usd ?? 0,
        };
      });
    setComparisonOutputs(outputs);
  }, [completedRuns]);

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center gap-3">
        <Link to={`/prompts/${id}/edit`} className="text-sm text-gray-500 hover:text-gray-700">
          &larr; Editor
        </Link>
        <h1 className="text-2xl font-bold text-gray-900">Evaluation: {prompt?.name ?? "..."}</h1>
      </div>

      {/* Eval runner */}
      <EvalRunner
        onRun={handleRun}
        onGenerateTests={handleGenerateTests}
        isPending={evalMutation.isPending}
        isGenerating={testGenMutation.isPending}
      />

      {/* Generated tests preview */}
      {generatedTests.length > 0 && (
        <div className="rounded-lg border border-purple-200 bg-purple-50 p-4">
          <div className="flex items-center justify-between">
            <h3 className="text-sm font-semibold text-purple-800">
              Generated {generatedTests.length} test case{generatedTests.length !== 1 ? "s" : ""}
            </h3>
            <button
              onClick={() => setGeneratedTests([])}
              className="text-xs text-purple-600 hover:text-purple-800"
            >
              Dismiss
            </button>
          </div>
          <p className="mt-1 text-xs text-purple-600">
            Add these to your prompt's eval config (front-matter) to use them in evaluations.
          </p>
          <pre className="mt-2 max-h-60 overflow-auto rounded bg-white p-2 text-xs">
            {JSON.stringify(generatedTests, null, 2)}
          </pre>
        </div>
      )}

      {/* Error messages */}
      {evalMutation.isError && (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Failed to start evaluation: {(evalMutation.error as Error).message}
        </div>
      )}
      {testGenMutation.isError && (
        <div className="rounded border border-red-200 bg-red-50 p-3 text-sm text-red-700">
          Failed to generate tests: {(testGenMutation.error as Error).message}
        </div>
      )}

      {/* Model comparison */}
      {comparisonOutputs.length > 0 && <ModelComparison outputs={comparisonOutputs} />}

      {completedRuns.length >= 2 && comparisonOutputs.length === 0 && (
        <button
          onClick={buildComparison}
          className="rounded border border-gray-300 px-3 py-1.5 text-sm text-gray-600 hover:bg-gray-50"
        >
          Compare {completedRuns.length} completed runs
        </button>
      )}

      {/* Results history */}
      {isLoading ? (
        <p className="text-sm text-gray-500">Loading evaluation history...</p>
      ) : (
        <EvalResults runs={runs} onDelete={handleDelete} />
      )}
    </div>
  );
}
