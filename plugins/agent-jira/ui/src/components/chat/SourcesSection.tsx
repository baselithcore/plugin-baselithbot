import { Link2 } from 'lucide-react';
import { ChatSource } from '../../types';

type SourcesSectionProps = {
  sources: ChatSource[];
  layout?: 'card' | 'panel';
};

const SourcesSection = ({ sources, layout = 'card' }: SourcesSectionProps) => {
  const wrapperClass = layout === 'card' ? 'card secondary' : 'side-panel-section';

  if (!sources.length) {
    return (
      <section className={wrapperClass}>
        <div className="section-header">
          <div>
            <p className="eyebrow">Fonti interrogate</p>
            <p className="muted small-text">Ancora nessuna fonte interrogata.</p>
          </div>
          <span className="badge neutral">0</span>
        </div>
        <div className="section-title">
          <Link2 size={16} /> Fonti
        </div>
        <div className="empty-card muted">Nessuna fonte interrogata.</div>
      </section>
    );
  }

  const scoreValues = sources
    .map((source) => {
      const value = source.score_avg ?? source.score;
      return typeof value === 'number' ? value : null;
    })
    .filter((value): value is number => value !== null);
  const minScore = scoreValues.length ? Math.min(...scoreValues) : 0;
  const maxScore = scoreValues.length ? Math.max(...scoreValues) : 0;
  const scoreRange = maxScore - minScore;

  return (
    <section className={wrapperClass}>
      <div className="section-header">
        <div>
          <p className="eyebrow">Fonti interrogate</p>
          <p className="muted small-text">Documenti e URL usati dall’agente per la risposta.</p>
        </div>
        <span className="badge neutral">{sources.length}</span>
      </div>
      <div className="section-title">
        <Link2 size={16} /> Fonti
      </div>
      <div className="source-list">
        {sources.map((source, idx) => {
          const coverage =
            typeof source.context_ratio === 'number'
              ? `${(source.context_ratio * 100).toFixed(0)}% copertura`
              : null;
          const scoreValue = source.score_avg ?? source.score;
          const normalizedScore =
            typeof scoreValue === 'number'
              ? scoreRange > 0
                ? ((scoreValue - minScore) / scoreRange) * 100
                : 100
              : null;
          const score =
            typeof normalizedScore === 'number'
              ? `score ${Math.min(100, Math.max(0, Math.round(normalizedScore)))}%`
              : null;
          const title = source.title || source.path || source.url || `Fonte ${idx + 1}`;
          const origin = source.origin || (source.url ? 'URL' : 'File');
          const href = source.url || source.path;

          return (
            <div key={`${source.path || source.url || idx}`} className="source-card">
              <div className="source-card-top">
                <span className="meta-pill">{origin}</span>
                <div className="source-meta">
                  {coverage && <span className="meta-pill subtle">{coverage}</span>}
                  {score && <span className="meta-pill subtle">{score}</span>}
                </div>
              </div>
              <div className="source-title">{title}</div>
              {href && (
                <p className="source-path muted small-text" title={href}>
                  {href}
                </p>
              )}
            </div>
          );
        })}
      </div>
    </section>
  );
};

export default SourcesSection;
