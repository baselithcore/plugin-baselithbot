import { useState, useEffect } from 'react';
import { useKbDocuments } from './kb/useKbDocuments';
import { useKbSearch } from './kb/useKbSearch';
import { useKbCounts } from './kb/useKbCounts';
import { KbSearch } from './kb/KbSearch';
import { KbCard } from './kb/KbCard';
import { GraphModal } from './kb/GraphModal';

type KbPanelProps = {
  onOpenInAnalysis?: (path: string) => void;
  tabActive?: boolean;
};

const KbPanel = ({ onOpenInAnalysis, tabActive }: KbPanelProps) => {
  const { docs, loading, error, deleting, removeDocument } = useKbDocuments();
  const { query, setQuery, filteredDocs, suggestions } = useKbSearch(docs);
  const { counts, countsLoading, loadCounts, resetCounts } = useKbCounts();

  const [expanded, setExpanded] = useState<string | null>(null);
  const [displayLimit, setDisplayLimit] = useState(12);
  const [graphDoc, setGraphDoc] = useState<{ path: string; label?: string } | null>(null);

  // Sync when tab becomes inactive without useEffect
  const [prevTabActive, setPrevTabActive] = useState(tabActive);
  if (tabActive !== prevTabActive) {
    setPrevTabActive(tabActive);
    if (!tabActive) {
      setExpanded(null);
      resetCounts();
    }
  }

  const totalDocs = docs.length;
  const visibleCount = filteredDocs.length;
  const visibleDocs = filteredDocs.slice(0, displayLimit);

  const toggleExpand = (docPath: string, docLabel?: string | null) => {
    const isExpanded = expanded === docPath;
    const next = isExpanded ? null : docPath;
    setExpanded(next);
    if (!isExpanded && docLabel) {
      loadCounts(docLabel);
    }
  };

  return (
    <section className="card full">
      <div className="kb-head">
        <div className="kb-header-row">
          <div className="kb-title">
            <p className="eyebrow">Intelligence Hub</p>
            <div className="kb-row">
              <h2 className="gradient-text">Knowledge Base</h2>
              <span
                className="badge badge-kb"
                title={`Totale: ${totalDocs || 0}${visibleCount !== totalDocs ? ` · Filtrati: ${visibleCount}` : ''}`}
              >
                {totalDocs || '0'} Documenti
              </span>
            </div>
          </div>

          <div className="kb-toolbar">
            <KbSearch query={query} setQuery={setQuery} suggestions={suggestions} />
          </div>
        </div>
        <p className="lede-home" style={{ marginTop: 0 }}>
          Esplora, analizza e gestisci il patrimonio informativo della tua Knowledge Base.
        </p>
      </div>

      {loading && <div className="inline-alert">Caricamento documenti in corso...</div>}
      {error && <div className="inline-alert variant-error">{error}</div>}

      {!loading && !error && filteredDocs.length === 0 && (
        <div className="card card-muted" style={{ padding: '60px', textAlign: 'center' }}>
          <div style={{ opacity: 0.5, marginBottom: '16px' }}>Nessun documento trovato</div>
          <p className="muted">
            Prova a cambiare i filtri di ricerca o carica nuovi file nell'Analysis Studio.
          </p>
        </div>
      )}

      <div className="kb-grid">
        {visibleDocs.map((doc) => (
          <KbCard
            key={doc.path}
            doc={doc}
            isExpanded={expanded === doc.path}
            onToggleExpand={() => toggleExpand(doc.path, doc.label)}
            counts={doc.label ? counts[doc.label] : undefined}
            countsLoading={doc.label ? countsLoading[doc.label] : false}
            onOpenInAnalysis={onOpenInAnalysis}
            onDelete={removeDocument}
            onViewGraph={(path) => setGraphDoc({ path, label: doc.label || undefined })}
            isDeleting={deleting === doc.path}
          />
        ))}
      </div>
      {visibleCount > displayLimit && (
        <div className="kb-load-more">
          <button
            type="button"
            className="btn-kb primary"
            onClick={() => setDisplayLimit((prev) => prev + 12)}
          >
            Carica altri ({visibleCount - displayLimit})
          </button>
        </div>
      )}

      {graphDoc && (
        <GraphModal
          isOpen={!!graphDoc}
          onClose={() => setGraphDoc(null)}
          documentPath={graphDoc.path}
          centerNodeId={graphDoc.path}
          title={graphDoc.label || undefined}
        />
      )}
    </section>
  );
};

export default KbPanel;
