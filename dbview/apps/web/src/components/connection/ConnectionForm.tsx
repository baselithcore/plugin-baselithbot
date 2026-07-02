import { useRef, useState } from 'react';
import { Loader2, CheckCircle2, Link2, Upload } from 'lucide-react';
import { DIALECT_META, type CreateConnectionDto, type DumpFormat } from '@dbview/shared';
import { api } from '../../lib/api.js';
import { DialectGrid } from './DialectGrid.js';
import { ConnectionFormFields } from './ConnectionFormFields.js';
import { URL_PLACEHOLDER, defaultState, paramsFromState, type FormState } from './form-state.js';

interface Props {
  onSubmit: (dto: CreateConnectionDto) => void;
  onTest: (dto: CreateConnectionDto) => void;
  submitting: boolean;
  testing: boolean;
}

export function ConnectionForm({ onSubmit, onTest, submitting, testing }: Props) {
  const [s, setS] = useState<FormState>(defaultState);
  const [showPw, setShowPw] = useState(false);
  const [touched, setTouched] = useState(false);
  const meta = DIALECT_META[s.dialect];
  const set = <K extends keyof FormState>(k: K, v: FormState[K]) => setS((p) => ({ ...p, [k]: v }));

  const dumpInputRef = useRef<HTMLInputElement | null>(null);
  const [dumpBusy, setDumpBusy] = useState(false);
  const [dumpInfo, setDumpInfo] = useState<string | null>(null);
  const [dumpError, setDumpError] = useState<string | null>(null);

  async function handleDumpFile(file: File): Promise<void> {
    setDumpBusy(true);
    setDumpError(null);
    setDumpInfo(null);
    try {
      const fmt: DumpFormat = /\.sql$/i.test(file.name) ? 'sqlite-sql' : 'sqlite-db';
      const res = await api.uploadDump(file, fmt);
      setS((p) => ({
        ...p,
        dialect: 'sqlite',
        filePath: res.filePath,
        name: p.name.trim() || file.name.replace(/\.(db|sqlite|sqlite3|sql)$/i, ''),
      }));
      const sizeKb = Math.max(1, Math.round(res.sizeBytes / 1024));
      const tablesPart = res.tables !== undefined ? ` · ${res.tables} tables` : '';
      setDumpInfo(`Loaded ${file.name} (${sizeKb} KB)${tablesPart}`);
    } catch (e) {
      setDumpError((e as Error).message);
    } finally {
      setDumpBusy(false);
      if (dumpInputRef.current) dumpInputRef.current.value = '';
    }
  }

  function validationErrors(): string[] {
    const errs: string[] = [];
    if (!s.name.trim()) errs.push('name');
    if (!meta.available) errs.push('dialect');
    if (s.mode === 'url') {
      if (!s.url.trim()) errs.push('url');
      return errs;
    }
    if (s.dialect === 'sqlite') {
      if (!s.filePath.trim()) errs.push('filePath');
    } else if (s.dialect === 'salesforce') {
      if (!s.instanceUrl.trim()) errs.push('instanceUrl');
      if (!s.clientId.trim()) errs.push('clientId');
      if (!s.clientSecret) errs.push('clientSecret');
    } else if (s.dialect === 'salesforce-data-cloud') {
      if (!s.sdcLoginUrl.trim()) errs.push('loginUrl');
      if (!s.sdcClientId.trim()) errs.push('clientId');
      if (!s.sdcClientSecret) errs.push('clientSecret');
    } else {
      if (!s.host.trim()) errs.push('host');
      if (s.dialect === 'falkordb') {
        if (!s.graph.trim()) errs.push('graph');
      } else if (s.dialect === 'qdrant') {
        // Qdrant only needs host/port; collection optional, apiKey optional.
      } else if (s.dialect === 'ultipa') {
        // Ultipa: graph optional (server resolves default); host required.
      } else if (s.dialect !== 'neo4j') {
        if (!s.database.trim()) errs.push('database');
      }
    }
    return errs;
  }

  function buildDto(): CreateConnectionDto | null {
    if (validationErrors().length > 0) return null;
    if (s.mode === 'url') {
      return { name: s.name.trim(), dialect: s.dialect, connectionString: s.url.trim() };
    }
    const params = paramsFromState(s);
    if (!params) return null;
    return { name: s.name.trim(), dialect: s.dialect, params };
  }

  const errors = validationErrors();
  const invalid = errors.length > 0;
  const showErrors = touched && invalid;

  return (
    <form
      className="overflow-hidden border-b"
      style={{ borderColor: 'rgb(var(--border-subtle))' }}
      onSubmit={(e) => {
        e.preventDefault();
        setTouched(true);
        const dto = buildDto();
        if (dto) onSubmit(dto);
      }}
    >
      <div className="flex flex-col gap-3 p-3">
        <input
          aria-label="Connection name"
          className="input"
          placeholder="Connection name"
          value={s.name}
          onChange={(e) => set('name', e.target.value)}
          required
          autoFocus
        />

        <DialectGrid value={s.dialect} onChange={(d) => set('dialect', d)} />

        <div className="flex flex-col gap-1.5">
          <input
            ref={dumpInputRef}
            type="file"
            accept=".db,.sqlite,.sqlite3,.sql"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) void handleDumpFile(f);
            }}
          />
          <button
            type="button"
            className="h-8 px-2 text-[11px] gap-1.5 inline-flex items-center justify-center rounded-md border transition-colors"
            style={{
              background: 'rgb(var(--surface-2) / 0.6)',
              color: 'rgb(var(--text-muted))',
              borderColor: 'rgb(var(--border-subtle))',
              borderStyle: 'dashed',
            }}
            onClick={() => dumpInputRef.current?.click()}
            disabled={dumpBusy}
            title="Upload a .db / .sqlite file or a SQLite-compatible .sql dump. Auto-creates a SQLite connection."
          >
            {dumpBusy ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <Upload className="w-3.5 h-3.5" />
            )}
            {dumpBusy ? 'Uploading dump…' : 'Import from dump file (.db / .sql)'}
          </button>
          {dumpInfo && (
            <div
              className="text-[10px] px-2 py-1 rounded font-mono"
              style={{
                background: 'rgb(var(--surface-2))',
                color: 'rgb(var(--text-muted))',
                border: '1px solid rgb(var(--border-subtle))',
              }}
            >
              {dumpInfo}
            </div>
          )}
          {dumpError && (
            <div
              className="text-[10px] px-2 py-1 rounded"
              style={{
                background: 'rgb(var(--danger) / 0.10)',
                color: 'rgb(var(--danger))',
                border: '1px solid rgb(var(--danger) / 0.35)',
              }}
            >
              {dumpError}
            </div>
          )}
        </div>

        {!meta.available && (
          <div
            className="text-[11px] px-2 py-1.5 rounded"
            style={{
              background: 'rgb(var(--surface-2))',
              color: 'rgb(var(--text-muted))',
              border: '1px dashed rgb(var(--border))',
            }}
          >
            <strong>{meta.label}</strong> coming soon — engine not yet wired.
          </div>
        )}

        <div className="flex items-center justify-between text-[11px]">
          <span style={{ color: 'rgb(var(--text-muted))' }}>
            {s.mode === 'fields' ? 'Connection details' : 'Raw connection string'}
          </span>
          <button
            type="button"
            className="btn-ghost h-6 px-2 text-[10px] gap-1"
            onClick={() => set('mode', s.mode === 'fields' ? 'url' : 'fields')}
            title="Switch input mode"
          >
            <Link2 className="w-3 h-3" />
            {s.mode === 'fields' ? 'Use URL' : 'Use fields'}
          </button>
        </div>

        {s.mode === 'url' ? (
          <input
            aria-label="Connection URL"
            className="input font-mono text-[11px]"
            placeholder={URL_PLACEHOLDER[s.dialect]}
            value={s.url}
            onChange={(e) => set('url', e.target.value)}
            autoComplete="off"
            spellCheck={false}
          />
        ) : (
          <ConnectionFormFields
            state={s}
            set={set}
            showPw={showPw}
            togglePw={() => setShowPw((v) => !v)}
          />
        )}

        {showErrors && (
          <div
            className="text-[11px] px-2 py-1.5 rounded flex flex-col gap-0.5"
            style={{
              background: 'rgb(var(--danger) / 0.10)',
              color: 'rgb(var(--danger))',
              border: '1px solid rgb(var(--danger) / 0.35)',
            }}
          >
            <span className="font-semibold">Required fields missing:</span>
            <span className="font-mono">{errors.join(', ')}</span>
          </div>
        )}

        <div className="flex gap-2 pt-1">
          <button
            type="button"
            className="btn flex-1"
            onClick={() => {
              setTouched(true);
              const dto = buildDto();
              if (dto) onTest(dto);
            }}
            disabled={testing || invalid}
            title={invalid ? `Missing: ${errors.join(', ')}` : 'Test reachability'}
          >
            {testing ? <Loader2 className="w-3.5 h-3.5 animate-spin" /> : null}
            Test
          </button>
          <button
            type="submit"
            className="btn-primary flex-1"
            disabled={submitting || invalid}
            title={invalid ? `Missing: ${errors.join(', ')}` : 'Save connection'}
          >
            {submitting ? (
              <Loader2 className="w-3.5 h-3.5 animate-spin" />
            ) : (
              <CheckCircle2 className="w-3.5 h-3.5" />
            )}
            {submitting ? 'Saving' : 'Save'}
          </button>
        </div>
      </div>
    </form>
  );
}
