import { useState, useEffect, useCallback } from 'react';
import { AnalysisResponse, KbDocumentEntry, JiraIssue } from '../../../types';
import { fetchJiraSearch } from '../../../api/client';
import { inferDocId, mergeJiraResults } from '../analysisUtils';

type UseAnalysisPersistenceProps = {
  initialKb?: { path: string; timestamp: number };
  kbDocuments: KbDocumentEntry[];
  setSelectedKb: (kb: string) => void;
  setFile: (file: File | null) => void;
  analysis: AnalysisResponse | null;
  setAnalysis: React.Dispatch<React.SetStateAction<AnalysisResponse | null>>;
  file: File | null;
  selectedKb: string;
  setPersistedJiraByDoc: React.Dispatch<React.SetStateAction<Record<string, JiraIssue[]>>>;
  setBaselineJiraByDoc: React.Dispatch<React.SetStateAction<Record<string, JiraIssue[]>>>;
};

export const useAnalysisPersistence = ({
  initialKb,
  kbDocuments,
  setSelectedKb,
  setFile,
  analysis,
  setAnalysis,
  file,
  selectedKb,
  setPersistedJiraByDoc,
  setBaselineJiraByDoc,
}: UseAnalysisPersistenceProps) => {
  const [restoreAttempted, setRestoreAttempted] = useState(false);
  const [restoreKey, setRestoreKey] = useState<string | null>(null);
  const [autoRunRequested, setAutoRunRequested] = useState(false);

  const publishLastDocContext = useCallback(
    (payload: AnalysisResponse | null, docHint?: string) => {
      if (typeof window === 'undefined' || !payload) return;
      const docId = inferDocId(payload, docHint || selectedKb, file);
      if (!docId) return;
      try {
        sessionStorage.setItem('console:last-doc-id', docId);
        window.dispatchEvent(new CustomEvent('console:last-doc-updated', { detail: docId }));
      } catch (err) {
        console.error('Unable to persist last doc context', err);
      }
    },
    [selectedKb, file]
  );

  const persistAnalysisCache = useCallback(
    (payload: AnalysisResponse | null, docHint?: string) => {
      if (typeof window === 'undefined' || !payload) return;
      const keys = new Set<string>();
      const docId = inferDocId(payload, docHint || selectedKb, file);
      if (docId) keys.add(docId);
      const kbLabel = payload.kb?.label || (payload.metadata as any)?.kb_label;
      if (kbLabel) keys.add(kbLabel);
      const kbPath = (payload.metadata as any)?.kb_path;
      if (kbPath) keys.add(kbPath);
      keys.forEach((key) => {
        try {
          sessionStorage.setItem(`console:analysis-cache:${key}`, JSON.stringify(payload));
        } catch (err) {
          console.error('Unable to persist analysis cache', err);
        }
      });
      publishLastDocContext(payload, docHint);
    },
    [selectedKb, file, publishLastDocContext]
  );

  const restoreAnalysisCache = (docKey: string | null) => {
    if (typeof window === 'undefined' || !docKey) return null;
    const raw = sessionStorage.getItem(`console:analysis-cache:${docKey}`);
    if (!raw) return null;
    try {
      return JSON.parse(raw) as AnalysisResponse;
    } catch {
      sessionStorage.removeItem(`console:analysis-cache:${docKey}`);
      return null;
    }
  };

  useEffect(() => {
    if (!analysis) return;
    persistAnalysisCache(analysis);
  }, [analysis, persistAnalysisCache]);

  useEffect(() => {
    if (!initialKb?.path) return;
    const cacheKey = `${initialKb.path}:${initialKb.timestamp}`;
    if (restoreAttempted && restoreKey === cacheKey) return;

    // Use an async tick for state bookkeeping to avoid "sync setState in effect" lint error
    // while keeping the restoration logic reactive to initialKb changes.
    const markRestored = (autoRun = false, kbToSelect?: string) => {
      setTimeout(() => {
        setRestoreAttempted(true);
        setRestoreKey(cacheKey);
        if (autoRun) setAutoRunRequested(true);
        if (kbToSelect) {
          setSelectedKb(kbToSelect);
          setFile(null);
        }
      }, 0);
    };

    // Logic to find match in KB documents
    const match = kbDocuments.find(
      (doc) => doc.path === initialKb.path || doc.label === initialKb.path
    );
    const candidates = [initialKb.path, match?.label, match?.path].filter(Boolean) as string[];

    for (const key of candidates) {
      const cached = restoreAnalysisCache(key);
      if (cached) {
        setAnalysis(cached);
        publishLastDocContext(cached, match?.path || initialKb.path);
        markRestored(false, match?.path || initialKb.path);

        // Background refresh dei ticket Jira
        const label = cached.kb?.label || (cached.metadata as any)?.kb_label;
        const labelAliases = (cached.metadata as any)?.jira_label_aliases;
        const labels =
          Array.isArray(labelAliases) && labelAliases.length > 0
            ? labelAliases
            : label
              ? [label]
              : [];
        if (labels.length > 0) {
          fetchJiraSearch(labels)
            .then((res) => {
              if (res.status === 'ok' && res.results.length > 0) {
                setAnalysis((prev) => {
                  if (!prev) return prev;
                  const freshResults = res.results;
                  const docId = inferDocId(prev, match?.path || initialKb.path, null);
                  if (docId) {
                    setPersistedJiraByDoc((map) => ({ ...map, [docId]: freshResults }));
                    setBaselineJiraByDoc((map) => ({ ...map, [docId]: freshResults }));
                  }
                  return {
                    ...prev,
                    jira: {
                      ...prev.jira,
                      results: freshResults,
                    },
                  };
                });
              }
            })
            .catch((e) => console.error('Silent Jira refresh failed', e));
        }
        return;
      }
    }

    // Fallback if no cache found
    markRestored(true, match?.path || initialKb.path);
  }, [
    initialKb,
    kbDocuments,
    restoreAttempted,
    restoreKey,
    setAnalysis,
    setSelectedKb,
    setFile,
    setPersistedJiraByDoc,
    setBaselineJiraByDoc,
    publishLastDocContext,
  ]);

  return {
    persistAnalysisCache,
    autoRunRequested,
    clearAutoRun: () => setAutoRunRequested(false),
  };
};
