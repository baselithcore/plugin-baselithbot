export const BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://127.0.0.1:8765/api/v1";

export async function jsonOrThrow<T>(res: Response, label: string): Promise<T> {
  if (!res.ok) {
    const txt = await res.text().catch(() => "");
    throw new Error(`${label} failed: ${res.status} ${txt}`);
  }
  return res.status === 204 ? (undefined as T) : res.json();
}

/** Upload-progress callback. `phase` flips to "processing" once bytes finish
 * and we wait for the server response. */
export type UploadProgress = (e: {
  phase: "uploading" | "processing";
  loaded: number;
  total: number;
  pct: number;
}) => void;

/** XHR-based POST that surfaces upload byte progress. Falls back to indeterminate
 * `processing` phase once the request body finishes streaming. */
export function postFormWithProgress<T>(
  url: string,
  fd: FormData,
  headers: Record<string, string>,
  onProgress?: UploadProgress,
  label = "upload",
): Promise<T> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", url);
    for (const [k, v] of Object.entries(headers)) xhr.setRequestHeader(k, v);
    xhr.upload.onprogress = (ev) => {
      if (!onProgress) return;
      const total = ev.lengthComputable ? ev.total : 0;
      const pct = total ? Math.round((ev.loaded / total) * 100) : 0;
      onProgress({ phase: "uploading", loaded: ev.loaded, total, pct });
    };
    xhr.upload.onload = () => {
      onProgress?.({ phase: "processing", loaded: 0, total: 0, pct: 100 });
    };
    xhr.onerror = () => reject(new Error(`${label} network error`));
    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(
            xhr.responseText
              ? (JSON.parse(xhr.responseText) as T)
              : (undefined as T),
          );
        } catch (e) {
          reject(e);
        }
      } else {
        const err = new Error(
          `${label} failed: ${xhr.status} ${xhr.responseText}`,
        ) as Error & { status?: number; detail?: string };
        err.status = xhr.status;
        try {
          err.detail = JSON.parse(xhr.responseText)?.detail ?? xhr.responseText;
        } catch {
          err.detail = xhr.responseText;
        }
        reject(err);
      }
    };
    xhr.send(fd);
  });
}
