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
