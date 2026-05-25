import { useEffect, useState } from 'react';

/**
 * Returns `value` delayed by `delayMs`. Useful to keep an input controlled and
 * snappy while deferring expensive downstream work (filter, fetch) until the
 * user stops typing.
 */
export function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    if (delayMs <= 0) {
      setDebounced(value);
      return;
    }
    const id = window.setTimeout(() => setDebounced(value), delayMs);
    return () => window.clearTimeout(id);
  }, [value, delayMs]);
  return debounced;
}
