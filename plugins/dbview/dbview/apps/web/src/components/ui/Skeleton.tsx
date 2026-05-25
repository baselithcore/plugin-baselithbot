import { cn } from '../../lib/cn.js';

interface Props {
  className?: string;
}

export function Skeleton({ className }: Props) {
  return <div className={cn('skeleton', className)} />;
}

export function GraphSkeleton() {
  return (
    <div className="absolute inset-0 grid-bg flex items-center justify-center">
      <div className="grid grid-cols-3 gap-12 opacity-60">
        {Array.from({ length: 6 }).map((_, i) => (
          <div key={i} className="flex flex-col gap-2">
            <Skeleton className="h-9 w-44" />
            <div className="flex flex-col gap-1.5 px-2">
              <Skeleton className="h-3 w-36" />
              <Skeleton className="h-3 w-32" />
              <Skeleton className="h-3 w-40" />
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

export function ResultsSkeleton() {
  return (
    <div className="flex flex-col gap-2 p-3">
      {Array.from({ length: 5 }).map((_, i) => (
        <div key={i} className="flex gap-3">
          <Skeleton className="h-4 w-12" />
          <Skeleton className="h-4 flex-1" />
          <Skeleton className="h-4 w-20" />
        </div>
      ))}
    </div>
  );
}
