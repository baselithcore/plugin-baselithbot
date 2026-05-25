FROM node:22-slim AS base
RUN corepack enable
WORKDIR /repo

FROM base AS deps
RUN apt-get update && apt-get install -y --no-install-recommends python3 make g++ \
 && rm -rf /var/lib/apt/lists/*
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml* ./
COPY turbo.json tsconfig.base.json ./
COPY packages/shared/package.json packages/shared/tsconfig.json ./packages/shared/
COPY packages/sql-core/package.json packages/sql-core/tsconfig.json ./packages/sql-core/
COPY packages/cypher-core/package.json packages/cypher-core/tsconfig.json ./packages/cypher-core/
COPY packages/document-core/package.json packages/document-core/tsconfig.json ./packages/document-core/
COPY packages/keyvalue-core/package.json packages/keyvalue-core/tsconfig.json ./packages/keyvalue-core/
COPY packages/search-core/package.json packages/search-core/tsconfig.json ./packages/search-core/
COPY packages/vector-core/package.json packages/vector-core/tsconfig.json ./packages/vector-core/
COPY apps/api/package.json apps/api/tsconfig.json apps/api/tsconfig.build.json ./apps/api/
RUN pnpm install --frozen-lockfile=false --ignore-scripts \
 && pnpm rebuild better-sqlite3 @nestjs/core esbuild

FROM deps AS build
COPY packages/shared/src ./packages/shared/src
COPY packages/sql-core/src ./packages/sql-core/src
COPY packages/cypher-core/src ./packages/cypher-core/src
COPY packages/document-core/src ./packages/document-core/src
COPY packages/keyvalue-core/src ./packages/keyvalue-core/src
COPY packages/search-core/src ./packages/search-core/src
COPY packages/vector-core/src ./packages/vector-core/src
COPY apps/api/src ./apps/api/src
RUN pnpm --filter @dbview/shared build \
 && pnpm --filter @dbview/sql-core build \
 && pnpm --filter @dbview/cypher-core build \
 && pnpm --filter @dbview/document-core build \
 && pnpm --filter @dbview/keyvalue-core build \
 && pnpm --filter @dbview/search-core build \
 && pnpm --filter @dbview/vector-core build \
 && pnpm --filter @dbview/api build \
 && pnpm --filter @dbview/api deploy --prod --legacy --ignore-scripts /deploy \
 && sh -c 'for d in /deploy/node_modules/.pnpm/better-sqlite3@*/node_modules/better-sqlite3; do echo "rebuild in $d"; (cd "$d" && npm rebuild --build-from-source); done' \
 && ls /deploy/node_modules/.pnpm/better-sqlite3@*/node_modules/better-sqlite3/build/Release/

FROM node:22-slim AS runtime
RUN apt-get update && apt-get install -y --no-install-recommends tini \
 && rm -rf /var/lib/apt/lists/* \
 && groupadd -r dbview && useradd -r -g dbview -d /app dbview
ENV NODE_ENV=production
WORKDIR /app
COPY --from=build --chown=dbview:dbview /deploy ./
COPY --from=build --chown=dbview:dbview /repo/apps/api/dist ./dist
RUN mkdir -p /data && chown dbview:dbview /data
USER dbview
EXPOSE 3001
ENTRYPOINT ["/usr/bin/tini", "--"]
HEALTHCHECK --interval=10s --timeout=3s --start-period=10s --retries=5 \
  CMD node -e "fetch('http://localhost:3001/api/health').then(r=>process.exit(r.ok?0:1)).catch(()=>process.exit(1))"
CMD ["node", "dist/main.js"]
