'use client';

import { Check, Copy } from 'lucide-react';
import { useState } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import type { LucideIcon } from 'lucide-react';

export function Section({
  title,
  icon: Icon,
  actions,
  children,
}: {
  title: string;
  icon: LucideIcon;
  actions?: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <Card className="overflow-hidden">
      <div className="flex items-center gap-2.5 border-b border-border px-4 py-3">
        <span className="flex h-8 w-8 items-center justify-center rounded-md border border-border bg-bg-canvas text-status-info">
          <Icon size={15} />
        </span>
        <h2 className="text-sm font-semibold tracking-tight">{title}</h2>
        {actions && <div className="ml-auto flex items-center gap-2">{actions}</div>}
      </div>
      <div className="divide-y divide-border">{children}</div>
    </Card>
  );
}

export function Row({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <div className="grid gap-2 px-4 py-3 md:grid-cols-[180px_1fr] items-center">
      <span className="text-[11px] uppercase tracking-wide text-text-muted">{label}</span>
      <span className="min-w-0 text-sm text-text-primary md:text-right">{children}</span>
    </div>
  );
}

export function Mono({ children }: { children: React.ReactNode }) {
  return <span className="font-mono text-[12px] text-text-secondary">{children}</span>;
}

export function CopyValue({ value, className = '' }: { value: string; className?: string }) {
  const [done, setDone] = useState(false);

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setDone(true);
      setTimeout(() => setDone(false), 1200);
    } catch {
      /* clipboard unavailable */
    }
  }

  return (
    <span className={`inline-flex items-center gap-2 ${className}`}>
      <code className="font-mono text-[11px] text-text-muted break-all leading-4">{value}</code>
      <Button size="icon-sm" variant="ghost" onClick={copy} aria-label="Copy" className="shrink-0">
        {done ? <Check size={13} className="text-status-success" /> : <Copy size={13} />}
      </Button>
    </span>
  );
}

export function StatusPill({
  tone,
  children,
}: {
  tone: 'success' | 'warning' | 'danger' | 'muted' | 'info';
  children: React.ReactNode;
}) {
  const toneCls =
    tone === 'success'
      ? 'text-status-success bg-status-success/10 border-status-success/30'
      : tone === 'warning'
        ? 'text-status-warning bg-status-warning/10 border-status-warning/30'
        : tone === 'danger'
          ? 'text-status-danger bg-status-danger/10 border-status-danger/30'
          : tone === 'info'
            ? 'text-status-info bg-status-info/10 border-status-info/30'
            : 'text-text-muted bg-bg-panel border-border';
  return (
    <span
      className={`inline-flex items-center gap-1.5 rounded-full border px-2 py-0.5 text-[11px] font-medium ${toneCls}`}
    >
      {children}
    </span>
  );
}

export function bytesHuman(n: number | undefined | null): string {
  if (!n || n <= 0) return '0 B';
  const u = ['B', 'KB', 'MB', 'GB', 'TB'];
  let i = 0;
  let v = n;
  while (v >= 1024 && i < u.length - 1) {
    v /= 1024;
    i++;
  }
  return `${v.toFixed(v < 10 ? 2 : v < 100 ? 1 : 0)} ${u[i]}`;
}
