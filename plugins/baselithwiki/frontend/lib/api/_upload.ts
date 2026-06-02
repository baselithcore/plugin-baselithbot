import { ApiError, BASE, getAccessToken } from './client';

/**
 * Progress callback invoked while bytes are flowing up to the server.
 * `loaded`/`total` mirror XHR `progress` semantics (bytes).
 * `pct` is a convenience: 0..100 when `total` is known, undefined when not.
 */
export interface UploadProgress {
  loaded: number;
  total: number;
  pct: number | undefined;
}

export interface UploadOptions {
  onProgress?: (p: UploadProgress) => void;
  signal?: AbortSignal;
}

/**
 * POST a multipart form with real upload-progress tracking + abort.
 *
 * Why XHR and not fetch: the Fetch API has no first-class request-side
 * progress events. ReadableStream uploads exist but are gated behind
 * `duplex: 'half'` and lack browser support. XHR remains the only
 * portable answer for "show me bytes-uploaded as a percentage".
 *
 * Returns the parsed JSON body. Throws `ApiError(status, text)` on
 * non-2xx; throws `DOMException('AbortError')` when the signal fires.
 */
export function postFormWithProgress<T>(
  path: string,
  form: FormData,
  opts: UploadOptions = {}
): Promise<T> {
  return new Promise<T>((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open('POST', `${BASE}${path}`);
    // Auth: bearer header (mirrors authFetch in client.ts) + cookie
    // credentials for refresh-cookie. Without this, admin uploads hit
    // require_admin → 401 even after a valid login.
    xhr.withCredentials = true;
    const token = getAccessToken();
    if (token) {
      xhr.setRequestHeader('Authorization', `Bearer ${token}`);
    }

    if (opts.onProgress) {
      const cb = opts.onProgress;
      xhr.upload.onprogress = (e) => {
        cb({
          loaded: e.loaded,
          total: e.total,
          pct: e.lengthComputable ? Math.round((e.loaded / e.total) * 100) : undefined,
        });
      };
    }

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as T);
        } catch (err) {
          reject(new ApiError(xhr.status, `invalid JSON response: ${err}`));
        }
        return;
      }
      reject(new ApiError(xhr.status, xhr.responseText || xhr.statusText));
    };
    xhr.onerror = () => reject(new ApiError(0, 'network error'));
    xhr.ontimeout = () => reject(new ApiError(0, 'request timed out'));

    if (opts.signal) {
      if (opts.signal.aborted) {
        xhr.abort();
        reject(new DOMException('aborted', 'AbortError'));
        return;
      }
      opts.signal.addEventListener('abort', () => {
        xhr.abort();
        reject(new DOMException('aborted', 'AbortError'));
      });
    }

    xhr.send(form);
  });
}

/**
 * Bounded-concurrency runner: caps in-flight tasks at `limit`, preserving
 * the input order in the returned `Promise.allSettled`-style result. Use
 * for parallel uploads when each request is heavy on bandwidth/disk and
 * you don't want N requests fighting for the same socket pool.
 */
export async function runWithConcurrency<T, R>(
  items: T[],
  limit: number,
  fn: (item: T, index: number) => Promise<R>
): Promise<PromiseSettledResult<R>[]> {
  const results: PromiseSettledResult<R>[] = new Array(items.length);
  let cursor = 0;
  const workers = new Array(Math.max(1, Math.min(limit, items.length))).fill(0).map(async () => {
    while (true) {
      const i = cursor++;
      if (i >= items.length) return;
      try {
        results[i] = { status: 'fulfilled', value: await fn(items[i], i) };
      } catch (err) {
        results[i] = { status: 'rejected', reason: err };
      }
    }
  });
  await Promise.all(workers);
  return results;
}
