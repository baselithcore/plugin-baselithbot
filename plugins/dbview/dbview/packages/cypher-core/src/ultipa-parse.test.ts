import { describe, expect, it } from 'vitest';
import { buildConnectionString } from '@dbview/shared';
import { parseUltipaConnection } from './ultipa-parse.js';

describe('parseUltipaConnection', () => {
  it('parses host + port without auth', () => {
    const t = parseUltipaConnection('ultipa://localhost:60061');
    expect(t).toEqual({
      hosts: ['localhost:60061'],
      username: undefined,
      password: undefined,
      defaultGraph: undefined,
      useSSL: false,
    });
  });

  it('parses ultipas:// as TLS', () => {
    const t = parseUltipaConnection('ultipas://node:60061/myGraph');
    expect(t.useSSL).toBe(true);
    expect(t.defaultGraph).toBe('myGraph');
  });

  it('decodes user/password and graph', () => {
    const t = parseUltipaConnection('ultipa://admin:p%40ss@host:60061/myGraph');
    expect(t.username).toBe('admin');
    expect(t.password).toBe('p@ss');
    expect(t.defaultGraph).toBe('myGraph');
  });

  it('defaults missing port to 60061', () => {
    const t = parseUltipaConnection('ultipa://host/g');
    expect(t.hosts).toEqual(['host:60061']);
  });

  it('parses multiple comma-separated hosts', () => {
    const t = parseUltipaConnection('ultipa://h1:60061,h2:60062/g');
    expect(t.hosts).toEqual(['h1:60061', 'h2:60062']);
  });

  it('round-trips buildConnectionString output', () => {
    const cs = buildConnectionString({
      dialect: 'ultipa',
      host: 'host.example',
      port: 60062,
      username: 'u',
      password: 'p',
      database: 'unused',
      graph: 'my graph',
      useSSL: true,
    });
    const t = parseUltipaConnection(cs);
    expect(t.useSSL).toBe(true);
    expect(t.hosts).toEqual(['host.example:60062']);
    expect(t.username).toBe('u');
    expect(t.password).toBe('p');
    expect(t.defaultGraph).toBe('my graph');
  });

  it('rejects garbage input', () => {
    expect(() => parseUltipaConnection('http://host/g')).toThrow();
    expect(() => parseUltipaConnection('not-a-url')).toThrow();
  });
});
