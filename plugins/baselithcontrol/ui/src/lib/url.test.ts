import { describe, it, expect } from 'vitest';
import { safeInternalUrl } from './url';

describe('safeInternalUrl', () => {
  it('allows root-relative same-origin paths', () => {
    expect(safeInternalUrl('/baselithbot')).toBe('/baselithbot');
    expect(safeInternalUrl('/api/baselithtwin/ui/')).toBe('/api/baselithtwin/ui/');
  });

  it('blocks XSS and open-redirect schemes', () => {
    expect(safeInternalUrl('javascript:alert(1)')).toBeNull();
    // eslint-disable-next-line no-script-url
    expect(safeInternalUrl('JavaScript:alert(1)')).toBeNull();
    expect(safeInternalUrl('data:text/html,<script>1</script>')).toBeNull();
    expect(safeInternalUrl('//evil.com')).toBeNull();
    expect(safeInternalUrl('https://evil.com')).toBeNull();
    expect(safeInternalUrl('relative/path')).toBeNull();
    expect(safeInternalUrl(null)).toBeNull();
    expect(safeInternalUrl(undefined)).toBeNull();
  });
});
