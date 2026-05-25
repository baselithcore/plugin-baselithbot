import { cn } from "@/lib/cn";

export function bumpVersion(v: string): string {
  const parts = v.split(".");
  const last = parts[parts.length - 1];
  const n = parseInt(last, 10);
  if (Number.isFinite(n)) {
    parts[parts.length - 1] = String(n + 1);
    return parts.join(".");
  }
  return `${v}-copy`;
}

export function Pill({
  children,
  tone,
}: {
  children: React.ReactNode;
  tone?: "success" | "muted";
}) {
  return (
    <span
      className={cn(
        "rounded-full border px-1.5 py-0.5 text-[10px] uppercase font-medium",
        tone === "success" &&
          "border-status-success/30 bg-status-success/10 text-status-success",
        tone === "muted" && "border-border bg-bg-panel-soft text-text-muted",
        !tone && "border-border bg-bg-canvas text-text-muted",
      )}
    >
      {children}
    </span>
  );
}

export function Stat({ label, value }: { label: string; value: string }) {
  return (
    <div className="min-w-[78px] rounded-md border border-border bg-bg-canvas px-3 py-2">
      <div className="text-[10px] uppercase tracking-wide text-text-muted">
        {label}
      </div>
      <div className="mt-1 text-sm font-semibold">{value}</div>
    </div>
  );
}
