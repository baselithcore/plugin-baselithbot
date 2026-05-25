import { useRef, useState } from 'react';
import { toast } from 'sonner';
import {
  applyScaffold,
  runWithConcurrency,
  updateTenantTheme,
  uploadTenantLogo,
  uploadTenantRaw,
  type ScaffoldRequestBody,
  type ScaffoldResultResponse,
} from '../../lib/api';
import type { DocUploadState } from '../upload/DocUploadList';
import { humanError } from './helpers';
import { DRAFT_KEY } from './schema';

export type ApplyPhase = 'idle' | 'scaffold' | 'theme' | 'logo' | 'docs' | 'done';

export type { DocUploadState };

export interface ScaffoldApplyState {
  applying: boolean;
  phase: ApplyPhase;
  /** Only meaningful while phase === 'docs'. Keys are filenames; ordered to match `docFiles`. */
  docs: DocUploadState[];
  result: ScaffoldResultResponse | null;
}

interface UseScaffoldApplyArgs {
  buildBody: () => ScaffoldRequestBody;
  themeBody: () => { primary?: string; primary_hover?: string; accent?: string };
  logoFile: File | null;
  docFiles: File[];
  /** Concurrent doc uploads. Default 3 — keeps a busy disk + bandwidth
   * happy without N parallel requests dog-piling the FastAPI worker. */
  docConcurrency?: number;
  onScaffolded?: (r: ScaffoldResultResponse) => void;
}

const DOCS_KEY = 'llm-wiki:conversations';

export function useScaffoldApply({
  buildBody,
  themeBody,
  logoFile,
  docFiles,
  docConcurrency = 3,
  onScaffolded,
}: UseScaffoldApplyArgs) {
  const [state, setState] = useState<ScaffoldApplyState>({
    applying: false,
    phase: 'idle',
    docs: [],
    result: null,
  });
  const abortRef = useRef<AbortController | null>(null);

  const cancel = () => {
    abortRef.current?.abort();
  };

  const apply = async (): Promise<ScaffoldResultResponse | null> => {
    abortRef.current?.abort();
    const ctrl = new AbortController();
    abortRef.current = ctrl;

    const initialDocs: DocUploadState[] = docFiles.map((f) => ({
      filename: f.name,
      size: f.size,
      pct: 0,
      status: 'pending',
    }));

    setState({ applying: true, phase: 'scaffold', docs: initialDocs, result: null });

    let result: ScaffoldResultResponse;
    try {
      result = await applyScaffold(buildBody(), ctrl.signal);
    } catch (err) {
      setState((s) => ({ ...s, applying: false, phase: 'idle' }));
      toast.error(humanError(err));
      return null;
    }

    // Theme: persist if any color was specified.
    const tb = themeBody();
    if (Object.keys(tb).length > 0) {
      setState((s) => ({ ...s, phase: 'theme' }));
      try {
        await updateTenantTheme(result.name, tb, ctrl.signal);
      } catch {
        toast.error('Tema non salvato (continuo).');
      }
    }

    // Logo upload (single file, sequential — fast).
    if (logoFile) {
      setState((s) => ({ ...s, phase: 'logo' }));
      try {
        await uploadTenantLogo(result.name, logoFile, { signal: ctrl.signal });
      } catch (err) {
        toast.error(`Logo non caricato: ${humanError(err)}`);
      }
    }

    // Doc uploads in parallel with bounded concurrency + per-file progress.
    if (docFiles.length > 0) {
      setState((s) => ({ ...s, phase: 'docs' }));
      const settled = await runWithConcurrency(docFiles, docConcurrency, async (file, i) => {
        setState((s) => ({
          ...s,
          docs: replaceAt(s.docs, i, { ...s.docs[i], status: 'uploading' }),
        }));
        try {
          await uploadTenantRaw(
            result.name,
            file,
            { overwrite: false },
            {
              signal: ctrl.signal,
              onProgress: (p) => {
                setState((s) => ({
                  ...s,
                  docs: replaceAt(s.docs, i, {
                    ...s.docs[i],
                    pct: p.pct ?? Math.round((p.loaded / Math.max(1, file.size)) * 100),
                  }),
                }));
              },
            }
          );
          setState((s) => ({
            ...s,
            docs: replaceAt(s.docs, i, { ...s.docs[i], pct: 100, status: 'done' }),
          }));
        } catch (err) {
          const aborted = (err as Error)?.name === 'AbortError';
          const msg = aborted ? 'aborted' : humanError(err);
          setState((s) => ({
            ...s,
            docs: replaceAt(s.docs, i, { ...s.docs[i], status: 'error', error: msg }),
          }));
          if (!aborted) toast.error(`${file.name}: ${msg}`);
          throw err;
        }
      });
      const okCount = settled.filter((s) => s.status === 'fulfilled').length;
      toast.success(`${okCount}/${docFiles.length} documenti caricati.`);
    }

    setState((s) => ({ ...s, phase: 'done', applying: false, result }));
    onScaffolded?.(result);

    try {
      localStorage.removeItem(DRAFT_KEY);
      localStorage.removeItem(DOCS_KEY); // fresh start with new wiki
    } catch {
      /* noop */
    }

    return result;
  };

  return { state, apply, cancel };
}

function replaceAt<T>(arr: T[], idx: number, value: T): T[] {
  const next = arr.slice();
  next[idx] = value;
  return next;
}
