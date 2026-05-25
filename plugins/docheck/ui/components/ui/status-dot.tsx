import { cn } from "@/lib/cn";

const TONE = {
  success: "bg-status-success shadow-[0_0_0_3px_rgba(16,185,129,0.18)]",
  warning: "bg-status-warning shadow-[0_0_0_3px_rgba(245,158,11,0.18)]",
  danger: "bg-status-danger shadow-[0_0_0_3px_rgba(239,68,68,0.18)]",
  info: "bg-status-info shadow-[0_0_0_3px_rgba(47,123,255,0.2)]",
  muted: "bg-text-faint shadow-[0_0_0_3px_rgba(83,92,107,0.15)]",
} as const;

export function StatusDot({
  tone = "info",
  pulse,
  className,
}: {
  tone?: keyof typeof TONE;
  pulse?: boolean;
  className?: string;
}) {
  return (
    <span
      className={cn(
        "inline-block h-2 w-2 rounded-full",
        TONE[tone],
        pulse && "animate-pulse-soft",
        className,
      )}
      aria-hidden
    />
  );
}
