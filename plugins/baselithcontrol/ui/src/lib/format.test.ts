import { describe, it, expect } from 'vitest';
import { getByPath, formatValue, highlightTone, relativeTime } from './format';

describe('getByPath', () => {
  it('reads nested object + array paths', () => {
    const obj = { queue: { depth: 7 }, items: [{ id: 'a' }, { id: 'b' }] };
    expect(getByPath(obj, 'queue.depth')).toBe(7);
    expect(getByPath(obj, 'items.1.id')).toBe('b');
    expect(getByPath(obj, 'missing.x')).toBeUndefined();
  });
});

describe('formatValue', () => {
  it('formats by type', () => {
    expect(formatValue(1500, 'number')).toBe((1500).toLocaleString());
    expect(formatValue(42, 'percent')).toBe('42%');
    expect(formatValue(2048, 'bytes')).toBe('2.0 KB');
    expect(formatValue(500, 'duration')).toBe('500ms');
    expect(formatValue(1500, 'duration')).toBe('1.5s');
    expect(formatValue(null, 'number')).toBe('—');
  });
});

describe('highlightTone', () => {
  it('applies threshold tones', () => {
    expect(highlightTone(60, { gte: 50, tone: 'warning' })).toBe('warning');
    expect(highlightTone(10, { gte: 50, tone: 'warning' })).toBe('neutral');
    expect(highlightTone(5, { lte: 10, tone: 'danger' })).toBe('danger');
    expect(highlightTone(1, null)).toBe('neutral');
  });
});

describe('relativeTime', () => {
  it('handles null and recent', () => {
    expect(relativeTime(null)).toBe('—');
    expect(relativeTime(Date.now() / 1000)).toMatch(/s ago$/);
  });
});
