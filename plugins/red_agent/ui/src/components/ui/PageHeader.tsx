import { ReactNode, useState } from 'react';
import { Icon } from './Icon';
import { MenuDivider, MenuItem, Popover } from './Popover';

interface PageHeaderProps {
  title: ReactNode;
  description?: ReactNode;
  breadcrumbs?: { label: string; to?: string }[];
  actions?: ReactNode;
  meta?: ReactNode;
  favorite?: boolean;
  onToggleFavorite?: () => void;
  badge?: { label: string; tone?: 'preview' | 'beta' | 'live' };
  utility?: boolean;
}

const BADGE_TONE = {
  preview: 'bg-bg-overlay text-text-secondary ring-bg-line-strong',
  beta: 'bg-accent-warn/15 text-accent-warn ring-accent-warn/30',
  live: 'bg-status-success/15 text-status-success ring-status-success/30',
};

export function PageHeader({
  title,
  description,
  breadcrumbs,
  actions,
  meta,
  favorite,
  onToggleFavorite,
  badge,
  utility = false,
}: PageHeaderProps) {
  const [internalFav, setInternalFav] = useState(favorite ?? false);
  const fav = favorite ?? internalFav;
  const showFavorite = onToggleFavorite !== undefined || favorite !== undefined;
  function toggle() {
    if (onToggleFavorite) onToggleFavorite();
    else setInternalFav((s) => !s);
  }

  return (
    <div className="mb-6">
      {breadcrumbs && breadcrumbs.length > 0 && (
        <nav className="mb-2 flex items-center gap-1 text-xs text-text-muted">
          {breadcrumbs.map((b, i) => (
            <span key={i} className="flex items-center gap-1">
              {i > 0 && <span className="text-text-subtle">/</span>}
              <span className={i === breadcrumbs.length - 1 ? 'text-text-secondary' : ''}>
                {b.label}
              </span>
            </span>
          ))}
        </nav>
      )}
      <div className="flex flex-wrap items-end justify-between gap-4">
        <div className="min-w-0">
          <div className="flex items-center gap-2">
            {showFavorite && (
              <button
                type="button"
                onClick={toggle}
                aria-label={fav ? 'Unfavorite' : 'Favorite'}
                className={`grid h-7 w-7 shrink-0 place-items-center rounded transition-colors ${
                  fav
                    ? 'text-accent-warn'
                    : 'text-text-muted hover:bg-bg-overlay hover:text-text-secondary'
                }`}
              >
                <Icon.Star size={16} fill={fav ? 'currentColor' : 'none'} />
              </button>
            )}
            <h1 className="font-display text-2xl font-medium text-text-primary tracking-tight">
              {title}
            </h1>
            {badge && (
              <span
                className={`inline-flex items-center gap-1 rounded px-1.5 py-0.5 text-2xs font-mono ring-1 ring-inset ${BADGE_TONE[badge.tone ?? 'preview']}`}
              >
                {badge.label}
              </span>
            )}
          </div>
          {description && (
            <p className={`mt-1 max-w-2xl text-sm text-text-muted ${showFavorite ? 'ml-9' : ''}`}>
              {description}
            </p>
          )}
          {meta && <div className={`mt-2 ${showFavorite ? 'ml-9' : ''}`}>{meta}</div>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {actions}
          {utility && (
            <div className="flex items-center gap-1 border-l border-bg-line pl-2">
              <button
                type="button"
                title="Print"
                onClick={() => window.print()}
                className="grid h-8 w-8 place-items-center rounded text-text-muted transition-colors hover:bg-bg-overlay hover:text-text-primary"
              >
                <Icon.Print size={14} />
              </button>
              <Popover
                width={220}
                trigger={
                  <button
                    type="button"
                    title="More"
                    className="grid h-8 w-8 place-items-center rounded text-text-muted transition-colors hover:bg-bg-overlay hover:text-text-primary"
                  >
                    <Icon.More size={14} />
                  </button>
                }
              >
                {(close) => (
                  <div className="py-1">
                    <MenuItem
                      icon={<Icon.Refresh size={12} />}
                      label="Refresh page"
                      onSelect={() => {
                        close();
                        window.location.reload();
                      }}
                    />
                    <MenuItem
                      icon={<Icon.Download size={12} />}
                      label="Copy link"
                      onSelect={async () => {
                        try {
                          await navigator.clipboard.writeText(window.location.href);
                        } catch {
                          // ignore
                        }
                        close();
                      }}
                    />
                    <MenuDivider />
                    <MenuItem
                      icon={<Icon.Print size={12} />}
                      label="Print"
                      onSelect={() => {
                        close();
                        window.print();
                      }}
                    />
                  </div>
                )}
              </Popover>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
