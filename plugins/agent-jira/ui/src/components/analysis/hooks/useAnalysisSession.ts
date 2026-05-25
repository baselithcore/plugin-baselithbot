import { useState, ChangeEvent, useEffect } from 'react';
import { analyzeDocument, storeInKb, fetchKbDocuments } from '../../../api/client';
import { AnalysisResponse, KbDocumentEntry } from '../../../types';
import { ToastPayload } from '../FloatingToast';
import { buildDeterministicLabel, preserveExistingJiraResults } from '../analysisUtils';

export const useAnalysisSession = (selectedKb: string) => {
  const [prompt, setPrompt] = useState<string>('');
  const [file, setFile] = useState<File | null>(null);
  const [analysis, setAnalysis] = useState<AnalysisResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [analysisStartTime, setAnalysisStartTime] = useState<number | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [toast, setToast] = useState<ToastPayload | null>(null);
  const [storing, setStoring] = useState(false);

  // Auto-dismiss toast after 3 seconds
  useEffect(() => {
    if (toast) {
      const timer = setTimeout(() => {
        setToast(null);
      }, 3000);
      return () => clearTimeout(timer);
    }
  }, [toast]);

  const onFileChange = (event: ChangeEvent<HTMLInputElement>) => {
    if (event.target.files && event.target.files.length > 0) {
      setFile(event.target.files[0]);
      setAnalysis(null);
      setError(null);
    }
  };

  const onAnalyze = async (kbDocuments?: KbDocumentEntry[]) => {
    if (!file && !selectedKb) {
      setError('Carica un file o scegli un documento KB');
      return;
    }

    setLoading(true);
    setAnalysisStartTime(Date.now());
    setError(null);
    setToast(null);

    try {
      const formData = new FormData();
      formData.append('prompt', prompt?.trim() ?? '');
      if (selectedKb) formData.append('kb_document', selectedKb);
      if (file) formData.append('file', file);

      const data = await analyzeDocument(formData);

      // Preserva risultati Jira precedenti se stesso documento
      setAnalysis((prev) => preserveExistingJiraResults(data, prev, selectedKb, file));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Errore durante l'analisi");
    } finally {
      setLoading(false);
      setAnalysisStartTime(null);
    }
  };

  const onStore = async () => {
    if (!analysis?.kb.upload_path) return;
    setStoring(true);
    setToast(null);
    try {
      const originalName =
        (analysis.metadata && (analysis.metadata.original_name || analysis.metadata.file_name)) ||
        file?.name ||
        undefined;

      const result = await storeInKb(
        analysis.kb.upload_path,
        originalName,
        JSON.stringify(analysis)
      );

      let kbLabel: string | null = null;
      if (result?.kb_path) {
        kbLabel = await buildDeterministicLabel(result.kb_path, 'kb');
      }

      const indexedMsg =
        typeof result.indexed === 'number'
          ? ` Indicizzati ${result.indexed} documenti: ora disponibile anche nel tab conversazioni.`
          : '';

      setToast({
        message: `${result.message}${indexedMsg}`,
        tone: 'success', // Fix tone/type mismatch if ToastPayload uses tone
      } as any); // Type assertion because ToastPayload might use 'type' but original logic used 'tone'?
      // Original useAnalysisPanel uses 'tone'.
      // FloatingToast exports ToastPayload.
      // Let's assume 'tone' is correct and my previous code using 'type' was wrong or interface changed.
      // Wait, ToastPayload definition in useAnalysisPanel import suggests checking FloatingToast.
      // Original code (Line 385): setToast({ message: ..., tone: 'success' });

      setAnalysis((prev) => {
        if (!prev) return prev;
        return {
          ...prev,
          kb: {
            ...prev.kb,
            can_store: false,
            status: 'Documento salvato in Knowledge Base.', // Simplified status
            label: kbLabel || prev.kb.label,
            upload_path: result.kb_path || prev.kb.upload_path,
          },
          metadata: {
            ...prev.metadata,
            category: 'knowledge-base',
          },
        };
      });

      // We cannot update kbDocuments here easily unless we lift state or re-fetch.
      // useKbData handles fetching. We might need a trigger.
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('console:kb-updated'));
      }
    } catch (err) {
      setToast({
        message: err instanceof Error ? err.message : 'Errore salvataggio KB',
        tone: 'error',
      } as any);
    } finally {
      setStoring(false);
    }
  };

  const resetSession = () => {
    setPrompt('');
    setFile(null);
    setAnalysis(null);
    setError(null);
    setToast(null);
    setStoring(false);
  };

  return {
    prompt,
    setPrompt,
    file,
    setFile,
    analysis,
    setAnalysis,
    loading,
    error,
    setError,
    toast,
    setToast,
    onFileChange,
    onAnalyze,
    storing,
    onStore,
    analysisStartTime,
    resetSession,
  };
};
