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

export async function runEval(
  promptId: string,
  models: string[]
): Promise<{ runs: Array<{ id: string; model: string; status: string }> }> {
  return apiFetch(`/api/v1/admin/prompts/${promptId}/eval`, {
    method: "POST",
    body: JSON.stringify({ models }),
  });
}

export async function fetchEvalRuns(
  promptId: string
): Promise<{ items: EvalRun[] }> {
  return apiFetch(`/api/v1/admin/prompts/${promptId}/eval/runs`);
}
