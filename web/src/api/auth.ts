import { apiFetch } from "./client";

export interface User {
  id: string;
  github_login: string;
  display_name: string | null;
  email: string | null;
  avatar_url: string | null;
  is_admin: boolean;
}

export async function fetchCurrentUser(): Promise<User | null> {
  const resp = await apiFetch<{ user: User | null }>("/api/v1/auth/me");
  return resp.user;
}

export async function logout(): Promise<void> {
  await apiFetch("/api/v1/auth/logout", { method: "POST" });
}
