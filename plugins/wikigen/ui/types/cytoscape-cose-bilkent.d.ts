/**
 * Ambient type declaration for `cytoscape-cose-bilkent`.
 *
 * Upstream ships no .d.ts. We only consume it through cytoscape's
 * `cytoscape.use(...)` extension API, so a permissive `any` shim is
 * sufficient — the actual layout config is typed at the use-site via
 * a cast.
 */
declare module 'cytoscape-cose-bilkent' {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const ext: any;
  export default ext;
}
