import { describe, it, expect } from 'vitest';
import { closestMatches, buildSuggestionMap } from './suggest.js';

describe('closestMatches', () => {
  it('finds case-insensitive near matches', () => {
    const r = closestMatches('customers', ['Brands', 'Models', 'Dealer_Brand', 'Dealers']);
    expect(r).toEqual([]);
  });

  it('suggests the closest known name', () => {
    const r = closestMatches('customer', ['Customers', 'Brands', 'Models']);
    expect(r[0]).toBe('Customers');
  });

  it('returns empty when needle is empty', () => {
    expect(closestMatches('', ['a', 'b'])).toEqual([]);
  });

  it('respects top parameter', () => {
    const r = closestMatches('Brand', ['Brands', 'Brand_Owner', 'Dealer_Brand', 'Models'], 2);
    expect(r.length).toBeLessThanOrEqual(2);
  });
});

describe('buildSuggestionMap', () => {
  it('maps each unknown to its closest matches', () => {
    const m = buildSuggestionMap(['customers', 'orderz'], ['Customers', 'Orders', 'Brands']);
    expect(m['customers']?.[0]).toBe('Customers');
    expect(m['orderz']?.[0]).toBe('Orders');
  });

  it('omits entries with no close matches', () => {
    const m = buildSuggestionMap(['xyz_unrelated'], ['Customers', 'Orders']);
    expect(m['xyz_unrelated']).toBeUndefined();
  });
});
