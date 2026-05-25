import type { SchemaGraph } from '@dbview/shared';

/**
 * Synthetic Postgres schema mirroring the layout of `infra/seed/shop`. Used by
 * the eval harness so cases can run offline (no live DB needed). Keep in sync
 * with the real seed when adding tables; harness regression checks
 * pruning + validator paths against this fixture.
 */
export const SHOP_SCHEMA: SchemaGraph = {
  kind: 'relational',
  dialect: 'postgres',
  generatedAt: '2026-01-01T00:00:00.000Z',
  tables: [
    {
      id: 'shop.customers',
      schema: 'shop',
      name: 'customers',
      displayName: 'Customers',
      description: 'End customers placing orders.',
      columns: [
        col('id', 'uuid', { isPrimaryKey: true, nullable: false }),
        col('name', 'text', { nullable: false }),
        col('email', 'text', { nullable: false, isUnique: true }),
        col('country', 'text'),
        col('created_at', 'timestamptz', { nullable: false }),
      ],
    },
    {
      id: 'shop.orders',
      schema: 'shop',
      name: 'orders',
      displayName: 'Orders',
      description: 'Purchase orders placed by customers.',
      columns: [
        col('id', 'uuid', { isPrimaryKey: true, nullable: false }),
        col('customer_id', 'uuid', { isForeignKey: true, nullable: false }),
        col('total_amount', 'numeric'),
        col('status', 'text', { nullable: false }),
        col('created_at', 'timestamptz', { nullable: false }),
      ],
    },
    {
      id: 'shop.order_items',
      schema: 'shop',
      name: 'order_items',
      displayName: 'Order Items',
      description: 'Line items inside a purchase order.',
      columns: [
        col('id', 'uuid', { isPrimaryKey: true, nullable: false }),
        col('order_id', 'uuid', { isForeignKey: true, nullable: false }),
        col('product_id', 'uuid', { isForeignKey: true, nullable: false }),
        col('quantity', 'integer', { nullable: false }),
        col('unit_price', 'numeric', { nullable: false }),
      ],
    },
    {
      id: 'shop.products',
      schema: 'shop',
      name: 'products',
      displayName: 'Products',
      description: 'Catalog items available for purchase.',
      columns: [
        col('id', 'uuid', { isPrimaryKey: true, nullable: false }),
        col('sku', 'text', { isUnique: true, nullable: false }),
        col('name', 'text', { nullable: false }),
        col('price', 'numeric'),
        col('category', 'text'),
      ],
    },
    {
      id: 'shop.suppliers',
      schema: 'shop',
      name: 'suppliers',
      displayName: 'Suppliers',
      description: 'Companies supplying products to the shop.',
      columns: [
        col('id', 'uuid', { isPrimaryKey: true, nullable: false }),
        col('name', 'text', { nullable: false }),
        col('country', 'text'),
      ],
    },
    {
      id: 'shop.shipments',
      schema: 'shop',
      name: 'shipments',
      displayName: 'Shipments',
      description: 'Shipping records for fulfilled orders.',
      columns: [
        col('id', 'uuid', { isPrimaryKey: true, nullable: false }),
        col('order_id', 'uuid', { isForeignKey: true, nullable: false }),
        col('tracking_number', 'text'),
        col('shipped_at', 'timestamptz'),
      ],
    },
    {
      id: 'shop.audit_log',
      schema: 'shop',
      name: 'audit_log',
      displayName: 'Audit Log',
      description: 'Internal audit trail; not for analytics.',
      columns: [
        col('id', 'uuid', { isPrimaryKey: true, nullable: false }),
        col('action', 'text'),
        col('actor', 'text'),
        col('at', 'timestamptz'),
      ],
    },
  ],
  edges: [
    fk('shop.orders', 'customer_id', 'shop.customers', 'id'),
    fk('shop.order_items', 'order_id', 'shop.orders', 'id'),
    fk('shop.order_items', 'product_id', 'shop.products', 'id'),
    fk('shop.shipments', 'order_id', 'shop.orders', 'id'),
  ],
};

function col(
  name: string,
  dataType: string,
  extras: {
    isPrimaryKey?: boolean;
    isForeignKey?: boolean;
    isUnique?: boolean;
    nullable?: boolean;
  } = {},
) {
  return {
    name,
    dataType,
    nullable: extras.nullable ?? true,
    isPrimaryKey: extras.isPrimaryKey ?? false,
    isForeignKey: extras.isForeignKey ?? false,
    isUnique: extras.isUnique ?? false,
  };
}

function fk(source: string, sourceColumn: string, target: string, targetColumn: string) {
  return {
    id: `${source}.${sourceColumn}->${target}.${targetColumn}`,
    source,
    sourceColumn,
    target,
    targetColumn,
  };
}
