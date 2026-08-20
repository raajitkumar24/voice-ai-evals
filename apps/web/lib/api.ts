export class ApiError extends Error {
  constructor(
    public readonly status: number,
    message: string,
  ) {
    super(message);
  }
}

export async function api<T>(path: string, init?: RequestInit): Promise<T> {
  const csrf = typeof document === "undefined"
    ? ""
    : document.cookie.split("; ").find((item) => item.startsWith("voice_evals_csrf="))?.split("=")[1] ?? "";
  const response = await fetch(`/api/v1${path}`, {
    credentials: "include",
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...(csrf ? {"X-CSRF-Token": decodeURIComponent(csrf)} : {}),
      ...init?.headers,
    },
  });
  if (!response.ok) {
    const body = (await response.json().catch(() => null)) as {detail?: string} | null;
    throw new ApiError(response.status, body?.detail ?? `Request failed (${response.status})`);
  }
  return (await response.json()) as T;
}

export function percent(value: number | null | undefined): string {
  return value == null ? "—" : `${Math.round(value * 1000) / 10}%`;
}
