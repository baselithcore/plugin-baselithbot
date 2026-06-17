/**
 * Animated aurora field rendered behind all chrome. Three slow-drifting blurred
 * gradient blobs (iris → cyan → magenta) give the app its premium, AI-native
 * depth. Pure CSS animation (see `.bb-aurora*` in index.css); honors
 * prefers-reduced-motion. Fixed + z-0, pointer-events none — never interactive.
 */
export function Aurora() {
  return (
    <div className="bb-aurora" aria-hidden>
      <div className="bb-aurora-blob" />
    </div>
  );
}
