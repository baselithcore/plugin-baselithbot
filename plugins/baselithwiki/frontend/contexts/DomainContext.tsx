import React, { createContext, useCallback, useContext, useEffect, useMemo, useState } from 'react';

/**
 * Domain Pack metadata served by `GET /api/branding`.
 *
 * The frontend keeps its theme (Tailwind tokens, framer-motion, layout)
 * intact across verticals. Only labels, page-type names, and grouping
 * rules vary — that's what this context exposes.
 *
 * Pairs with `BrandingContext` (theme/colors): the two are intentionally
 * separate so a vertical swap doesn't have to repaint the UI.
 */

export interface PageTypeMeta {
  id: string;
  label: string;
  plural?: string | null;
  folder?: string | null;
}

export interface GroupingRuleMeta {
  key: string;
  label: string;
  page_type: string;
  group_by: string[];
  extra_fields: string[];
}

export interface SuggestedQuestion {
  label: string;
  prompt: string;
  hint?: string;
  category?: string;
  icon?: string | null;
}

export interface UITheme {
  primary?: string | null;
  primary_hover?: string | null;
  accent?: string | null;
}

export interface UILabels {
  app_name: string;
  short_name?: string | null;
  vault_label?: string;
  tagline?: string | null;
  empty_state?: string | null;
  hero_question?: string | null;
  hero_highlight?: string | null;
  hero_pill?: string | null;
  hero_pill_icon?: string | null;
  disclaimer?: string | null;
  suggested_questions?: SuggestedQuestion[];
  theme?: UITheme | null;
  logo_path?: string | null;
  page_type_labels?: Record<string, string>;
  extra?: Record<string, unknown>;
}

export interface DomainBranding {
  domain: string;
  label: string;
  description: string;
  language: string;
  ui: UILabels;
  logo_url?: string | null;
  page_types: PageTypeMeta[];
  subtypes: Record<string, string[]>;
  groups: GroupingRuleMeta[];
  tenant?: { name: string; is_active: boolean };
  vault?: { name: string } | null;
  obsidian?: { enabled: boolean; user_can_open: boolean };
  setup_mode?: boolean;
  setup_error?: string | null;
}

interface DomainContextType {
  branding: DomainBranding | null;
  loading: boolean;
  error: string | null;
  pageTypeLabel: (id: string) => string;
  refresh: () => void;
}

const DEFAULT_BRANDING: DomainBranding = {
  domain: 'unknown',
  label: 'Wiki',
  description: '',
  language: 'it',
  ui: {
    app_name: 'Wiki',
    vault_label: 'Vault',
  },
  page_types: [],
  subtypes: {},
  groups: [],
};

/**
 * Apply tenant theme overrides as CSS custom properties on `<html>`.
 *
 * Wins over the static branding.json palette: the wizard wrote
 * `pack.yaml ui.theme.{primary,primary_hover,accent}` and the user
 * expects those colors EVERYWHERE — including the sidebar bg, which
 * historically came from the static palette only.
 *
 * Variables touched:
 *   --color-brand, --color-brand-strong, --color-brand-soft, --color-brand-ring
 *   --color-accent
 *   --color-sidebar-bg, --color-sidebar-active-bg, --color-sidebar-hover,
 *   --color-sidebar-active-text
 *
 * Passing `null` clears the overrides — used when the active pack has
 * no theme configured so the static defaults take over again.
 */
