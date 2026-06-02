import { Lock, FileSignature, Server } from 'lucide-react';

interface Props {
  modelId?: string;
  validatorId?: string | null;
  retentionDays?: number;
}

export function StatusFooter({
  modelId = 'medgemma:4b',
  validatorId = null,
  retentionDays = 90,
}: Props) {
  return (
    <footer
      className="border-t border-ink-200/60 bg-surface-base/85 backdrop-blur-xl dark:border-ink-700/60 dark:bg-surface-dark-base/80"
      role="contentinfo"
    >
      <div className="mx-auto flex max-w-[1480px] flex-wrap items-center justify-between gap-3 px-5 py-2.5 text-2xs text-ink-400 md:px-7">
        <div className="flex flex-wrap items-center gap-4">
          <span className="flex items-center gap-1.5">
            <Server className="h-3 w-3" aria-hidden />
            <span className="font-mono">{modelId}</span>
          </span>
          <span className="flex items-center gap-1.5">
            <Lock className="h-3 w-3" aria-hidden />
            PII pseudonymized · retention {retentionDays}gg
          </span>
          {validatorId && (
            <span className="flex items-center gap-1.5 text-accent-700 dark:text-accent-300">
              <FileSignature className="h-3 w-3" aria-hidden />
              <span className="font-mono">{validatorId}</span>
            </span>
          )}
        </div>
        <div className="flex items-center gap-2">
          <span className="font-mono text-2xs">BaselithMed v0.1.0</span>
          <span aria-hidden>·</span>
          <span>Pre-Triage CDS · uso clinico assistivo</span>
        </div>
      </div>
    </footer>
  );
}
