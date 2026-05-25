import { authHeaders } from "../auth";
import { BASE } from "./_base";
import type {
  ChunkRow,
  DocumentReportRow,
  DocumentRow,
  ListDocumentsParams,
  ListDocumentsResult,
  Report,
} from "./types";

export interface AnalyzeOptions {
  lang?: string;
}

export async function uploadDocument(
  file: File,
): Promise<{ id: string; sha256: string }> {
  const fd = new FormData();
  fd.append("file", file);
  const res = await fetch(`${BASE}/documents`, {
    method: "POST",
    body: fd,
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`upload failed: ${res.status}`);
  return res.json();
}

export async function analyzeDocument(
  docId: string,
  policies: string[],
  options: AnalyzeOptions = {},
): Promise<Report> {
  const body: Record<string, unknown> = { policies };
  if (options.lang) body.lang = options.lang;
  const res = await fetch(`${BASE}/documents/${docId}/analyze`, {
    method: "POST",
    headers: { "Content-Type": "application/json", ...authHeaders() },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    let detail: unknown = null;
    try {
      detail = await res.json();
    } catch {
      /* non-JSON */
    }
    const d = (detail as { detail?: unknown })?.detail;
    if (d && typeof d === "object" && "message" in d) {
      throw new Error(String((d as { message: string }).message));
    }
    throw new Error(`analyze failed: ${res.status}`);
  }
  return res.json();
}

export async function listDocuments(
  arg: number | ListDocumentsParams = 50,
): Promise<DocumentRow[]> {
  const params: ListDocumentsParams =
    typeof arg === "number" ? { limit: arg } : arg;
  const result = await listDocumentsPage(params);
  return result.rows;
}

export async function listDocumentsPage(
  params: ListDocumentsParams = {},
): Promise<ListDocumentsResult> {
  const qs = new URLSearchParams();
  qs.set("limit", String(params.limit ?? 50));
  if (params.offset) qs.set("offset", String(params.offset));
  if (params.q) qs.set("q", params.q);
  if (params.status && params.status.length)
    qs.set("status", params.status.join(","));
  const res = await fetch(`${BASE}/documents?${qs.toString()}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`docs failed: ${res.status}`);
  const total = Number(res.headers.get("X-Total-Count") ?? "0");
  const rows = (await res.json()) as DocumentRow[];
  return { rows, total };
}

export async function getDocument(docId: string): Promise<DocumentRow> {
  const res = await fetch(`${BASE}/documents/${docId}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`get doc failed: ${res.status}`);
  return res.json();
}

export async function deleteDocument(docId: string): Promise<void> {
  const res = await fetch(`${BASE}/documents/${docId}`, {
    method: "DELETE",
    headers: { ...authHeaders() },
  });
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`delete failed: ${res.status} ${txt}`);
  }
}

export async function downloadDocument(
  docId: string,
  filename: string,
): Promise<void> {
  const res = await fetch(`${BASE}/documents/${docId}/download`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`download failed: ${res.status}`);
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  a.remove();
  URL.revokeObjectURL(url);
}

export async function listDocumentReports(
  docId: string,
): Promise<DocumentReportRow[]> {
  const res = await fetch(`${BASE}/documents/${docId}/reports`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`doc reports failed: ${res.status}`);
  return res.json();
}

export async function getChunks(docId: string): Promise<ChunkRow[]> {
  const res = await fetch(`${BASE}/documents/${docId}/chunks`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`chunks failed: ${res.status}`);
  return res.json();
}

export async function getReport(reportId: string): Promise<Report> {
  const res = await fetch(`${BASE}/reports/${reportId}`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`get report failed: ${res.status}`);
  return res.json();
}

export async function exportReportMarkdown(docId: string): Promise<string> {
  const res = await fetch(`${BASE}/reports/${docId}/export.md`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`export.md failed: ${res.status}`);
  return res.text();
}

export async function exportReportJson(docId: string): Promise<unknown> {
  const res = await fetch(`${BASE}/reports/${docId}/export.json`, {
    headers: { ...authHeaders() },
  });
  if (!res.ok) throw new Error(`export.json failed: ${res.status}`);
  return res.json();
}
