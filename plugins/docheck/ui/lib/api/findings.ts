import { authHeaders } from "../auth";
import { BASE } from "./_base";
import type { Decision, DecisionKind, ReportSummary } from "./types";

export async function setFindingDecision(
  reportId: string,
  findingId: string,
  decision: DecisionKind,
  note?: string,
): Promise<{ ok: boolean; decision: DecisionKind }> {
  const res = await fetch(
    `${BASE}/reports/${reportId}/findings/${findingId}/decision`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ decision, note }),
    },
  );
  if (!res.ok) throw new Error(`decision failed: ${res.status}`);
  return res.json();
}

export async function listDecisions(
  reportId: string,
): Promise<Record<string, Decision>> {
  const res = await fetch(`${BASE}/reports/${reportId}/decisions`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`decisions failed: ${res.status}`);
  return res.json();
}

export async function askFinding(
  reportId: string,
  findingId: string,
  question: string,
): Promise<{ answer: string; grounded: boolean }> {
  const res = await fetch(
    `${BASE}/reports/${reportId}/findings/${findingId}/ask`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ question }),
    },
  );
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`ask failed: ${res.status} ${txt}`);
  }
  return res.json();
}

export interface AskStreamHandlers {
  onToken: (text: string) => void;
  onDone: (full: string, grounded: boolean) => void;
  onError: (message: string) => void;
  signal?: AbortSignal;
}

export async function askFindingStream(
  reportId: string,
  findingId: string,
  question: string,
  handlers: AskStreamHandlers,
): Promise<void> {
  const res = await fetch(
    `${BASE}/reports/${reportId}/findings/${findingId}/ask/stream`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json", ...authHeaders() },
      body: JSON.stringify({ question }),
      signal: handlers.signal,
    },
  );
  if (!res.ok || !res.body) {
    const txt = await res.text().catch(() => "");
    handlers.onError(`ask stream failed: ${res.status} ${txt}`);
    return;
  }

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buf = "";
  let full = "";
  let grounded = false;
  let done = false;

  while (!done) {
    const { value, done: streamDone } = await reader.read();
    if (streamDone) break;
    buf += decoder.decode(value, { stream: true });
    let nl = buf.indexOf("\n");
    while (nl !== -1) {
      const line = buf.slice(0, nl).trim();
      buf = buf.slice(nl + 1);
      nl = buf.indexOf("\n");
      if (!line) continue;
      try {
        const evt = JSON.parse(line) as
          | { type: "token"; text: string }
          | { type: "done"; grounded: boolean; answer: string }
          | { type: "error"; message: string };
        if (evt.type === "token") {
          full += evt.text;
          handlers.onToken(evt.text);
        } else if (evt.type === "done") {
          full = evt.answer || full;
          grounded = evt.grounded;
          done = true;
        } else if (evt.type === "error") {
          handlers.onError(evt.message);
          return;
        }
      } catch {
        // Tolerate stray lines (e.g. mid-decode boundaries) silently.
      }
    }
  }
  handlers.onDone(full, grounded);
}

export async function getReportSummary(
  reportId: string,
  locale?: string,
): Promise<ReportSummary> {
  const qs = locale ? `?locale=${encodeURIComponent(locale)}` : "";
  const ctl = new AbortController();
  const timer = setTimeout(() => ctl.abort(), 60_000);
  try {
    const res = await fetch(`${BASE}/reports/${reportId}/summary${qs}`, {
      method: "POST",
      headers: { ...authHeaders() },
      signal: ctl.signal,
    });
    if (!res.ok) {
      const txt = await res.text().catch(() => "");
      throw new Error(`summary failed: ${res.status} ${txt}`);
    }
    return await res.json();
  } catch (err) {
    if ((err as { name?: string })?.name === "AbortError") {
      throw new Error("summary timeout (60s)");
    }
    throw err;
  } finally {
    clearTimeout(timer);
  }
}
