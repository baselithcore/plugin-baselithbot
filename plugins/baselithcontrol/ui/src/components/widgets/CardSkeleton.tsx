// Loading placeholder mirroring the PluginCard shape to avoid layout shift.
export function CardSkeleton() {
  return (
    <div className="glass shimmer flex min-h-[11.5rem] flex-col gap-3.5 p-4">
      <div className="flex items-center gap-3">
        <div className="h-10 w-10 rounded-lg surf" />
        <div className="flex-1 space-y-1.5">
          <div className="h-3.5 w-24 rounded surf" />
          <div className="h-2.5 w-14 rounded surf" />
        </div>
        <div className="h-5 w-16 rounded-md surf" />
      </div>
      <div className="h-3 w-full rounded surf" />
      <div className="h-3 w-2/3 rounded surf" />
      <div className="mt-1 flex gap-1.5 border-t brd pt-3">
        <div className="h-7 flex-1 rounded-lg surf" />
        <div className="h-7 flex-1 rounded-lg surf" />
        <div className="h-7 flex-1 rounded-lg surf" />
      </div>
    </div>
  );
}
