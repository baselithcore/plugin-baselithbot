import { describe, expect, it } from 'vitest';
import { SalesforceDataCloudSafetyValidator } from './safety.js';

const validator = new SalesforceDataCloudSafetyValidator();

const knownTables = new Set([
  'data_cloud.Account__dlm',
  'Account__dlm',
  'data_cloud.Owner__dlm',
  'Owner__dlm',
]);
const knownColumns = new Map<string, Set<string>>([
  ['data_cloud.Account__dlm', new Set(['Id__c', 'Name__c', 'OwnerId__c'])],
  ['data_cloud.Owner__dlm', new Set(['Id__c', 'Email__c'])],
]);

function v(sql: string, rowLimit = 100) {
  return validator.validate(sql, { rowLimit, knownTables, knownColumns });
}

describe('SalesforceDataCloudSafetyValidator', () => {
  it('accepts a simple SELECT and injects LIMIT when missing', () => {
    const r = v('SELECT Id__c, Name__c FROM Account__dlm', 50);
    expect(r.sql).toBe('SELECT Id__c, Name__c FROM Account__dlm LIMIT 50');
    expect(r.involvedTables).toContain('Account__dlm');
  });

  it('preserves an existing LIMIT', () => {
    const r = v('SELECT Id__c FROM Account__dlm LIMIT 5');
    expect(r.sql).toBe('SELECT Id__c FROM Account__dlm LIMIT 5');
  });

  it('rejects SELECT *', () => {
    expect(() => v('SELECT * FROM Account__dlm')).toThrow(/SELECT \*/);
  });

  it('rejects DDL/DML', () => {
    expect(() => v('UPDATE Account__dlm SET Name__c = 1')).toThrow();
    expect(() => v('DROP TABLE Account__dlm')).toThrow();
    expect(() => v('DELETE FROM Account__dlm')).toThrow();
  });

  it('rejects unknown tables', () => {
    expect(() => v('SELECT Id__c FROM Ghost__dlm')).toThrow(/not in schema/);
  });

  it('rejects multiple statements', () => {
    expect(() => v('SELECT Id__c FROM Account__dlm; SELECT Id__c FROM Owner__dlm')).toThrow(
      /Multiple statements/i,
    );
  });

  it('supports CTEs and joins', () => {
    const r = v(
      'WITH a AS (SELECT Id__c, OwnerId__c FROM Account__dlm) SELECT a.Id__c, o.Email__c FROM a JOIN Owner__dlm o ON a.OwnerId__c = o.Id__c',
      25,
    );
    expect(r.sql).toContain('LIMIT 25');
  });

  it('rejects hallucinated columns on a real entity (bare-name lookup)', () => {
    expect(() => v('SELECT HireDate__c FROM Account__dlm')).toThrow(/not in schema/i);
  });

  it('rejects hallucinated columns with explicit table qualifier', () => {
    expect(() => v('SELECT Account__dlm.HireDate__c FROM Account__dlm')).toThrow(/not in schema/i);
  });

  it('rejects hallucinated columns with alias', () => {
    expect(() => v('SELECT a.HireDate__c FROM Account__dlm a')).toThrow(/not in schema/i);
  });

  it('accepts genuinely-existing columns', () => {
    const r = v('SELECT Id__c, Name__c, OwnerId__c FROM Account__dlm', 10);
    expect(r.sql).toContain('LIMIT 10');
  });
});
