import { apiFetch } from "./client";

export interface PromptListItem {
  id: string;
  name: string;
  domain: string | null;
  description: string | null;
  type: string;
  environment: string;
  tags: string[];
  active: boolean;
  version: string | null;
  default_model: string | null;
  modality_input: string | null;
  modality_output: string | null;
  updated_at: string | null;
}

export interface PromptDetail {
  id: string;
  name: string;
  version: string;
  org: string;
  app: string;
  domain: string | null;
  description: string | null;
  type: string;
  role: string;
  model: Record<string, unknown>;
  modality: Record<string, string> | null;
  tts: Record<string, unknown> | null;
  audio: Record<string, unknown> | null;
  environment: string;
  active: boolean;
  tags: string[];
  body: string;
  includes: string[];
  eval: Record<string, unknown> | null;
  git_sha: string | null;
  updated_at: string | null;
}

export interface Org {
  id: string;
  github_owner: string;
  display_name: string | null;
  avatar_url: string | null;
}

export interface App {
  id: string;
  org_id: string;
  github_repo: string;
  subdirectory: string;
  display_name: string | null;
  default_branch: string;
  last_synced_at: string | null;
}

export async function fetchOrgs(): Promise<Org[]> {
  const resp = await apiFetch<{ items: Org[] }>("/api/v1/admin/orgs");
  return resp.items;
}

export async function fetchApps(orgId: string): Promise<App[]> {
  const resp = await apiFetch<{ items: App[] }>(
    `/api/v1/admin/orgs/${orgId}/apps`
  );
  return resp.items;
}

export async function fetchPrompts(
  appId: string,
  params?: Record<string, string>
): Promise<{ items: PromptListItem[]; total: number }> {
  const query = params
    ? "?" + new URLSearchParams(params).toString()
    : "";
  return apiFetch(`/api/v1/admin/apps/${appId}/prompts${query}`);
}

export async function fetchPromptDetail(
  promptId: string
): Promise<PromptDetail> {
  return apiFetch(`/api/v1/admin/prompts/${promptId}`);
}

export async function updatePrompt(
  promptId: string,
  data: { front_matter?: Record<string, unknown>; body?: string; commit_message: string }
): Promise<unknown> {
  return apiFetch(`/api/v1/admin/prompts/${promptId}`, {
    method: "PUT",
    body: JSON.stringify(data),
  });
}

export async function createPrompt(
  data: Record<string, unknown>
): Promise<unknown> {
  return apiFetch("/api/v1/admin/prompts", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function deletePrompt(
  promptId: string,
  commitMessage: string
): Promise<void> {
  await apiFetch(`/api/v1/admin/prompts/${promptId}`, {
    method: "DELETE",
    body: JSON.stringify({ commit_message: commitMessage }),
  });
}

export async function fetchPromptHistory(
  promptId: string
): Promise<{ items: Array<{ sha: string; message: string; author: string; date: string }> }> {
  return apiFetch(`/api/v1/admin/prompts/${promptId}/history`);
}

export async function syncApp(appId: string): Promise<{ synced: number }> {
  return apiFetch(`/api/v1/admin/apps/${appId}/sync`, { method: "POST" });
}

export async function syncAll(): Promise<{ synced: number }> {
  return apiFetch("/api/v1/admin/sync", { method: "POST" });
}

export async function fetchTTSStatus(): Promise<{ configured: boolean; provider: string | null }> {
  return apiFetch("/api/v1/admin/tts/status");
}

export async function previewTTS(
  promptId: string,
  data: { variables: Record<string, unknown>; tts_config?: Record<string, unknown> }
): Promise<Blob> {
  const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
  const resp = await fetch(`${API_BASE}/api/v1/admin/prompts/${promptId}/tts-preview`, {
    method: "POST",
    credentials: "include",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  });
  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new Error(body?.error?.message || resp.statusText);
  }
  return resp.blob();
}

// ── Analytics ──

export interface AnalyticsItem {
  day?: string;
  count?: number;
  total?: number;
  hits?: number;
  hit_rate?: number;
  avg_ms?: number;
  min_ms?: number;
  max_ms?: number;
  sample_count?: number;
  prompt_id?: string;
  prompt_name?: string;
  request_count?: number;
  avg_latency_ms?: number;
  cache_rate?: number;
  api_key_id?: string;
  key_name?: string;
}

export async function fetchRequestsPerDay(
  appId?: string,
  days = 30
): Promise<{ items: AnalyticsItem[] }> {
  const params = new URLSearchParams({ days: String(days) });
  if (appId) params.set("app_id", appId);
  return apiFetch(`/api/v1/admin/analytics/requests-per-day?${params}`);
}

export async function fetchCacheHitRate(
  appId?: string,
  days = 30
): Promise<{ items: AnalyticsItem[] }> {
  const params = new URLSearchParams({ days: String(days) });
  if (appId) params.set("app_id", appId);
  return apiFetch(`/api/v1/admin/analytics/cache-hit-rate?${params}`);
}

export async function fetchTopPrompts(
  appId?: string,
  days = 30,
  limit = 10
): Promise<{ items: AnalyticsItem[] }> {
  const params = new URLSearchParams({ days: String(days), limit: String(limit) });
  if (appId) params.set("app_id", appId);
  return apiFetch(`/api/v1/admin/analytics/top-prompts?${params}`);
}

export async function fetchUsageByKey(
  days = 30,
  limit = 10
): Promise<{ items: AnalyticsItem[] }> {
  const params = new URLSearchParams({ days: String(days), limit: String(limit) });
  return apiFetch(`/api/v1/admin/analytics/usage-by-key?${params}`);
}

// ── Prompt content at SHA (for diff viewer) ──

export async function fetchPromptContentAtSha(
  promptId: string,
  sha: string
): Promise<{ sha: string; front_matter: Record<string, unknown>; body: string; raw: string }> {
  return apiFetch(`/api/v1/admin/prompts/${promptId}/at/${sha}`);
}

// ── Batch operations ──

export async function batchUpdatePrompts(data: {
  prompt_ids: string[];
  action?: string;
  field: string;
  value: unknown;
  commit_message?: string;
}): Promise<{ ok: boolean; updated: number; commit_sha: string }> {
  return apiFetch("/api/v1/admin/prompts/batch", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

export async function batchDeletePrompts(data: {
  prompt_ids: string[];
  commit_message?: string;
}): Promise<{ ok: boolean; deleted: number }> {
  return apiFetch("/api/v1/admin/prompts/batch-delete", {
    method: "POST",
    body: JSON.stringify(data),
  });
}

// ── Prompty import/export ──

export async function exportPrompty(promptId: string): Promise<string> {
  const API_BASE = import.meta.env.VITE_API_BASE_URL || "";
  const resp = await fetch(`${API_BASE}/api/v1/admin/prompts/${promptId}/export/prompty`, {
    credentials: "include",
  });
  if (!resp.ok) throw new Error("Export failed");
  return resp.text();
}

export async function importPrompty(
  appId: string,
  content: string
): Promise<unknown> {
  return apiFetch("/api/v1/admin/prompts/import/prompty", {
    method: "POST",
    body: JSON.stringify({ app_id: appId, content }),
  });
}
