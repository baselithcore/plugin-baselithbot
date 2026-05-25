import { describe, expect, it } from 'vitest';
import { SalesforceSafetyValidator } from './safety.js';

const validator = new SalesforceSafetyValidator();
const knownSObjects = new Set(['account', 'contact', 'opportunity']);
const knownFields = new Map<string, Set<string>>([
  ['account', new Set(['id', 'name', 'industry', 'annualrevenue', 'ownerid', 'createddate'])],
  ['contact', new Set(['id', 'name', 'email', 'accountid', 'createddate'])],
  ['opportunity', new Set(['id', 'name', 'amount', 'stagename', 'accountid', 'closedate'])],
]);

function validate(soql: string, rowLimit = 100) {
  return validator.validate(soql, { rowLimit, knownSObjects, knownFields });
}

describe('SalesforceSafetyValidator', () => {
  it('accepts a simple SELECT and leaves an existing LIMIT alone', () => {
    const r = validate('SELECT Id, Name FROM Account LIMIT 5');
    expect(r.query).toBe('SELECT Id, Name FROM Account LIMIT 5');
  });

  it('injects LIMIT when missing', () => {
    const r = validate('SELECT Id, Name FROM Account', 50);
    expect(r.query).toBe('SELECT Id, Name FROM Account LIMIT 50');
  });

  it('strips a trailing semicolon', () => {
    const r = validate('SELECT Id FROM Account LIMIT 1;');
    expect(r.query).toBe('SELECT Id FROM Account LIMIT 1');
  });

  it('rejects SELECT *', () => {
    expect(() => validate('SELECT * FROM Account')).toThrow(/SELECT \*/i);
  });

  it('rejects non-SELECT statements', () => {
    expect(() => validate('UPDATE Account SET Name = "x"')).toThrow(/Only SELECT/i);
    expect(() => validate('DELETE FROM Account')).toThrow(/Only SELECT|DELETE/i);
    expect(() => validate('INSERT INTO Account (Name) VALUES ("x")')).toThrow(
      /Only SELECT|INSERT/i,
    );
  });

  it('rejects multiple statements via embedded semicolon', () => {
    expect(() => validate('SELECT Id FROM Account; SELECT Id FROM Contact')).toThrow(
      /Multiple statements/i,
    );
  });

  it('rejects unknown sObjects', () => {
    expect(() => validate('SELECT Id FROM Bogus')).toThrow(/Unknown sObject/);
  });

  it('accepts case-insensitive sObject names', () => {
    const r = validate('select id from account');
    expect(r.query.toLowerCase()).toContain('from account');
  });

  it('ignores DML keywords appearing inside string literals', () => {
    const r = validate("SELECT Id, Name FROM Account WHERE Name = 'DELETE all things'");
    expect(r.query).toMatch(/SELECT Id, Name FROM Account/);
  });

  it('rejects DROP/ALTER/CREATE keywords', () => {
    expect(() => validate('SELECT Id FROM Account DROP')).toThrow(/DROP/);
  });

  it('rejects unknown bare field reference', () => {
    expect(() => validate('SELECT Id, Bogus FROM Account')).toThrow(
      /Field 'Bogus' not in schema for sObject 'Account'/,
    );
  });

  it('rejects unknown field in WHERE clause', () => {
    expect(() => validate("SELECT Id FROM Account WHERE InventedColumn = 'x'")).toThrow(
      /Field 'InventedColumn' not in schema/,
    );
  });

  it('accepts dotted lookup paths without validating each segment', () => {
    const r = validate('SELECT Id, Account.Owner.Name FROM Contact LIMIT 5');
    expect(r.query).toMatch(/Account\.Owner\.Name/);
  });

  it('accepts SOQL date literals (LAST_N_DAYS:30) without flagging them as fields', () => {
    const r = validate('SELECT Id, Name FROM Account WHERE CreatedDate = LAST_N_DAYS:30');
    expect(r.query).toMatch(/LAST_N_DAYS:30/);
  });

  it('accepts aggregate functions and date functions', () => {
    const r = validate('SELECT CALENDAR_YEAR(CreatedDate), COUNT(Id) FROM Account');
    expect(r.query).toMatch(/COUNT\(Id\)/);
  });

  it('accepts parent-child sub-select against a different sObject', () => {
    const r = validate('SELECT Id, Name, (SELECT Id FROM Contacts) FROM Account LIMIT 5');
    expect(r.query).toMatch(/FROM Account/);
  });
});
