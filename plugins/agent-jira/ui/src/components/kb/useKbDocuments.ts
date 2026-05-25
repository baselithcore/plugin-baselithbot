import { useState, useEffect, useCallback } from 'react';
import { fetchKbDocuments, deleteKbDocument } from '../../api/client';
import { KbDocumentEntry } from '../../types';

export const useKbDocuments = () => {
  const [docs, setDocs] = useState<KbDocumentEntry[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleting, setDeleting] = useState<string | null>(null);

  const loadDocs = useCallback((isInitial: boolean) => {
    if (isInitial) setLoading(true);
    fetchKbDocuments()
      .then((res) => setDocs(res.documents || []))
      .catch((err) => {
        if (isInitial) setError(err instanceof Error ? err.message : 'Errore nel caricamento KB');
        else console.error(err);
      })
      .finally(() => {
        if (isInitial) setLoading(false);
      });
  }, []);

  useEffect(() => {
    loadDocs(true);
    const handleUpdate = () => loadDocs(false);
    window.addEventListener('console:kb-updated', handleUpdate);
    return () => window.removeEventListener('console:kb-updated', handleUpdate);
  }, [loadDocs]);

  const removeDocument = async (path: string) => {
    if (!window.confirm('Sei sicuro di voler eliminare questo documento dalla KB?')) return;
    setDeleting(path);
    try {
      await deleteKbDocument(path);
      if (typeof window !== 'undefined') {
        window.dispatchEvent(new CustomEvent('console:kb-updated'));
      }
    } catch (err) {
      alert(err instanceof Error ? err.message : "Errore durante l'eliminazione");
    } finally {
      setDeleting(null);
    }
  };

  return {
    docs,
    loading,
    error,
    deleting,
    removeDocument,
    refresh: () => loadDocs(false),
  };
};
