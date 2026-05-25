import { AnimatePresence, motion } from 'framer-motion';
import { useDeferredValue, useEffect, useMemo, useRef, useState } from 'react';
import { fetchPage } from '../lib/api';
import type { Source } from '../lib/types';
import { cn } from '../lib/cn';
import { extractVerbatims, findVerbatimByArticle, type Verbatim } from '../lib/verbatim';
import { DrawerHeader } from './sources/DrawerHeader';
import { MarkdownPreview } from './sources/MarkdownPreview';
import { EmptyPreview, PreviewSkeleton } from './sources/placeholders';
import { PreviewHeader } from './sources/PreviewHeader';
import { PreviewToolbar, type PreviewTab } from './sources/PreviewToolbar';
import { SourcesList } from './sources/SourcesList';
import { VerbatimList } from './sources/VerbatimList';

interface Props {
  sources: Source[];
  open: boolean;
  onClose: () => void;
  activeDocId: string | null;
  activeAnchor?: string | null;
  onSelect: (id: string | null, anchor?: string | null) => void;
}

export function SourcesDrawer({
  sources,
  open,
  onClose,
  activeDocId,
  activeAnchor,
  onSelect,
}: Props) {
  const [preview, setPreview] = useState<{
    docId: string;
    title: string;
    body: string;
    obsidianUri: string | null;
  } | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState('');
  const [listFilter, setListFilter] = useState('');
  const [tab, setTab] = useState<PreviewTab>('content');
  const [activeHit, setActiveHit] = useState(-1);
  const previewRef = useRef<HTMLDivElement>(null);
  const previewScrollRef = useRef<HTMLDivElement>(null);
  const searchInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    setQuery('');
    setTab('content');
    setActiveHit(-1);
    if (!activeDocId) {
      setPreview(null);
      setError(null);
      return;
    }
    setLoading(true);
    setError(null);
    const ctrl = new AbortController();
    fetchPage(activeDocId, ctrl.signal)
      .then((p) =>
        setPreview({
          docId: p.document_id,
          title: p.title,
          body: p.body,
          obsidianUri: p.obsidian_uri ?? null,
        })
      )
      .catch((e) => {
        if ((e as Error).name !== 'AbortError') {
          setError('Impossibile caricare la fonte.');
          setPreview(null);
        }
      })
      .finally(() => setLoading(false));
    return () => ctrl.abort();
  }, [activeDocId]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', onKey);
    return () => window.removeEventListener('keydown', onKey);
  }, [open, onClose]);

  useEffect(() => {
    if (preview && previewScrollRef.current) {
      previewScrollRef.current.scrollTop = 0;
    }
  }, [preview?.docId]); // eslint-disable-line react-hooks/exhaustive-deps

  const verbatims = useMemo<Verbatim[]>(
    () => (preview ? extractVerbatims(preview.body) : []),
    [preview]
  );

  useEffect(() => {
    if (!preview || !activeAnchor || !previewRef.current) return;
    const normalized = activeAnchor.replace(/[-_]/g, ' ').replace(/\s+/g, '\\s*');
    try {
      const re = new RegExp(normalized, 'i');
      const el = previewRef.current;
      const walker = document.createTreeWalker(el, NodeFilter.SHOW_TEXT);
      let node: Node | null;
      while ((node = walker.nextNode())) {
        if (node.textContent && re.test(node.textContent)) {
          (node.parentElement as HTMLElement | null)?.scrollIntoView({
            behavior: 'smooth',
            block: 'center',
          });
          break;
        }
      }
    } catch {
      /* skip */
    }
  }, [preview, activeAnchor]);

  const focusedVerbatim = useMemo(
    () => findVerbatimByArticle(verbatims, activeAnchor ?? undefined),
    [verbatims, activeAnchor]
  );

  // deferred: aggiorna il conteggio fuori dal critical-path del typing,
  // l'input resta reattivo anche su body grandi.
  const deferredQuery = useDeferredValue(query);
  const hitCount = useMemo(() => {
    const q = deferredQuery.trim();
    if (q.length < 2 || !preview) return 0;
    const body = preview.body.replace(/^---\s*\n[\s\S]*?\n---\s*\n?/, '');
    const escaped = q.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
    try {
      return (body.match(new RegExp(escaped, 'gi')) ?? []).length;
    } catch {
      return 0;
    }
  }, [deferredQuery, preview]);

  // Reset active hit quando query / docId / tab cambiano: i [data-hit-index]
  // vengono ricreati a ogni render del MarkdownPreview, l'indice precedente
  // potrebbe puntare a un match diverso (regex match positions cambiano).
  useEffect(() => {
    setActiveHit(-1);
  }, [query, activeDocId, tab]);

  // Scroll smooth al match attivo + applica classe `search-hit--active`.
  // Doppio rAF per attendere il commit di react-markdown post-update.
  useEffect(() => {
    if (tab !== 'content' || activeHit < 0 || !previewRef.current) return;
    const root = previewRef.current;
    const apply = () => {
      const all = root.querySelectorAll<HTMLElement>('[data-hit-index]');
      all.forEach((el) => el.classList.remove('search-hit--active'));
      const target = root.querySelector<HTMLElement>(
        `[data-hit-index="${activeHit}"]`
      );
      if (target) {
        target.classList.add('search-hit--active');
        target.scrollIntoView({ behavior: 'smooth', block: 'center' });
      }
    };
    const id1 = requestAnimationFrame(() => {
      const id2 = requestAnimationFrame(apply);
      (apply as unknown as { _rafId?: number })._rafId = id2;
    });
    return () => cancelAnimationFrame(id1);
  }, [activeHit, tab, preview]);

  const totalHits = hitCount;
  const nextHit = () => {
    if (totalHits === 0) return;
    setActiveHit((prev) => (prev + 1 + totalHits) % totalHits);
  };
  const prevHit = () => {
    if (totalHits === 0) return;
    setActiveHit((prev) => {
      const base = prev < 0 ? 0 : prev;
      return (base - 1 + totalHits) % totalHits;
    });
  };

  const filteredSources = useMemo(() => {
    const q = listFilter.trim().toLowerCase();
    if (!q) return sources;
    return sources.filter((s) => {
      const blob = [s.title, s.rango, s.edizione, s.subtype].filter(Boolean).join(' ').toLowerCase();
      return blob.includes(q);
    });
  }, [sources, listFilter]);

  const activeSource = sources.find((s) => s.document_id === activeDocId) ?? null;

  const focusSearchShortcut = (e: React.KeyboardEvent<HTMLDivElement>) => {
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'f' && preview) {
      e.preventDefault();
      searchInputRef.current?.focus();
      searchInputRef.current?.select();
    }
  };

  return (
    <AnimatePresence>
      {open && (
        <motion.aside
          key="sources"
          initial={{ x: 400, opacity: 0 }}
          animate={{ x: 0, opacity: 1 }}
          exit={{ x: 400, opacity: 0 }}
          transition={{ duration: 0.26, ease: [0.16, 1, 0.3, 1] }}
          role="complementary"
          aria-label="pannello fonti"
          onKeyDown={focusSearchShortcut}
          className="fixed right-0 top-0 z-30 flex h-full w-full sm:w-[460px] md:w-[540px] lg:w-[620px] flex-col
                     bg-[var(--color-canvas-raised)] border-l border-[var(--color-border)]
                     shadow-2xl"
        >
          <DrawerHeader count={sources.length} onClose={onClose} />

          <div className="flex-1 flex min-h-0">
            <SourcesList
              sources={filteredSources}
              total={sources.length}
              activeDocId={activeDocId}
              filter={listFilter}
              setFilter={setListFilter}
              onSelect={onSelect}
            />

            <div
              className={cn(
                'flex-1 flex flex-col min-w-0',
                activeDocId ? 'flex' : 'hidden sm:flex'
              )}
            >
              {!activeDocId && <EmptyPreview />}
              {activeDocId && loading && <PreviewSkeleton />}
              {activeDocId && error && (
                <div className="p-4 text-xs text-[var(--color-danger)]" role="alert">
                  {error}
                </div>
              )}
              {activeDocId && preview && !loading && (
                <>
                  <PreviewHeader
                    title={preview.title}
                    docId={preview.docId}
                    source={activeSource}
                    obsidianUri={preview.obsidianUri}
                    onBack={() => onSelect(null, null)}
                  />
                  <PreviewToolbar
                    query={query}
                    setQuery={setQuery}
                    hitCount={hitCount}
                    activeHit={activeHit}
                    onPrevHit={prevHit}
                    onNextHit={nextHit}
                    inputRef={searchInputRef}
                    verbatimCount={verbatims.length}
                    tab={tab}
                    setTab={setTab}
                  />
                  <div
                    ref={previewScrollRef}
                    className="flex-1 overflow-y-auto overflow-x-hidden"
                  >
                    {tab === 'verbatim' && verbatims.length > 0 && (
                      <VerbatimList items={verbatims} focused={focusedVerbatim} />
                    )}
                    {tab === 'content' && (
                      <div ref={previewRef} className="px-4 py-3">
                        <MarkdownPreview body={preview.body} query={query} limit={6000} />
                        {preview.body.length > 6000 && (
                          <p className="mt-3 text-[10px] text-ink-subtle italic">
                            … contenuto troncato ({(preview.body.length / 1024).toFixed(1)} KB
                            totali). Apri in Obsidian per il testo completo.
                          </p>
                        )}
                      </div>
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        </motion.aside>
      )}
    </AnimatePresence>
  );
}
