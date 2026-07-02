import { describe, expect, it } from 'vitest';
import { SalesforceDataCloudIntrospector } from './introspector.js';
import type {
  SalesforceDataCloudClient,
  SdcMetadataEntity,
  SdcMetadataListResponse,
} from './client.js';

function makeClient(entities: SdcMetadataEntity[]): SalesforceDataCloudClient {
  return {
    async listEntities(): Promise<SdcMetadataListResponse> {
      return { metadata: entities };
    },
    async describeEntity(name: string): Promise<SdcMetadataEntity> {
      const e = entities.find((x) => x.name === name);
      if (!e) throw new Error(`unknown entity ${name}`);
      return e;
    },
    async close() {},
  } as unknown as SalesforceDataCloudClient;
}

describe('SalesforceDataCloudIntrospector', () => {
  it('maps DMOs to TableNodes with PK/FK detection', async () => {
    const entities: SdcMetadataEntity[] = [
      {
        name: 'Account__dlm',
        category: 'DataModelObject',
        primaryKeys: [{ name: 'Id__c' }],
        fields: [
          { name: 'Id__c', type: 'STRING_TYPE', isPrimaryKey: true },
          { name: 'Name__c', type: 'STRING_TYPE' },
          { name: 'Industry__c', type: 'STRING_TYPE' },
        ],
        relationships: [
          {
            fromEntity: 'Account__dlm',
            toEntity: 'Owner__dlm',
            fromEntityAttribute: 'OwnerId__c',
            toEntityAttribute: 'Id__c',
            relationshipName: 'AccountOwner',
          },
        ],
      },
      {
        name: 'Owner__dlm',
        category: 'DataModelObject',
        fields: [
          { name: 'Id__c', type: 'STRING_TYPE', isPrimaryKey: true },
          { name: 'Email__c', type: 'STRING_TYPE' },
        ],
      },
    ];
    // Add OwnerId__c to Account so the FK flag has a target.
    entities[0]!.fields!.push({ name: 'OwnerId__c', type: 'STRING_TYPE' });

    const intro = new SalesforceDataCloudIntrospector(makeClient(entities));
    const graph = await intro.introspect();

    expect(graph.kind).toBe('relational');
    expect(graph.dialect).toBe('salesforce-data-cloud');
    expect(graph.tables.map((t) => t.id)).toEqual([
      'data_cloud.Account__dlm',
      'data_cloud.Owner__dlm',
    ]);

    const accountTable = graph.tables[0]!;
    const idCol = accountTable.columns.find((c) => c.name === 'Id__c')!;
    expect(idCol.isPrimaryKey).toBe(true);
    expect(idCol.dataType).toBe('string');

    const ownerIdCol = accountTable.columns.find((c) => c.name === 'OwnerId__c')!;
    expect(ownerIdCol.isForeignKey).toBe(true);

    expect(graph.edges).toEqual([
      {
        id: 'Account__dlm.OwnerId__c->Owner__dlm.Id__c',
        source: 'data_cloud.Account__dlm',
        sourceColumn: 'OwnerId__c',
        target: 'data_cloud.Owner__dlm',
        targetColumn: 'Id__c',
        constraintName: 'AccountOwner',
      },
    ]);
  });

  it('drops edges whose endpoints are not in the schema', async () => {
    const entities: SdcMetadataEntity[] = [
      {
        name: 'Account__dlm',
        fields: [{ name: 'Id__c', type: 'STRING_TYPE', isPrimaryKey: true }],
        relationships: [
          {
            fromEntity: 'Account__dlm',
            toEntity: 'Ghost__dlm',
            fromEntityAttribute: 'X',
            toEntityAttribute: 'Id__c',
          },
        ],
      },
    ];
    const graph = await new SalesforceDataCloudIntrospector(makeClient(entities)).introspect();
    expect(graph.edges).toEqual([]);
  });

  it('honors excludePattern', async () => {
    const entities: SdcMetadataEntity[] = [
      { name: 'Account__dlm', fields: [{ name: 'Id', type: 'STRING_TYPE' }] },
      { name: 'sys_internal__dlm', fields: [{ name: 'Id', type: 'STRING_TYPE' }] },
    ];
    const graph = await new SalesforceDataCloudIntrospector(makeClient(entities), {
      excludePattern: /^sys_/,
    }).introspect();
    expect(graph.tables.map((t) => t.name)).toEqual(['Account__dlm']);
  });

  it('propagates field displayName/description and entity displayName', async () => {
    const entities: SdcMetadataEntity[] = [
      {
        name: 'Individual__dlm',
        displayName: 'Persone Fisiche',
        description: 'Individui unificati',
        fields: [
          { name: 'ssot__Id__c', type: 'STRING_TYPE', isPrimaryKey: true },
          {
            name: 'ssot__HireDate__c',
            type: 'DATE_TYPE',
            displayName: 'Hire Date',
            description: 'Data di assunzione del dipendente',
          },
          { name: 'ssot__CreatedDate__c', type: 'DATE_TIME_TYPE', displayName: 'Created Date' },
          { name: 'ssot_HireDate_c', type: 'DATE_TYPE', displayName: 'ssot HireDate c' },
        ],
      },
    ];
    const intro = new SalesforceDataCloudIntrospector(makeClient(entities));
    const graph = await intro.introspect();
    const table = graph.tables[0]!;
    expect(table.displayName).toBe('Persone Fisiche');
    expect(table.description).toBe('Individui unificati');
    const hire = table.columns.find((c) => c.name === 'ssot__HireDate__c')!;
    expect(hire.displayName).toBe('Hire Date');
    expect(hire.description).toBe('Data di assunzione del dipendente');
    // displayName that normalizes to the technical name → suppressed.
    const echo = table.columns.find((c) => c.name === 'ssot_HireDate_c')!;
    expect(echo.displayName).toBeUndefined();
  });

  it('filters noisy system fields (KQ_*, DataSourceId, InternalOrganization, cdp_sys_*)', async () => {
    const entities: SdcMetadataEntity[] = [
      {
        name: 'X__dlm',
        fields: [
          { name: 'ssot__Id__c', type: 'STRING_TYPE', isPrimaryKey: true },
          { name: 'KQ_some_qualifier', type: 'STRING_TYPE' },
          { name: 'ssot__DataSourceObjectId__c', type: 'STRING_TYPE' },
          { name: 'ssot__InternalOrganization__c', type: 'STRING_TYPE' },
          { name: 'cdp_sys_partition', type: 'STRING_TYPE' },
          { name: 'ssot__Name__c', type: 'STRING_TYPE' },
        ],
      },
    ];
    const graph = await new SalesforceDataCloudIntrospector(makeClient(entities)).introspect();
    const names = graph.tables[0]!.columns.map((c) => c.name);
    expect(names).toEqual(['ssot__Id__c', 'ssot__Name__c']);
  });

  it('fetches describe-entity when list omits fields', async () => {
    const entities: SdcMetadataEntity[] = [{ name: 'Lean__dlm' /* no fields */ }];
    const fullDescribe: SdcMetadataEntity = {
      name: 'Lean__dlm',
      fields: [{ name: 'Id__c', type: 'STRING_TYPE', isPrimaryKey: true }],
    };
    const client = {
      async listEntities() {
        return { metadata: entities };
      },
      async describeEntity(name: string) {
        if (name === 'Lean__dlm') return fullDescribe;
        throw new Error('unexpected');
      },
      async close() {},
    } as unknown as SalesforceDataCloudClient;

    const graph = await new SalesforceDataCloudIntrospector(client).introspect();
    expect(graph.tables[0]!.columns).toHaveLength(1);
    expect(graph.tables[0]!.columns[0]!.name).toBe('Id__c');
  });
});
