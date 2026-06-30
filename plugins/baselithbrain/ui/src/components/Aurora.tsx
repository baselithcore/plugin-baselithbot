/**
 * Static canvas wash rendered behind all chrome — two very faint, fixed corner
 * tints over the base background (see `.bb-aurora` in index.css). No animation,
 * no blobs: just a hint of depth so flat panels read against the canvas. Fixed +
 * z-0, pointer-events none — never interactive.
 */
export function Aurora() {
  return <div className="bb-aurora" aria-hidden />;
}
