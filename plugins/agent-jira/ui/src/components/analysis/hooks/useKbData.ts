import { useState, useEffect } from 'react';
import { fetchKbDocuments } from '../../../api/client';
import { KbDocumentEntry } from '../../../types';

export const useKbData = (initialKb: { path: string; timestamp: number } | null = null) => {
  const [selectedKb, setSelectedKb] = useState<string>(initialKb?.path || '');
  const [kbDocuments, setKbDocuments] = useState<KbDocumentEntry[]>([]);
  const [loadingKb, setLoadingKb] = useState<boolean>(true);

  // Sync with prop change without useEffect
  const [prevInitialId, setPrevInitialId] = useState(initialKb?.timestamp);
  if (initialKb?.timestamp !== prevInitialId) {
    setPrevInitialId(initialKb?.timestamp);
    setSelectedKb(initialKb?.path || '');
  }

  useEffect(() => {
    fetchKbDocuments()
      .then((res) => {
        setKbDocuments(res.documents);
      })
      .catch((err) => {
        console.error('Failed to fetch KB documents', err);
      })
      .finally(() => {
        setLoadingKb(false);
      });
  }, []);

  return {
    selectedKb,
    setSelectedKb,
    kbDocuments,
    loadingKb,
  };
};
