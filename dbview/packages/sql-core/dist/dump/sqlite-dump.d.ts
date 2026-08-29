export declare function isSqliteDatabaseBuffer(buf: Buffer): boolean;
export declare function writeSqliteDbFile(targetPath: string, buf: Buffer): void;
export declare function applySqliteSqlDump(targetPath: string, sql: string): {
    tables: number;
};
//# sourceMappingURL=sqlite-dump.d.ts.map