"use client";

import { useState } from "react";
import { getHealth } from "@/shared/api/health";

export function SystemStatus() {
  const [status, setStatus] = useState("Not checked");
  const [pending, setPending] = useState(false);
  async function check() {
    setPending(true);
    setStatus("Checking control API…");
    try {
      await getHealth(AbortSignal.timeout(5000));
      setStatus("Control API reachable · local reference mode");
    } catch {
      setStatus("Control API unavailable. Start the backend and retry.");
    } finally { setPending(false); }
  }
  return <section aria-labelledby="status-heading">
    <h2 id="status-heading">Development connection</h2>
    <p role="status" aria-live="polite">{status}</p>
    <button type="button" disabled={pending} onClick={check}>Check connection</button>
  </section>;
}
