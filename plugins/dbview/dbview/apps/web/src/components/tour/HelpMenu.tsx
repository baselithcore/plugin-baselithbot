import { useState } from 'react';
import * as Popover from '@radix-ui/react-popover';
import { Compass, HelpCircle, RotateCcw } from 'lucide-react';
import { useAppStore } from '../../store/app.js';
import { TOURS, TOUR_ORDER } from './tours/index.js';

export function HelpMenu() {
  const [open, setOpen] = useState(false);
  const startTour = useAppStore((s) => s.startTour);
  const toursCompleted = useAppStore((s) => s.toursCompleted);
  const resetOnboarding = useAppStore((s) => s.resetOnboarding);

  const launch = (id: (typeof TOUR_ORDER)[number]) => {
    setOpen(false);
    startTour(id);
  };

  return (
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger asChild>
        <button
          data-tour="help-button"
          className="btn-icon"
          aria-label="Help and tours"
          title="Help and tours"
        >
          <HelpCircle className="w-4 h-4" />
        </button>
      </Popover.Trigger>
      <Popover.Portal>
        <Popover.Content
          align="end"
          sideOffset={6}
          className="w-72 rounded-lg border shadow-xl outline-none"
          style={{
            background: 'rgb(var(--surface-elevated))',
            borderColor: 'rgb(var(--border))',
            color: 'rgb(var(--text))',
          }}
        >
          <div
            className="px-3 py-2 border-b text-[11px] font-medium uppercase tracking-wide"
            style={{
              borderColor: 'rgb(var(--border-subtle))',
              color: 'rgb(var(--text-dim))',
            }}
          >
            Interactive tours
          </div>
          <div className="p-1.5 flex flex-col gap-0.5">
            {TOUR_ORDER.map((id) => {
              const tour = TOURS[id];
              const done = toursCompleted.includes(id);
              return (
                <button
                  key={id}
                  onClick={() => launch(id)}
                  className="flex items-start gap-2.5 text-left px-2.5 py-2 rounded-md hover:bg-surface-2/65 transition-colors"
                >
                  <Compass className="w-3.5 h-3.5 mt-0.5 text-accent shrink-0" />
                  <div className="min-w-0 flex-1">
                    <div className="flex items-center gap-1.5">
                      <span className="text-[13px] font-medium">{tour.title}</span>
                      {done && <span className="chip h-4 px-1 text-[9px] uppercase">done</span>}
                    </div>
                    <p
                      className="text-[11px] leading-snug mt-0.5"
                      style={{ color: 'rgb(var(--text-muted))' }}
                    >
                      {tour.description}
                    </p>
                  </div>
                </button>
              );
            })}
          </div>
          <div
            className="px-3 py-2 border-t flex items-center justify-between gap-2"
            style={{ borderColor: 'rgb(var(--border-subtle))' }}
          >
            <span className="text-[11px]" style={{ color: 'rgb(var(--text-dim))' }}>
              ⌘K · Command palette
            </span>
            <button
              onClick={() => {
                resetOnboarding();
                setOpen(false);
              }}
              className="inline-flex items-center gap-1 text-[11px] px-2 py-1 rounded-md hover:bg-surface-2/65 transition-colors"
              style={{ color: 'rgb(var(--text-muted))' }}
              title="Reset onboarding state"
            >
              <RotateCcw className="w-3 h-3" />
              Reset
            </button>
          </div>
        </Popover.Content>
      </Popover.Portal>
    </Popover.Root>
  );
}
