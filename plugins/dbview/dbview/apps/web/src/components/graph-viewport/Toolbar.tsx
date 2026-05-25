import { useEffect, useRef } from 'react';
import { useReactFlow } from '@xyflow/react';
import {
  Box,
  Layers,
  Maximize2,
  Minimize2,
  Network,
  RefreshCw,
  Scan,
  Search,
  SearchX,
  Square,
  Workflow,
  X,
} from 'lucide-react';
import { cn } from '../../lib/cn.js';

export interface ToolbarProps {
  countsPrimary: string;
  countsSecondary: string;
  search: string;
  setSearch: (q: string) => void;
  searchPlaceholder?: string;
  /** Number of entities matching `search`. `null` when no schema is loaded. */
  matchCount: number | null;
  /** Total searchable entities for the current kind (tables, labels, …). */
  totalSearchable: number;
  /** True while the debounced filter is still catching up with the input. */
  searchPending: boolean;
  isFetching: boolean;
  onRefresh: () => void;
  showViewSwitch: boolean;
  view3D: boolean;
  setView3D: (v: boolean) => void;
  canFitView: boolean;
  showDataModeSwitch: boolean;
  dataMode: 'schema' | 'data';
  setDataMode: (m: 'schema' | 'data') => void;
  /** True when the viewport currently occupies the browser fullscreen. */
  isFullscreen: boolean;
  /** Toggle browser fullscreen on the canvas container. */
  onToggleFullscreen: () => void;
  /** Set to false when the Fullscreen API is not available in this environment. */
  canFullscreen: boolean;
}

