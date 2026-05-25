"use client";

import { useState } from "react";
import { ChevronDown } from "lucide-react";
import type { ReasoningStep } from "@/lib/api";
import { cn } from "@/lib/cn";

interface Props {
  steps: ReasoningStep[];
}

export function ReasoningTimeline({ steps }: Props) {
  if (steps.length === 0) {
    return <p className="text-xs text-text-muted">No reasoning available.</p>;
  }
  return (
    <ol className="relative space-y-3 pl-4 before:content-[''] before:absolute before:left-[7px] before:top-1 before:bottom-1 before:w-px before:bg-gradient-to-b before:from-status-info/30 before:via-border before:to-transparent">
      {steps.map((s, i) => (
        <Step key={s.step} step={s} idx={i} last={i === steps.length - 1} />
      ))}
    </ol>
  );
}

function Step({
  step,
  idx,
  last,
}: {
  step: ReasoningStep;
  idx: number;
  last: boolean;
}) {
  const [open, setOpen] = useState(false);
  const hasIO = step.input || step.output;

  return (
    <li
      className="relative animate-slide-up"
      style={{ animationDelay: `${idx * 40}ms` }}
    >
      <span className="absolute -left-[14px] top-1 flex h-4 w-4 items-center justify-center rounded-full border-2 border-status-info bg-bg-panel">
        <span className="h-1.5 w-1.5 rounded-full bg-status-info" />
      </span>
      <div className="rounded-lg border border-border bg-bg-canvas p-3">
        <div className="flex items-center gap-2 text-[11px] text-text-muted">
          <span className="font-mono">#{step.step}</span>
          <span className="text-text-secondary font-medium">{step.agent}</span>
          {step.action && (
            <span className="rounded border border-border bg-bg-panel px-1.5 py-0.5 font-mono text-[10px] text-text-muted">
              {step.action}
            </span>
          )}
        </div>

        {step.thought && (
          <p className="mt-2 text-[12px] leading-5 italic text-text-secondary">
            {step.thought}
          </p>
        )}

        {hasIO && (
          <button
            type="button"
            onClick={() => setOpen((v) => !v)}
            aria-expanded={open}
            className="mt-2 inline-flex items-center gap-1 rounded-md border border-border bg-bg-panel px-2 h-6 text-[10px] font-mono text-text-secondary hover:bg-bg-panel-elev hover:text-text-primary transition-colors"
          >
            <ChevronDown
              size={11}
              className={cn("transition-transform", open && "rotate-180")}
            />
            {open ? "Hide I/O" : "Show I/O"}
          </button>
        )}

        {open && hasIO && (
          <pre className="mt-2 max-h-56 overflow-auto whitespace-pre-wrap break-words rounded-md border border-border bg-bg-panel-elev p-2.5 font-mono text-[10.5px] leading-5 text-text-secondary animate-slide-up">
            {JSON.stringify(
              { input: step.input, output: step.output },
              null,
              2,
            )}
          </pre>
        )}
      </div>
      {!last && <div className="h-1" />}
    </li>
  );
}
