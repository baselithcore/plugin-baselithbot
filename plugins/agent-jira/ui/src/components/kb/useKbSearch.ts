import { useState, useMemo } from 'react';
import { KbDocumentEntry } from '../../types';

export const useKbSearch = (docs: KbDocumentEntry[]) => {
  const [query, setQuery] = useState('');

  const filteredDocs = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return docs;
    return docs.filter((doc) => {
      const fileName = doc.path.split('/').pop() || doc.path;
      const stem = fileName.replace(/\.[^.]+$/, '');
      const haystack = `${doc.label || ''} ${doc.path} ${fileName} ${stem}`.toLowerCase();
      return haystack.includes(q);
    });
  }, [docs, query]);

  const suggestions = useMemo(() => filteredDocs.slice(0, 6), [filteredDocs]);

  return {
    query,
    setQuery,
    filteredDocs,
    suggestions,
  };
};
