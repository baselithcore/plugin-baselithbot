import { Eye, EyeOff } from 'lucide-react';
import { DIALECT_META, type SslMode } from '@dbview/shared';
import type { FormState } from './form-state.js';

interface Props {
  state: FormState;
  set: <K extends keyof FormState>(k: K, v: FormState[K]) => void;
  showPw: boolean;
  togglePw: () => void;
}

export function ConnectionFormFields({ state, set, showPw, togglePw }: Props) {
  const { dialect } = state;
  const meta = DIALECT_META[dialect];

  if (dialect === 'sqlite' || dialect === 'duckdb') {
    return (
      <div className="flex flex-col gap-2">
        <Field label="Database file path">
          <input
            className="input font-mono text-[11px]"
            placeholder={
              dialect === 'duckdb' ? '/absolute/path/to/file.duckdb' : '/absolute/path/to/file.db'
            }
            value={state.filePath}
            onChange={(e) => set('filePath', e.target.value)}
            autoComplete="off"
            spellCheck={false}
            required
          />
        </Field>
      </div>
    );
  }

  if (dialect === 'salesforce-data-cloud') {
    return (
      <div className="flex flex-col gap-2">
        <Field label="Login URL (My Domain)">
          <input
            className="input font-mono text-[11px]"
            placeholder="https://acme.my.salesforce.com"
            value={state.sdcLoginUrl}
            onChange={(e) => set('sdcLoginUrl', e.target.value)}
            autoComplete="off"
            spellCheck={false}
            required
          />
        </Field>
        <Field label="API version">
          <input
            className="input font-mono text-[11px]"
            placeholder="v60.0"
            value={state.sdcApiVersion}
            onChange={(e) => set('sdcApiVersion', e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </Field>
        <Field label="Consumer key (Client ID)">
          <input
            className="input font-mono text-[11px]"
            placeholder="3MVG9..."
            value={state.sdcClientId}
            onChange={(e) => set('sdcClientId', e.target.value)}
            autoComplete="off"
            spellCheck={false}
            required
          />
        </Field>
        <Field label="Consumer secret">
          <div className="relative">
            <input
              className="input pr-7 font-mono text-[11px]"
              type={showPw ? 'text' : 'password'}
              placeholder="••••••••"
              value={state.sdcClientSecret}
              onChange={(e) => set('sdcClientSecret', e.target.value)}
              autoComplete="new-password"
              required
            />
            <button
              type="button"
              onClick={togglePw}
              aria-label={showPw ? 'Hide secret' : 'Show secret'}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-surface-3"
              style={{ color: 'rgb(var(--text-muted))' }}
              tabIndex={-1}
            >
              {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
        </Field>
        <Field label="Dataspace (optional)">
          <input
            className="input font-mono text-[11px]"
            placeholder="default"
            value={state.sdcDataspace}
            onChange={(e) => set('sdcDataspace', e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </Field>
      </div>
    );
  }

  if (dialect === 'salesforce') {
    return (
      <div className="flex flex-col gap-2">
        <Field label="Instance URL">
          <input
            className="input font-mono text-[11px]"
            placeholder="https://acme.my.salesforce.com"
            value={state.instanceUrl}
            onChange={(e) => set('instanceUrl', e.target.value)}
            autoComplete="off"
            spellCheck={false}
            required
          />
        </Field>
        <Field label="API version">
          <input
            className="input font-mono text-[11px]"
            placeholder="v60.0"
            value={state.apiVersion}
            onChange={(e) => set('apiVersion', e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </Field>
        <Field label="Consumer key (Client ID)">
          <input
            className="input font-mono text-[11px]"
            placeholder="3MVG9..."
            value={state.clientId}
            onChange={(e) => set('clientId', e.target.value)}
            autoComplete="off"
            spellCheck={false}
            required
          />
        </Field>
        <Field label="Consumer secret">
          <div className="relative">
            <input
              className="input pr-7 font-mono text-[11px]"
              type={showPw ? 'text' : 'password'}
              placeholder="••••••••"
              value={state.clientSecret}
              onChange={(e) => set('clientSecret', e.target.value)}
              autoComplete="new-password"
              required
            />
            <button
              type="button"
              onClick={togglePw}
              aria-label={showPw ? 'Hide secret' : 'Show secret'}
              className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-surface-3"
              style={{ color: 'rgb(var(--text-muted))' }}
              tabIndex={-1}
            >
              {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
            </button>
          </div>
        </Field>
        <label className="flex items-center gap-2 text-[11px]">
          <input
            type="checkbox"
            checked={state.isSandbox}
            onChange={(e) => set('isSandbox', e.target.checked)}
          />
          <span style={{ color: 'rgb(var(--text-muted))' }}>Sandbox org</span>
        </label>
      </div>
    );
  }

  const portPlaceholder = meta.defaultPort?.toString() ?? '';

  return (
    <div className="flex flex-col gap-2">
      <div className="grid grid-cols-[1fr_88px] gap-2">
        <Field label="Host">
          <input
            className="input"
            placeholder="localhost"
            value={state.host}
            onChange={(e) => set('host', e.target.value)}
            autoComplete="off"
            spellCheck={false}
            required
          />
        </Field>
        <Field label="Port">
          <input
            className="input"
            type="number"
            min={1}
            max={65535}
            placeholder={portPlaceholder}
            value={state.port}
            onChange={(e) => set('port', e.target.value)}
            autoComplete="off"
          />
        </Field>
      </div>

      {dialect === 'falkordb' ? (
        <Field label="Graph name">
          <input
            className="input"
            placeholder="default"
            value={state.graph}
            onChange={(e) => set('graph', e.target.value)}
            autoComplete="off"
            spellCheck={false}
            required
          />
        </Field>
      ) : dialect === 'ultipa' ? (
        <Field label="Default graph (optional)">
          <input
            className="input"
            placeholder="myGraph"
            value={state.graph}
            onChange={(e) => set('graph', e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </Field>
      ) : dialect === 'qdrant' ? (
        <Field label="Default collection (optional)">
          <input
            className="input"
            placeholder="my-collection"
            value={state.collection}
            onChange={(e) => set('collection', e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        </Field>
      ) : (
        <Field
          label={dialect === 'mongodb' || dialect === 'neo4j' ? 'Database' : 'Database / schema'}
        >
          <input
            className="input"
            placeholder={dialect === 'neo4j' ? 'neo4j' : 'mydb'}
            value={state.database}
            onChange={(e) => set('database', e.target.value)}
            autoComplete="off"
            spellCheck={false}
            required={dialect !== 'neo4j'}
          />
        </Field>
      )}

      {dialect === 'qdrant' ? (
        <>
          <Field label="API key (optional)">
            <div className="relative">
              <input
                className="input pr-7"
                type={showPw ? 'text' : 'password'}
                placeholder="qdrant-api-key"
                value={state.apiKey}
                onChange={(e) => set('apiKey', e.target.value)}
                autoComplete="off"
                spellCheck={false}
              />
              <button
                type="button"
                onClick={togglePw}
                aria-label={showPw ? 'Hide key' : 'Show key'}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-surface-3"
                style={{ color: 'rgb(var(--text-muted))' }}
                tabIndex={-1}
              >
                {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </Field>
          <label className="flex items-center gap-2 text-[11px]">
            <input
              type="checkbox"
              checked={state.https}
              onChange={(e) => set('https', e.target.checked)}
            />
            <span style={{ color: 'rgb(var(--text-muted))' }}>Use HTTPS (TLS)</span>
          </label>
        </>
      ) : (
        <div className="grid grid-cols-2 gap-2">
          <Field label="Username">
            <input
              className="input"
              placeholder={dialect === 'falkordb' ? '(optional)' : 'user'}
              value={state.username}
              onChange={(e) => set('username', e.target.value)}
              autoComplete="username"
            />
          </Field>
          <Field label="Password">
            <div className="relative">
              <input
                className="input pr-7"
                type={showPw ? 'text' : 'password'}
                placeholder="••••••••"
                value={state.password}
                onChange={(e) => set('password', e.target.value)}
                autoComplete="new-password"
              />
              <button
                type="button"
                onClick={togglePw}
                aria-label={showPw ? 'Hide password' : 'Show password'}
                className="absolute right-1.5 top-1/2 -translate-y-1/2 p-1 rounded hover:bg-surface-3"
                style={{ color: 'rgb(var(--text-muted))' }}
                tabIndex={-1}
              >
                {showPw ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
              </button>
            </div>
          </Field>
        </div>
      )}

      {dialect !== 'falkordb' && dialect !== 'qdrant' && dialect !== 'ultipa' && (
        <Field label="SSL / TLS">
          <select
            className="select w-full h-9 text-[12px] font-sans"
            value={state.sslMode}
            onChange={(e) => set('sslMode', e.target.value as SslMode)}
          >
            <option value="disable">Disabled (plain TCP)</option>
            <option value="require">Required (no cert verify)</option>
            <option value="verify-full">Required + verify certificate</option>
          </select>
        </Field>
      )}

      {dialect === 'ultipa' && (
        <label className="flex items-center gap-2 text-[11px]">
          <input
            type="checkbox"
            checked={state.useSSL}
            onChange={(e) => set('useSSL', e.target.checked)}
          />
          <span style={{ color: 'rgb(var(--text-muted))' }}>Use TLS (gRPC over SSL)</span>
        </label>
      )}

      {dialect === 'mongodb' && (
        <Field label="Auth source (optional)">
          <input
            className="input"
            placeholder="admin"
            value={state.authSource}
            onChange={(e) => set('authSource', e.target.value)}
            autoComplete="off"
          />
        </Field>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label
      className="flex flex-col gap-1.5 text-[10px] uppercase tracking-wider"
      style={{ color: 'rgb(var(--text-muted))' }}
    >
      <span>{label}</span>
      {children}
    </label>
  );
}
