import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import {
  fetchOrgs,
  fetchApps,
  fetchPrompts,
  fetchPromptDetail,
  updatePrompt,
  createPrompt,
  deletePrompt,
  fetchPromptHistory,
  syncApp,
  fetchTTSStatus,
  previewTTS,
  fetchRequestsPerDay,
  fetchCacheHitRate,
  fetchTopPrompts,
  fetchUsageByKey,
  fetchPromptContentAtSha,
  batchUpdatePrompts,
  batchDeletePrompts,
} from "../api/prompts";

export function useOrgs() {
  return useQuery({ queryKey: ["orgs"], queryFn: fetchOrgs });
}

export function useApps(orgId: string | null) {
  return useQuery({
    queryKey: ["apps", orgId],
    queryFn: () => fetchApps(orgId!),
    enabled: !!orgId,
  });
}

export function usePromptList(appId: string | null, params?: Record<string, string>) {
  return useQuery({
    queryKey: ["prompts", appId, params],
    queryFn: () => fetchPrompts(appId!, params),
    enabled: !!appId,
  });
}

export function usePromptDetail(promptId: string | null) {
  return useQuery({
    queryKey: ["prompt", promptId],
    queryFn: () => fetchPromptDetail(promptId!),
    enabled: !!promptId,
  });
}

export function usePromptHistory(promptId: string | null) {
  return useQuery({
    queryKey: ["prompt-history", promptId],
    queryFn: () => fetchPromptHistory(promptId!),
    enabled: !!promptId,
  });
}

export function useUpdatePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, data }: { id: string; data: Parameters<typeof updatePrompt>[1] }) =>
      updatePrompt(id, data),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: ["prompt", id] });
      qc.invalidateQueries({ queryKey: ["prompts"] });
    },
  });
}

export function useCreatePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createPrompt,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prompts"] }),
  });
}

export function useDeletePrompt() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, message }: { id: string; message: string }) =>
      deletePrompt(id, message),
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prompts"] }),
  });
}

export function useSyncApp() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: syncApp,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prompts"] }),
  });
}

export function useTTSStatus() {
  return useQuery({
    queryKey: ["tts-status"],
    queryFn: fetchTTSStatus,
    staleTime: 60_000,
  });
}

export function useTTSPreview() {
  return useMutation({
    mutationFn: ({ promptId, data }: { promptId: string; data: { variables: Record<string, unknown>; tts_config?: Record<string, unknown> } }) =>
      previewTTS(promptId, data),
  });
}

// ── Analytics hooks ──

export function useRequestsPerDay(appId?: string, days = 30) {
  return useQuery({
    queryKey: ["analytics", "requests-per-day", appId, days],
    queryFn: () => fetchRequestsPerDay(appId, days),
    staleTime: 60_000,
  });
}

export function useCacheHitRate(appId?: string, days = 30) {
  return useQuery({
    queryKey: ["analytics", "cache-hit-rate", appId, days],
    queryFn: () => fetchCacheHitRate(appId, days),
    staleTime: 60_000,
  });
}

export function useTopPrompts(appId?: string, days = 30, limit = 10) {
  return useQuery({
    queryKey: ["analytics", "top-prompts", appId, days, limit],
    queryFn: () => fetchTopPrompts(appId, days, limit),
    staleTime: 60_000,
  });
}

export function useUsageByKey(days = 30, limit = 10) {
  return useQuery({
    queryKey: ["analytics", "usage-by-key", days, limit],
    queryFn: () => fetchUsageByKey(days, limit),
    staleTime: 60_000,
  });
}

// ── Prompt content at SHA (for diff viewer) ──

export function usePromptContentAtSha(promptId: string | null, sha: string | null) {
  return useQuery({
    queryKey: ["prompt-at-sha", promptId, sha],
    queryFn: () => fetchPromptContentAtSha(promptId!, sha!),
    enabled: !!promptId && !!sha,
  });
}

// ── Batch operations ──

export function useBatchUpdate() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: batchUpdatePrompts,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prompts"] }),
  });
}

export function useBatchDelete() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: batchDeletePrompts,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["prompts"] }),
  });
}
