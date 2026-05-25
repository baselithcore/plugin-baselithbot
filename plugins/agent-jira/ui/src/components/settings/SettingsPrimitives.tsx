import type { ReactNode } from 'react';

type CardProps = {
  title: string;
  description: string;
  icon: ReactNode;
  action?: ReactNode;
  className?: string;
  children: ReactNode;
};

type DetailTileProps = {
  label: string;
  value: ReactNode;
  icon: ReactNode;
  hint?: string;
  action?: ReactNode;
  mono?: boolean;
};

type MetricTileProps = {
  label: string;
  value: string;
  helper: string;
  tone?: 'default' | 'success' | 'warning';
};

export const SectionCard = ({
  title,
  description,
  icon,
  action,
  className,
  children,
}: CardProps) => (
  <section className={`settings-card ${className || ''}`.trim()}>
    <div className="settings-card-head">
      <div className="settings-card-title-wrap">
        <span className="settings-card-icon">{icon}</span>
        <div>
          <h2 className="settings-card-title">{title}</h2>
          <p className="settings-card-description">{description}</p>
        </div>
      </div>
      {action ? <div className="settings-card-action">{action}</div> : null}
    </div>
    {children}
  </section>
);

export const DetailTile = ({ label, value, icon, hint, action, mono = false }: DetailTileProps) => (
  <div className="settings-detail-tile">
    <div className="settings-detail-top">
      <span className="settings-detail-icon">{icon}</span>
      <span className="settings-detail-label">{label}</span>
      {action ? <span className="settings-detail-action">{action}</span> : null}
    </div>
    <div className={`settings-detail-value ${mono ? 'settings-detail-value--mono' : ''}`}>
      {value}
    </div>
    {hint ? <p className="settings-detail-hint">{hint}</p> : null}
  </div>
);

export const MetricTile = ({ label, value, helper, tone = 'default' }: MetricTileProps) => (
  <div className={`settings-metric settings-metric--${tone}`}>
    <span className="settings-metric-label">{label}</span>
    <strong className="settings-metric-value">{value}</strong>
    <span className="settings-metric-helper">{helper}</span>
  </div>
);
