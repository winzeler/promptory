const API_BASE = import.meta.env.VITE_API_BASE_URL || "";

export async function apiFetch<T = unknown>(
  path: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE}${path}`;
  const resp = await fetch(url, {
    credentials: "include",
    headers: {
      "Content-Type": "application/json",
      ...options.headers,
    },
    ...options,
  });

  if (!resp.ok) {
    const body = await resp.json().catch(() => ({}));
    throw new ApiError(
      body?.error?.message || resp.statusText,
      resp.status,
      body?.error?.code
    );
  }

  if (resp.status === 204) return undefined as T;
  return resp.json();
}

export class ApiError extends Error {
  constructor(
    message: string,
    public status: number,
    public code?: string
  ) {
    super(message);
    this.name = "ApiError";
  }
}
