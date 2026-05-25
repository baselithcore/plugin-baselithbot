import { Quote } from 'lucide-react';

export function EmptyPreview() {
  return (
    <div className="grid h-full place-items-center px-6 py-10 text-center">
      <div>
        <div className="mx-auto grid size-10 place-items-center rounded-full bg-[var(--color-surface)] text-ink-subtle">
          <Quote size={16} aria-hidden />
        </div>
        <p className="mt-3 text-[12px] font-medium text-ink">Seleziona una fonte</p>
        <p className="mt-1 text-[11px] leading-relaxed text-ink-subtle">
          L'anteprima e i passaggi citati compariranno qui.
        </p>
      </div>
    </div>
  );
}

export function PreviewSkeleton() {
  return (
    <div className="p-4 space-y-2">
      <div className="skeleton h-3 w-40 rounded" />
      <div className="skeleton h-3 w-full rounded" />
      <div className="skeleton h-3 w-5/6 rounded" />
      <div className="skeleton h-3 w-4/6 rounded" />
    </div>
  );
}
