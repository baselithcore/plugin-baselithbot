declare module 'path' {
  export function dirname(path: string): string;
  export function resolve(...paths: string[]): string;
}

declare module 'node:path' {
  export * from 'path';
}

declare module 'url' {
  export function fileURLToPath(url: string | URL): string;
}

declare module 'node:url' {
  export * from 'url';
}

interface ImportMeta {
  url: string;
}