function applyTenantTheme(
  theme: { primary?: string | null; primary_hover?: string | null; accent?: string | null } | null
): void {
  const root = document.documentElement;
  const cleared = [
    '--color-brand-tenant',
    '--color-accent-tenant',
    '--color-sidebar-bg-tenant',
    '--color-sidebar-active-bg-tenant',
    '--color-sidebar-hover-tenant',
    '--color-sidebar-active-text-tenant',
  ];
  if (!theme || (!theme.primary && !theme.primary_hover && !theme.accent)) {
    for (const v of cleared) root.style.removeProperty(v);
    // also clear forced overrides on actual variables
    root.style.removeProperty('--color-brand');
    root.style.removeProperty('--color-brand-strong');
    root.style.removeProperty('--color-brand-soft');
    root.style.removeProperty('--color-brand-ring');
    root.style.removeProperty('--color-accent');
    root.style.removeProperty('--color-sidebar-bg');
    root.style.removeProperty('--color-sidebar-active-bg');
    root.style.removeProperty('--color-sidebar-hover');
    return;
  }

  const primary = theme.primary || theme.accent || '#003b5c';
  const primaryHover = theme.primary_hover || primary;
  const accent = theme.accent || primary;

  root.style.setProperty('--color-brand', primary);
  root.style.setProperty('--color-brand-strong', primaryHover);
  root.style.setProperty('--color-accent', accent);
  // alpha-tinted variants — `xx1a` is ~10%, `xx33` ~20%, `xx47` ~28%.
  root.style.setProperty('--color-brand-soft', `${primary}1a`);
  root.style.setProperty('--color-brand-ring', `${primary}47`);
  // Sidebar palette: forced when tenant defines a primary so the picker
  // is visible. Otherwise the static branding.json sidebar applies.
  if (theme.primary) {
    root.style.setProperty('--color-sidebar-bg', primary);
    root.style.setProperty('--color-sidebar-active-bg', `${primary}33`);
    root.style.setProperty('--color-sidebar-hover', `${primary}1a`);
    root.style.setProperty('--color-sidebar-active-text', '#ffffff');
  }
}

const DomainContext = createContext<DomainContextType>({
  branding: null,
  loading: true,
  error: null,
  pageTypeLabel: (id) => id,
  refresh: () => {},
});

export const useDomain = () => useContext(DomainContext);

export const DomainProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [branding, setBranding] = useState<DomainBranding | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [reloadCounter, setReloadCounter] = useState(0);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    fetch('/api/branding')
      .then(async (res) => {
        if (!res.ok) {
          throw new Error(`HTTP ${res.status}`);
        }
        return (await res.json()) as DomainBranding;
      })
      .then((data) => {
        if (cancelled) return;
        setBranding(data);
        if (data.ui?.app_name) {
          document.title = data.ui.app_name;
        }
        const theme = data.ui?.theme ?? null;
        applyTenantTheme(theme);
        // Re-apply on dark/light toggle: BrandingContext re-applies the
        // static palette when <html> class changes, which would otherwise
        // wipe our overrides.
        const rootEl = document.documentElement;
        const reapply = () => applyTenantTheme(theme);
        const obs = new MutationObserver((muts) => {
          for (const m of muts) {
            if (m.type === 'attributes' && m.attributeName === 'class') reapply();
          }
        });
        obs.observe(rootEl, { attributes: true, attributeFilter: ['class'] });
        // Tag for cleanup if branding refetches.
        if ((rootEl as unknown as { __wikiThemeObs?: MutationObserver }).__wikiThemeObs) {
          (rootEl as unknown as { __wikiThemeObs?: MutationObserver }).__wikiThemeObs!.disconnect();
        }
        (rootEl as unknown as { __wikiThemeObs?: MutationObserver }).__wikiThemeObs = obs;
      })
      .catch((err: Error) => {
        if (cancelled) return;
        console.error('[DomainContext] failed to load /api/branding:', err);
        setError(err.message);
        setBranding(DEFAULT_BRANDING);
      })
      .finally(() => {
        if (!cancelled) setLoading(false);
      });

    return () => {
      cancelled = true;
    };
  }, [reloadCounter]);

  const pageTypeLabelMap = useMemo(() => {
    const map = new Map<string, string>();
    if (branding) {
      for (const pt of branding.page_types) {
        map.set(pt.id, pt.label);
      }
      const overrides = branding.ui?.page_type_labels ?? {};
      for (const [id, label] of Object.entries(overrides)) {
        map.set(id, label);
      }
    }
    return map;
  }, [branding]);

  const pageTypeLabel = useMemo(
    () => (id: string) => pageTypeLabelMap.get(id) ?? id,
    [pageTypeLabelMap]
  );

  const refresh = useCallback(() => setReloadCounter((n) => n + 1), []);

  const value = useMemo<DomainContextType>(
    () => ({ branding, loading, error, pageTypeLabel, refresh }),
    [branding, loading, error, pageTypeLabel, refresh]
  );

  return <DomainContext.Provider value={value}>{children}</DomainContext.Provider>;
};
