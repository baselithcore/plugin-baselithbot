import type { ReactNode } from 'react';

export type Tone = 'neutral' | 'ok' | 'warn' | 'danger' | 'accent';

export function Card({ title, action, children }: { title?: string; action?: ReactNode; children: ReactNode }) {
  return (
    <section className="card">
      {(title || action) && (
        <header className="card-head">
          {title && <h3>{title}</h3>}
          {action}
        </header>
      )}
      <div className="card-body">{children}</div>
    </section>
  );
}

export function Badge({ tone = 'neutral', children }: { tone?: Tone; children: ReactNode }) {
  return <span className={`badge badge-${tone}`}>{children}</span>;
}

export function Button({
  children,
  onClick,
  variant = 'primary',
  type = 'button',
  disabled,
  small,
}: {
  children: ReactNode;
  onClick?: () => void;
  variant?: 'primary' | 'ghost' | 'danger';
  type?: 'button' | 'submit';
  disabled?: boolean;
  small?: boolean;
}) {
  return (
    <button className={`btn btn-${variant}${small ? ' btn-sm' : ''}`} onClick={onClick} type={type} disabled={disabled}>
      {children}
    </button>
  );
}

export function Field({ label, children }: { label: string; children: ReactNode }) {
  return (
    <label className="field">
      <span className="field-label">{label}</span>
      {children}
    </label>
  );
}

export function Empty({ text }: { text: string }) {
  return <p className="empty">{text}</p>;
}

export function ErrorNote({ text }: { text: string }) {
  return <p className="error-note">{text}</p>;
}

export function Skeleton({ rows = 3 }: { rows?: number }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', gap: 8 }}>
      {Array.from({ length: rows }).map((_, i) => (
        <div key={i} className="skel" style={{ width: `${90 - i * 12}%` }} />
      ))}
    </div>
  );
}

export function Kpi({
  icon,
  value,
  label,
  alert,
}: {
  icon: string;
  value: number | string;
  label: string;
  alert?: boolean;
}) {
  return (
    <div className="kpi">
      <div className="k-top">
        <span className="k-ico">{icon}</span>
      </div>
      <p className={`k-val${alert ? ' alert' : ''}`}>{value}</p>
      <span className="k-label">{label}</span>
    </div>
  );
}
