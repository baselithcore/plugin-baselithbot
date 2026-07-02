import { describe, expect, it } from 'vitest';
import type { ExecuteQueryResponse } from '@dbview/shared';
import { detectAllNullColumns, parseSummaryJson } from './summarizer.js';

describe('parseSummaryJson', () => {
  it('extracts summary from clean JSON', () => {
    const r = parseSummaryJson('{"summary":"Top customer is Acme."}');
    expect(r).toEqual({ summary: 'Top customer is Acme.', highlights: [], followUps: [] });
  });

  it('extracts highlights and followUps when present', () => {
    const r = parseSummaryJson(
      JSON.stringify({
        summary: '5 brands found.',
        highlights: ['Acme — $1.2M', 'TopCo — $980k'],
        followUps: ['Top brand last quarter?', 'Revenue trend?'],
      })
    );
    expect(r).toEqual({
      summary: '5 brands found.',
      highlights: ['Acme — $1.2M', 'TopCo — $980k'],
      followUps: ['Top brand last quarter?', 'Revenue trend?'],
    });
  });

  it('accepts snake_case follow_ups alias', () => {
    const r = parseSummaryJson(
      '{"summary":"x","follow_ups":["Top brand last quarter?","Revenue trend by month?"]}'
    );
    expect(r?.followUps).toEqual(['Top brand last quarter?', 'Revenue trend by month?']);
  });

  it('caps highlights and followUps to declared maxima', () => {
    const r = parseSummaryJson(
      JSON.stringify({
        summary: 'x',
        highlights: ['a', 'b', 'c', 'd', 'e', 'f'],
        followUps: [
          'Top brand last quarter?',
          'Revenue trend by month?',
          'Top region by sales?',
          'Average order value last year?',
          'Customers by segment in 2024?',
        ],
      })
    );
    expect(r?.highlights.length).toBe(4);
    expect(r?.followUps.length).toBe(3);
  });

  it('strips markdown fences', () => {
    const r = parseSummaryJson('```json\n{"summary":"Hello"}\n```');
    expect(r?.summary).toBe('Hello');
  });

  it('finds JSON inside surrounding prose', () => {
    const r = parseSummaryJson('Here it is: {"summary":"Inline"} done.');
    expect(r?.summary).toBe('Inline');
  });

  it('falls back to raw text when there is no JSON envelope', () => {
    const r = parseSummaryJson('No customers matched.');
    expect(r).toEqual({ summary: 'No customers matched.', highlights: [], followUps: [] });
  });

  it('returns null on empty/blank input', () => {
    expect(parseSummaryJson('')).toBeNull();
    expect(parseSummaryJson('   ')).toBeNull();
  });

  it('returns null when summary field is missing or empty', () => {
    expect(parseSummaryJson('{"summary":""}')).toBeNull();
    expect(parseSummaryJson('{"other":"x"}')).toBeNull();
  });

  it('returns null on malformed JSON', () => {
    expect(parseSummaryJson('{not json')).toBeNull();
  });

  it('drops non-string entries from arrays', () => {
    const r = parseSummaryJson(
      JSON.stringify({
        summary: 'x',
        highlights: ['valid', 42, null, '   ', 'also valid'],
        followUps: [{}, 'Top brand last quarter?'],
      })
    );
    expect(r?.highlights).toEqual(['valid', 'also valid']);
    expect(r?.followUps).toEqual(['Top brand last quarter?']);
  });
});

describe('sanitizeFollowUps', () => {
  it('drops English anaphora', async () => {
    const { sanitizeFollowUps } = await import('./summarizer.js');
    expect(
      sanitizeFollowUps([
        'What are the details of these sales?',
        'Show the top three by revenue last quarter',
        'Which of those customers are recurring?',
      ])
    ).toEqual(['Show the top three by revenue last quarter']);
  });

  it('drops Italian anaphora', async () => {
    const { sanitizeFollowUps } = await import('./summarizer.js');
    expect(
      sanitizeFollowUps([
        'Quali sono i dettagli di queste vendite?',
        'Mostra i top 3 modelli per fatturato 2024',
        'Quali di questi clienti sono ricorrenti?',
      ])
    ).toEqual(['Mostra i top 3 modelli per fatturato 2024']);
  });

  it('dedupes case-insensitive and trims whitespace', async () => {
    const { sanitizeFollowUps } = await import('./summarizer.js');
    expect(
      sanitizeFollowUps([
        'Top brand last quarter?',
        '  Top  brand   last quarter?  ',
        'TOP BRAND LAST QUARTER?',
        'Revenue trend by month?',
      ])
    ).toEqual(['Top brand last quarter?', 'Revenue trend by month?']);
  });
});

describe('isGroundedInSchema', () => {
  const vocab = {
    identifiers: new Set(['car_options', 'option_set_price', 'model_name', 'sales_count']),
    noiseWords: new Set([
      'show',
      'list',
      'top',
      'by',
      'the',
      'for',
      'in',
      'of',
      'and',
      'compare',
      'between',
      'where',
      'mostra',
      'i',
      'le',
      'di',
      'con',
      'tra',
      'a',
      'e',
    ]),
  };

  it('accepts questions that only reference known identifiers', async () => {
    const { isGroundedInSchema } = await import('./summarizer.js');
    expect(isGroundedInSchema('Show top model_name by sales_count in car_options', vocab)).toBe(
      true
    );
  });

  it('rejects questions that reference invented columns', async () => {
    const { isGroundedInSchema } = await import('./summarizer.js');
    expect(
      isGroundedInSchema(
        'Compare option_set_price between 2019 and 2023 by manufactured_date',
        vocab
      )
    ).toBe(false);
  });

  it('ignores quoted literals and numeric values', async () => {
    const { isGroundedInSchema } = await import('./summarizer.js');
    expect(
      isGroundedInSchema(
        'Show car_options where model_name = "F12 Berlinetta" and sales_count > 10',
        vocab
      )
    ).toBe(true);
  });
});

describe('detectAllNullColumns', () => {
  const baseResult = (
    rows: unknown[][],
    columns = ['id', 'name', 'metric']
  ): ExecuteQueryResponse => ({
    columns,
    rows,
    rowCount: rows.length,
    durationMs: 1,
    truncated: false,
  });

  it('returns columns where every preview row is null', () => {
    const r = baseResult([
      ['1', 'Acme', null],
      ['2', 'TopCo', null],
    ]);
    expect(detectAllNullColumns(r)).toEqual(['metric']);
  });

  it('returns empty when at least one row has a value', () => {
    const r = baseResult([
      ['1', 'Acme', null],
      ['2', 'TopCo', 100],
    ]);
    expect(detectAllNullColumns(r)).toEqual([]);
  });

  it('treats undefined like null', () => {
    const r = baseResult([
      ['1', 'Acme', undefined],
      ['2', 'TopCo', undefined],
    ]);
    expect(detectAllNullColumns(r)).toEqual(['metric']);
  });

  it('returns empty for zero-row results', () => {
    expect(detectAllNullColumns(baseResult([]))).toEqual([]);
  });

  it('returns multiple all-null columns', () => {
    const r = baseResult(
      [
        ['1', null, null],
        ['2', null, null],
      ],
      ['id', 'a', 'b']
    );
    expect(detectAllNullColumns(r)).toEqual(['a', 'b']);
  });
});
