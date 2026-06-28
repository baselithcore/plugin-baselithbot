/** Hairline-divided KPI strip — restrained typographic metrics, no icon tiles. */

export interface Kpi {
  key: string;
  label: string;
  value: string;
  sub?: string;
  dot?: 'ok' | 'warn' | 'bad';
}

const KpiStrip = ({ items }: { items: Kpi[] }) => (
  <div className="ov-kpis">
    {items.map((k) => (
      <div className="ov-kpi" key={k.key}>
        <span className="ov-kpi-label">
          {k.dot && <i className={`ov-dot ${k.dot}`} aria-hidden="true" />}
          {k.label}
        </span>
        <span className="ov-kpi-value">{k.value}</span>
        {k.sub && <span className="ov-kpi-sub">{k.sub}</span>}
      </div>
    ))}
  </div>
);

export default KpiStrip;
