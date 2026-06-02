import { Activity, History as HistoryIcon } from 'lucide-react';
import type { IngestJob, IngestStreamEvent } from '../../lib/types';
import { SectionHeader } from '../ui';
import { EventTimeline, JobCard } from './JobCard';

interface HistoryTabProps {
  activeJob: IngestJob | null;
  events: IngestStreamEvent[];
  jobs: IngestJob[];
  onRetry?: (job: IngestJob) => void;
}

export function HistoryTab({ activeJob, events, jobs, onRetry }: HistoryTabProps) {
  return (
    <div className="space-y-5 px-5 py-4">
      {activeJob && (
        <section>
          <SectionHeader title="Job attivo" icon={Activity} />
          <JobCard job={activeJob} onRetry={onRetry} />
          <EventTimeline events={events} />
        </section>
      )}

      <section>
        <SectionHeader
          title="Cronologia"
          icon={HistoryIcon}
          trailing={
            jobs.length > 0 && (
              <span className="text-[10px] font-medium tabular-nums text-ink-subtle">
                {jobs.length}
              </span>
            )
          }
        />
        {jobs.length === 0 ? (
          <div className="text-[11.5px] text-ink-subtle">Nessun documento ancora elaborato.</div>
        ) : (
          <div className="space-y-2">
            {jobs.map((j) => (
              <JobCard key={j.id} job={j} compact onRetry={onRetry} />
            ))}
          </div>
        )}
      </section>
    </div>
  );
}
