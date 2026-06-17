import { useCallback, useEffect, useRef, useState } from 'react';
import { useTranslation } from 'react-i18next';
import { FlaskConical, SearchCheck, FileText, Play, Lock } from 'lucide-react';
import { fetchJobs, runDevTool } from '@/lib/api';
import type { DevToolKind, JobView } from '@/types';
import { useControlStore } from '@/store/useControlStore';
import { useUiStore } from '@/store/useUiStore';
import { SectionCard, severityBadge } from './parts';

const TOOLS: { kind: DevToolKind; icon: typeof Play; labelKey: string; hintKey: string }[] = [
  {
    kind: 'test',
    icon: FlaskConical,
    labelKey: 'console.tool_test',
    hintKey: 'console.tool_test_hint',
  },
  {
    kind: 'lint',
    icon: SearchCheck,
    labelKey: 'console.tool_lint',
    hintKey: 'console.tool_lint_hint',
  },
  {
    kind: 'docs',
    icon: FileText,
    labelKey: 'console.tool_docs',
    hintKey: 'console.tool_docs_hint',
  },
];

function statusSeverity(status: string): string {
  if (status === 'succeeded') return 'pass';
  if (status === 'running') return 'warn';
  return 'fail';
}

export function DevToolsPanel() {
  const { t } = useTranslation();
  const isAdmin = useControlStore((s) => s.me?.is_admin ?? false);
  const pushToast = useUiStore((s) => s.pushToast);
  const [jobs, setJobs] = useState<JobView[]>([]);
  const [open, setOpen] = useState<string | null>(null);
  const timer = useRef<number | null>(null);

  const load = useCallback(async () => {
    try {
      const next = await fetchJobs();
      setJobs(next);
      return next;
    } catch {
      return [];
    }
  }, []);

  useEffect(() => {
    if (!isAdmin) return;
    void load();
    timer.current = window.setInterval(async () => {
      const next = await load();
      if (!next.some((j) => j.running) && timer.current) {
        window.clearInterval(timer.current);
        timer.current = null;
      }
    }, 2000);
    return () => {
      if (timer.current) window.clearInterval(timer.current);
    };
  }, [isAdmin, load]);

  const start = useCallback(
    async (kind: DevToolKind) => {
      try {
        const job = await runDevTool(kind);
        pushToast(t('console.job_started', { kind }), 'info');
        setOpen(job.id);
        await load();
        if (!timer.current) {
          timer.current = window.setInterval(async () => {
            const next = await load();
            if (!next.some((j) => j.running) && timer.current) {
              window.clearInterval(timer.current);
              timer.current = null;
            }
          }, 2000);
        }
      } catch (err) {
        pushToast(err instanceof Error ? err.message : 'failed', 'danger');
      }
    },
    [load, pushToast, t]
  );

  if (!isAdmin) {
    return (
      <div className="glass flex flex-col items-center justify-center gap-3 p-12 text-center">
        <span className="flex h-12 w-12 items-center justify-center rounded-lg surf t-dim">
          <Lock className="h-5 w-5" />
        </span>
        <p className="text-[14px] font-semibold t-primary">{t('console.admin_only')}</p>
        <p className="max-w-xs text-[12px] t-dim">{t('console.admin_only_hint')}</p>
      </div>
    );
  }

  return (
    <div className="space-y-5">
      <div className="grid gap-3 sm:grid-cols-3">
        {TOOLS.map(({ kind, icon: Icon, labelKey, hintKey }) => {
          const running = jobs.some((j) => j.kind === kind && j.running);
          return (
            <button
              key={kind}
              type="button"
              disabled={running}
              onClick={() => void start(kind)}
              className="group flex flex-col gap-2 rounded-xl border brd bg-[var(--surface-inset)] p-4 text-left transition hover:border-[var(--accent-border)] hover:bg-[var(--surface-2)] disabled:opacity-60"
            >
              <span className="flex items-center justify-between">
                <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[var(--accent-soft)] t-accent">
                  <Icon className="h-4 w-4" />
                </span>
                {running ? (
                  <span className="led status-pulse text-amber-500" />
                ) : (
                  <Play className="h-4 w-4 t-faint group-hover:t-accent" />
                )}
              </span>
              <span className="text-[14px] font-bold t-primary">{t(labelKey)}</span>
              <span className="text-[11px] t-dim">{t(hintKey)}</span>
            </button>
          );
        })}
      </div>

      <SectionCard icon={Play} title={t('console.jobs')} hint={t('console.jobs_hint')}>
        {jobs.length === 0 ? (
          <p className="py-6 text-center text-[12px] t-dim">{t('console.no_jobs')}</p>
        ) : (
          <div className="space-y-2">
            {jobs.map((job) => (
              <div key={job.id} className="rounded-lg border brd surf">
                <button
                  type="button"
                  onClick={() => setOpen(open === job.id ? null : job.id)}
                  className="flex w-full items-center justify-between gap-3 px-3 py-2.5 text-left"
                >
                  <div className="flex items-center gap-2.5">
                    <span
                      className={`rounded-md border px-2 py-0.5 text-[10px] font-bold uppercase ${severityBadge(
                        statusSeverity(job.status)
                      )}`}
                    >
                      {job.status}
                    </span>
                    <span className="font-mono text-[12px] font-semibold t-primary">
                      {job.command}
                    </span>
                  </div>
                  <span className="font-mono text-[11px] tabular-nums t-faint">
                    {job.duration != null
                      ? `${job.duration.toFixed(1)}s`
                      : job.exit_code != null
                        ? `exit ${job.exit_code}`
                        : '…'}
                  </span>
                </button>
                {open === job.id && (
                  <pre className="max-h-80 overflow-auto border-t brd bg-[var(--surface-inset)] p-3 font-mono text-[11px] leading-relaxed t-dim">
                    {job.output || t('console.no_output')}
                  </pre>
                )}
              </div>
            ))}
          </div>
        )}
      </SectionCard>
    </div>
  );
}
