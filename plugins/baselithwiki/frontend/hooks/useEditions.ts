import { useEffect, useMemo, useState } from 'react';
import { fetchEditions } from '../lib/api';
import { ALL_EDITIONS_ID, type EditionOption } from '../components/EditionSelector';

const EDITION_KEY = 'llm-wiki:edition';

/**
 * Loads editions from `/api/groups/editions` and persists the selected
 * edition id to localStorage. Returns the current selection + label.
 */
export function useEditions() {
  const [editionId, setEditionId] = useState<string>(() => {
    try {
      return localStorage.getItem(EDITION_KEY) ?? ALL_EDITIONS_ID;
    } catch {
      return ALL_EDITIONS_ID;
    }
  });
  const [editions, setEditions] = useState<EditionOption[]>([]);

  useEffect(() => {
    try {
      localStorage.setItem(EDITION_KEY, editionId);
    } catch {
      /* storage disabled */
    }
  }, [editionId]);

  // carica edizioni dal backend (raggruppate per prodotto+edizione-iso)
  useEffect(() => {
    const ctrl = new AbortController();
    fetchEditions(ctrl.signal)
      .then((r) =>
        setEditions(
          r.editions.map((e) => ({
            id: e.id,
            label: e.label,
            edizione: e.edizione,
            edizioneIso: e.edizione_iso,
            stato: e.stato,
            note: e.note,
          }))
        )
      )
      .catch(() => {
        /* backend offline → dropdown mostra solo "Tutte le edizioni" */
      });
    return () => ctrl.abort();
  }, []);

  const currentEdition = useMemo(
    () => editions.find((e) => e.id === editionId) ?? null,
    [editions, editionId]
  );
  const editionLabel = currentEdition
    ? `${currentEdition.label}, Ed. ${currentEdition.edizione}${currentEdition.note ? ', ' + currentEdition.note : ''}`
    : null;

  return { editions, editionId, setEditionId, editionLabel };
}
