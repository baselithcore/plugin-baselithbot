import {
  Trash2,
  Calendar,
  ScrollText,
  FlaskConical,
  Network,
  FileText,
  FileEdit,
  Table as TableIcon,
  Presentation,
  FileCode,
  File,
  ChevronRight,
  Info,
} from 'lucide-react';
import { KbDocumentEntry } from '../../types';

interface KbCardProps {
  doc: KbDocumentEntry;
  isExpanded: boolean;
  onToggleExpand: () => void;
  counts?: { stories: number; test_cases: number };
  countsLoading?: boolean;
  onOpenInAnalysis?: (path: string) => void;
  onDelete: (path: string) => void;
  onViewGraph?: (path: string) => void;
  isDeleting: boolean;
}

const getFileIcon = (path: string) => {
  const ext = (path.split('.').pop() || '').toLowerCase();
  if (['pdf'].includes(ext)) return <FileText size={20} />;
  if (['doc', 'docx'].includes(ext)) return <FileEdit size={20} />;
  if (['xls', 'xlsx', 'csv'].includes(ext)) return <TableIcon size={20} />;
  if (['ppt', 'pptx'].includes(ext)) return <Presentation size={20} />;
  if (['md', 'markdown'].includes(ext)) return <FileCode size={20} />;
  return <File size={20} />;
};

const getFileLabel = (path: string) => {
  const ext = (path.split('.').pop() || '').toLowerCase();
  if (['pdf'].includes(ext)) return 'PDF';
  if (['doc', 'docx'].includes(ext)) return 'Word';
  if (['xls', 'xlsx', 'csv'].includes(ext)) return 'Excel';
  if (['ppt', 'pptx'].includes(ext)) return 'PPT';
  if (['md', 'markdown'].includes(ext)) return 'Markdown';
  return 'Doc';
};

export const KbCard = ({
  doc,
  isExpanded,
  onToggleExpand,
  counts,
  countsLoading,
  onOpenInAnalysis,
  onDelete,
  onViewGraph,
  isDeleting,
}: KbCardProps) => {
  const fileName = doc.path.split('/').pop() || doc.path;
  const displayTitle = doc.label || fileName.replace(/\.[^.]+$/, '');

  return (
    <article className={`kb-card ${isExpanded ? 'is-expanded' : ''}`}>
      <div className="kb-card-header">
        <div className="kb-type-icon" title={getFileLabel(doc.path)}>
          {getFileIcon(doc.path)}
        </div>
        <div className="kb-card-header-actions">
          <button
            type="button"
            className={`btn-kb ${isExpanded ? 'active' : ''}`}
            onClick={(e) => {
              e.stopPropagation();
              onToggleExpand();
            }}
            title="Dettagli Jira"
          >
            <Info size={16} />
          </button>
          <button
            type="button"
            className="btn-kb variant-danger"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(doc.path);
            }}
            disabled={isDeleting}
            title="Elimina"
          >
            {isDeleting ? <span className="dot-loader" /> : <Trash2 size={16} />}
          </button>
        </div>
      </div>

      <div className="kb-card-content">
        <h3 className="kb-card-title" title={displayTitle}>
          {displayTitle}
        </h3>
        <p className="kb-card-subtitle" title={fileName}>
          {fileName}
        </p>

        {(isExpanded || counts) && (
          <div className="kb-card-badges">
            {countsLoading ? (
              <>
                <div className="kb-badge kb-badge-loading">
                  <ScrollText size={12} /> <span className="dot-loader" />
                </div>
                <div className="kb-badge kb-badge-loading">
                  <FlaskConical size={12} /> <span className="dot-loader" />
                </div>
              </>
            ) : (
              <>
                <a
                  href={doc.jira_story_url || doc.jira_search_url || '#'}
                  target="_blank"
                  rel="noreferrer"
                  className={`kb-badge kb-badge-story ${(counts?.stories ?? 0) === 0 ? 'is-zero' : ''}`}
                  title="User Stories"
                  onClick={(e) => e.stopPropagation()}
                >
                  <ScrollText size={12} /> {counts?.stories ?? 0} Stories
                </a>

                <a
                  href={doc.jira_test_url || doc.jira_search_url || '#'}
                  target="_blank"
                  rel="noreferrer"
                  className={`kb-badge kb-badge-test ${(counts?.test_cases ?? 0) === 0 ? 'is-zero' : ''}`}
                  title="Test Cases"
                  onClick={(e) => e.stopPropagation()}
                >
                  <FlaskConical size={12} /> {counts?.test_cases ?? 0} Tests
                </a>
              </>
            )}
          </div>
        )}
      </div>

      <div className="kb-card-footer">
        <div className="kb-card-date">
          <Calendar size={14} />
          {doc.uploaded_at
            ? new Date(doc.uploaded_at).toLocaleDateString('it-IT', {
                day: '2-digit',
                month: 'short',
              })
            : 'N/D'}
        </div>
        <div className="kb-card-actions">
          <button className="btn-kb" onClick={() => onViewGraph?.(doc.path)} title="Esplora Grafo">
            <Network size={14} />
          </button>
          <button className="btn-kb primary" onClick={() => onOpenInAnalysis?.(doc.path)}>
            Apri <ChevronRight size={14} />
          </button>
        </div>
      </div>
    </article>
  );
};
