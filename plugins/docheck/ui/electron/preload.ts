import { contextBridge } from 'electron';

contextBridge.exposeInMainWorld('docheck', {
  version: process.env.npm_package_version ?? '0.1.0',
  apiBase: 'http://127.0.0.1:8765/api/v1',
});
