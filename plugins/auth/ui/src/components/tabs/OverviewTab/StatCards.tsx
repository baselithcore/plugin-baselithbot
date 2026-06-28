/** KPI stat-card row for the Overview dashboard. */

import type { LucideIcon } from 'lucide-react';

export interface Stat {
  key: string;
  icon: LucideIcon;
  label: string;
  value: string;
  hint?: string;
  tone?: 'accent' | 'success' | 'warning' | 'danger';
}

const StatCards = ({ stats }: { stats: Stat[] }) => (
  <div className="ov-stats">
    {stats.map((s) => {
      const Icon = s.icon;
      return (
        <div className={`ov-stat ${s.tone ? `tone-${s.tone}` : ''}`} key={s.key}>
          <span className="ov-stat-ico">
            <Icon size={18} aria-hidden="true" />
          </span>
          <div className="ov-stat-body">
            <span className="ov-stat-value">{s.value}</span>
            <span className="ov-stat-label">{s.label}</span>
            {s.hint && <span className="ov-stat-hint">{s.hint}</span>}
          </div>
        </div>
      );
    })}
  </div>
);

export default StatCards;
