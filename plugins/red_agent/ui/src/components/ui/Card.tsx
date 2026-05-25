import { ReactNode } from 'react';
import { Icon } from './Icon';
import { MenuDivider, MenuItem, Popover } from './Popover';

interface CardProps {
  title?: ReactNode;
  subtitle?: ReactNode;
  action?: ReactNode;
  menu?: boolean;
  children: ReactNode;
  className?: string;
  bodyClassName?: string;
  padded?: boolean;
}

export function Card({
  title,
  subtitle,
  action,
  menu = false,
  children,
  className = '',
  bodyClassName = '',
  padded = true,
}: CardProps) {
  return (
    <section className={`ra-card ${className}`}>
      {(title || action || menu) && (
        <header className="flex items-start justify-between gap-3 border-b border-bg-line/60 px-5 py-3.5">
          <div className="min-w-0">
            {title && (
              <h3 className="font-display text-sm font-medium text-text-primary truncate">
                {title}
              </h3>
            )}
            {subtitle && <p className="mt-0.5 text-xs text-text-muted truncate">{subtitle}</p>}
          </div>
          <div className="flex shrink-0 items-center gap-1">
            {action}
            {menu && (
              <Popover
                width={200}
                trigger={
                  <button
                    type="button"
                    className="grid h-7 w-7 place-items-center rounded text-text-muted transition-colors hover:bg-bg-overlay hover:text-text-primary"
                    title="More"
                    aria-label="More"
                  >
                    <Icon.More size={14} />
                  </button>
                }
              >
                {(close) => (
                  <div className="py-1">
                    <MenuItem
                      icon={<Icon.Refresh size={12} />}
                      label="Refresh"
                      onSelect={() => {
                        close();
                        window.location.reload();
                      }}
                    />
                    <MenuDivider />
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
                  </div>
                )}
              </Popover>
            )}
          </div>
        </header>
      )}
      <div className={`${padded ? 'p-5' : ''} ${bodyClassName}`}>{children}</div>
    </section>
  );
}
