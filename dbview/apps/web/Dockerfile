FROM node:22-alpine AS base
RUN corepack enable
WORKDIR /repo

FROM base AS deps
COPY pnpm-workspace.yaml package.json pnpm-lock.yaml* ./
COPY turbo.json tsconfig.base.json ./
COPY packages/shared/package.json packages/shared/tsconfig.json ./packages/shared/
COPY apps/web/package.json apps/web/tsconfig.json ./apps/web/
RUN pnpm install --frozen-lockfile=false --ignore-scripts \
 && pnpm rebuild esbuild

FROM deps AS build
COPY packages/shared/src ./packages/shared/src
COPY apps/web ./apps/web
RUN pnpm --filter @dbview/shared build \
 && pnpm --filter @dbview/web build

FROM nginxinc/nginx-unprivileged:alpine AS runtime
USER 0
RUN rm /etc/nginx/conf.d/default.conf
COPY --from=build --chown=101:101 /repo/apps/web/dist /usr/share/nginx/html
COPY apps/web/nginx.conf /etc/nginx/conf.d/default.conf
USER 101
EXPOSE 8080
HEALTHCHECK --interval=10s --timeout=3s --retries=3 \
  CMD wget -q --spider http://localhost:8080/ || exit 1
