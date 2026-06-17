// Plugin UI mount paths are root-relative, same-origin paths (e.g. "/baselithbot",
// "/api/baselithtwin/ui/"). Before placing one in an href we open with
// target="_blank", restrict it to exactly that shape: a single leading slash not
// followed by another. This blocks javascript:/data:/vbscript: (XSS) and
// protocol-relative "//evil.com" (open-redirect) while allowing our real paths.
export function safeInternalUrl(url: string | null | undefined): string | null {
  if (!url) return null;
  return /^\/(?!\/)/.test(url) ? url : null;
}
