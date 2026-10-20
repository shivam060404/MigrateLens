import type { HealthResponse } from "./generated";

export async function getHealth(signal?: AbortSignal): Promise<HealthResponse> {
  const response = await fetch("/api/v1/health/live", { signal, cache: "no-store" });
  if (!response.ok) throw new Error("The control API is unavailable.");
  const body: unknown = await response.json();
  if (typeof body !== "object" || body === null || !("status" in body) ||
      body.status !== "ok" || !("service" in body) || body.service !== "migratelens-control" ||
      !("mode" in body) || body.mode !== "local-reference") {
    throw new Error("The control API returned an unexpected response.");
  }
  return body as HealthResponse;
}
