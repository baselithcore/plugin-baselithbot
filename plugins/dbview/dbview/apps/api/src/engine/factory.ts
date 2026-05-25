import {
  isDocumentDialect,
  isGraphDialect,
  isKeyValueDialect,
  isSaasDialect,
  isSearchDialect,
  isSqlDialect,
  isVectorDialect,
  parseSalesforceConnection,
  type Dialect,
  type ExecuteQueryResponse,
  type UnifiedSchema,
} from '@dbview/shared';
import {
  createExecutor as createSqlExecutor,
  createIntrospector as createSqlIntrospector,
} from '@dbview/sql-core';
import {
  FalkorExecutor,
  FalkorIntrospector,
  Neo4jExecutor,
  Neo4jIntrospector,
  UltipaExecutor,
  UltipaIntrospector,
} from '@dbview/cypher-core';
import { QdrantExecutor, QdrantIntrospector } from '@dbview/vector-core';
import { RedisExecutor, RedisIntrospector } from '@dbview/keyvalue-core';
import { ElasticsearchExecutor, ElasticsearchIntrospector } from '@dbview/search-core';
import { MongoExecutor, MongoIntrospector } from '@dbview/document-core';
import {
  SalesforceClient,
  SalesforceExecutor,
  SalesforceIntrospector,
} from './salesforce/index.js';
import {
  SalesforceDataCloudClient,
  SalesforceDataCloudExecutor,
  SalesforceDataCloudIntrospector,
} from './salesforce-data-cloud/index.js';

export interface QueryEngine {
  introspect(): Promise<UnifiedSchema>;
  execute(query: string, rowLimit: number): Promise<ExecuteQueryResponse>;
  close(): Promise<void>;
  /**
   * Optional lightweight reachability probe. When implemented, callers should
   * prefer it over `introspect()` for connection-test paths (avoids paying full
   * introspection cost for engines like Salesforce that describe every sObject).
   */
  verifyReachable?(): Promise<void>;
}

export function createQueryEngine(dialect: Dialect, connectionString: string): QueryEngine {
  if (isSqlDialect(dialect)) {
    const introspector = createSqlIntrospector(dialect, connectionString);
    const executor = createSqlExecutor(dialect, connectionString);
    return {
      introspect: () => introspector.introspect(),
      execute: (q, n) => executor.run(q, n),
      close: async () => {
        await Promise.all([introspector.close(), executor.close()]);
      },
    };
  }
  if (isGraphDialect(dialect)) {
    if (dialect === 'falkordb') {
      const introspector = new FalkorIntrospector(connectionString);
      const executor = new FalkorExecutor(connectionString);
      return {
        introspect: () => introspector.introspect(),
        execute: (q, n) => executor.run(q, n),
        close: async () => {
          await Promise.all([introspector.close(), executor.close()]);
        },
      };
    }
    if (dialect === 'ultipa') {
      const introspector = new UltipaIntrospector(connectionString);
      const executor = new UltipaExecutor(connectionString);
      return {
        introspect: () => introspector.introspect(),
        execute: (q, n) => executor.run(q, n),
        close: async () => {
          await Promise.all([introspector.close(), executor.close()]);
        },
      };
    }
    const introspector = new Neo4jIntrospector(connectionString);
    const executor = new Neo4jExecutor(connectionString);
    return {
      introspect: () => introspector.introspect(),
      execute: (q, n) => executor.run(q, n),
      close: async () => {
        await Promise.all([introspector.close(), executor.close()]);
      },
    };
  }
  if (isVectorDialect(dialect)) {
    const introspector = new QdrantIntrospector(connectionString);
    const executor = new QdrantExecutor(connectionString);
    return {
      introspect: () => introspector.introspect(),
      execute: (q, n) => executor.run(q, n),
      close: async () => {
        await Promise.all([introspector.close(), executor.close()]);
      },
    };
  }
  if (isKeyValueDialect(dialect)) {
    const introspector = new RedisIntrospector(connectionString);
    const executor = new RedisExecutor(connectionString);
    return {
      introspect: () => introspector.introspect(),
      execute: (q, n) => executor.run(q, n),
      close: async () => {
        await Promise.all([introspector.close(), executor.close()]);
      },
    };
  }
  if (isSearchDialect(dialect)) {
    const introspector = new ElasticsearchIntrospector(connectionString);
    const executor = new ElasticsearchExecutor(connectionString);
    return {
      introspect: () => introspector.introspect(),
      execute: (q, n) => executor.run(q, n),
      close: async () => {
        await Promise.all([introspector.close(), executor.close()]);
      },
    };
  }
  if (isSaasDialect(dialect)) {
    if (dialect === 'salesforce-data-cloud') {
      const client = new SalesforceDataCloudClient(connectionString);
      const introspector = new SalesforceDataCloudIntrospector(client);
      const executor = new SalesforceDataCloudExecutor(client);
      return {
        introspect: () => introspector.introspect(),
        execute: (q, n) => executor.run(q, n),
        close: async () => {
          await client.close();
        },
        verifyReachable: () => client.ping(),
      };
    }
    const { apiVersion } = parseSalesforceConnection(connectionString);
    const client = new SalesforceClient(connectionString);
    const introspector = new SalesforceIntrospector(client, apiVersion);
    const executor = new SalesforceExecutor(client);
    return {
      introspect: () => introspector.introspect(),
      execute: (q, n) => executor.run(q, n),
      close: async () => {
        await client.close();
      },
      verifyReachable: () => client.ping(),
    };
  }
  if (isDocumentDialect(dialect)) {
    const introspector = new MongoIntrospector(connectionString);
    const executor = new MongoExecutor(connectionString);
    return {
      introspect: () => introspector.introspect(),
      execute: (q, n) => executor.run(q, n),
      close: async () => {
        await Promise.all([introspector.close(), executor.close()]);
      },
    };
  }
  throw new Error(`Unsupported dialect: ${dialect as string}`);
}
