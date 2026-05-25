import { describe, expect, it } from 'vitest';
import { defaultState, paramsFromState } from './form-state.js';

function withOverrides(o: Partial<ReturnType<typeof defaultState>>) {
  return { ...defaultState(), ...o };
}

describe('paramsFromState', () => {
  it('returns null when sqlite has no filePath', () => {
    const s = withOverrides({ dialect: 'sqlite', filePath: '   ' });
    expect(paramsFromState(s)).toBeNull();
  });

  it('builds sqlite params with trimmed path', () => {
    const s = withOverrides({ dialect: 'sqlite', filePath: '  /tmp/x.db  ' });
    expect(paramsFromState(s)).toEqual({ dialect: 'sqlite', filePath: '/tmp/x.db' });
  });

  it('rejects postgres without host or database', () => {
    expect(
      paramsFromState(withOverrides({ dialect: 'postgres', host: '', database: 'db' }))
    ).toBeNull();
    expect(
      paramsFromState(withOverrides({ dialect: 'postgres', host: 'h', database: '' }))
    ).toBeNull();
  });

  it('builds postgres params with parsed port and undefined disabled ssl', () => {
    const s = withOverrides({
      dialect: 'postgres',
      host: 'h',
      port: '5432',
      database: 'db',
      username: 'u',
      password: 'p',
      sslMode: 'disable',
    });
    expect(paramsFromState(s)).toEqual({
      dialect: 'postgres',
      host: 'h',
      port: 5432,
      database: 'db',
      username: 'u',
      password: 'p',
      sslMode: undefined,
    });
  });

  it('keeps explicit ssl when not disabled', () => {
    const s = withOverrides({
      dialect: 'mysql',
      host: 'h',
      port: '',
      database: 'db',
      sslMode: 'require',
    });
    const out = paramsFromState(s);
    expect(out).toMatchObject({ dialect: 'mysql', sslMode: 'require', port: undefined });
  });

  it('mssql includes trustServerCertificate flag', () => {
    const s = withOverrides({
      dialect: 'mssql',
      host: 'h',
      database: 'db',
      trustServerCertificate: false,
    });
    expect(paramsFromState(s)).toMatchObject({ dialect: 'mssql', trustServerCertificate: false });
  });

  it('mongodb accepts authSource optional', () => {
    const s = withOverrides({
      dialect: 'mongodb',
      host: 'h',
      database: 'db',
      authSource: 'admin',
    });
    expect(paramsFromState(s)).toMatchObject({ dialect: 'mongodb', authSource: 'admin' });
  });

  it('mongodb authSource omitted when empty', () => {
    const s = withOverrides({ dialect: 'mongodb', host: 'h', database: 'db' });
    expect(paramsFromState(s)).toMatchObject({ authSource: undefined });
  });

  it('neo4j allows empty database', () => {
    const s = withOverrides({ dialect: 'neo4j', host: 'h', database: '' });
    expect(paramsFromState(s)).toMatchObject({ dialect: 'neo4j', database: undefined });
  });

  it('falkordb requires graph', () => {
    expect(
      paramsFromState(withOverrides({ dialect: 'falkordb', host: 'h', graph: '' }))
    ).toBeNull();
    expect(
      paramsFromState(withOverrides({ dialect: 'falkordb', host: 'h', graph: 'g' }))
    ).toMatchObject({
      dialect: 'falkordb',
      graph: 'g',
    });
  });

  it('ultipa graph optional + useSSL flag', () => {
    const s = withOverrides({ dialect: 'ultipa', host: 'h', useSSL: true });
    expect(paramsFromState(s)).toMatchObject({ dialect: 'ultipa', useSSL: true, graph: undefined });
  });

  it('qdrant only requires host', () => {
    const s = withOverrides({
      dialect: 'qdrant',
      host: 'h',
      apiKey: 'k',
      collection: 'c',
      https: true,
    });
    expect(paramsFromState(s)).toMatchObject({
      dialect: 'qdrant',
      host: 'h',
      apiKey: 'k',
      collection: 'c',
      https: true,
    });
  });

  it('treats blank username as undefined', () => {
    const s = withOverrides({
      dialect: 'postgres',
      host: 'h',
      database: 'db',
      username: '   ',
    });
    expect(paramsFromState(s)).toMatchObject({ username: undefined });
  });

  it('rejects salesforce missing instanceUrl / clientId / clientSecret', () => {
    expect(
      paramsFromState(
        withOverrides({
          dialect: 'salesforce',
          instanceUrl: '',
          clientId: 'cid',
          clientSecret: 'sec',
        })
      )
    ).toBeNull();
    expect(
      paramsFromState(
        withOverrides({
          dialect: 'salesforce',
          instanceUrl: 'https://x.my.salesforce.com',
          clientId: '',
          clientSecret: 'sec',
        })
      )
    ).toBeNull();
    expect(
      paramsFromState(
        withOverrides({
          dialect: 'salesforce',
          instanceUrl: 'https://x.my.salesforce.com',
          clientId: 'cid',
          clientSecret: '',
        })
      )
    ).toBeNull();
  });

  it('builds salesforce params, trims trailing slashes, defaults apiVersion', () => {
    const s = withOverrides({
      dialect: 'salesforce',
      instanceUrl: 'https://acme.my.salesforce.com/',
      apiVersion: '',
      clientId: '3MVG9abc',
      clientSecret: 'secret-value',
      isSandbox: true,
    });
    expect(paramsFromState(s)).toEqual({
      dialect: 'salesforce',
      instanceUrl: 'https://acme.my.salesforce.com',
      apiVersion: 'v60.0',
      clientId: '3MVG9abc',
      clientSecret: 'secret-value',
      isSandbox: true,
    });
  });

  it('rejects salesforce-data-cloud missing loginUrl / clientId / clientSecret', () => {
    expect(
      paramsFromState(
        withOverrides({
          dialect: 'salesforce-data-cloud',
          sdcLoginUrl: '',
          sdcClientId: 'cid',
          sdcClientSecret: 'sec',
        })
      )
    ).toBeNull();
    expect(
      paramsFromState(
        withOverrides({
          dialect: 'salesforce-data-cloud',
          sdcLoginUrl: 'https://acme.my.salesforce.com',
          sdcClientId: '',
          sdcClientSecret: 'sec',
        })
      )
    ).toBeNull();
    expect(
      paramsFromState(
        withOverrides({
          dialect: 'salesforce-data-cloud',
          sdcLoginUrl: 'https://acme.my.salesforce.com',
          sdcClientId: 'cid',
          sdcClientSecret: '',
        })
      )
    ).toBeNull();
  });

  it('builds salesforce-data-cloud params, trims slashes, defaults apiVersion, omits empty dataspace', () => {
    const s = withOverrides({
      dialect: 'salesforce-data-cloud',
      sdcLoginUrl: 'https://acme.my.salesforce.com/',
      sdcApiVersion: '',
      sdcClientId: '3MVG9xyz',
      sdcClientSecret: 'cdp-secret',
      sdcDataspace: '   ',
    });
    expect(paramsFromState(s)).toEqual({
      dialect: 'salesforce-data-cloud',
      loginUrl: 'https://acme.my.salesforce.com',
      apiVersion: 'v60.0',
      clientId: '3MVG9xyz',
      clientSecret: 'cdp-secret',
      dataspace: undefined,
    });
  });

  it('builds salesforce-data-cloud params with custom dataspace and apiVersion', () => {
    const s = withOverrides({
      dialect: 'salesforce-data-cloud',
      sdcLoginUrl: 'https://acme.my.salesforce.com',
      sdcApiVersion: 'v61.0',
      sdcClientId: 'cid',
      sdcClientSecret: 'sec',
      sdcDataspace: 'brand_a',
    });
    expect(paramsFromState(s)).toEqual({
      dialect: 'salesforce-data-cloud',
      loginUrl: 'https://acme.my.salesforce.com',
      apiVersion: 'v61.0',
      clientId: 'cid',
      clientSecret: 'sec',
      dataspace: 'brand_a',
    });
  });
});
