/**
 * Shared admin page header.
 *
 * One consistent anatomy for every admin tab: an accent icon tile, a title with
 * an optional count pill, an optional subtitle, and a right-aligned actions slot
 * (search, filters, primary buttons). Replaces the per-tab bespoke headers so
 * the whole console reads as one product. Styles live in index.css
 * (`.page-head*`, `.count-pill`, `.admin-search`).
 */

import type { ReactNode } from 'react';

interface PageHeaderProps {
  icon: ReactNode;
  title: string;
  subtitle?: string;
  /** Pre-formatted, localized pill text (e.g. "12 active"). */
  countLabel?: string;
  actions?: ReactNode;
}

const PageHeader = ({ icon, title, subtitle, countLabel, actions }: PageHeaderProps) => (
  <div className="page-head">
    <div className="page-head-titles">
      <span className="page-head-ico">{icon}</span>
      <div>
        <div className="page-head-titlerow">
          <h2 className="page-head-title">{title}</h2>
          {countLabel && <span className="count-pill">{countLabel}</span>}
        </div>
        {subtitle && <p className="page-head-sub">{subtitle}</p>}
      </div>
    </div>
    {actions && <div className="page-head-actions">{actions}</div>}
  </div>
);

export default PageHeader;
