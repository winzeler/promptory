import { apiFetch } from "./client";

export interface EvalRun {
  id: string;
  prompt_id: string;
  prompt_version: string | null;
  provider: string | null;
  model: string | null;
  status: string;
  results: Record<string, unknown> | null;
  error_message: string | null;
  cost_usd: number | null;
  duration_ms: number | null;
  triggered_by: string;
  created_at: string;
}

export interface GeneratedTest {
  description: string;
  vars: Record<string, string>;
  assertions: Array<{ type: string; value: string; threshold?: number }>;
}

export async function runEval(
  promptId: string,
  models: string[],
  variables?: Record<string, string>,
): Promise<{ runs: Array<{ id: string; model: string; status: string }> }> {
  return apiFetch(`/api/v1/admin/prompts/${promptId}/eval`, {
    method: "POST",
    body: JSON.stringify({ models, variables }),
  });
}

export async function fetchEvalRuns(
  promptId: string,
): Promise<{ items: EvalRun[] }> {
  return apiFetch(`/api/v1/admin/prompts/${promptId}/eval/runs`);
}

export async function fetchEvalRun(runId: string): Promise<EvalRun> {
  return apiFetch(`/api/v1/admin/eval/runs/${runId}`);
}

export async function deleteEvalRun(runId: string): Promise<{ ok: boolean }> {
  return apiFetch(`/api/v1/admin/eval/runs/${runId}`, { method: "DELETE" });
}

export async function generateTests(
  promptId: string,
  model?: string,
): Promise<{ tests: GeneratedTest[]; eval_config: Record<string, unknown>; message: string }> {
  return apiFetch(`/api/v1/admin/prompts/${promptId}/generate-tests`, {
    method: "POST",
    body: JSON.stringify({ model }),
  });
}
