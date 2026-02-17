import { useQuery, useQueryClient } from "@tanstack/react-query";
import { fetchCurrentUser, logout as logoutApi, User } from "../api/auth";

export function useAuth() {
  const queryClient = useQueryClient();

  const { data: user, isLoading: loading } = useQuery({
    queryKey: ["auth", "me"],
    queryFn: fetchCurrentUser,
    retry: false,
    staleTime: 60_000,
  });

  const logout = async () => {
    await logoutApi();
    queryClient.setQueryData(["auth", "me"], null);
    window.location.href = "/login";
  };

  return { user: user ?? null, loading, logout };
}