export function Toolbar({
  countsPrimary,
  countsSecondary,
  search,
  setSearch,
  searchPlaceholder,
  matchCount,
  totalSearchable,
  searchPending,
  isFetching,
  onRefresh,
  showViewSwitch,
  view3D,
  setView3D,
  canFitView,
  showDataModeSwitch,
  dataMode,
  setDataMode,
  isFullscreen,
  onToggleFullscreen,
  canFullscreen,
}: ToolbarProps) {
  const inputRef = useRef<HTMLInputElement>(null);
  const rf = useReactFlow();

  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      const tag = (e.target as HTMLElement | null)?.tagName;
      const inEditable =
        tag === 'INPUT' ||
        tag === 'TEXTAREA' ||
        (e.target as HTMLElement | null)?.isContentEditable;
      if (e.key === '/' && !inEditable) {
        e.preventDefault();
        inputRef.current?.focus();
        inputRef.current?.select();
        return;
      }
      if (e.key === 'Escape' && document.activeElement === inputRef.current) {
        if (search) {
          e.preventDefault();
          setSearch('');
        } else {
          inputRef.current?.blur();
        }
      }
    }
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [search, setSearch]);

  const hasQuery = search.length > 0;
  const noMatches = hasQuery && matchCount === 0 && !searchPending;

  return (
    <div
      data-tour="graph-toolbar"
      className="absolute top-2 left-2 right-2 flex flex-wrap items-center gap-2 z-10"
    >
      <div className="toolbar-surface h-8 px-2.5 gap-2 text-[11px] font-mono text-text-muted">
        <Workflow className="w-3 h-3" />
        <span>{countsPrimary}</span>
        <span className="text-text-dim">·</span>
        <span>{countsSecondary}</span>
      </div>
      <div
        className={cn(
          'toolbar-surface gap-2 px-2.5 h-8 text-[12px] transition-shadow',
          'focus-within:ring-1 focus-within:ring-accent/45',
          noMatches && 'ring-1 ring-rose-400/45'
        )}
        style={{ width: 320, maxWidth: 'min(320px, calc(100vw - 48px))' }}
      >
        {noMatches ? (
          <SearchX className="w-3.5 h-3.5 text-rose-400 shrink-0" aria-hidden />
        ) : (
          <Search
            className={cn(
              'w-3.5 h-3.5 shrink-0',
              hasQuery ? 'text-accent' : 'text-text-dim',
              searchPending && 'animate-pulse'
            )}
            aria-hidden
          />
        )}
        <input
          ref={inputRef}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          onKeyDown={(e) => {
            // Stop ⌘[ / ⌘] (panel toggles) from firing while user is typing.
            if ((e.metaKey || e.ctrlKey) && (e.key === '[' || e.key === ']')) {
              e.stopPropagation();
            }
          }}
          placeholder={searchPlaceholder ?? 'Filter tables, columns…'}
          type="search"
          role="searchbox"
          aria-label="Filter schema entities"
          aria-controls="dbview-schema-canvas"
          aria-describedby="dbview-schema-search-count"
          spellCheck={false}
          autoCorrect="off"
          autoCapitalize="off"
          autoComplete="off"
          // Hide WebKit's native search clear; we render our own with focus
          // restore + matching style. `[&::-webkit-search-cancel-button]:hidden`
          // is the Tailwind way to target the shadow DOM pseudo element.
          className="bg-transparent flex-1 outline-none placeholder:text-text-dim min-w-0 [&::-webkit-search-cancel-button]:hidden [&::-webkit-search-decoration]:hidden"
        />
        <span
          id="dbview-schema-search-count"
          aria-live="polite"
          className={cn(
            'chip h-5 px-1.5 text-[10px] font-mono shrink-0 transition-colors',
            !hasQuery && 'opacity-60',
            noMatches && 'chip-danger'
          )}
          title={
            hasQuery
              ? `${matchCount ?? 0} matches out of ${totalSearchable}`
              : `${totalSearchable} entities`
          }
        >
          {hasQuery ? `${matchCount ?? 0}/${totalSearchable}` : totalSearchable}
        </span>
        {hasQuery ? (
          <button
            onClick={() => {
              setSearch('');
              inputRef.current?.focus();
            }}
            className="btn-icon w-5 h-5 shrink-0"
            aria-label="Clear search"
            title="Clear (Esc)"
          >
            <X className="w-3 h-3" />
          </button>
        ) : (
          <kbd
            className="hidden md:inline-flex items-center rounded border px-1 text-[9px] font-mono text-text-dim shrink-0"
            style={{ borderColor: 'rgb(var(--border-subtle))' }}
            aria-hidden
            title="Press / to focus filter"
          >
            /
          </kbd>
        )}
      </div>
      <button
        className="toolbar-surface btn-icon w-8 h-8"
        onClick={onRefresh}
        aria-label="Refresh schema"
        title="Refresh schema"
      >
        <RefreshCw className={isFetching ? 'w-3.5 h-3.5 animate-spin' : 'w-3.5 h-3.5'} />
      </button>
      {canFitView && (
        <button
          className="toolbar-surface btn-icon w-8 h-8"
          onClick={() => rf.fitView({ padding: 0.2, duration: 320 })}
          aria-label="Fit view"
          title="Fit view to canvas"
        >
          <Scan className="w-3.5 h-3.5" />
        </button>
      )}
      {canFullscreen && (
        <button
          className="toolbar-surface btn-icon w-8 h-8"
          onClick={onToggleFullscreen}
          aria-label={isFullscreen ? 'Exit fullscreen' : 'Enter fullscreen'}
          aria-pressed={isFullscreen}
          title={isFullscreen ? 'Exit fullscreen (Esc)' : 'Fullscreen'}
        >
          {isFullscreen ? (
            <Minimize2 className="w-3.5 h-3.5" />
          ) : (
            <Maximize2 className="w-3.5 h-3.5" />
          )}
        </button>
      )}
      {showDataModeSwitch && (
        <div className="toolbar-surface h-8 p-0.5 gap-0.5">
          <button
            className={cn(
              'segmented-item font-mono text-[10px]',
              dataMode === 'schema' && 'segmented-item-active'
            )}
            onClick={() => setDataMode('schema')}
            aria-pressed={dataMode === 'schema'}
            title="Show label types and relationship types (schema)"
          >
            <Layers className="w-3 h-3" />
            Schema
          </button>
          <button
            className={cn(
              'segmented-item font-mono text-[10px]',
              dataMode === 'data' && 'segmented-item-active'
            )}
            onClick={() => setDataMode('data')}
            aria-pressed={dataMode === 'data'}
            title="Sample real nodes and relationships (limit 200)"
          >
            <Network className="w-3 h-3" />
            Data
          </button>
        </div>
      )}
      {showViewSwitch && (
        <div className="toolbar-surface h-8 p-0.5 gap-0.5">
          <button
            className={cn(
              'segmented-item font-mono text-[10px]',
              !view3D && 'segmented-item-active'
            )}
            onClick={() => setView3D(false)}
            aria-pressed={!view3D}
            title="2D layout"
          >
            <Square className="w-3 h-3" />
            2D
          </button>
          <button
            className={cn(
              'segmented-item font-mono text-[10px]',
              view3D && 'segmented-item-active'
            )}
            onClick={() => setView3D(true)}
            aria-pressed={view3D}
            title="3D force-directed"
          >
            <Box className="w-3 h-3" />
            3D
          </button>
        </div>
      )}
    </div>
  );
}
