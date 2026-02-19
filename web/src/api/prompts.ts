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
