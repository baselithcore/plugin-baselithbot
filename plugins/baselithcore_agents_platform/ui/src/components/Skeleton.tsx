interface SkeletonProps {
  height?: number;
  className?: string;
}

/** Shimmer placeholder shown while lazy routes and data resolve. */
export function Skeleton({ height = 96, className = '' }: SkeletonProps) {
  return (
    <div
      className={`animate-pulse rounded-xl bg-ink-700/60 ${className}`}
      style={{ height }}
      aria-hidden="true"
    />
  );
}
