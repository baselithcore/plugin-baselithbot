// Ambient page backdrop: a single ultra-faint static hairline grid, masked to
// fade near the top. Linear/Vercel keep the canvas flat and quiet — no drifting
// blobs, no motion. Purely decorative (aria-hidden, pointer-events-none) and
// pinned behind all content.
export function Backdrop() {
  return (
    <div aria-hidden className="pointer-events-none fixed inset-0 -z-10 overflow-hidden">
      <div className="aurora-grid" />
    </div>
  );
}
